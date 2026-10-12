"""Record hash-reviewed native Options captures and banner instruction evidence."""
import argparse,json,hashlib
from pathlib import Path
from PIL import Image

UI=Path('work/ui/field/0.1.28');MP=Path('work/output/0.1.28-title-credit-vwf-4x-candidate/manifest.en.json')
HASHES={'options_actual.png':'7c4a2452c001e7b6a468123a349a7f6fe1f0badc77f99e1859b38495c5d5c5a9',
 'options_camera_allies.png':'54d885f81aa9a138437338b568aace7d0e8dcba87bdf4002103765b20bc15ceb'}
VISIBLE=set(range(66,80))|{11,12,166,194,228}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args()
    m=json.loads(MP.read_text());p=json.loads((UI/'validation.en.json').read_text());captures=[]
    for name,digest in HASHES.items():
        path=UI/name;meta=json.loads(path.with_suffix('.json').read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest or Image.open(path).size!=(480,272):raise ValueError('Reviewed Options capture differs')
        if meta['version']!=m['version'] or meta['loaded_executable_sha256']!=m['output_elf_sha256']:raise ValueError('Capture identity differs')
        captures.append(dict(file=str(path),sha256=digest,visually_reviewed=True))
    for pk,mk in [('iso_sha256','iso_sha256'),('executable_sha256','output_elf_sha256'),('archive_sha256','dialogue_cpk_sha256')]:
        if p[pk]!=m[mk]:raise ValueError('Validation identity differs')
    banner=json.loads((UI/'banner_native_instruction.en.json').read_text())
    if banner['version']!=m['version'] or banner['executable_sha256']!=m['output_elf_sha256'] or len(banner['native_instruction_cases'])!=3:
        raise ValueError('Native instruction evidence identity differs')
    if not all(r['passed'] for r in banner['native_instruction_cases']):raise ValueError('Native banner instruction case failed')
    savepath=Path('work/ui/title/0.1.28/after_save.png')
    savedigest='7a7e241e0ef6942cac2d386a541c6b51d5da539d3f689bf7569993e0b42bf8e3'
    savemeta=json.loads(savepath.with_suffix('.json').read_text())
    if hashlib.sha256(savepath.read_bytes()).hexdigest()!=savedigest or savemeta['loaded_executable_sha256']!=m['output_elf_sha256']:
        raise ValueError('Reviewed system-save completion capture differs')
    saveproof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=m['output_elf_sha256'],archive_sha256=m['dialogue_cpk_sha256'],
      status='native_system_save_creation_QA_passed',save_display_qa_passed=True,system_save_creation_passed=True,
      game_save_load_restart_verified=False,scope='Fresh isolated emulator system-save creation and English Save completed. result only.',
      captures=[dict(file=str(savepath),sha256=savedigest,visually_reviewed=True)],
      limitations=['System-save restart/load and game-state saves were not tested.'])
    p.update(status='installed_static_checks_and_shared_Options_display_QA_passed',native_options_layout_verified=True,
      options_capture_scope='Title-menu Options uses the same labels and widget geometry as the reported field Options screen.',
      options_captures=captures,camera_selection_Default_to_Allies_and_back_observed=True,
      native_banner_instruction_verified=True,native_banner_instruction_evidence=str(UI/'banner_native_instruction.en.json'))
    for r in p['entries']:
        if r['table']==0 and r['native_index'] in VISIBLE:r['individual_native_layout_verified']=True
    print(json.dumps({k:p[k]for k in ['status','options_capture_scope','options_captures','native_banner_instruction_verified',
      'natural_episode_banner_interception_verified','native_party_catalog_tutorial_talk_verified']},indent=2))
    if not a.write:print('DRY RUN');return
    (UI/'validation.en.json').write_text(json.dumps(p,indent=2)+'\n')
    m['field_ui_translation_coverage'].update(native_options_verified=True,native_banner_instruction_verified=True,
      native_other_field_screens_verified=False,natural_episode_interception_verified=False)
    MP.write_text(json.dumps(m,indent=2)+'\n')
    savedest=Path('work/ui/save/0.1.28/validation.en.json');savedest.parent.mkdir(parents=True,exist_ok=True)
    if savedest.exists():raise ValueError('Fresh save evidence required')
    savedest.write_text(json.dumps(saveproof,indent=2)+'\n')
    print('Scoped native Options and instruction QA recorded.')

if __name__=='__main__':main()
