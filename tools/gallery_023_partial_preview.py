"""Pure partial gallery review preview; no evidence or asset writer."""
import json, hashlib
from pathlib import Path
from collect_gallery_023_evidence import PREP,EXPECTED_ELF,collect

MANIFEST=Path('work/output/0.1.23-title-credit-vwf-4x-candidate/manifest.en.json')
ROOT=Path('work/ui/runtime/0.1.23')

def sha(data):return hashlib.sha256(data).hexdigest()

def build():
    baseline=collect(MANIFEST);manifest=json.loads(MANIFEST.read_bytes());prep=json.loads(PREP.read_bytes())
    entries=prep['gallery_label_proposal']['entries']; by_target={e['target']:e for e in entries}
    reviewed=[];observed=set();good=set()
    groups=[('gallery_tabs',['Dictionary','Knowledge','Characters','Select','Confirm','Back','Close']),
        ('gallery_dictionary_series',['Blood+','R.O.D -READ OR DIE-','Sgt. Frog','s-CRY-ed',
         'Slayers REVOLUTION','My-HiME','Sorcerous Stabber Orphen','Rune Soldier','Original'])]
    for name,targets in groups:
        picture=ROOT/(name+'.png');capture=ROOT/(name+'.json');raw=picture.read_bytes();meta=json.loads(capture.read_bytes())
        if raw[:8]!=b'\x89PNG\r\n\x1a\n' or meta['version']!='0.1.23' or meta['loaded_executable_sha256']!=EXPECTED_ELF:
            raise ValueError('Actual native gallery capture identity differs')
        if Path(meta['build_manifest']).resolve()!=MANIFEST.resolve():raise ValueError('Capture manifest binding differs')
        labels=[]
        for target in targets:
            entry=by_target[target];observed.add(entry['id']);passed=target!='Confirm'
            if passed:good.add(entry['id'])
            labels.append(dict(id=entry['id'],target=target,English_translation_observed=True,
                full_text_visible=passed,layout_visual_qa_passed=passed,
                review='Root reviewed native captures; independent agent viewed matching PNG.' if passed else
                'Confirm trailing glyphs are occluded by the following Cross/Back icon; visible prefix Conf is not full-label layout QA.'))
        reviewed.append(dict(path=str(picture),sha256=sha(raw),capture_metadata=str(capture),
            capture_metadata_sha256=sha(capture.read_bytes()),visually_reviewed=True,labels=labels))
    knowledge=ROOT/'gallery_knowledge_series.png';km=ROOT/'gallery_knowledge_series.json';meta=json.loads(km.read_bytes())
    if meta['version']!='0.1.23' or meta['loaded_executable_sha256']!=EXPECTED_ELF or Path(meta['build_manifest']).resolve()!=MANIFEST.resolve():
        raise ValueError('Knowledge defect capture binding differs')
    planned=json.loads(Path('work/source/gallery_knowledge_024_proposal.en.json').read_bytes())
    baseline.update(status='pure_partial_gallery_review_pending_root_approval',
        selected_label_count=19,English_translation_observed_count=len(observed),
        full_text_and_layout_passed_count=len(good),
        reviewed_label_count=len(good),inspected_capture_annotations=reviewed,
        unreviewed_labels=[dict(id=e['id'],target=e['target'])for e in entries if e['id']not in good],
        unobserved_selected_labels=[dict(id=e['id'],target=e['target'])for e in entries if e['id']not in observed],
        known_selected_layout_defects=[dict(target='Confirm',cause='Following Cross/Back icon occludes trailing glyphs.')],
        remaining_UI_defects=[dict(capture=str(knowledge),capture_sha256=sha(knowledge.read_bytes()),
            capture_metadata_sha256=sha(km.read_bytes()),scope='Six observed Japanese knowledge categories',
            proposed_targets=[r['target']for r in planned['rows']],already_translated=False)],
        generic_DTB_menu_label='Native table2 index12 fullwidth Latin title; outside nineteen-label patch and not evidence for either season-specific target.',
        actual_iso_sha256=manifest['iso_sha256'],actual_archive_sha256=manifest['dialogue_cpk_sha256'],
        gallery_selected_labels_display_qa_passed=False,entire_gallery_translated=False,proof_written=False)
    if len(observed)!=16 or len(good)!=15:raise ValueError('Partial observed/reviewed coverage count differs')
    return baseline

if __name__=='__main__':
    print(json.dumps(build(),indent=2));print('DRY: no proof, assets or emulator operations.')
