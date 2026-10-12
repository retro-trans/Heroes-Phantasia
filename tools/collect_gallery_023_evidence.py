"""Pure reviewed gallery capture collector; no emulator or proof writer."""
import argparse, hashlib, json
from pathlib import Path
from executable_text_patch import Elf
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

PREP=Path('work/output/0.1.23-gallery-assets/executable.en.json')
EXPECTED_ELF='5bd8174a02da1611393d251da6ace01d51fe937e2c2d0ef607835af459da85fb'

def sha(data):return hashlib.sha256(data).hexdigest()

def collect(manifest=None,reviews=None):
    prep_raw=PREP.read_bytes();prep=json.loads(prep_raw)
    data=PREP.with_name('EBOOT.BIN').read_bytes();elf=Elf(data)
    if sha(data)!=EXPECTED_ELF or prep['output_elf_sha256']!=EXPECTED_ELF or prep['version']!='0.1.23':
        raise ValueError('Written23 gallery preparation differs')
    authoritative_font_metadata(data,prep);validate_native_png_metadata(data,prep)
    entries={e['id']:e for e in prep['gallery_label_proposal']['entries']}
    if len(entries)!=19:raise ValueError('Expected nineteen reviewed labels')
    for e in entries.values():
        raw=e['target'].encode('ascii')+b'\0';p=elf.file_offset(e['target_rva'],len(raw))
        if data[p:p+len(raw)]!=raw or elf.word(e['pointer_slot'])!=e['target_rva']:
            raise ValueError('Current selected pointer/string differs')
    build=None
    if manifest:
        build=json.loads(manifest.read_bytes())
        if build['version']!='0.1.23' or build['output_elf_sha256']!=EXPECTED_ELF:
            raise ValueError('Actual23 build manifest does not bind gallery candidate')
        if not build.get('iso_sha256')or not build.get('dialogue_cpk_sha256'):
            raise ValueError('Actual ISO/archive identity missing')
    reviewed=[];covered=set()
    if reviews:
        if build is None:raise ValueError('Capture review requires actual build identity')
        review=json.loads(reviews.read_bytes())
        if any(review.get(k)!=build[k] for k in ('version','iso_sha256','output_elf_sha256')):
            raise ValueError('Review annotations belong to another build')
        for c in review['captures']:
            path=Path(c['path']).resolve()
            if not path.is_relative_to(Path('work/ui').resolve()):raise ValueError('Capture outside UI evidence')
            raw=path.read_bytes()
            if raw[:8]!=b'\x89PNG\r\n\x1a\n' or sha(raw)!=c['reviewed_capture_sha256']:
                raise ValueError('Reviewed capture pixels missing/stale')
            ids=c['label_ids']
            if not ids or len(ids)!=len(set(ids))or any(i not in entries for i in ids):
                raise ValueError('Unknown/duplicate reviewed label IDs')
            if c.get('visually_reviewed')is not True or c.get('full_text_visible')is not True or c.get('layout_visual_qa_passed')is not True:
                raise ValueError('Capture requires explicit full-text/layout human review')
            if c['observed_targets']!=[entries[i]['target']for i in ids]:
                raise ValueError('Observed target annotations differ from protected labels')
            covered.update(ids);reviewed.append(dict(path=str(path),sha256=sha(raw),label_ids=ids,
                full_text_visible=True,layout_visual_qa_passed=True))
    return dict(schema_version=1,version='0.1.23',status='pure_gallery_capture_collection',
        preparation_metadata_sha256=sha(prep_raw),executable_sha256=EXPECTED_ELF,
        actual_iso_sha256=build['iso_sha256']if build else None,
        actual_archive_sha256=build['dialogue_cpk_sha256']if build else None,
        selected_label_count=19,reviewed_label_count=len(covered),
        unreviewed_labels=[dict(id=i,target=e['target'])for i,e in entries.items()if i not in covered],
        inspected_capture_annotations=reviewed,
        gallery_selected_labels_display_qa_passed=bool(build and len(covered)==19),
        limitation='Human capture annotations establish only selected gallery labels; no universal game UI, dictionary-body or movie QA claim.',
        emulator_operations=False,proof_written=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path);p.add_argument('--reviews',type=Path);a=p.parse_args()
    print(json.dumps(collect(a.manifest,a.reviews),indent=2))
    print('DRY: no capture, emulator, assets or evidence files written.')
