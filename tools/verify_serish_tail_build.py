"""Verify the installed scoped tail correction and native instruction evidence."""
import argparse,json
from pathlib import Path
from prepare_serish_tail_compact import build,sha
from inspect_iso import inventory as iso_inventory
from unpack_cpk import inventory as cpk_inventory
from rebuild_dialogue import parse
from title_stamp import prepare,RESOURCE
from PIL import Image

ROOT=Path('work/output/0.1.31-title-credit-vwf-4x-candidate')
UI=Path('work/ui/dialogue/0.1.31')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true')
    ap.add_argument('--reviewed-title-sha256');ap.add_argument('--reviewed-menu-sha256');a=ap.parse_args()
    mp=ROOT/'manifest.en.json';m=json.loads(mp.read_text());expected,prep=build();actual=(ROOT/'EBOOT.BIN').read_bytes()
    if actual!=expected or sha(actual)!=m['output_elf_sha256']:raise ValueError('Executable readback differs')
    with Path(m['iso_path']).open('rb')as f:
        entries=iso_inventory(Path(m['iso_path']));r=next(r for r in entries if r['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');f.seek(r['offset'])
        if f.read(r['size'])!=actual:raise ValueError('Nested executable differs')
    _,old=cpk_inventory(Path('work/output/0.1.29-title-credit-vwf-4x-candidate/HP.CPK'));_,new=cpk_inventory(ROOT/'HP.CPK')
    changed=[r['path']for r,s in zip(old,new)if r!=s]
    if len(old)!=len(new)or changed!=['menu/TitleMenu_Data.bin']:raise ValueError('Unselected archive records differ')
    text=b'\x1cPrincess Serish\x0eWho will accompany you?\x12\x0e';records=[]
    with (ROOT/'HP.CPK').open('rb')as f:
        for name in prep['serish_tail_patch']['resources']:
            r=next(r for r in new if r['path']==name)
            if r['compression']!='none':raise ValueError('Expected raw prepared phase')
            f.seek(r['offset']);raw=f.read(r['stored_size']);p=parse(name,raw);body=p['spans'][p['refs'][6][1]][0]
            if body!=text:raise ValueError('Installed selected record differs')
            records.append(dict(resource=name,reference_index=6,record_sha256=sha(body),resource_sha256=sha(raw),unchanged=True))
    native_path=UI/'tail_native_instruction.en.json';native=json.loads(native_path.read_text())
    for k in ('version','iso_sha256'):
        if native[k]!=m[k]:raise ValueError('Native proof identity differs')
    if native['executable_sha256']!=m['output_elf_sha256']or native['archive_sha256']!=m['dialogue_cpk_sha256']:raise ValueError('Native proof hash differs')
    if len(native['cases'])!=9 or not all(c['passed']for c in native['cases']):raise ValueError('Native cases failed')
    if [c['case']for c in native['cases']if c['selected']]!=['serish_mouth','repeat_serish']:raise ValueError('Selected cases differ')
    # The builder has already checked the complete original/modified spans and
    # all replacement hashes. Recheck the selected title bytes and display here
    # without repeating multi-gigabyte whole-file checks for this UI-only QA.
    title,stamp,_,preview=prepare(m['config'])
    if (ROOT/'TitleMenu_Data.bin').read_bytes()!=title or m['version']!=stamp['version']:raise ValueError('Title/version differs')
    r=next(r for r in new if r['path']==RESOURCE)
    with (ROOT/'HP.CPK').open('rb')as f:
        f.seek(r['offset'])
        if f.read(r['stored_size'])!=title:raise ValueError('Archive title differs')
    with Path(m['iso_path']).open('rb')as f:
        iso_row=next(r for r in entries if r['path']=='PSP_GAME/USRDIR/HP.CPK');f.seek(iso_row['offset']+r['offset'])
        if f.read(len(title))!=title:raise ValueError('Nested title differs')
    title_ui=Path('work/ui/title/0.1.31');box=(390,244,474,266);expected_pixels=bytes((c>>3)*255//31 for c in preview.convert('RGB').crop(box).tobytes());captures=[]
    for screen,reviewed in [('title_actual',a.reviewed_title_sha256),('main_menu',a.reviewed_menu_sha256)]:
        path=title_ui/(screen+'.png');im=Image.open(path).convert('RGB');meta=json.loads(path.with_suffix('.json').read_text());digest=sha(path.read_bytes())
        if im.size!=(480,272)or meta['version']!=m['version']or meta['loaded_executable_sha256']!=m['output_elf_sha256']or meta['format_name']!='RGBA5551':raise ValueError('Title capture identity/format differs')
        errors=[abs(x-y)for x,y in zip(im.crop(box).tobytes(),expected_pixels)];mean=sum(errors)/len(errors)
        if mean>4 or max(errors)>20:raise ValueError('Displayed version/credit differs')
        if a.write and digest!=reviewed:raise ValueError('Review title/menu capture and supply its hash')
        captures.append(dict(screen=screen,path=str(path),sha256=digest,visually_reviewed=digest==reviewed,stamp_region=list(box),mean_channel_error=mean,max_channel_error=max(errors)))
    title_proof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=sha(actual),archive_sha256=m['dialogue_cpk_sha256'],runtime_verified_title=True,
      captures=captures,title_asset_sha256=stamp['output_sha256'],credit=stamp['credit'],lines=stamp['lines'],scope='Current title and main-menu display plus selected nested title readback. Complete structural verification performed by build_local.py.',full_game_verified=False)
    proof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=sha(actual),archive_sha256=m['dialogue_cpk_sha256'],
      status='installed_tail_correction_native_instruction_checks_passed_story_scene_pending',patch=prep['serish_tail_patch'],
      native_instruction_evidence=str(native_path),native_instruction_evidence_sha256=sha(native_path.read_bytes()),native_instruction_verified=True,
      selected_records=records,changed_archive_rows=changed,other_archive_rows_exact=len(new)-1,title_verified=True,
      native_story_scene_verified=False,full_game_verified=False,limitations=['Synthetic associated-window instruction tests do not establish natural Serish scene playback.','Other characters and dialogue tails still require placement review.'])
    proof['patch']['native_instruction_verified']=True
    print(json.dumps({k:v for k,v in proof.items()if k!='patch'},indent=2))
    if not a.write:print('DRY RUN');return
    dest=UI/'validation.en.json'
    if dest.exists():raise ValueError('Fresh evidence required')
    dest.write_text(json.dumps(proof,indent=2)+'\n')
    title_dest=title_ui/'validation.en.json'
    if title_dest.exists():raise ValueError('Fresh title evidence required')
    title_dest.write_text(json.dumps(title_proof,indent=2)+'\n')
    m.update(runtime_verified_title=True,title_validation=str(title_dest),status=proof['status']);m['title_stamp']['runtime_verified']=True
    m['speech_tail_coverage']=dict(installed_in_iso=True,selected_record_count=2,unique_shots=1,native_instruction_verified=True,natural_scene_verified=False,validation=str(dest))
    mp.write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
