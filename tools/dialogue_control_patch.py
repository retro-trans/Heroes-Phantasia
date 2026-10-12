"""Build fresh 0.1.12 dialogue control assets from reviewed 0.1.11; dry-run default."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from build_menu_patch import START, align, relocate_code
from dialogue_vwf_hooks import Block, address, r, route
from live_vwf import i, j, jal, words

SOURCE=Path('work/output/0.1.11-setup-assets/EBOOT.BIN')
SOURCE_REPORT=SOURCE.with_name('setup_patch.en.json')
OUTPUT=Path('work/output/0.1.12-dialogue-assets')
SHA='d53dce4ae053ed04fb3701b80434ba47adfa12a4561253d12c7ba7b93f0828ee'
from dialogue_measure import measure

TABLE_PATCHES=((0x2ef2e4,0xeb834,0xeaef0,'count_05'),
               (0x2ef32c,0xeb834,0xeaef0,'count_17'),
               (0x2f1444,0xf0f3c,0xf0e18,'draw_05'),
               (0x2f148c,0xf0f3c,0xf0e18,'draw_17'))

def build():
    original=SOURCE.read_bytes();report=json.loads(SOURCE_REPORT.read_text())
    if hashlib.sha256(original).hexdigest()!=SHA or report['output_elf_sha256']!=SHA:
        raise ValueError('Expected reviewed 0.1.11 input executable/report')
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
    for site,expected,target,label in TABLE_PATCHES:
        if (site,2) not in sites:raise ValueError('Missing existing control-table R32 relocation')
        replace(site,words([target]),words([expected]))
    while len(payload)%16:payload.append(0)
    lut=START+len(payload)
    payload.extend(words([round(v) for v in struct.unpack_from('<129f',prefix,0x800)]))
    while len(payload)%16:payload.append(0)
    off=len(payload);hook=START+off;code=measure(lut);payload.extend(code)
    additions.extend(relocate_code(payload,off,len(code)))
    if (0xed15c,4) not in sites:raise ValueError('Missing inherited measurement R26 relocation')
    oldhook=struct.unpack_from('<I',original,0xed15c+192)[0]
    if oldhook>>26!=2 or oldhook&0x3ffffff!=0x17482f0>>2:
        raise ValueError('Unexpected inherited dialogue measurement hook')
    replace(0xed15c,words([j(hook),0]),words([oldhook,0]))
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
    report.update(version='0.1.12',status='dialogue_controls_candidate_runtime_unverified',runtime_verified=False,input_sha256=SHA,input_version='0.1.11',output_sha256=digest,output_elf_sha256=digest,elf_bytes=len(patch),payload_bytes=len(payload),module_growth_bytes=len(payload),payload_growth=len(payload)-len(prefix),inherited_added_relocations=report['added_relocations'],added_relocations=len(additions),total_relocations=ph[3][4]//8,inherited_payload_sha256=hashlib.sha256(prefix).hexdigest(),inherited_payload_preserved=True,inherited_relocation_table_sha256=hashlib.sha256(rel).hexdigest(),relocation_table_sha256=hashlib.sha256(rel+b''.join(additions)).hexdigest(),relocation_prefix_unchanged=True,dialogue_control_patch_changes=changes)
    report['hooks']['dialogue_control_measure']=hex(hook)
    report['changed_rvas'].extend(changes)
    report['dialogue_control_patch']=dict(table_patches=[dict(rva=hex(site),original=hex(expected),target=hex(target),label=label,existing_relocation='R32 retained') for site,expected,target,label in TABLE_PATCHES],measurement_site='0xed15c',measurement_hook=hex(hook),integer_advance_lut=hex(lut),measurement_bytes=len(code),maximum_probe_bytes=1024,terminal_probe_bytes=1,maximum_line_objects=32,supported_width_neutral_controls=['05:3','16:2','17:1'],native_pair_advance_px=13,argument_digits_excluded_from_count_and_draw=True,wrapping_inserted=False,ruby_runtime_expansion_measurement_verified=False,runtime_verified=False)
    report['limitations'].append('Control-aware dialogue width/count/draw fixes require phase and battle runtime QA. No automatic wrapping, translated ruby span association, runtime expansion width or universal panel/page limits are claimed.')
    return bytes(patch),report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    data,report=build()
    print(json.dumps({k:report[k] for k in ('version','input_sha256','output_elf_sha256','elf_bytes','payload_bytes','module_growth_bytes','added_relocations','dialogue_control_patch','dialogue_control_patch_changes')},indent=2))
    print('Inherited strings:',len(report['strings']))
    if not a.write:print('DRY RUN: no output written.');return
    if any((OUTPUT/name).exists() for name in ('EBOOT.BIN','setup_patch.en.json')):raise ValueError('Refusing to overwrite fresh-version output')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/'EBOOT.BIN').write_bytes(data)
    (OUTPUT/'setup_patch.en.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()

