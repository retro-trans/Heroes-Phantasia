"""Guarded fresh gallery preparation writer; default is a read-only dry preview."""
import argparse, json, struct
from pathlib import Path
from gallery_label_patch import build, canonical, sha
from executable_text_patch import Elf
from prepare_relocation_019 import coverage, section_load
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

APPROVED_PLAN = 'b9092d370cc6ed02a1759332f56294b4edb61504a80c3fde8073d86488df1d39'
APPROVED_ELF = '5bd8174a02da1611393d251da6ace01d51fe937e2c2d0ef607835af459da85fb'

def verify(data,report):
    if sha(data)!=APPROVED_ELF or report['output_elf_sha256']!=APPROVED_ELF:
        raise ValueError('Reviewed gallery executable hash differs')
    if report['version']!='0.1.23' or len(data)!=report['elf_bytes']:
        raise ValueError('Version or file size differs')
    font=authoritative_font_metadata(data,report)
    png=validate_native_png_metadata(data,report)
    sections=coverage(data); elf=Elf(data); proof=report['gallery_label_proposal']
    allocation=proof['allocation']; offset=elf.file_offset(allocation['rva'],allocation['bytes'])
    if sha(data[offset:offset+allocation['bytes']])!=allocation['sha256']:
        raise ValueError('Gallery allocation readback hash differs')
    for entry in proof['entries']:
        raw=entry['target'].encode('ascii')+b'\0'; p=elf.file_offset(entry['target_rva'],len(raw))
        if data[p:p+len(raw)]!=raw or elf.word(entry['pointer_slot'])!=entry['target_rva']:
            raise ValueError('Gallery string or typed pointer readback differs')
        if elf.relocs[entry['relocation_ordinal']]!=(entry['pointer_slot'],2):
            raise ValueError('Gallery typed relocation readback differs')
    for base in (0x08804000,0x08900000,0x08fff000):
        memory,visited,skipped,_=section_load(data,base)
        if skipped or len(visited)!=report['total_relocations']:
            raise ValueError('Actual section loader skips or misses relocation records')
        for entry in proof['entries']:
            if struct.unpack_from('<I',memory[0],entry['pointer_slot'])[0]!=base+entry['target_rva']:
                raise ValueError('Actual section-loaded gallery pointer differs')
    return dict(authoritative_font_metadata_passed=True,native_PNG_full_triples_passed=png,
        actual_SHT_coverage_sections=len(sections),gallery_readback_strings_and_pointers=19,
        actual_SHT_three_base_pointers_passed=True,runtime_verified=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('work/output/0.1.23-gallery-assets'))
    parser.add_argument('--approved-plan-sha256')
    args=parser.parse_args()
    data,report=build(); key=canonical(report)
    if key!=APPROVED_PLAN or sha(data)!=APPROVED_ELF:
        raise ValueError('Current fresh planner inputs differ from reviewed dry plan; new root review required')
    checks=verify(data,report)
    print(json.dumps(dict(version=report['version'],canonical_plan_sha256=key,
        output_elf_sha256=sha(data),elf_bytes=len(data),
        payload_bytes=report['gallery_label_proposal']['payload_bytes'],
        loaded_growth_bytes=0,new_relocations=0,
        sample=[dict(target=e['target'],slot=e['pointer_slot'],rva=e['target_rva'])
               for e in report['gallery_label_proposal']['entries'][:7]],checks=checks),indent=2))
    if not args.write:
        print('DRY: no preparation assets, ISO or emulator changes.');return
    if args.approved_plan_sha256!=APPROVED_PLAN:
        raise ValueError('Explicit exact approved canonical plan hash required')
    destination=args.output.resolve()
    if destination.exists()or not destination.is_relative_to(Path('work/output').resolve()):
        raise ValueError('Fresh output directory inside work/output required')
    # Rebuild after approval checks; never reuse a stale in-memory candidate.
    fresh,current=build()
    if canonical(current)!=key or fresh!=data:
        raise ValueError('Planner inputs changed between dry preview and writer')
    verify(fresh,current)
    destination.mkdir(parents=True); path=destination/'EBOOT.BIN';path.write_bytes(fresh)
    readback=path.read_bytes(); checks=verify(readback,current)
    current.update(status='written_gallery_pointer_candidate_runtime_unverified',output=str(path),
        approved_dry_plan_sha256=key,written_readback_verified=True)
    current['gallery_writer_readback']=dict(**checks,writer_sha256=sha(Path(__file__).read_bytes()),
        output_elf_sha256=sha(readback))
    metadata=destination/'executable.en.json'
    metadata.write_text(json.dumps(current,indent=2)+'\n',encoding='utf8')
    saved=json.loads(metadata.read_bytes())
    if saved!=current:raise ValueError('Preparation metadata readback differs')
    verify(readback,saved)
    print('Verified fresh preparation:',path)

if __name__=='__main__':
    main()
