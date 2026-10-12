"""Read back .29 corrections and publish scoped installation evidence; dry first."""
import argparse,json,shutil
from pathlib import Path
from prepare_save_tutorial import build,sha
from executable_text_patch import Elf
from inspect_iso import inventory as iso_inventory
from unpack_cpk import inventory as cpk_inventory
from append_cpk import sha as file_sha

ROOT=Path('work/output/0.1.29-title-credit-vwf-4x-candidate')
UI=Path('work/ui/field/0.1.29')
REFERENCES=[('tutorial_heading','16b71ba7-1a73-40b7-9a24-17af29f55fb1'),('tutorial_body','4058946a-04fa-4338-845b-c75376a4c779'),
 ('save_menu','770bcc84-65f6-4e90-a873-41eea73e588d'),('system_notice','fb69356c-1320-4a07-af5a-a7203d7e23f2')]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true')
    ap.add_argument('--reviewed-header-sha256');ap.add_argument('--reviewed-body-sha256');a=ap.parse_args()
    mp=ROOT/'manifest.en.json';m=json.loads(mp.read_text());expected,prep,_=build();actual=(ROOT/'EBOOT.BIN').read_bytes()
    if expected!=actual or sha(actual)!=m['output_elf_sha256']or file_sha(Path(m['iso_path']))!=m['iso_sha256']:raise ValueError('Build identity differs')
    with Path(m['iso_path']).open('rb')as f:
        entries=iso_inventory(Path(m['iso_path']));r=next(r for r in entries if r['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');f.seek(r['offset'])
        if f.read(r['size'])!=actual:raise ValueError('Nested executable differs')
        r=next(r for r in entries if r['path']=='PSP_GAME/USRDIR/MOVIE/HPMOVE03.PMF');f.seek(r['offset'])
        if sha(f.read(r['size']))!='c2f6dbaa03b713c42ffad7e60c66f8664ea6d1def5bd82513fd75adb076d5946':raise ValueError('English prologue differs')
    if file_sha(ROOT/'HP.CPK')!=m['dialogue_cpk_sha256']:raise ValueError('Archive hash differs')
    _,old=cpk_inventory(Path('work/output/0.1.28-title-credit-vwf-4x-candidate/HP.CPK'));_,new=cpk_inventory(ROOT/'HP.CPK')
    changed=[r['path']for r,s in zip(old,new)if r!=s]
    if len(old)!=len(new)or changed!=['menu/TitleMenu_Data.bin']:raise ValueError('Unselected archive records differ')
    native_path=UI/'tutorial_native_instruction.en.json';native=json.loads(native_path.read_text())
    for key in ('version','iso_sha256'):
        if native[key]!=m[key]:raise ValueError('Native proof identity differs')
    if native['executable_sha256']!=m['output_elf_sha256']or native['archive_sha256']!=m['dialogue_cpk_sha256']:raise ValueError('Native proof hash differs')
    if len(native['native_instruction_cases'])!=5 or not all(x['passed']for x in native['native_instruction_cases']):raise ValueError('Native width cases failed')
    captures=[]
    for screen,reviewed in [('save_points_header',a.reviewed_header_sha256),('save_points_body',a.reviewed_body_sha256)]:
        path=UI/(screen+'.png');meta=json.loads(path.with_suffix('.json').read_text())
        if meta['version']!=m['version']or meta['loaded_executable_sha256']!=m['output_elf_sha256']:raise ValueError('Panel capture identity differs')
        if a.write and file_sha(path)!=reviewed:raise ValueError('Review panel screenshot and supply its hash')
        captures.append(dict(screen=screen,path=str(path),sha256=file_sha(path),visually_reviewed=file_sha(path)==reviewed))
    p=prep['save_tutorial_patch'];inherited=prep['field_ui_patch']
    # Recheck all inherited field pointer/text bindings before counting them in
    # this build; historical .28 screenshot observations stay historical.
    from native_menu_install_plan import cstring
    from executable_text_patch import encoded_text
    e=Elf(actual)
    for r in inherited['entries']:
        if e.word(r['pointer_slot'])!=r['target_rva']or cstring(e,r['target_rva'])!=encoded_text(r['target'],'ascii')+b'\0':raise ValueError('Inherited field translation differs')
    proof=dict(schema_version=1,version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=sha(actual),archive_sha256=m['dialogue_cpk_sha256'],
      status='installed_static_checks_and_native_tutorial_width_passed_scene_pending',entries=inherited['entries']+p['entries'],episode_banner=inherited['episode_inline_banner'],
      save_ui_translation_rows=4,tutorial_constructor=p,source_font_scale=4,English_prologue_retained=True,
      native_instruction_evidence=str(native_path),native_instruction_evidence_sha256=file_sha(native_path),native_tutorial_width_verified=True,
      native_tutorial_panel_display_verified=True,tutorial_panel_debugger_triggered=True,native_tutorial_scene_display_verified=False,
      native_panel_captures=captures,native_save_menu_and_notice_display_verified=False,
      native_options_layout_verified=False,native_party_catalog_tutorial_talk_verified=False,natural_episode_banner_interception_verified=False,
      full_game_verified=False,nested_iso_executable_readback_exact=True,changed_archive_rows=changed,other_archive_rows_exact=len(new)-1,
      limitations=['Actual Save Points panel was summoned through the native loader; natural guild arrival, save-menu and system-notice appearance still need gameplay verification.','Whole-game Japanese coverage and speech-bubble tail defects remain open.'])
    print(json.dumps({k:v for k,v in proof.items()if k not in ('entries','tutorial_constructor','episode_banner')},indent=2))
    if not a.write:print('DRY RUN');return
    dest=UI/'validation.en.json'
    if dest.exists():raise ValueError('Fresh evidence required')
    dest.write_text(json.dumps(proof,indent=2)+'\n');refs=[]
    for screen,id in REFERENCES:
        source=Path('C:/Users/Binh/AppData/Local/Temp')/('codex-clipboard-'+id+'.png');target=UI/('reference_'+screen+'.png');shutil.copyfile(source,target)
        refs.append(dict(screen=screen,path=str(target),sha256=file_sha(target),source='user screenshot',source_build_version_unknown=True,actual_candidate_capture=False))
    layout=dict(version=m['version'],native_resolution=[480,272],reference_resolution=[960,544],references=refs,regions=[
      dict(screen='tutorial_heading',native_rect=[0,87,480,99],targets=['Field Tutorial','Save Points']),
      dict(screen='tutorial_body',native_rect=[0,87,480,99],targets=['Use this object to save your data.','It also restores HP and PP to their maximum values.'],
        line_widths_px=[216,338],centered_left_px=[132,71],native_instruction_verified=True,native_panel_display_verified=True,native_field_event_verified=False),
      dict(screen='save_menu',native_rect=[0,101,120,77],targets=['Save','Delete Data','Cancel']),
      dict(screen='system_notice',native_rect=[0,87,480,99],targets=[r['target']for r in p['entries']if r['table']==1])])
    (UI/'layout.en.json').write_text(json.dumps(layout,indent=2)+'\n')
    m.update(field_ui_translation_coverage=dict(installed_in_iso=True,menu_rows=48,episode_banner_rows=1,validation=str(dest),native_options_layout_verified=False),
      save_tutorial_translation_coverage=dict(installed_in_iso=True,translation_rows=4,native_width_verified=True,native_panel_display_verified=True,native_scene_display_verified=False,validation=str(dest)))
    mp.write_text(json.dumps(m,indent=2)+'\n');print('Installation evidence, screenshot references and layout ledger written.')

if __name__=='__main__':main()
