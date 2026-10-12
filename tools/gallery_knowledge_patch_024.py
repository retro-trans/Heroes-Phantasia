"""Pure frozen23 Knowledge/footer pointer proposal; no executable writer."""
import argparse, copy, json, struct
from pathlib import Path
from gallery_label_patch import sha, canonical, ORIGINAL
from executable_text_patch import Elf, reference_index
from png_tail_allocate import plan
from prepare_relocation_019 import coverage, section_load, pair_shapes
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

SOURCE=Path('work/output/0.1.23-gallery-assets/EBOOT.BIN')
SOURCE_SHA='5bd8174a02da1611393d251da6ace01d51fe937e2c2d0ef607835af459da85fb'
QUEUES=[Path('work/translation/en/executable_gallery_0001.json'),Path('work/translation/en/executable_gallery_0002.json')]
QUEUE_SHAS=['7e4f1cd6eda516b327981d8b69138f6f3f2a42fb7ab7fe259bcf8548e30e3e55','05a1cd3b5698b87eb2f4ca7f4d30907305d2e92af00d4f1a585d3e1832e252c8']
FOOTER_ID='exe_00094c4b_cp932'

def build():
    incoming=SOURCE.read_bytes(); rawmeta=SOURCE.with_name('executable.en.json').read_bytes(); before=json.loads(rawmeta)
    if sha(incoming)!=SOURCE_SHA or before['output_elf_sha256']!=SOURCE_SHA or before['version']!='0.1.23':
        raise ValueError('Frozen23 executable/report differs')
    elf=Elf(incoming); original=Elf(ORIGINAL.read_bytes())
    oldfont=authoritative_font_metadata(incoming,before); oldpng=validate_native_png_metadata(incoming,before)
    references,_=reference_index(original)
    qrows=[]
    for path,expected in zip(QUEUES,QUEUE_SHAS):
        raw=path.read_bytes()
        if sha(raw)!=expected:raise ValueError('Approved working target snapshot differs')
        qrows.append(json.loads(raw)['rows'])
    if len(qrows[0])!=19 or len(qrows[1])!=6:raise ValueError('Reviewed row count differs')
    old=before['gallery_label_proposal']; previous={e['id']:e for e in old['entries']}
    if len(previous)!=19:raise ValueError('Frozen nineteen-label scope differs')
    # All original23 translations and pointers are checked, including old Confirm.
    for row in qrows[0]:
        entry=previous[row['id']]; ptr=entry['pointer_slot']; target=entry['target'].encode('ascii')+b'\0'
        off=elf.file_offset(entry['target_rva'],len(target))
        if elf.word(ptr)!=entry['target_rva'] or incoming[off:off+len(target)]!=target:
            raise ValueError('Preexisting gallery target/pointer differs')
        if elf.relocs[entry['relocation_ordinal']]!=(ptr,2):raise ValueError('Preexisting gallery R32 differs')
        if row['id']!=FOOTER_ID and row['target']!=entry['target']:raise ValueError('Unselected working target differs')
    footer=next(r for r in qrows[0]if r['id']==FOOTER_ID)
    if footer['target']!='Enter' or previous[FOOTER_ID]['target']!='Confirm':raise ValueError('Approved footer revision differs')
    payload=bytearray(); entries=[]
    floats=struct.unpack('<131f',incoming[elf.file_offset(before['float_width_lut_rva'],524):elf.file_offset(before['float_width_lut_rva'],524)+524])
    for row in qrows[1]+[footer]:
        is_footer=row['id']==FOOTER_ID
        source=row['expected_source_rva']if is_footer else row['source_rva']
        slot=row['typed_R_MIPS_32_pointer_slot_rva']if is_footer else row['pointer_slot_rva']
        raw=row['source'].encode('cp932')+b'\0'; offset=original.file_offset(source)
        if original.data[offset:offset+len(raw)]!=raw or sha(raw)!=row['source_sha256_with_NUL']or offset!=row['offset']:
            raise ValueError('Original UI source byte/hash/offset guard failed')
        refs=[r for r in references if r['kind']=='R_MIPS_32'and r['sites']==[slot]and r['address']==source]
        ordinal=row['relocation_ordinal']
        if len(refs)!=1 or refs[0]['relocation_ordinals']!=[ordinal]or elf.relocs[ordinal]!=(slot,2):
            raise ValueError('Typed original/current R32 guard failed')
        expected=previous[FOOTER_ID]['target_rva']if is_footer else source
        if elf.word(slot)!=expected:raise ValueError('Current selected pointer differs')
        target=row['target'].encode('ascii')+b'\0'
        if any(c<32 or c>126 for c in target[:-1]):raise ValueError('Target not printable Latin')
        entries.append(dict(id=row['id'],target=row['target'],source_rva=source,source_sha256=sha(raw),pointer_slot=slot,
            relocation_ordinal=ordinal,expected_old_pointer=expected,relative_offset=len(payload),encoded_bytes=len(target),
            estimated_16px_VWF_width=sum(floats[c]for c in target[:-1]),runtime_verified=False))
        payload.extend(target)
    if len(payload)!=71 or [e['pointer_slot']for e in entries]!=list(range(0x948a8,0x948c0,4))+[0x9479c]:
        raise ValueError('Reviewed seven-pointer/71-byte scope differs')
    reservation=plan(before,[dict(name='gallery_six_Knowledge_and_Enter',data=bytes(payload),alignment=4)])
    placement=reservation['patches'][0]
    if placement['rva']!=3052144 or reservation['remaining_bytes']!=108:raise ValueError('Reviewed free-tail placement differs')
    for active in before['additional_scopes']['tail_reservations']+before['native_tail_compaction']['chunks']:
        if placement['rva']<active['rva']+active['bytes']and active['rva']<placement['rva']+len(payload):
            raise ValueError('New strings overlap active code/font/data')
    start=elf.file_offset(placement['rva'],len(payload))
    if start!=placement['file_offset']:raise ValueError('Tail physical offset differs')
    output=bytearray(incoming);output[start:start+len(payload)]=payload; allowed=set(range(start,start+len(payload)))
    for e in entries:
        e['target_rva']=placement['rva']+e['relative_offset']; off=elf.file_offset(e['pointer_slot'],4)
        struct.pack_into('<I',output,off,e['target_rva']);allowed.update(range(off,off+4))
    output=bytes(output);out=Elf(output)
    if len(output)!=len(incoming)or out.ph!=elf.ph or out.relocs!=elf.relocs or pair_shapes(output)!=pair_shapes(incoming):
        raise ValueError('ELF/load/relocation/HI-LO contracts changed')
    if any(a!=b and i not in allowed for i,(a,b)in enumerate(zip(incoming,output))):raise ValueError('Unselected file bytes changed')
    models=[];coverage(output)
    for base in(0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);b,visited,skipped,_=section_load(output,base)
        mask=set(range(placement['rva'],placement['rva']+len(payload)))
        for e in entries:
            slot=e['pointer_slot'];mask.update(range(slot,slot+4))
            if struct.unpack_from('<I',b[0],slot)[0]!=base+e['target_rva']:raise ValueError('Section-loaded selected R32 differs')
        if skipped or len(visited)!=len(elf.relocs)or a[1:]!=b[1:]or any(x!=y and i not in mask for i,(x,y)in enumerate(zip(a[0],b[0]))):
            raise ValueError('Section-loaded unselected memory differs')
        for entry in previous.values():
            if entry['id']!=FOOTER_ID and struct.unpack_from('<I',b[0],entry['pointer_slot'])[0]!=base+entry['target_rva']:
                raise ValueError('Preexisting eighteen loaded gallery pointers differ')
        models.append(dict(base=base,relocations=len(visited),selected_R32=7,preexisting_unchanged_gallery_R32=18,skipped_sections=skipped,unselected_loaded_memory_exact=True))
    report=copy.deepcopy(before);report.update(version='0.1.24',input_version='0.1.23',input_sha256=SOURCE_SHA,
        output_elf_sha256=sha(output),output_sha256=sha(output),elf_bytes=len(output),status='pure_knowledge_footer_candidate_runtime_unverified',runtime_verified=False)
    report['gallery_023_history']=dict(source=str(SOURCE),metadata_sha256=sha(rawmeta),historical_gallery_label_proposal=report.pop('gallery_label_proposal'),
        historical_writer_readback=report.pop('gallery_writer_readback',None),historical_approved_plan=report.get('approved_dry_plan_sha256'),
        note='Nineteen-label23 proof remains historical. Current revision changes only footer ID15 pointer; old Confirm bytes are retained.')
    for key in('output','approved_dry_plan_sha256','written_readback_verified'):report.pop(key,None)
    report['trailer_recovery']['free_tail_regions']=reservation['free_tail_regions'];report['trailer_recovery']['remaining_tail_bytes']=108
    allocation={k:v for k,v in placement.items()if k!='data'};report['additional_scopes']['tail_reservations'].append(allocation)
    current=copy.deepcopy(list(previous.values()))
    current_footer=next(e for e in current if e['id']==FOOTER_ID)
    current_footer.update(next(e for e in entries if e['id']==FOOTER_ID))
    report['gallery_current_entries']=current+entries[:6]
    proof=dict(input_metadata_sha256=sha(rawmeta),queue_sha256=dict(zip(map(str,QUEUES),QUEUE_SHAS)),entries=entries,
        allocation=allocation,payload_bytes=71,remaining_tail_bytes=108,loaded_growth_bytes=0,new_relocations=0,
        excluded_tail_old_bytes_sha256=sha(incoming[start:start+71]),all_PH_SHT_relocations_pairs_exact=True,
        all_unselected_file_bytes_exact=True,all_active_font_code_PNG_bytes_exact=True,old_Confirm_bytes_retained=True,
        original19_pointers_checked=19,preexisting_unchanged_gallery_pointers=18,three_base_actual_SHT_models=models,
        Enter_estimated_13px_width=entries[-1]['estimated_16px_VWF_width']*13/16,observed_footer_gap=35,
        runtime_verified=False,entire_gallery_translated=False,
        limitations=['Knowledge destination widths and current Enter appearance require actual24 screen QA.','Other native table/menu/image labels remain outside this scope.'])
    report['gallery_knowledge_footer_proposal']=proof
    newfont=authoritative_font_metadata(output,report)
    if {k:v for k,v in newfont.items()if k!='additional_scopes'}!={k:v for k,v in oldfont.items()if k!='additional_scopes'}:
        raise ValueError('Authoritative font contract changed')
    if report['additional_scopes']['tail_reservations'][:-1]!=before['additional_scopes']['tail_reservations']:raise ValueError('Inherited reservations changed')
    newpng=validate_native_png_metadata(output,report)
    if newpng!=oldpng:raise ValueError('Native PNG metadata changed')
    proof['authoritative_font_contract_exact']=True;proof['native_PNG_full_metadata_checks']=newpng
    proof['code_input_sha256']={str(p):sha(p.read_bytes())for p in [Path(__file__),Path('tools/gallery_label_patch.py'),Path('tools/executable_text_patch.py'),Path('tools/png_tail_allocate.py'),Path('tools/prepare_relocation_019.py'),Path('tools/build_local.py'),Path('tools/save_logo_overlay.py')]}
    return output,report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path);a=p.parse_args()
    data,report=build();print(json.dumps(report['gallery_knowledge_footer_proposal'],indent=2));print('ELF SHA256',sha(data));print('CANONICAL PLAN SHA256',canonical(report))
    if a.report:
        if a.report.exists()or not a.report.resolve().is_relative_to(Path('work/source').resolve()):raise ValueError('Fresh ignored proposal path required')
        a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('DRY: no executable assets, ISO or emulator operations.')
