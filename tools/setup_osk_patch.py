"""Build fresh 0.1.10 setup keyboard assets from reviewed 0.1.9; dry-run default."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from build_menu_patch import START, align, relocate_code
from dialogue_vwf_hooks import Block, address, r, route
from live_vwf import i, j, jal, words

SOURCE=Path('work/output/0.1.9-setup-assets/EBOOT.BIN')
SOURCE_REPORT=SOURCE.with_name('setup_patch.en.json')
OUTPUT=Path('work/output/0.1.10-setup-assets')
SHA='fc26d53588901616e952bf4a61bc45356df97b22b75d3a57eaff6ec36b6b2e71'
ERRORS=[(0x2eac18,'The name could not be accepted.',0x50174,0x50180),
        (0x2eac50,'Enter a name within the allowed length.',0x50178,0x50188)]

def header_palette():
    h=Block();h.emit(i(35,29,24,0x20));address(h,25,0x4fca8)
    h.branch(5,24,25,'native');h.emit(i(13,0,5,0))
    h.label('native');h.emit(j(0xe9264),0);return h.finish()

def field_advance(lut):
    h=Block();h.emit(i(9,29,29,-16),i(43,29,24,0),i(43,29,25,4),i(37,29,24,0x88))
    h.emit(i(11,24,25,32));h.branch(5,25,0,'native')
    h.emit(i(11,24,25,129));h.branch(4,25,0,'native')
    h.emit(i(13,0,25,127));h.branch(4,24,25,'native')
    address(h,25,lut);h.emit(r(0,24,24,0,2),r(25,24,25),i(35,25,24,0))
    h.emit(i(57,29,0,8),0x44980000,0x46800020,0x4600a500,i(49,29,0,8))
    h.branch(4,0,0,'done');h.label('native');h.emit(0x4616a500)
    h.label('done');h.emit(i(35,29,24,0),i(35,29,25,4),j(0x516fc),i(9,29,29,16))
    return h.finish()

def surname_measure(lut):
    # Return twice ceil(pixel_width/13), matching the native placement formula.
    # Printable Latin uses the same integer advances as the field draw hook;
    # valid CP932 two-byte glyphs retain13px. Unknown/control input stays native.
    h=Block();h.emit(r(4,0,8),i(13,0,9,0));address(h,12,lut)
    h.label('loop');h.emit(i(36,8,10,0));h.branch(4,10,0,'end')
    h.emit(i(11,10,11,32));h.branch(5,11,0,'native')
    h.emit(i(11,10,11,127));h.branch(5,11,0,'ascii')
    h.emit(i(11,10,11,0x81));h.branch(5,11,0,'native')
    h.emit(i(11,10,11,0xa0));h.branch(5,11,0,'japanese')
    h.emit(i(11,10,11,0xe0));h.branch(5,11,0,'native')
    h.emit(i(11,10,11,0xfd));h.branch(4,11,0,'native')
    h.label('japanese');h.emit(i(36,8,11,1),i(11,11,13,0x40));h.branch(5,13,0,'native')
    h.emit(i(11,11,13,0xfd));h.branch(4,13,0,'native')
    h.emit(i(13,0,13,0x7f));h.branch(4,11,13,'native')
    h.emit(i(9,9,9,13),i(9,8,8,2));h.branch(4,0,0,'loop')
    h.label('ascii');h.emit(r(0,10,11,0,2),r(12,11,11),i(35,11,11,0),r(9,11,9),i(9,8,8,1))
    h.branch(4,0,0,'loop');h.label('end')
    h.emit(i(9,9,9,12),i(13,0,10,13),r(9,10,0,0x1b),0x00001012,r(0,2,2,0,1),0x03e00008,0)
    h.label('native');h.emit(j(0x128b64),0);return h.finish()

def build():
    original=SOURCE.read_bytes();report=json.loads(SOURCE_REPORT.read_text())
    if hashlib.sha256(original).hexdigest()!=SHA or report['output_elf_sha256']!=SHA:
        raise ValueError('Expected reviewed 0.1.9 input executable/report')
    phoff,shoff=struct.unpack_from('<II',original,28)
    phnum=struct.unpack_from('<H',original,44)[0];shnum=struct.unpack_from('<H',original,48)[0]
    if phnum!=4:raise ValueError('Unexpected segment count')
    ph=[list(struct.unpack_from('<8I',original,phoff+32*n)) for n in range(phnum)]
    sections=[list(struct.unpack_from('<10I',original,shoff+40*n)) for n in range(shnum)]
    if ph[2][2]!=START or ph[3][0]!=0x700000a0:raise ValueError('Unexpected inherited segments')
    prefix=original[ph[2][1]:ph[2][1]+ph[2][4]];payload=bytearray(prefix)
    rel=original[ph[3][1]:ph[3][1]+ph[3][4]]
    sites=set(struct.iter_unpack('<II',rel));patch=bytearray(original);changes=[];additions=[]
    def replace(site,new,old):
        if original[site+192:site+192+len(old)]!=old:raise ValueError(f'Changed site {site:x}')
        patch[site+192:site+192+len(new)]=new
        changes.append(dict(rva=hex(site),expected_hex=old.hex(),replacement_hex=new.hex()))
    oldlimits=[4,8,4,8,12,15];newlimits=[9,17,9,17,25,15]
    replace(0x470980,words(newlimits[:5]),words(oldlimits[:5]))
    assert struct.unpack_from('<I',original,0x470980+192+20)[0]==15
    replace(0x115324,words([i(13,0,5,0xdb0f)]),words([i(13,0,5,0xdb00)]))
    entries=[]
    for file,text,high,low in ERRORS:
        source=original[file:original.index(b'\0',file)];source.decode('cp932')
        if any(c<32 for c in source):raise ValueError('Unexpected error-message control')
        while len(payload)%4:payload.append(0)
        addr=START+len(payload);payload.extend(text.encode('ascii')+b'\0')
        hi,lo=[struct.unpack_from('<I',original,s+192)[0] for s in (high,low)]
        signed=struct.unpack('<h',struct.pack('<H',lo&65535))[0]
        if hi>>26!=15 or lo>>26!=9 or ((hi&65535)<<16)+signed!=file-192:
            raise ValueError('Error-message address pair changed')
        if (high,5) not in sites or (low,6) not in sites:raise ValueError('Existing error-message relocations missing')
        replace(high,words([(hi&0xffff0000)|(((addr+0x8000)>>16)&65535)]),words([hi]))
        replace(low,words([(lo&0xffff0000)|(addr&65535)]),words([lo]))
        entries.append(dict(original_file_offset=hex(file),target=text,payload_rva=hex(addr),pointer_rvas=[],address_pairs=[[hex(high),hex(low)]],context='Name editor invalid-input dialog reached through 0x513d8/0x4e854 and drawn by 0x50184.',decision='Generic wording covers existing conversion validation and new length rejection; fullwidth-only instruction no longer applies.'))
        assert patch[file:file+len(source)+1]==original[file:file+len(source)+1]
    # Six native 512-byte OSK records: UTF16 description followed by fallback.
    # Relocate a full copy so sixth record and every nontext byte stay unchanged.
    while len(payload)%16:payload.append(0)
    descaddr=START+len(payload);table=bytearray(original[0x4709f0+192:0x4709f0+192+6*512])
    descriptions=['Enter the protagonist\'s surname.','Enter the protagonist\'s given name.',
                  'Enter the protagonist\'s surname.','Enter the protagonist\'s given name.',
                  'Enter the protagonist\'s title.']
    defaults=['Watari','Eiji','Fudo','Shinobu','S.I.R. Ace']
    for n,(description,default) in enumerate(zip(descriptions,defaults)):
        for part,text in ((0,description),(256,default)):
            encoded=text.encode('utf-16-le')+b'\0\0'
            if len(encoded)>256:raise ValueError('OSK field exceeds record capacity')
            table[n*512+part:n*512+part+256]=encoded+bytes(256-len(encoded))
            entries.append(dict(original_file_offset=hex(0x4709f0+192+n*512+part),target=text,payload_rva=hex(descaddr+n*512+part),pointer_rvas=[],address_pairs=[],encoding='utf-16-le',context='OSK description' if part==0 else 'OSK fallback default',decision='Description permits Latin by removing obsolete fullwidth-only restriction.' if part==0 else 'Latin protagonist default; sixth unrelated record preserved.'))
    assert table[5*512:]==original[0x4709f0+192+5*512:0x4709f0+192+6*512]
    payload.extend(table)
    replace(0x1152e8,words([i(15,0,4,(descaddr+0x8000)>>16)]),words([i(15,0,4,0x47)]))
    replace(0x1152f4,words([i(9,4,4,descaddr)]),words([i(9,4,4,0x9f0)]))
    if (0x1152e8,5) not in sites or (0x1152f4,6) not in sites:raise ValueError('OSK description relocations missing')
    while len(payload)%16:payload.append(0)
    off=len(payload);paletteaddr=START+off;code=header_palette();payload.extend(code)
    additions.extend(relocate_code(payload,off,len(code)))
    if (0xea6ac,4) not in sites:raise ValueError('Palette call relocation missing')
    replace(0xea6ac,words([jal(paletteaddr)]),words([jal(0xe9264)]))
    # The setup field caller already obtains the resident font through E928C.
    # Only these call sites bypass the protagonist's Japanese-only cached font.
    for site,name,oldtarget in [(0x51778,'classify',0xe9c64)]:
        if (site,4) not in sites:raise ValueError('Field call relocation missing')
        replace(site,words([jal(int(report['hooks'][name],16))]),words([jal(oldtarget)]))
    while len(payload)%16:payload.append(0)
    off=len(payload);fieldrouteaddr=START+off;code=route(0xe9918);payload.extend(code)
    additions.extend(relocate_code(payload,off,len(code)))
    for site in (0x517c0,0x87d8c,0xee330):
        if (site,4) not in sites:raise ValueError('Protagonist renderer relocation missing')
        replace(site,words([jal(fieldrouteaddr)]),words([jal(0xe9918)]))
    while len(payload)%16:payload.append(0)
    lut=START+len(payload);payload.extend(words([round(v) for v in struct.unpack_from('<129f',prefix,0x800)]))
    while len(payload)%16:payload.append(0)
    off=len(payload);advanceaddr=START+off;code=field_advance(lut);payload.extend(code)
    additions.extend(relocate_code(payload,off,len(code)))
    if any(s==0x517c8 and ((flags>>8)&255)==0 for s,flags in sites):raise ValueError('Unexpected advance relocation')
    replace(0x517c8,words([j(advanceaddr),0]),words([i(4,0,0,-52),0x4616a500]))
    additions.append(struct.pack('<II',0x517c8,4))
    while len(payload)%16:payload.append(0)
    off=len(payload);measureaddr=START+off;code=surname_measure(lut);payload.extend(code)
    additions.extend(relocate_code(payload,off,len(code)))
    if (0x51654,4) not in sites:raise ValueError('Surname measure relocation missing')
    replace(0x51654,words([jal(measureaddr)]),words([jal(0x128b64)]))
    payload_file=align(len(patch),64);patch.extend(bytes(payload_file-len(patch)));patch.extend(payload)
    rel_file=align(len(patch),16);patch.extend(bytes(rel_file-len(patch)));patch.extend(rel+b''.join(additions))
    for s in sections:
        if s[1]==0x700000a0:s[4]=rel_file+(s[4]-ph[3][1])
        elif s[3]==START and s[4]==ph[2][1]:s[4]=payload_file;s[5]=len(payload)
    payload_section=next(n for n,s in enumerate(sections) if s[3]==START and s[4]==payload_file)
    sections.append([0,0x700000a0,0,0,rel_file+len(rel),len(additions)*8,0,payload_section,4,8])
    newsh=align(len(patch),4);patch.extend(bytes(newsh-len(patch)))
    for s in sections:patch.extend(struct.pack('<10I',*s))
    ph[2][1]=payload_file;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=rel_file;ph[3][4]=len(rel)+len(additions)*8
    for n,p in enumerate(ph):struct.pack_into('<8I',patch,phoff+32*n,*p)
    struct.pack_into('<I',patch,32,newsh)
    struct.pack_into('<H',patch,48,len(sections))
    spans=sorted((s[4],s[4]+s[5]) for s in sections if s[1]==0x700000a0)
    assert spans[0][0]==rel_file and spans[-1][1]==rel_file+ph[3][4]
    assert all(a[1]==b[0] for a,b in zip(spans,spans[1:]))
    assert payload[:len(prefix)]==prefix and patch[rel_file:rel_file+len(rel)]==rel
    for off,flags in sites:assert off+4<=ph[(flags>>8)&255][4]
    digest=hashlib.sha256(patch).hexdigest()
    report.update(version='0.1.10',status='setup_keyboard_candidate_runtime_unverified',runtime_verified=False,input_sha256=SHA,input_version='0.1.9',output_sha256=digest,output_elf_sha256=digest,elf_bytes=len(patch),payload_bytes=len(payload),module_growth_bytes=len(payload),payload_growth=len(payload)-len(prefix),inherited_added_relocations=report['added_relocations'],added_relocations=len(additions),total_relocations=ph[3][4]//8,inherited_payload_sha256=hashlib.sha256(prefix).hexdigest(),inherited_payload_preserved=True,relocation_table_sha256=hashlib.sha256(rel).hexdigest(),relocation_prefix_unchanged=True,osk_patch_changes=changes)
    report['hooks']['setup_header_palette']=hex(paletteaddr)
    report['inherited_relocation_table_sha256']=hashlib.sha256(rel).hexdigest()
    report['relocation_table_sha256']=hashlib.sha256(rel+b''.join(additions)).hexdigest()
    report['hooks'].update(setup_field_renderer=hex(fieldrouteaddr),setup_field_advance=hex(advanceaddr),setup_surname_measure=hex(measureaddr))
    report['setup_fields']=dict(decoder_site='0x51778',renderer_site='0x517c0',advance_site='0x517c8',surname_measure_site='0x51654',japanese_cache_path_preserved=True,latin_font='Inherited resident 4x Latin bank',later_player_name_cache_expansions_verified=False)
    report['runtime_player_name_route']=dict(sites=['0x87d8c','0xee330'],hook=hex(fieldrouteaddr),font_source='Both callers obtain the resident font through E928C.',japanese_cache_path_preserved=True,existing_latin_decoder_and_cursor_hooks_preserved=True,runtime_verified=False,remaining='Runtime substitution, layout measurement and other cached-name callers still require live verification.')
    report['strings'].extend(entries)
    report['changed_rvas'].extend(changes)
    report['default_name_storage'].update(osk_character_limits=dict(male_surname=9,male_given_name=17,female_surname=9,female_given_name=17,title=25,other=15),osk_output_utf16_bytes=128,osk_inputtype='0xDB0F',persistent_cp932_limits_unchanged=True)
    report['osk']=dict(limit_table_rva='0x470980',old_limits=oldlimits,new_limits=newlimits,input_mask_site='0x115324',old_input_mask='0xDB00',new_input_mask='0xDB0F',language='Japanese (unchanged)',sources=['https://pspdev.github.io/pspsdk/psputility__osk_8h_source.html'],failure_path=['0x511f4','0x513b0','0x513d8','0x4e854','0x50184'],notes='Latin digit/symbol/lowercase/uppercase bits added; existing Japanese input bits retained. OSK character limit remains subordinate to CP932 byte-capacity checks.')
    report['limitations'].append('Setup fields and two resident-font player-name callers bypass the Japanese-only cache for Latin glyphs. Later runtime substitution and layout measurement remain unverified.')
    report['limitations'].append('Mixed CP932 surname placement measures Latin advances and13px Japanese glyphs. Long custom-name layout still requires visual verification.')
    return bytes(patch),report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    data,report=build()
    print(json.dumps({k:report[k] for k in ('version','input_sha256','output_elf_sha256','elf_bytes','payload_bytes','module_growth_bytes','added_relocations','osk','osk_patch_changes')},indent=2))
    print('Relocated errors and OSK:',json.dumps(report['strings'][-12:],indent=2))
    if not a.write:print('DRY RUN: no output written.');return
    if any((OUTPUT/name).exists() for name in ('EBOOT.BIN','setup_patch.en.json')):raise ValueError('Refusing to overwrite fresh-version output')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/'EBOOT.BIN').write_bytes(data)
    (OUTPUT/'setup_patch.en.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
