"""Build a relocated, cold-boot menu VWF candidate; inspect-only by default.

Reconstructs the resident font from extracted assets, verified against a live snapshot.
Appends a dedicated PRX load segment and rebuilds both relocation views.
--write emits only versioned local outputs; the original ISO remains read-only.
"""
import argparse,hashlib,json,pathlib,shutil,struct
from live_vwf import ELF,SHA,make_payload,decoder_hook,width_hook,high_hooks,j,jal,i,words

ROOT=pathlib.Path('work/output/0.1.0-menu-vwf-4x-candidate')
SOURCE_SHA='4cd58941d49d3c1d4f2bc433de0035d89bbd81f79a48bfdb79d6a79d2793c6bf'
ISO=pathlib.Path('Heroes Phantasia (Japan).iso')
START=0x16f9b00
def align(n,a):return (n+a-1)//a*a
def reloc(off,typ,segment=2):return struct.pack('<II',off,typ|(segment<<8))

class FontInput:
    def __init__(self,data):self.data=data
    def read(self,addr,n):
        if addr==0:return words([230,0x1000,0x10000])
        if 0x1000<=addr<0x1000+2760:return self.data[addr-0x1000:addr-0x1000+n]
        if addr==0x10000:return self.data[2760:2760+n]
        raise ValueError('Unexpected font snapshot address')

def init_hook(table,pixels):
    code=[i(9,29,29,-32),i(43,29,31,28),i(43,29,4,24),jal(0xea204),0,
        i(43,29,8,0),i(43,29,9,4),i(35,29,8,24),i(35,8,8,4),i(13,0,9,325),i(43,8,9,0)]
    for address,offset in ((table,4),(pixels,8)):
        code.extend([i(15,0,9,address>>16),i(13,9,9,address),i(43,8,9,offset)])
    code.extend([i(35,29,8,0),i(35,29,9,4),i(35,29,31,28),0x03e00008,i(9,29,29,32)])
    return words(code)

def relocate_code(payload,offset,size):
    """Mark absolute instructions; signed HI/ADDIU pairs survive load-base carry."""
    additions=[];pos=offset
    while pos<offset+size:
        word=struct.unpack_from('<I',payload,pos)[0];op=word>>26
        if op in (2,3):additions.append(reloc(pos,4))
        if op==15:
            low=struct.unpack_from('<I',payload,pos+4)[0]
            rt=(word>>16)&31
            if low>>26!=13 or (low>>21)&31!=rt or (low>>16)&31!=rt:
                raise ValueError('Unrecognized address pair')
            address=((word&65535)<<16)|(low&65535)
            struct.pack_into('<II',payload,pos,i(15,0,rt,(address+0x8000)>>16),i(9,rt,rt,address))
            additions.extend([reloc(pos,5),reloc(pos+4,6)]);pos+=4
        pos+=4
    return additions

def build(full_4x=False,dialogue=False,speaker_labels=False,bubble_layout=False,compact_font=False,association_fix=False):
    if association_fix and not compact_font:raise ValueError('Association fix requires the compact candidate')
    if compact_font and not bubble_layout:raise ValueError('Compact candidate requires bubble layout')
    if bubble_layout and not speaker_labels:raise ValueError('Bubble layout requires speaker and dialogue hooks')
    if speaker_labels and not dialogue:raise ValueError('Speaker labels require dialogue hooks')
    if dialogue and not full_4x:raise ValueError('Dialogue candidate requires the full 4x repertoire')
    original=ELF.read_bytes()
    assets=list(pathlib.Path('work/source/cpk').rglob('ALLResidentNML*'))
    if len(assets)!=1:raise ValueError('Expected one resident font asset')
    native=assets[0].read_bytes()
    charset=native[0x7ccb0:0x7ce80].split(b'\0',1)[0].decode('cp932')
    if len(charset)!=230:raise ValueError('Resident charset changed')
    snapshot=b''.join(struct.pack('<Iff',int.from_bytes(c.encode('cp932'),'big'),float(n),-1.0)
        for n,c in enumerate(charset))+native[0x658b0+17*384:0x658b0+247*384]
    if hashlib.sha256(original).hexdigest()!=SHA or hashlib.sha256(snapshot).hexdigest()!=SOURCE_SHA:
        raise ValueError('Build inputs changed')
    texture_width=64 if full_4x else 128
    payload,descriptor,textptr,info=make_payload(FontInput(snapshot),0,START,0,4,
        high_texture_width=texture_width,full_4x=full_4x,max_payload_bytes=0x60000 if full_4x else None,compact_font=compact_font)
    info.pop('atlas');_,table,pixels=struct.unpack('<III',descriptor)
    initializer=init_hook(table,pixels);payload[0x500:0x500+len(initializer)]=initializer
    hooks=[(0,len(decoder_hook(0))),(0x100,len(width_hook(0,START+0x800))),
        *[(o,len(h)) for o,h in zip((0x200,0x300,0x400),high_hooks(0,info['high_bank'],START+0x600,texture_width,offset_units=compact_font))],
        (0x500,len(initializer))]
    dialogue_changes=[];dialogue_info=None
    if dialogue:
        from dialogue_vwf_hooks import append
        blocks,dialogue_changes,dialogue_info=append(payload,START,speaker_labels=speaker_labels)
        hooks=[h for h in hooks if h[0]!=0]+blocks
    bubble_info=None
    if bubble_layout:
        from bubble_layout_hooks import append as append_bubble
        blocks,bubble_changes,bubble_info=append_bubble(payload,START,compact_catalog=compact_font,association_fix=association_fix)
        hooks.extend(blocks);dialogue_changes.extend(bubble_changes)
    additions=[]
    for offset,size in hooks:additions.extend(relocate_code(payload,offset,size))
    phoff,shoff=struct.unpack_from('<II',original,28)
    phnum=struct.unpack_from('<H',original,44)[0];shnum=struct.unpack_from('<H',original,48)[0]
    if (phoff,phnum,shoff,shnum)!=(0x34,3,0x47bbc4,55):raise ValueError('ELF layout changed')
    ph=[list(struct.unpack_from('<8I',original,phoff+n*32)) for n in range(3)]
    sections=[list(struct.unpack_from('<10I',original,shoff+n*40)) for n in range(shnum)]
    relsections=[s for s in sections if s[1]==0x700000a0]
    oldrel=original[ph[2][1]:ph[2][1]+ph[2][4]]
    if len(oldrel)//8!=71807 or sum(s[5] for s in relsections)!=len(oldrel):raise ValueError('Relocation counts changed')
    sites={struct.unpack_from('<II',oldrel,n) for n in range(0,len(oldrel),8)}
    patch=bytearray(original)
    changes=[(0xe9cc8,words([j(START),0]),False),(0x87dc0,words([j(START+0x100),0]),False),
        (0xea5c4,words([j(START+0x200),0]),False),
        (0xea6a0,words([jal(START+0x300)]),True),(0xea6e4,words([jal(START+0x400)]),True),
        (0x4c0ec,words([jal(START+0x500)]),True)]
    expected={0xe9cc8:0x03e00008,0x87dc0:0x1000ffd9,0xea5c4:0x00a04025,
        0xea6a0:jal(0x1b7d28),0xea6e4:jal(0xd7fc),0x4c0ec:jal(0xea204)}
    for offset,data,existing,old in dialogue_changes:
        changes.append((offset,data,existing));expected[offset]=old
    if dialogue:
        assert original[0xee8d8+0xc0:0xee8dc+0xc0]==words([0x10000014])
        assert original[0xed160+0xc0:0xed164+0xc0]==words([i(43,4,23,0x48)])
    if speaker_labels:assert original[0xec050+0xc0:0xec054+0xc0]==words([i(5,4,0,-39)])
    if bubble_layout:assert original[0xe4e10+0xc0:0xe4e14+0xc0]==words([i(35,4,5,0x31c)])
    for offset,data,existing in changes:
        actual=struct.unpack_from('<I',original,offset+0xc0)[0]
        if actual!=expected[offset]:raise ValueError(f'Hook changed at {offset:x}: {actual:x}')
        if existing and (offset,4) not in sites:raise ValueError('Existing call relocation missing')
        if not existing and any(off==offset and (flags>>8)&255==0 for off,flags in sites):
            raise ValueError('Unexpected existing hook relocation')
        if not existing:additions.append(reloc(offset,4,0))
        patch[offset+0xc0:offset+0xc0+len(data)]=data
    for n,pointer in enumerate(textptr):
        offset=0x948d4+n*4
        if (offset,2) not in sites:raise ValueError('Menu pointer relocation missing')
        struct.pack_into('<I',patch,offset+0xc0,pointer)
    payload_file=align(len(patch),64);patch.extend(bytes(payload_file-len(patch)));patch.extend(payload)
    rel_file=align(len(patch),16);patch.extend(bytes(rel_file-len(patch)))
    patch.extend(oldrel+b''.join(additions))
    for s in relsections:s[4]=rel_file+(s[4]-ph[2][1])
    sections.append([0,1,7,START,payload_file,len(payload),0,0,64,0])
    sections.append([0,0x700000a0,0,0,rel_file+len(oldrel),len(additions)*8,0,len(sections)-1,4,8])
    new_shoff=align(len(patch),4);patch.extend(bytes(new_shoff-len(patch)))
    for s in sections:patch.extend(struct.pack('<10I',*s))
    newph=[ph[0],ph[1],[1,payload_file,START,0,len(payload),len(payload),7,64],ph[2]]
    newph[3][1]=rel_file;newph[3][4]=len(oldrel)+len(additions)*8
    for n,p in enumerate(newph):struct.pack_into('<8I',patch,phoff+n*32,*p)
    struct.pack_into('<I',patch,32,new_shoff);struct.pack_into('<H',patch,44,4);struct.pack_into('<H',patch,48,len(sections))
    # Both loader views must cover identical records, without gaps or duplicates.
    spans=sorted((s[4],s[4]+s[5]) for s in sections if s[1]==0x700000a0)
    assert spans[0][0]==rel_file and spans[-1][1]==rel_file+newph[3][4]
    assert all(a[1]==b[0] for a,b in zip(spans,spans[1:]))
    assert bytes(patch[rel_file:rel_file+len(oldrel)])==oldrel
    info.update(version='0.1.6' if association_fix else '0.1.5' if compact_font else '0.1.4' if bubble_layout else '0.1.3' if speaker_labels else '0.1.2' if dialogue else '0.1.1' if full_4x else '0.1.0',status='cold_boot_candidate_unverified',elf_bytes=len(patch),payload_bytes=len(payload),
        added_relocations=len(additions),module_growth_bytes=len(payload),startup_hook='0x4c0ec',
        original_elf_sha256=SHA,font_input_sha256=SOURCE_SHA,output_elf_sha256=hashlib.sha256(patch).hexdigest())
    if dialogue:info['dialogue_hooks']=dialogue_info
    if bubble_layout:info['bubble_layout']=bubble_info
    return bytes(patch),info

def record_for(image,target):
    with image.open('rb') as f:
        f.seek(16*2048);pvd=f.read(2048)
        if pvd[1:6]!=b'CD001':raise ValueError('ISO descriptor changed')
        root=pvd[156:];todo=[(struct.unpack_from('<I',root,2)[0],struct.unpack_from('<I',root,10)[0],'')];seen=set()
        while todo:
            block,size,parent=todo.pop()
            if block in seen:continue
            seen.add(block);f.seek(block*2048);data=f.read(size);pos=0
            while pos<len(data):
                n=data[pos]
                if not n:pos=align(pos+1,2048);continue
                rec=data[pos:pos+n];record_offset=block*2048+pos;pos+=n
                name=rec[33:33+rec[32]]
                if name in (b'\0',b'\1'):continue
                name=name.decode('ascii').split(';')[0];path=parent+'/'+name if parent else name
                extent,length=struct.unpack_from('<I',rec,2)[0],struct.unpack_from('<I',rec,10)[0]
                if rec[25]&2:todo.append((extent,length,path))
                elif path==target:return record_offset,extent,length
    raise ValueError('ISO target absent')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--iso',action='store_true')
    p.add_argument('--full-4x',action='store_true',help='0.1.1 candidate with all 96 Latin glyphs in 64x64 source slots')
    a=p.parse_args()
    output_root=pathlib.Path('work/output/0.1.1-menu-full-vwf-4x-candidate') if a.full_4x else ROOT
    data,info=build(a.full_4x);rec,extent,length=record_for(ISO,'PSP_GAME/SYSDIR/EBOOT.BIN')
    info['iso_original_eboot']={'directory_record':rec,'sector':extent,'bytes':length}
    print(json.dumps(info,indent=2))
    if not a.write:print('DRY RUN: no output written.');return
    output_root.mkdir(parents=True,exist_ok=True);(output_root/'EBOOT.BIN').write_bytes(data)
    if a.iso:
        dest=output_root/('Heroes-Phantasia-'+info['version']+('-menu-full-vwf-4x-candidate.iso' if a.full_4x else '-menu-vwf-4x-candidate.iso'));shutil.copyfile(ISO,dest)
        with dest.open('r+b') as f:
            end=align(f.seek(0,2),2048);f.write(bytes(end-f.tell()));f.write(data)
            final=align(f.tell(),2048);f.write(bytes(final-f.tell()))
            f.seek(rec+2);f.write(struct.pack('<I',end//2048)+struct.pack('>I',end//2048))
            f.seek(rec+10);f.write(struct.pack('<I',len(data))+struct.pack('>I',len(data)))
            f.seek(16*2048+80);f.write(struct.pack('<I',final//2048)+struct.pack('>I',final//2048))
        info['iso_bytes']=final
    (output_root/'manifest.en.json').write_text(json.dumps(info,indent=2)+'\n')
    print('Wrote versioned local candidate; cold-boot validation required.')

if __name__=='__main__':main()
