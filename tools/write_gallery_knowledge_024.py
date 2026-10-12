"""Guarded fresh Knowledge/footer asset writer; read-only dry preview by default."""
import argparse, json, struct
from pathlib import Path
from gallery_knowledge_patch_024 import build, canonical, sha, FOOTER_ID
from executable_text_patch import Elf
from prepare_relocation_019 import coverage, section_load
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

APPROVED_PLAN='be3cff3f82711f7ced83ffd808fadb3dbc3bfb0c1ecbe7ef8f3e8c1cdb9748b3'
APPROVED_ELF='17cdb7435ed0a2abdf04fcc453140e6e6cda06b2021e74a4ca527ee869763ccb'

def verify(data,report):
    if sha(data)!=APPROVED_ELF or report['output_elf_sha256']!=APPROVED_ELF or report['version']!='0.1.24' or len(data)!=report['elf_bytes']:
        raise ValueError('Reviewed24 executable identity differs')
    authoritative_font_metadata(data,report); png=validate_native_png_metadata(data,report)
    ss=coverage(data);elf=Elf(data);proof=report['gallery_knowledge_footer_proposal'];allocation=proof['allocation']
    offset=elf.file_offset(allocation['rva'],allocation['bytes'])
    if allocation['bytes']!=71 or sha(data[offset:offset+71])!=allocation['sha256']:
        raise ValueError('Seven-label allocation readback differs')
    entries=report['gallery_current_entries']
    if len(entries)!=25 or len({e['id']for e in entries})!=25:raise ValueError('Current25-label scope differs')
    for e in entries:
        raw=e['target'].encode('ascii')+b'\0';p=elf.file_offset(e['target_rva'],len(raw))
        if data[p:p+len(raw)]!=raw or elf.word(e['pointer_slot'])!=e['target_rva']or elf.relocs[e['relocation_ordinal']]!=(e['pointer_slot'],2):
            raise ValueError('Current gallery string/pointer/R32 readback differs')
    old=next(e for e in report['gallery_023_history']['historical_gallery_label_proposal']['entries']if e['id']==FOOTER_ID)
    p=elf.file_offset(old['target_rva'],8)
    if old['target']!='Confirm' or data[p:p+8]!=b'Confirm\0':raise ValueError('Old Confirm bytes were not preserved')
    for base in(0x08804000,0x08900000,0x08fff000):
        memory,visited,skipped,_=section_load(data,base)
        if skipped or len(visited)!=report['total_relocations']:raise ValueError('Actual SHT relocation coverage differs')
        for e in entries:
            if struct.unpack_from('<I',memory[0],e['pointer_slot'])[0]!=base+e['target_rva']:
                raise ValueError('Actual section-loaded gallery pointer differs')
    return dict(authoritative_font_metadata_passed=True,native_PNG_full_triples_passed=png,
        actual_SHT_coverage_sections=len(ss),current_gallery_strings_and_R32_readback=25,
        actual_SHT_three_base_pointers_passed=True,old_Confirm_bytes_retained=True,runtime_verified=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('work/output/0.1.24-gallery-assets'))
    parser.add_argument('--approved-plan-sha256');args=parser.parse_args()
    data,report=build();digest=canonical(report)
    if digest!=APPROVED_PLAN or sha(data)!=APPROVED_ELF:raise ValueError('Planner inputs changed; fresh root review required')
    checks=verify(data,report)
    print(json.dumps(dict(version='0.1.24',canonical_plan_sha256=digest,output_elf_sha256=sha(data),
        elf_bytes=len(data),payload_bytes=71,loaded_growth_bytes=0,new_relocations=0,
        sample=[dict(target=e['target'],pointer_slot=e['pointer_slot'],target_rva=e['target_rva'])for e in report['gallery_knowledge_footer_proposal']['entries']],checks=checks),indent=2))
    if not args.write:print('DRY: no preparation assets, ISO or emulator changes.');return
    if args.approved_plan_sha256!=APPROVED_PLAN:raise ValueError('Exact reviewed canonical plan approval required')
    destination=args.output.resolve()
    if destination.exists()or not destination.is_relative_to(Path('work/output').resolve()):raise ValueError('Fresh directory inside work/output required')
    fresh,current=build()
    if fresh!=data or canonical(current)!=digest:raise ValueError('Inputs changed between preview and writer')
    verify(fresh,current);destination.mkdir(parents=True);path=destination/'EBOOT.BIN';path.write_bytes(fresh)
    readback=path.read_bytes();checks=verify(readback,current)
    current.update(status='written_knowledge_footer_candidate_runtime_unverified',output=str(path),
        approved_dry_plan_sha256=digest,written_readback_verified=True)
    current['gallery_024_writer_readback']=dict(**checks,writer_sha256=sha(Path(__file__).read_bytes()),output_elf_sha256=sha(readback))
    target=destination/'executable.en.json';target.write_text(json.dumps(current,indent=2)+'\n',encoding='utf8')
    saved=json.loads(target.read_bytes())
    if saved!=current:raise ValueError('Preparation metadata readback differs')
    verify(readback,saved);print('Verified fresh preparation:',path)

if __name__=='__main__':main()
