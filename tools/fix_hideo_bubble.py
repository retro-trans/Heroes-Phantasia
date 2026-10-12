"""Guarded Hideo ruby width/geometry correction; dry by default, fresh assets only."""
import argparse,copy,hashlib,json,struct
from pathlib import Path
from executable_text_patch import Elf
from build_menu_patch import align,relocate_code
from dialogue_measure_1a import measure_1a,instruction_cases
from bubble_layout_hooks import geometry
from prepare_relocation_019 import sections,coverage,section_load
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from live_vwf import j

SOURCE=Path('work/output/0.1.26-special-label-assets/EBOOT.BIN')
SHA='77811ae695a05aacd0db22b66c0af6aa62a1e6158556c269afad8b487fe9c5a4'
OUT=Path('work/output/0.1.27-bubble-assets')
def sha(b):return hashlib.sha256(b).hexdigest()

def build():
    incoming=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('executable.en.json').read_text())
    if sha(incoming)!=SHA or before['output_elf_sha256']!=SHA:raise ValueError('Frozen26 identity differs')
    e=Elf(incoming);ss=sections(incoming);ph=[list(p) for p in e.ph];p=ph[2];rp=ph[3]
    oldpayload=incoming[p[1]:p[1]+p[4]];payload=bytearray(oldpayload);additions=[];changes=[]
    lut=before['body_integer_lut_rva'];metric=0x2e43c0
    # Compare the entire inherited generators after their signed HI/LO fixup.
    for site,oldcode in ((before['font_hooks']['measurement'],measure_1a(lut)),
                         (0x2e5200,geometry(metric,True,True,glyph_limit=131))):
        old=bytearray(oldcode);relocate_code(old,0,len(old))
        if incoming[e.file_offset(site,len(old)):e.file_offset(site,len(old))+len(old)]!=old:
            raise ValueError('Inherited hook generator differs at '+hex(site))
    def append(code):
        payload.extend(bytes(align(len(payload),16)-len(payload)));off=len(payload)
        payload.extend(code);additions.extend(relocate_code(payload,off,len(code)))
        return p[2]+off,len(code)
    measured,size=append(measure_1a(lut,True));shaped,gsize=append(geometry(metric,True,True,True,131))
    output=bytearray(incoming)
    for site,old,new in ((0xed15c,before['font_hooks']['measurement'],measured),(0xe4e0c,0x2e5200,shaped)):
        f=e.file_offset(site,8)
        if incoming[f:f+8]!=struct.pack('<II',j(old),0) or (site,4) not in e.relocs:
            raise ValueError('Existing entry branch/relocation differs')
        output[f:f+8]=struct.pack('<II',j(new),0)
        changes.append(dict(site_rva=site,old_target=old,new_target=new))
    file=align(len(output),64);output.extend(bytes(file-len(output)));output.extend(payload)
    relfile=align(len(output),16);output.extend(bytes(relfile-len(output)))
    rel=incoming[rp[1]:rp[1]+rp[4]];output.extend(rel+b''.join(additions))
    binding=None
    for index,s in enumerate(ss):
        if s[1]==0x700000a0:s[4]=relfile+(s[4]-rp[1])
        elif s[3]==p[2] and s[4]==p[1]:s[4]=file;s[5]=len(payload);binding=index
    if binding is None:raise ValueError('No loaded payload section')
    ss.append([0,0x700000a0,0,0,relfile+len(rel),len(additions)*8,0,binding,4,8])
    shoff=align(len(output),4);output.extend(bytes(shoff-len(output)))
    for s in ss:output.extend(struct.pack('<10I',*s))
    ph[2][1]=file;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=relfile;ph[3][4]=len(rel)+len(additions)*8
    phoff=struct.unpack_from('<I',incoming,28)[0]
    for index,row in enumerate(ph):struct.pack_into('<8I',output,phoff+32*index,*row)
    struct.pack_into('<I',output,32,shoff);struct.pack_into('<H',output,48,len(ss))
    result=bytes(output);out=Elf(result);coverage(result)
    if out.relocs[:len(e.relocs)]!=e.relocs:raise ValueError('Inherited relocations differ')
    models=[]
    for base in (0x8804000,0x8900000,0x8fff000):
        old,_,_,_=section_load(incoming,base);new,visited,skipped,_=section_load(result,base)
        expected=bytearray(old[0])
        for q in changes:struct.pack_into('<I',expected,q['site_rva'],j(base+q['new_target']))
        if new[0]!=expected or new[1]!=old[1] or new[2][:len(oldpayload)]!=old[2] or skipped:
            raise ValueError('Unselected loaded memory changed')
        models.append(dict(base=base,relocations=len(visited),unchanged_native_memory_except_two_entry_branches=True))
    widths=list(struct.unpack('<131I',incoming[e.file_offset(lut,524):e.file_offset(lut,524)+524]))
    samples=[([b"I shall now leave for Hideo\x0f2Hideo\x0f's\x11",b'world, bound\x11',b'for Japan.\x12'],True),
             ([b'Hideo\x0f2Hideo\x0f\x12'],True),([b'Hideo\x0f2Other\x0f\x12'],False),
             ([b'Hideo\x0fXHideo\x0f\x12'],False),([b'Hideo\x0f2Hi\0'],False),
             ([b'Hideo\x0f2Hideo\x11\x12'],False),([b'A'*1016+b'\x0f2Hideo\x0f\x12'],True),
             ([b'A'*1017+b'\x0f2Hideo\x0f\x12'],False)]
    cases=instruction_cases(widths,measure_1a(0x240000,True),samples)
    report=copy.deepcopy(before)
    for key in ('output','approved_dry_plan_sha256','written_readback_verified'):report.pop(key,None)
    report.update(version='0.1.27',input_version='0.1.26',input_sha256=SHA,output_elf_sha256=sha(result),
        output_sha256=sha(result),elf_bytes=len(result),payload_bytes=len(payload),module_growth_bytes=len(payload),
        added_relocations=len(out.relocs)-report['original_relocations'],total_relocations=len(out.relocs),
        relocation_table_sha256=sha(rel+b''.join(additions)),runtime_verified=False,status='bubble_layout_candidate')
    report['font_native_tail_loaded_extension_bytes']=len(payload)
    report['font_native_tail_loaded_extension_sha256']=sha(payload)
    report['font_hooks']['measurement']=measured
    report['hideo_bubble_fix']=dict(entry_changes=changes,measurement_bytes=size,geometry_bytes=gsize,
        loaded_growth_bytes=len(payload)-len(oldpayload),new_relocations=len(additions),three_base_SHT_models=models,
        emitted_instruction_cases=cases,reading_signature='0F 32 48 69 64 65 6F 0F',
        source_controls_and_arguments_preserved=True,reading_and_base_not_rewritten=True,
        scope='Exact Latin Hideo reading. Geometry retains unit-scale, stationary, unrotated and 1..4-line guards.',
        runtime_verified=False)
    oldfont=authoritative_font_metadata(incoming,before);newfont=authoritative_font_metadata(result,report)
    # Font bytes, trailer offsets and routes remain identical except the new measured-width entry.
    for k in ('font_compressed_sha256','high_bank_sha256','font_descriptor_rva'):
        if before.get(k)!=report.get(k):raise ValueError('Font identity differs')
    if validate_native_png_metadata(result,report)!=validate_native_png_metadata(incoming,before):
        raise ValueError('PNG metadata differs')
    return result,report

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256');a=ap.parse_args()
    data,report=build();print(json.dumps({k:report[k] for k in ('version','output_elf_sha256','elf_bytes','hideo_bubble_fix')},indent=2))
    if not a.write:print('DRY RUN');return
    if a.expected_sha256!=sha(data) or OUT.exists():raise ValueError('Reviewed digest and fresh folder required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data)
    if sha((OUT/'EBOOT.BIN').read_bytes())!=sha(data):raise ValueError('Readback differs')
    (OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
