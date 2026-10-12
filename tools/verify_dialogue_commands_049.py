"""Verify selected .49 ISO/archive and current isolated runtime evidence."""
import argparse,json
from pathlib import Path
from PIL import Image
from prepare_bubble_scenes_036 import read,sha
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from title_stamp import prepare,RESOURCE

ROOT=Path('work/output/0.1.49-title-credit-vwf-4x-candidate')
BASE=Path('work/output/0.1.47-title-credit-vwf-4x-candidate')
UI=Path('work/ui/dialogue/0.1.49')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--reviewed-title-sha256');ap.add_argument('--reviewed-menu-sha256');a=ap.parse_args()
    mp=ROOT/'manifest.en.json';m=json.loads(mp.read_text());e=(ROOT/'EBOOT.BIN').read_bytes();p=m['setup_patch']
    if e!=(Path('work/output/0.1.49-dialogue-command-assets')/'EBOOT.BIN').read_bytes()or sha(e)!=m['output_elf_sha256']:raise ValueError('Executable readback differs')
    _,old=inventory(BASE/'HP.CPK');_,new=inventory(ROOT/'HP.CPK');changed=[x['path']for x,y in zip(old,new)if x!=y]
    names=['phase/bin/p101110.bin','phase/bin/p101111.bin'];expected=set(names+[RESOURCE])
    if len(old)!=len(new)or set(changed)!=expected:raise ValueError('Unselected archive rows changed')
    raw=read(ROOT/'HP.CPK',names+[RESOURCE,'fld/event/d01.evt'])
    title,_,_,preview=prepare(m['config'])
    if raw[RESOURCE]!=title or sha(raw['fld/event/d01.evt'])!=p['field_labels_047']['event_sha256']:raise ValueError('Title or original notice event changed')
    for name in names:
        if raw[name]!=(Path('work/output/0.1.49-dialogue-command-assets')/name).read_bytes():raise ValueError('Installed Lina resource differs')
    index=iso_inventory(Path(m['iso_path']));exe=next(x for x in index if x['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');archive=next(x for x in index if x['path']=='PSP_GAME/USRDIR/HP.CPK')
    with Path(m['iso_path']).open('rb')as f:
        f.seek(exe['offset'])
        if f.read(exe['size'])!=e:raise ValueError('Nested executable changed')
        for name in expected:
            row=next(x for x in new if x['path']==name);f.seek(archive['offset']+row['offset'])
            if row['compression']!='none'or f.read(row['stored_size'])!=raw[name]:raise ValueError('Nested selected resource changed')
    native=json.loads((UI/'native_geometry.en.json').read_text());loaded=json.loads((UI/'loaded_strings.en.json').read_text())
    if native['loaded_iso_sha256']!=m['iso_sha256']or native['candidate_sha256']!=sha(e)or not native['installed_candidate']or not native['native_instruction_verified']:raise ValueError('Current native evidence differs')
    lina=[c for c in native['cases']if c['case'].startswith('lina_')]
    if len(lina)!=2 or any(c['visible_lines']!=6 or not all(c[k]for k in ('passed','sloping_text_interior_verified','original_tail_ray_verified','tail_dark_outline_verified','repeat_draw_exact','fan_fill_matches_contour'))for c in lina):raise ValueError('Native Lina fit not proved')
    if loaded['iso_sha256']!=m['iso_sha256']or loaded['executable_sha256']!=sha(e)or len(loaded['labels'])!=36 or len(loaded['notices'])!=12:raise ValueError('Incomplete/current live labels evidence')
    captures=[];box=(390,244,474,266);pixels=bytes((c>>3)*255//31 for c in preview.convert('RGB').crop(box).tobytes())
    for name,reviewed in [('title_actual',a.reviewed_title_sha256),('main_menu',a.reviewed_menu_sha256)]:
        path=Path('work/ui/title/0.1.49')/(name+'.png');im=Image.open(path).convert('RGB');meta=json.loads(path.with_suffix('.json').read_text());digest=sha(path.read_bytes())
        if im.size!=(480,272)or meta['version']!='0.1.49'or meta['loaded_executable_sha256']!=sha(e):raise ValueError('Capture identity differs')
        errors=[abs(x-y)for x,y in zip(im.crop(box).tobytes(),pixels)]
        if sum(errors)/len(errors)>4 or max(errors)>20 or (a.write and digest!=reviewed):raise ValueError('Reviewed title stamp differs')
        captures.append(dict(path=str(path),sha256=digest,mean_stamp_channel_error=sum(errors)/len(errors),visually_reviewed=digest==reviewed))
    result=dict(version='0.1.49',status='dialogue_commands_static_native_regression_and_startup_passed',executable_sha256=sha(e),iso_sha256=m['iso_sha256'],archive_sha256=m['dialogue_cpk_sha256'],changed_archive_rows=changed,unselected_archive_rows_exact=len(new)-3,nested_executable_and_selected_assets_exact=True,native_geometry_cases=len(native['cases']),native_lina_fit_verified=True,loaded_labels=36,loaded_notices=12,measurement_cases=21,scanner_cases=10,loaded_growth_bytes=0,title_version_and_credit_verified=True,captures=captures,natural_lina_and_command_menu_display_verified=False,full_game_verified=False)
    print(json.dumps(result,indent=2))
    if not a.write:print('DRY RUN');return
    dest=UI/'validation.en.json'
    if dest.exists():raise ValueError('Fresh proof required')
    dest.write_text(json.dumps(result,indent=2)+'\n');m['dialogue_commands_049_coverage']=result;m.update(status=result['status'],runtime_verified_title=True,title_validation=str(dest));m['title_stamp']['runtime_verified']=True;mp.write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':main()
