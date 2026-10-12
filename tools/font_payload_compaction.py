"""Dry relocation-backed replacement of one loaded payload range.

This primitive has no writer. References into removed data reject unless their
whole referring instruction block is explicitly replaced by the caller. Every
other inherited relocation is compared after simulated loading at three bases.
"""
import hashlib,struct
from build_menu_patch import START,align
from compact_vwf_patch import loaded


def replace_range(original,start,size,replacement,replaced_code_ranges=()):
    phoff,shoff=struct.unpack_from('<II',original,28)
    ph=[list(struct.unpack_from('<8I',original,phoff+n*32))for n in range(4)]
    sections=[list(struct.unpack_from('<10I',original,shoff+n*40))for n in range(struct.unpack_from('<H',original,48)[0])]
    if ph[2][2]!=START or start%16 or size%16 or len(replacement)%16:raise ValueError('Unaligned payload range')
    prefix=original[:0x508880];old=original[ph[2][1]:ph[2][1]+ph[2][4]]
    if not 0<=start<start+size<=len(old):raise ValueError('Range outside loaded payload')
    end=start+size;delta=len(replacement)-size
    payload=bytearray(old[:start]+replacement+old[end:]);patch=bytearray(prefix)
    records=list(struct.iter_unpack('<II',original[ph[3][1]:ph[3][1]+ph[3][4]]))
    removed=[];newrecords=[];changed=[];skip=set()
    def mapped(address):
        if START+start<=address<START+end:raise ValueError(f'Active reference into removed bank0x{address:x}')
        return address+delta if START+end<=address<START+len(old) else address
    def site(off,flags):
        seg=flags>>8&255
        if seg==2 and start<=off<end:raise ValueError('Relocation inside removed font pixels')
        return off+delta if seg==2 and off>=end else off
    def read(off,flags):return struct.unpack_from('<I',original,ph[flags>>8&255][1]+off)[0]
    def put(off,flags,value):
        seg=flags>>8&255;where=site(off,flags)
        if seg==2:struct.pack_into('<I',payload,where,value)
        else:struct.pack_into('<I',patch,ph[seg][1]+where,value)
    for n,(off,flags)in enumerate(records):
        seg=flags>>8&255;typ=flags&255;target=flags>>16&255
        if target not in (0,1):raise ValueError('Unsupported inherited target segment')
        if seg==2 and any(a<=off<b for a,b in replaced_code_ranges):removed.append((off,flags));continue
        newrecords.append((site(off,flags),flags))
        if n in skip:continue
        w=read(off,flags)
        if typ==2:a=w
        elif typ==4:a=(w&0x3ffffff)*4
        elif typ==5:
            q=next(k for k in range(n+1,len(records))if records[k][1]&255==6)
            oo,ff=records[q];lo=read(oo,ff)
            a=((w&65535)<<16)+struct.unpack('<h',struct.pack('<H',lo&65535))[0]
        elif typ==6:continue
        else:raise ValueError('Unknown inherited relocation')
        new=mapped(a) if target==0 else a
        if new!=a:
            if typ==2:put(off,flags,new)
            elif typ==4:put(off,flags,(w&0xfc000000)|(new>>2))
            else:
                if q!=n+1 or ff>>16&255!=target:raise ValueError('Changed nonadjacent HI/LO')
                put(off,flags,(w&0xffff0000)|((new+0x8000)>>16&65535))
                put(oo,ff,(lo&0xffff0000)|(new&65535));skip.add(q)
            changed.append(dict(segment=seg,old_offset=off,new_offset=site(off,flags),type=typ,old_rva=a,new_rva=new))
    rel=b''.join(struct.pack('<II',*r)for r in newrecords)
    payloadfile=align(len(patch),64);patch.extend(bytes(payloadfile-len(patch)));patch.extend(payload)
    relfile=align(len(patch),16);patch.extend(bytes(relfile-len(patch)));patch.extend(rel)
    payloadsection=next(n for n,s in enumerate(sections)if s[3]==START and s[4]==ph[2][1])
    kept=0
    for s in sections:
        if s[1]==0x700000a0:
            if s[4]<ph[3][1]+71807*8:s[4]=relfile+kept;kept+=s[5]
            else:s[4]=relfile+kept;s[5]=0
        elif s[3]==START and s[4]==ph[2][1]:s[4]=payloadfile;s[5]=len(payload)
        elif s[1]!=8 and s[5] and s[4]+s[5]>len(prefix):raise ValueError('Unexpected nonpayload appended section')
    if kept!=71807*8:raise ValueError('Native relocation partition changed')
    sections.append([0,0x700000a0,0,0,relfile+kept,len(rel)-kept,0,payloadsection,4,8])
    newsh=align(len(patch),4);patch.extend(bytes(newsh-len(patch)))
    for s in sections:patch.extend(struct.pack('<10I',*s))
    ph[2][1]=payloadfile;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=relfile;ph[3][4]=len(rel)
    for n,p in enumerate(ph):struct.pack_into('<8I',patch,phoff+32*n,*p)
    struct.pack_into('<I',patch,32,newsh);struct.pack_into('<H',patch,48,len(sections))
    comparisons=0
    for base in (0x8804000,0x8900000,0x8fff000):
        olds,_,nextlo=loaded(original,base);news,_,_=loaded(patch,base)
        for n,(off,flags)in enumerate(records):
            if (off,flags)in removed:continue
            seg=flags>>8&255;typ=flags&255;ow=struct.unpack_from('<I',olds[seg],off)[0]
            nw=struct.unpack_from('<I',news[seg],site(off,flags))[0]
            if typ==2:x,y=ow,nw
            elif typ==4:x,y=(ow&0x3ffffff)*4,(nw&0x3ffffff)*4
            elif typ==5:
                oo,ff=records[nextlo[n]];ss=ff>>8&255
                ol=struct.unpack_from('<I',olds[ss],oo)[0];nl=struct.unpack_from('<I',news[ss],site(oo,ff))[0]
                x=((ow&65535)<<16)+struct.unpack('<h',struct.pack('<H',ol&65535))[0]
                y=((nw&65535)<<16)+struct.unpack('<h',struct.pack('<H',nl&65535))[0]
            else:continue
            if base+START+start<=x<base+START+end:raise ValueError('Loaded active bank reference remains')
            expected=x+delta if base+START+end<=x<base+START+len(old)else x
            if y!=expected:raise ValueError(f'Loaded relocation mismatch{off:x}/{typ}')
            comparisons+=1
    return bytes(patch),dict(old_range=[START+start,START+end],old_bytes=size,new_bytes=len(replacement),delta=delta,
                            removed_relocations=removed,address_changes=changed,loaded_pointer_comparisons=comparisons,
                            loaded_bases=[0x8804000,0x8900000,0x8fff000],loaded_model_passed=True,
                            old_payload_preserved=False,old_relocations_preserved=False,no_assets_written=True)
