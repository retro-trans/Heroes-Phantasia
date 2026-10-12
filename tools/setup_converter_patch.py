"""Build fresh 0.1.11 setup converter assets from reviewed 0.1.10; dry-run default."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from build_menu_patch import START, align, relocate_code
from dialogue_vwf_hooks import Block, address, r, route
from live_vwf import i, j, jal, words

SOURCE=Path('work/output/0.1.10-setup-assets/EBOOT.BIN')
SOURCE_REPORT=SOURCE.with_name('setup_patch.en.json')
OUTPUT=Path('work/output/0.1.11-setup-assets')
SHA='0e9434ec638b41a65c35af917d63b2e72452b9d9ba299a9dd1a529d1b247f852'
FORWARD_CALLERS=(0x4ea64,0x4eaa0,0x4eadc,0x5126c)
REVERSE_CALLERS=(0x51188,0x5127c)

def scoped_ascii(h,saved_ra,callers,character):
    # Only caller-scratch t8/t9 are used. The native conversion frame is intact.
    h.emit(i(35,29,24,saved_ra))
    for caller in callers:
        address(h,25,caller);h.branch(4,24,25,'scoped')
    h.branch(4,0,0,'native');h.label('scoped')
    h.emit(i(11,character,25,32));h.branch(5,25,0,'native')
    h.emit(i(11,character,25,127));h.branch(4,25,0,'native')

def forward_ascii():
    h=Block();scoped_ascii(h,0x38,FORWARD_CALLERS,2)
    # ASCII decoder v0 is already the Unicode code point. Native UTF16 encoder
    # and s1/s2 byte-capacity/count handling remain responsible for output.
    h.emit(r(2,0,5),j(0x1c4354),i(9,29,4,0x10))
    h.label('native');h.emit(i(37,6,5,0),j(0x1c4354),i(9,29,4,0x10))
    return h.finish()

def reverse_ascii():
    h=Block();scoped_ascii(h,0x3c,REVERSE_CALLERS,3)
    # Native CP932 encoder receives the ASCII identity mapping directly.
    # Reproduce its scratch output pointer initialization before branching.
    h.emit(i(43,29,29,0x10),r(3,0,5),j(0x1c4470),0)
    h.label('native');h.emit(r(19,3,4,0x2b),i(43,29,29,0x10),j(0x1c4440),0)
    return h.finish()

def build():
    original=SOURCE.read_bytes();report=json.loads(SOURCE_REPORT.read_text())
    if hashlib.sha256(original).hexdigest()!=SHA or report['output_elf_sha256']!=SHA:
        raise ValueError('Expected reviewed 0.1.10 input executable/report')
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
    hookmap={}
    for name,site,code,expected in [
        ('setup_cp932_to_utf16_ascii',0x1c434c,forward_ascii(),words([i(37,6,5,0),i(9,29,4,0x10)])),
        ('setup_utf16_to_cp932_ascii',0x1c4438,reverse_ascii(),words([r(19,3,4,0x2b),i(43,29,29,0x10)]))]:
        if any(off in (site,site+4) and ((flags>>8)&255)==0 for off,flags in sites):
            raise ValueError('Unexpected relocation at converter inline site')
        while len(payload)%16:payload.append(0)
        off=len(payload);hookmap[name]=START+off;payload.extend(code)
        additions.extend(relocate_code(payload,off,len(code)))
        replace(site,words([j(hookmap[name]),0]),expected)
        additions.append(struct.pack('<II',site,4))
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
    report.update(version='0.1.11',status='setup_converter_candidate_runtime_unverified',runtime_verified=False,input_sha256=SHA,input_version='0.1.10',output_sha256=digest,output_elf_sha256=digest,elf_bytes=len(patch),payload_bytes=len(payload),module_growth_bytes=len(payload),payload_growth=len(payload)-len(prefix),inherited_added_relocations=report['added_relocations'],added_relocations=len(additions),total_relocations=ph[3][4]//8,inherited_payload_sha256=hashlib.sha256(prefix).hexdigest(),inherited_payload_preserved=True,inherited_relocation_table_sha256=hashlib.sha256(rel).hexdigest(),relocation_table_sha256=hashlib.sha256(rel+b''.join(additions)).hexdigest(),relocation_prefix_unchanged=True,converter_patch_changes=changes)
    report['hooks'].update({k:hex(v) for k,v in hookmap.items()})
    report['changed_rvas'].extend(changes)
    report['setup_conversion']=dict(forward_site='0x1c434c',reverse_site='0x1c4438',forward_caller_returns=list(map(hex,FORWARD_CALLERS)),reverse_caller_returns=list(map(hex,REVERSE_CALLERS)),ascii_range=[32,126],strategy='Bypass only ASCII lookup mappings in setup callers; native encoders, decoding, counts, NUL and capacity branches retained.',japanese_mapping_preserved=True,runtime_verified=False)
    report['limitations'].append('Printable ASCII conversion bypass is scoped to setup initialization/reset and name-editor conversion calls. Keyboard default retention and ASCII/mixed acceptance need runtime verification.')
    return bytes(patch),report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    data,report=build()
    print(json.dumps({k:report[k] for k in ('version','input_sha256','output_elf_sha256','elf_bytes','payload_bytes','module_growth_bytes','added_relocations','setup_conversion','converter_patch_changes')},indent=2))
    print('Inherited strings:',len(report['strings']))
    if not a.write:print('DRY RUN: no output written.');return
    if any((OUTPUT/name).exists() for name in ('EBOOT.BIN','setup_patch.en.json')):raise ValueError('Refusing to overwrite fresh-version output')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/'EBOOT.BIN').write_bytes(data)
    (OUTPUT/'setup_patch.en.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()

