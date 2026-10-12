"""Fresh .13 ruby/name/reveal-cap candidate from reviewed .12; dry by default."""
import argparse,hashlib,json,struct
from pathlib import Path
from build_menu_patch import START,align,relocate_code,reloc
from live_vwf import words,j,jal,i
from dialogue_vwf_hooks import r
from dialogue_ruby_hooks import *
from dialogue_wrap import literal_reveal_cap
from audit_ruby_spans import audit

SOURCE=Path('work/output/0.1.12-dialogue-assets/EBOOT.BIN')
OUTPUT=Path('work/output/0.1.13-dialogue-assets')
SHA='3d2271c1e91fc8198886ed0d81922d0ff48d1217076a5340d6ddf5fc07648da5'
PREVIEW_SHA='4cb5fb279a080e5dfd97e74b0da1c2e2fdf8b8f61fb28f2402f03c33a5917d67'


def build():
    original=SOURCE.read_bytes();report=json.loads(SOURCE.with_name('setup_patch.en.json').read_text())
    if hashlib.sha256(original).hexdigest()!=SHA or report['output_elf_sha256']!=SHA:
        raise ValueError('Expected reviewed .12 input/report')
    phoff,shoff=struct.unpack_from('<II',original,28);phnum=struct.unpack_from('<H',original,44)[0]
    shnum=struct.unpack_from('<H',original,48)[0]
    if phnum!=4:raise ValueError('Unexpected inherited segment count')
    ph=[list(struct.unpack_from('<8I',original,phoff+32*n)) for n in range(phnum)]
    sections=[list(struct.unpack_from('<10I',original,shoff+40*n)) for n in range(shnum)]
    if ph[2][2]!=START or ph[3][0]!=0x700000a0:raise ValueError('Inherited payload changed')
    prefix=original[ph[2][1]:ph[2][1]+ph[2][4]];payload=bytearray(prefix)
    previous=original[ph[3][1]:ph[3][1]+ph[3][4]];sites=set(struct.iter_unpack('<II',previous))
    patch=bytearray(original);changes=[];additions=[];hooks={}
    def append(name,code):
        while len(payload)%16:payload.append(0)
        off=len(payload);hooks[name]=START+off;payload.extend(code)
        additions.extend(relocate_code(payload,off,len(code)))
        return START+off
    def replace(site,new,expected,new_relocation=False):
        if original[site+192:site+192+len(expected)]!=expected:
            raise ValueError(f'Unexpected original words {site:x}')
        if new_relocation:
            if any(s==site and (f>>8)&255==0 for s,f in sites):raise ValueError('Unexpected existing relocation')
            additions.append(reloc(site,4,0))
        elif (site,4) not in sites:raise ValueError('Expected inherited R26 relocation')
        patch[site+192:site+192+len(new)]=new
        changes.append(dict(rva=hex(site),expected_hex=expected.hex(),replacement_hex=new.hex()))
    body=[round(v) for v in struct.unpack_from('<129f',prefix,0x800)]
    while len(payload)%16:payload.append(0)
    small=START+len(payload);payload.extend(words(ruby_widths(body)))
    associations=audit();records=association_records(associations,body)
    while len(payload)%16:payload.append(0)
    table=START+len(payload);packed,pointers=pack_associations(records,table);payload.extend(packed)
    additions.extend(reloc(n-START,2) for n in pointers)
    dec=append('ruby_decoder',ruby_decoder())
    font=append('ruby_small_latin_font',small_latin_font())
    advance=append('ruby_advance',ruby_advance(small))
    center=append('ruby_center',ruby_center(table))
    names=append('name_glyph_units',name_glyph_units())
    cap=append('literal_reveal_cap',literal_reveal_cap())
    replace(0xe9cc8,words([j(dec),0]),words([j(START),0]))
    replace(0xea4ac,words([j(font),0]),words([i(5,7,9,40),r(8,0,20,0x25)]),True)
    replace(0xf0dcc,words([j(advance),0]),words([i(4,0,0,3),i(9,17,17,8)]),True)
    replace(0xf0d2c,words([j(center),0]),words([r(0,4,5,0,4),r(5,4,5,0x23)]),True)
    replace(0xee984,words([j(cap),0]),words([i(13,0,6,45),i(43,17,30,8)]),True)
    for site in NAME_COUNT_CALLS:replace(site,words([jal(names)]),words([jal(0x128b64)]))
    payload_file=align(len(patch),64);patch.extend(bytes(payload_file-len(patch)));patch.extend(payload)
    rel_file=align(len(patch),16);patch.extend(bytes(rel_file-len(patch)));patch.extend(previous+b''.join(additions))
    for s in sections:
        if s[1]==0x700000a0:s[4]=rel_file+(s[4]-ph[3][1])
        elif s[3]==START and s[4]==ph[2][1]:s[4]=payload_file;s[5]=len(payload)
    payload_section=next(n for n,s in enumerate(sections) if s[3]==START and s[4]==payload_file)
    sections.append([0,0x700000a0,0,0,rel_file+len(previous),len(additions)*8,0,payload_section,4,8])
    newsh=align(len(patch),4);patch.extend(bytes(newsh-len(patch)))
    for s in sections:patch.extend(struct.pack('<10I',*s))
    ph[2][1]=payload_file;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=rel_file;ph[3][4]=len(previous)+len(additions)*8
    for n,p in enumerate(ph):struct.pack_into('<8I',patch,phoff+32*n,*p)
    struct.pack_into('<I',patch,32,newsh);struct.pack_into('<H',patch,48,len(sections))
    assert payload[:len(prefix)]==prefix and patch[rel_file:rel_file+len(previous)]==previous
    spans=sorted((s[4],s[4]+s[5]) for s in sections if s[1]==0x700000a0)
    assert spans[0][0]==rel_file and spans[-1][1]==rel_file+ph[3][4] and all(a[1]==b[0] for a,b in zip(spans,spans[1:]))
    assert len(set(struct.iter_unpack('<II',previous+b''.join(additions))))==ph[3][4]//8
    digest=hashlib.sha256(patch).hexdigest()
    report.update(version='0.1.13',input_version='0.1.12',input_sha256=SHA,status='ruby_name_reveal_candidate_runtime_unverified',runtime_verified=False,output_sha256=digest,output_elf_sha256=digest,elf_bytes=len(patch),payload_bytes=len(payload),module_growth_bytes=len(payload),payload_growth=len(payload)-len(prefix),inherited_added_relocations=report['added_relocations'],added_relocations=len(additions),total_relocations=ph[3][4]//8,inherited_payload_sha256=hashlib.sha256(prefix).hexdigest(),inherited_payload_preserved=True,inherited_relocation_table_sha256=hashlib.sha256(previous).hexdigest(),relocation_table_sha256=hashlib.sha256(previous+b''.join(additions)).hexdigest(),relocation_prefix_unchanged=True)
    report['hooks'].update({name:hex(address) for name,address in hooks.items()});report['changed_rvas'].extend(changes)
    report['dialogue_ruby_patch']=dict(changes=changes,hooks={n:hex(a) for n,a in hooks.items()},association_table=hex(table),association_ledger_sha256=hashlib.sha256(packed).hexdigest(),association_records=len(records),ruby_spans=associations['ruby_spans'],association_counts=associations['counts'],small_advance_lut=hex(small),original_control_arguments_preserved=True,source_assets_rewritten=False,small_destination_px=8,private_latin_accent=128,reveal_cap=dict(site='0xee984',supported='Validated literal Latin plus05/16/17 with actual A3 count match',maximum_probe_bytes=1024,terminal_probe_bytes=1,native_fallback=45),name_count_calls=list(map(hex,NAME_COUNT_CALLS)),wrapping_installed=False,runtime_verified=False)
    report['limitations'].append('Ruby/small-font centering, runtime name reveal counts and validated Latin cap require .13 runtime QA. Unknown ruby signatures and unhandled cap streams retain native behavior; wrapping/page capacity and mixed runtime pixel measurement remain unverified.')
    return bytes(patch),report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    data,report=build()
    print(json.dumps({k:report[k] for k in ('version','input_sha256','output_elf_sha256','elf_bytes','payload_bytes','payload_growth','added_relocations','total_relocations','dialogue_ruby_patch')},indent=2))
    print('Inherited setup strings:',len(report['strings']))
    if not a.write:print('DRY RUN: no output written.');return
    if report['output_elf_sha256']!=PREVIEW_SHA:
        raise ValueError('Draft/glossary inputs changed since .13 preview; repeat independent review before write')
    if any((OUTPUT/n).exists() for n in ('EBOOT.BIN','setup_patch.en.json')):raise ValueError('Refusing to overwrite versioned output')
    OUTPUT.mkdir(parents=True,exist_ok=True);(OUTPUT/'EBOOT.BIN').write_bytes(data)
    (OUTPUT/'setup_patch.en.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
