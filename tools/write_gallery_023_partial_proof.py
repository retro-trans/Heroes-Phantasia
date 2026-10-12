"""Guarded partial23 Gallery evidence writer; dry preview only unless approved."""
import argparse, json
from pathlib import Path
from gallery_023_partial_preview import build, MANIFEST, sha
from gallery_label_patch import canonical

def proposal():
    proof=build();manifest=json.loads(MANIFEST.read_bytes())
    proof.update(iso_sha256=proof['actual_iso_sha256'],archive_sha256=proof['actual_archive_sha256'],
        status='partial_gallery_capture_review',build_manifest=str(MANIFEST),build_manifest_sha256=sha(MANIFEST.read_bytes()),
        coverage_note='Installed23 labels:16 English observed,15 full text/layout pass,Confirm occluded,three selected labels unobserved. Six Knowledge labels remain Japanese in23; approved working24 drafts are not installed23 translations.')
    if proof['iso_sha256']!=manifest['iso_sha256']or proof['archive_sha256']!=manifest['dialogue_cpk_sha256']or proof['executable_sha256']!=manifest['output_elf_sha256']:
        raise ValueError('Actual23 ISO/archive/executable proof binding differs')
    if (proof['selected_label_count'],proof['English_translation_observed_count'],proof['full_text_and_layout_passed_count'])!=(19,16,15):
        raise ValueError('Reviewed partial23 coverage differs')
    if proof['gallery_selected_labels_display_qa_passed']or proof['entire_gallery_translated']or proof['emulator_operations']:
        raise ValueError('Partial proof may not assert complete Gallery or emulator operations')
    proof['proof_code_input_sha256']={str(p):sha(p.read_bytes())for p in(
        Path(__file__),Path('tools/gallery_023_partial_preview.py'),Path('tools/collect_gallery_023_evidence.py'),
        Path('tools/build_local.py'),Path('tools/save_logo_overlay.py'))}
    return proof

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true')
    p.add_argument('--output',type=Path,default=Path('work/ui/gallery/0.1.23/partial_display_qa.en.json'))
    p.add_argument('--approved-plan-sha256');a=p.parse_args();report=proposal();digest=canonical(report)
    print(json.dumps(report,indent=2));print('CANONICAL PARTIAL PROOF SHA256',digest)
    if not a.write:print('DRY: no proof, assets or emulator operations.');return
    if a.approved_plan_sha256!=digest:raise ValueError('Exact fresh reviewed partial-proof hash required')
    target=a.output.resolve()
    if target.exists()or not target.is_relative_to(Path('work/ui').resolve())or target.suffix!='.json':
        raise ValueError('Fresh JSON evidence path inside work/ui required')
    fresh=proposal()
    if fresh!=report or canonical(fresh)!=digest:raise ValueError('Reviewed captures/build/tool inputs changed')
    fresh.update(proof_written=True,approved_partial_proof_sha256=digest)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(fresh,indent=2)+'\n',encoding='utf8')
    if json.loads(target.read_bytes())!=fresh:raise ValueError('Partial evidence readback differs')
    print('Verified partial evidence:',target)

if __name__=='__main__':main()
