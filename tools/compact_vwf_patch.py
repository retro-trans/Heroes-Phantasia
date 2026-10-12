"""Dry .14 memory recovery: retain native resident pixels, remove duplicate bank.

No executable writer. All changes are relocation-backed and reported individually.
"""
import hashlib, json, struct
from pathlib import Path
from build_menu_patch import START, align

SOURCE = Path('work/output/0.1.13-dialogue-assets/EBOOT.BIN')
SHA = '4cb5fb279a080e5dfd97e74b0da1c2e2fdf8b8f61fb28f2402f03c33a5917d67'

def loaded(data,base):
    """Separate REL1 loader model, preserving next-LO and signed-low carry."""
    ph=[struct.unpack_from('<8I',data,52+n*32) for n in range(4)]
    rs=list(struct.iter_unpack('<II',data[ph[3][1]:ph[3][1]+ph[3][4]]))
    raw=[data[p[1]:p[1]+p[4]] for p in ph[:3]];segs=list(map(bytearray,raw))
    bases=[base+p[2] for p in ph[:3]];nextlo=[None]*len(rs);q=None
    for n in range(len(rs)-1,-1,-1):
        nextlo[n]=q
        if rs[n][1]&255==6:q=n
    for n,(off,f) in enumerate(rs):
        typ=f&255;s=f>>8&255;t=f>>16&255;v=struct.unpack_from('<I',raw[s],off)[0];b=bases[t]
        if typ==2:w=(v+b)&0xffffffff
        elif typ==4:w=(v&0xfc000000)|((((v&0x3ffffff)*4+b)>>2)&0x3ffffff)
        elif typ==6:w=(v&0xffff0000)|((v+b)&65535)
        elif typ==5:
            oo,ff=rs[nextlo[n]];z=struct.unpack_from('<I',raw[ff>>8&255],oo)[0]
            a=((v&65535)<<16)+struct.unpack('<h',struct.pack('<H',z&65535))[0]
            w=(v&0xffff0000)|(((a+b+0x8000)>>16)&65535)
        else:raise ValueError('Unexpected REL1 type')
        struct.pack_into('<I',segs[s],off,w)
    return segs,rs,nextlo

def check_loaded(before,after,low_end,removed_bytes,removed_records):
    count=0
    for base in (0x8804000,0x8900000,0x8fff000):
        old,records,lows=loaded(before,base);new,_,_=loaded(after,base)
        for z,(off,f) in enumerate(records):
            if (off,f) in removed_records:continue
            s=f>>8&255;typ=f&255;no=off-removed_bytes if s==2 and off>=low_end else off
            ow=struct.unpack_from('<I',old[s],off)[0];nw=struct.unpack_from('<I',new[s],no)[0]
            if typ==2:x,y=ow,nw
            elif typ==4:x,y=(ow&0x3ffffff)*4,(nw&0x3ffffff)*4
            elif typ==5:
                oo,ff=records[lows[z]];ss=ff>>8&255
                nn=oo-removed_bytes if ss==2 and oo>=low_end else oo
                ol=struct.unpack_from('<I',old[ss],oo)[0];nl=struct.unpack_from('<I',new[ss],nn)[0]
                x=((ow&65535)<<16)+struct.unpack('<h',struct.pack('<H',ol&65535))[0]
                y=((nw&65535)<<16)+struct.unpack('<h',struct.pack('<H',nl&65535))[0]
            else:continue
            old_size=struct.unpack_from('<I',before,52+2*32+16)[0]
            expected=x-removed_bytes if base+START+low_end<=x<base+START+old_size else x
            if y!=expected:raise ValueError(f'Loaded target mismatch {off:x}/{typ}/{base:x}')
            count+=1
    return dict(load_bases=['0x8804000','0x8900000','0x8fff000'],pointer_comparisons=count,passed=True)

def build():
    original = SOURCE.read_bytes()
    if hashlib.sha256(original).hexdigest() != SHA:
        raise ValueError('Frozen .13 input changed')
    report = json.loads(SOURCE.with_name('setup_patch.en.json').read_text())
    phoff, shoff = struct.unpack_from('<II', original, 28)
    ph = [list(struct.unpack_from('<8I', original, phoff+n*32)) for n in range(4)]
    sections = [list(struct.unpack_from('<10I', original, shoff+n*40))
                for n in range(struct.unpack_from('<H', original, 48)[0])]
    payload = original[ph[2][1]:ph[2][1]+ph[2][4]]
    records = list(struct.iter_unpack('<II', original[ph[3][1]:ph[3][1]+ph[3][4]]))
    def read(off, flags):
        return struct.unpack_from('<I', original, ph[(flags>>8)&255][1]+off)[0]
    # Checked initializer's LUI/ADDIU/SW pixel-pointer overwrite, not EA204.
    hi, lo, store = struct.unpack_from('<3I', payload, 0x538)
    if hi != 0x3c090170 or lo != 0x2529b490 or store != 0xad090008:
        raise ValueError('Unexpected original initializer pixel overwrite')
    low_start = ((hi&65535)<<16)+struct.unpack('<h', struct.pack('<H', lo&65535))[0]-START
    low_bytes = 326*384
    low_end = low_start+low_bytes
    if low_end != 24223120-START:
        raise ValueError('Low bank must end at verified high bank')
    # The embedded native pixels exactly match the persistent resident asset.
    assets = list(Path('work/source/cpk').rglob('ALLResidentNML*'))
    if len(assets) != 1: raise ValueError('Resident asset ambiguous')
    native = assets[0].read_bytes()
    native_pixels = native[0x658b0+17*384:0x658b0+247*384]
    if payload[low_start:low_start+230*384] != native_pixels:
        raise ValueError('Duplicated native pixels differ')
    table_hi, table_lo = struct.unpack_from('<2I', payload, 0x52c)
    table = (((table_hi&65535)<<16)+struct.unpack('<h', struct.pack('<H', table_lo&65535))[0])-START
    charset = native[0x7ccb0:0x7ce80].split(b'\0',1)[0].decode('cp932')
    actual = [struct.unpack_from('<Iff', payload, table+n*12) for n in range(326)]
    native_entries = sorted((int.from_bytes(c.encode('cp932'),'big'),float(n),-1.0)
                            for n,c in enumerate(charset))
    if [r for r in actual if r[0]>=0x8140] != native_entries:
        raise ValueError('Native table slot identities changed')
    latin = [r[0] for r in actual if r[0]<0x8140]
    if latin != list(range(32,127))+[128]:
        raise ValueError('Unsupported Latin entries require native pixel storage')
    def mapped(a):
        if START+low_start <= a < START+low_end:
            raise ValueError(f'Remaining reference to removed pixels {a:x}')
        return a-low_bytes if START+low_end <= a < START+len(payload) else a
    new_payload = bytearray(payload[:low_start]+payload[low_end:])
    new_payload[0x538:0x544] = bytes(12)
    patch = bytearray(original)
    fixes=[]
    def write(off, flags, value, old_value, kind):
        seg=(flags>>8)&255
        new_off=off-low_bytes if seg==2 and off>=low_end else off
        if seg==2:
            if low_start<=off<low_end:raise ValueError('Relocation inside removed pixel data')
            struct.pack_into('<I',new_payload,new_off,value)
        else:struct.pack_into('<I',patch,ph[seg][1]+off,value)
        if value!=old_value:
            fixes.append(dict(segment=seg,old_offset=hex(off),new_offset=hex(new_off),
                              kind=kind,old_word=hex(old_value),new_word=hex(value)))
    removed={(0x538,0x205),(0x53c,0x206)}
    if not removed.issubset(set(records)):raise ValueError('Pixel-pointer relocations absent')
    skip=set();new_records=[];semantic=[]
    for index,(off,flags) in enumerate(records):
        if (off,flags) in removed:continue
        seg=(flags>>8)&255;typ=flags&255;target=(flags>>16)&255
        if target not in (0,1):raise ValueError('Unexpected target segment')
        new_off=off-low_bytes if seg==2 and off>=low_end else off
        if seg==2 and low_start<=off<low_end:raise ValueError('Pixel bytes carry relocation')
        new_records.append((new_off,flags))
        if index in skip:continue
        w=read(off,flags)
        if typ==2:
            a=w;new=mapped(a) if target==0 else a
            write(off,flags,new,w,'R32')
        elif typ==4:
            a=(w&0x3ffffff)*4;new=mapped(a) if target==0 else a
            write(off,flags,(w&0xfc000000)|(new>>2),w,'R26')
        elif typ==5:
            # Only payload-targeting pairs change. Original multi-HI ordering
            # remains intact; every changed pair must be adjacent and same base.
            q=next(n for n in range(index+1,len(records)) if records[n][1]&255==6)
            oo,ff=records[q];lw=read(oo,ff)
            a=((w&65535)<<16)+struct.unpack('<h',struct.pack('<H',lw&65535))[0]
            new=mapped(a) if target==0 else a
            if new!=a:
                if q!=index+1 or ((ff>>16)&255)!=target:raise ValueError('Nonadjacent changed HI/LO')
                write(off,flags,(w&0xffff0000)|(((new+0x8000)>>16)&65535),w,'HI16')
                write(oo,ff,(lw&0xffff0000)|(new&65535),lw,'LO16')
                skip.add(q)
        elif typ==6:continue
        else:raise ValueError('Unexpected relocation type')
        if new!=a:
            semantic.append(dict(site_segment=seg,site_offset=hex(off),type=typ,
                                 old_address=hex(a),new_address=hex(new),delta=new-a,
                                 load_bases_verified=[hex(x) for x in (0x8804000,0x8900000,0x8fff000)]))
            for base in (0x8804000,0x8900000,0x8fff000):
                if typ==5:
                    nw=(new+0x8000)>>16;nl=struct.unpack('<h',struct.pack('<H',new&65535))[0]
                    assert ((nw<<16)+nl+base)==new+base
                else:assert new+base==mapped(a)+base
    rel=b''.join(struct.pack('<II',*r) for r in new_records)
    assert len(set(new_records))==len(new_records)
    # Preserve original nonloaded metadata/sections; remove accumulated appended
    # file copies by keeping the original-file prefix before the first candidate.
    prefix_end=0x508880
    patch=patch[:prefix_end]
    payload_file=align(len(patch),64);patch.extend(bytes(payload_file-len(patch)));patch.extend(new_payload)
    rel_file=align(len(patch),16);patch.extend(bytes(rel_file-len(patch)));patch.extend(rel)
    payload_section=next(n for n,s in enumerate(sections) if s[3]==START and s[4]==ph[2][1])
    # Retain original ten section boundaries; one compact appended relocation section.
    kept=0
    for s in sections:
        if s[1]==0x700000a0:
            if s[4]<ph[3][1]+71807*8:
                s[4]=rel_file+kept;s[7]=s[7];kept+=s[5]
            else:s[4]=rel_file+kept;s[5]=0
        elif s[3]==START and s[4]==ph[2][1]:s[4]=payload_file;s[5]=len(new_payload)
        elif s[1]!=8 and s[5] and s[4]+s[5]>prefix_end:
            raise ValueError('Nonpayload section extends past preserved prefix')
    if kept!=71807*8:raise ValueError('Original relocation section partition changed')
    sections.append([0,0x700000a0,0,0,rel_file+kept,len(rel)-kept,0,payload_section,4,8])
    newsh=align(len(patch),4);patch.extend(bytes(newsh-len(patch)))
    for s in sections:patch.extend(struct.pack('<10I',*s))
    ph[2][1]=payload_file;ph[2][4]=ph[2][5]=len(new_payload)
    ph[3][1]=rel_file;ph[3][4]=len(rel)
    for n,p in enumerate(ph):struct.pack_into('<8I',patch,phoff+32*n,*p)
    struct.pack_into('<I',patch,32,newsh);struct.pack_into('<H',patch,48,len(sections))
    # Arbitrary report pointer values need the identical mapping, not stale addresses.
    def metadata(v):
        if isinstance(v,dict):return {k:metadata(x) for k,x in v.items()}
        if isinstance(v,list):return [metadata(x) for x in v]
        if isinstance(v,str) and v.startswith('0x'):
            # Active addresses into removed storage must fail, not remain stale.
            try:a=int(v,16)
            except ValueError:return v
            return hex(mapped(a))
        return v
    report=metadata(report)
    stale=('old_payload_preserved','old_relocations_preserved','inherited_payload_preserved',
           'relocation_prefix_unchanged','old_payload_sha256','old_relocations_sha256',
           'inherited_payload_sha256','inherited_relocation_table_sha256',
           'relocation_table_sha256','payload_growth','inherited_added_relocations')
    historical={k:report.pop(k) for k in stale if k in report}
    report['historical_build_proofs']=dict(scope='Input .13 build history only; not compact-output preservation proofs.',values=historical)
    report.update(version='0.1.14',input_version='0.1.13',input_sha256=SHA,
                  output_sha256=hashlib.sha256(patch).hexdigest(),output_elf_sha256=hashlib.sha256(patch).hexdigest(),
                  elf_bytes=len(patch),payload_bytes=len(new_payload),module_growth_bytes=len(new_payload),
                  runtime_verified=False,status='compact_native_pixels_dry_candidate',
                  total_relocations=len(new_records),added_relocations=0)
    font=json.loads(Path('work/output/0.1.6-opening-vwf-4x-candidate/manifest.en.json').read_text())
    report.update(high_bank=mapped(font['high_bank']),high_bank_bytes=font['high_bank_bytes'],
                  high_glyph_count=font['high_glyph_count'],high_codes=font['high_codes'],
                  high_glyph_offsets=font['high_glyph_offsets'],high_lookup_entry_bytes=2,
                  high_lookup_unit=256,relocation_table_sha256=hashlib.sha256(rel).hexdigest(),
                  payload_growth=-low_bytes,old_payload_preserved=False,
                  old_relocations_preserved=False,relocation_prefix_unchanged=False)
    snapshot=b''.join(struct.pack('<Iff',int.from_bytes(c.encode('cp932'),'big'),float(n),-1.)
                      for n,c in enumerate(charset))+native_pixels
    report.update(font_input_sha256=hashlib.sha256(snapshot).hexdigest(),
                  font_asset_sha256=hashlib.sha256(native).hexdigest(),
                  high_bank_sha256=hashlib.sha256(payload[low_end:low_end+188928]).hexdigest(),
                  original_relocations=71807)
    report['memory_compaction']=dict(removed_bytes=low_bytes,old_payload_bytes=len(payload),
        new_payload_bytes=len(new_payload),bytes_below_012=335072-len(new_payload),
        removed_range=[hex(START+low_start),hex(START+low_end)],
        initializer_nopped_rvas=['0x16fa038','0x16fa03c','0x16fa040'],
        initializer_expected_words=[hex(hi),hex(lo),hex(store)],native_pixel_pointer_retained=True,
        native_glyph_records_verified=len(native_entries),latin_high_glyphs_verified=len(latin),
        native_pixel_sha256=hashlib.sha256(native_pixels).hexdigest(),
        high_bank_sha256=hashlib.sha256(payload[low_end:low_end+188928]).hexdigest(),
        high_bank_bytes_preserved=new_payload[low_start:low_start+188928]==payload[low_end:low_end+188928],
        removed_relocations=[[hex(a),hex(f)] for a,f in sorted(removed)],
        address_changes=semantic,word_changes=fixes,runtime_verified=False)
    report['memory_compaction']['loaded_relocation_model']=check_loaded(original,bytes(patch),low_end,low_bytes,removed)
    return bytes(patch),report

if __name__=='__main__':
    data,report=build()
    print(json.dumps(report,indent=2))
    print('DRY RUN: no executable or report written.')
