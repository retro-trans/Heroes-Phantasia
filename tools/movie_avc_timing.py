"""Pure guarded AVC SPS-VUI/per-AU SEI transplant for fixed-size mux experiments."""
import hashlib
import re

START=re.compile(b'\x00\x00\x01')

def nals(data):
    matches=list(START.finditer(data));result=[]
    for i,m in enumerate(matches):
        start=m.start()-int(m.start()>0 and data[m.start()-1]==0)
        end=len(data) if i+1==len(matches) else matches[i+1].start()-int(data[matches[i+1].start()-1]==0)
        result.append((data[m.end()]&31,data[start:end],data[m.end():end].rstrip(b'\0')))
    return result

def rbsp(payload):
    return re.sub(b'\0\0\x03',b'\0\0',payload)

def ebsp(payload):
    out=bytearray();zeros=0
    for value in payload:
        if zeros>=2 and value<=3:out.append(3);zeros=0
        out.append(value);zeros=zeros+1 if value==0 else 0
    return bytes(out)

class Bits:
    def __init__(self,data):self.bits=''.join(f'{x:08b}' for x in data);self.pos=0
    def get(self,count):
        assert self.pos+count<=len(self.bits)
        value=int(self.bits[self.pos:self.pos+count] or '0',2);self.pos+=count;return value
    def ue(self):
        zeros=0
        while self.get(1)==0:
            zeros+=1;assert zeros<32
        return (1<<zeros)-1+self.get(zeros)

def sps(payload):
    assert payload[0]&31==7
    reader=Bits(rbsp(payload[1:]));profile=reader.get(8);constraints=reader.get(8);level=reader.get(8);sid=reader.ue()
    assert profile in (66,77) and level==21 and sid==0,'Only bounded Baseline/Main2.1/SPS0 supported'
    log_frame=reader.ue();poc=reader.ue();assert poc==2,'No reordered-picture timing supported'
    refs=reader.ue();assert refs==1
    gap=reader.get(1);width=reader.ue();height=reader.ue();frame_only=reader.get(1);assert frame_only==1
    direct=reader.get(1);crop=[]
    if reader.get(1):crop=[reader.ue() for _ in range(4)]
    assert (width+1)*16==480 and (height+1)*16==272 and not any(crop)
    vui_start=reader.pos;assert reader.get(1)==1,'VUI must exist'
    stop=reader.bits.rfind('1')+1;assert stop>reader.pos
    return reader.bits[:vui_start],reader.bits[vui_start:stop],dict(profile=profile,level=level,sps_id=sid,
        max_num_ref_frames=refs,pic_order_cnt_type=poc,frame_mbs_only=frame_only,width=480,height=272,
        log2_max_frame_num_minus4=log_frame,constraints_byte=constraints,gaps_allowed=gap,direct_8x8=direct)

def timing_lengths(vui):
    r=Bits(b'');r.bits=vui
    assert r.get(1)==1
    if r.get(1):
        if r.get(8)==255:r.get(16);r.get(16)
    if r.get(1):r.get(1)
    if r.get(1):
        r.get(3);r.get(1)
        if r.get(1):r.get(24)
    if r.get(1):r.ue();r.ue()
    if r.get(1):r.get(32);r.get(32);r.get(1)
    values=[]
    for _ in range(2):
        if r.get(1):
            count=r.ue()+1;r.get(4);r.get(4)
            for _ in range(count):r.ue();r.ue();r.get(1)
            r.get(5);remove=r.get(5)+1;output=r.get(5)+1;r.get(5)
            values.append((remove,output))
    assert values and all(x==values[0] for x in values)
    r.get(1);assert r.get(1)==1,'Require native pic_struct_present'
    return values[0]

def omit_optional_clock(raw,payload,lengths):
    body=rbsp(payload[1:]);pos=0;messages=bytearray();changed=0
    while pos<len(body) and body[pos]!=128:
        kind=0
        while body[pos]==255:kind+=255;pos+=1
        kind+=body[pos];pos+=1;size=0
        while body[pos]==255:size+=255;pos+=1
        size+=body[pos];pos+=1;value=body[pos:pos+size];assert len(value)==size;pos+=size
        if kind==1:
            bits=Bits(value).bits;stop=sum(lengths)+4
            assert int(bits[sum(lengths):stop],2)==0,'Only progressive pic_struct0 supported'
            assert lengths==(8,6) and len(value)==8 and bits[stop]=='1','Require exact native optional-clock syntax'
            # HRD delay fields and pic_struct preserved; optional clock flag false.
            minimal=bits[:stop]+'0'+'1';minimal+='0'*(-len(minimal)%8)
            value=bytes(int(minimal[i:i+8],2) for i in range(0,len(minimal),8));changed+=1
            assert len(value)==3 and Bits(value).bits[:stop]==bits[:stop]
        messages.extend(b'\xff'*(kind//255)+bytes([kind%255]))
        messages.extend(b'\xff'*(len(value)//255)+bytes([len(value)%255]));messages.extend(value)
    assert body[pos:]==b'\x80'
    if not changed:return raw,0
    return b'\0\0\0\1'+payload[:1]+ebsp(bytes(messages)+b'\x80'),changed

def transplant(original_video,replacement_video,original_units,replacement_units,compact_clock=False):
    assert len(original_units)==len(replacement_units)
    first_native=[payload for kind,raw,payload in nals(original_video[:original_units[0]['end']]) if kind==7]
    assert len(first_native)==1
    _,native_vui,native_fields=sps(first_native[0]);out=bytearray();sps_count=sei_count=clock_count=0
    lengths=timing_lengths(native_vui)
    all_fields=[];sei_hash=hashlib.sha256()
    for old,new in zip(original_units,replacement_units):
        assert old['idr']==new['idr']
        original=nals(original_video[old['start']:old['end']]);replacement=nals(replacement_video[new['start']:new['end']])
        native_sei=[]
        for kind,raw,payload in original:
            if kind==6:
                if compact_clock:
                    raw,count=omit_optional_clock(raw,payload,lengths);clock_count+=count
                native_sei.append(raw)
        assert replacement[0][0]==9
        seen_vcl=False
        for kind,raw,payload in replacement:
            if kind==6:continue # Encoder metadata/timing belongs to another mux model.
            if kind in (1,5) and not seen_vcl:
                for sei in native_sei:out.extend(sei);sei_hash.update(sei);sei_count+=1
                seen_vcl=True
            if kind==7:
                core,_,fields=sps(payload);all_fields.append(fields)
                bits=core+native_vui;bits+='0'*(-len(bits)%8)
                new_rbsp=bytes(int(bits[i:i+8],2) for i in range(0,len(bits),8))
                raw=b'\0\0\0\1'+payload[:1]+ebsp(new_rbsp)
                _,verified_vui,verified_fields=sps(payload[:1]+ebsp(new_rbsp))
                assert verified_vui==native_vui and verified_fields==fields;sps_count+=1
            out.extend(raw)
        assert seen_vcl
    return bytes(out),dict(status='static_timing_transplant_psp_runtime_unverified',native_sps=native_fields,
        new_sps_core_variants=all_fields[:1],rewritten_sps_count=sps_count,retained_native_sei_count=sei_count,
        retained_native_sei_sha256=sei_hash.hexdigest(),native_vui_bits=len(native_vui),
        compact_clock_optional=compact_clock,optional_clock_timestamp_fields_omitted=clock_count,
        picture_timing_payload_bytes_removed_per_frame=5 if compact_clock else 0,
        pic_struct_and_both_hrd_delay_bits_exact=True,
        all_original_sei_byte_exact=not compact_clock,hrd_delay_fields_preserved=True,
        native_vui_bits_sha256=hashlib.sha256(native_vui.encode()).hexdigest(),
        sources=['https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavcodec/h264_ps.c',
                 'https://www.itu.int/rec/T-REC-H.264-202408-I/en'],
        caveats=['Requires every AU padded to its original byte size and every original non-video packet unchanged.',
                 'Different SPS core constraints/frame_num coding are retained from the actual encoder, not replaced by original core.',
                 'Native PSP media-engine decode, buffer behavior and visual QA are still required.'])
