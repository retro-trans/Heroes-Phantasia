"""Scoped 0.1.35 installed bytes, title captures and native layout evidence."""
import argparse,json
from pathlib import Path
from PIL import Image
from prepare_english_bubbles_v3 import build,sha
from prepare_bubble_reflows_034 import build as phase_build
from title_stamp import prepare as title_prepare,RESOURCE as TITLE
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from rebuild_dialogue import parse

ROOT=Path('work/output/0.1.35-title-credit-vwf-4x-candidate')
UI=Path('work/ui/dialogue/0.1.35')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true')
    ap.add_argument('--reviewed-title-sha256');ap.add_argument('--reviewed-menu-sha256');a=ap.parse_args()
    mp=ROOT/'manifest.en.json';m=json.loads(mp.read_text());expected,prep=build()
    installed=(ROOT/'EBOOT.BIN').read_bytes()
    if installed!=expected or sha(installed)!=m['output_elf_sha256']:raise ValueError('Executable differs')
    _,phases,layout=phase_build();title,stamp,_,preview=title_prepare(m['config'])
    _,old=inventory(Path('work/output/0.1.34-title-credit-vwf-4x-candidate/HP.CPK'));_,new=inventory(ROOT/'HP.CPK')
    changes=[r['path']for r,s in zip(old,new)if r!=s]
    if len(new)!=len(old)or set(changes)!={TITLE}:raise ValueError('Unselected archive row changed')
    iso=iso_inventory(Path(m['iso_path']));exe=next(r for r in iso if r['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');archive=next(r for r in iso if r['path']=='PSP_GAME/USRDIR/HP.CPK')
    with Path(m['iso_path']).open('rb')as f,(ROOT/'HP.CPK').open('rb')as c:
        f.seek(exe['offset'])
        if f.read(exe['size'])!=installed:raise ValueError('Nested executable differs')
        for name,raw in {**phases,TITLE:title}.items():
            row=next(r for r in new if r['path']==name)
            if row['compression']!='none':raise ValueError('Selected resource compressed')
            c.seek(row['offset']);f.seek(archive['offset']+row['offset'])
            if c.read(row['stored_size'])!=raw or f.read(len(raw))!=raw:raise ValueError('Selected installed bytes differ')
    native=json.loads((UI/'native_installed.en.json').read_text())
    if native['candidate_sha256']!=sha(installed)or native['loaded_iso_sha256']!=m['iso_sha256']or not native['installed_candidate']or len(native['cases'])!=163 or not all(r['passed']for r in native['cases']):raise ValueError('Native geometry proof differs')
    if not all(r.get('fan_fill_matches_contour') for r in native['cases'] if r['selected']):raise ValueError('Triangle-fan fill proof missing')
    fill=json.loads((UI/'fill_regression.en.json').read_text())
    if fill['candidate_sha256']!=sha(installed)or fill['iso_sha256']!=m['iso_sha256']or len(fill['records'])!=3:
        raise ValueError('Fill regression identity differs')
    if not all(r['old_absolute_triangle_area_excess_px2']>0 and r['new_triangle_area_excess_px2']==0 for r in fill['records']):raise ValueError('Reported fill regressions differ')
    protected=[]
    with Path('work/output/0.1.34-title-credit-vwf-4x-candidate/HP.CPK').open('rb')as f:
        for name in ('phase/bin/p101040.bin','phase/bin/p101041.bin'):
            row=next(r for r in old if r['path']==name)
            if row['compression']!='none':raise ValueError('Prior phase unexpectedly compressed')
            f.seek(row['offset']);before=parse(name,f.read(row['stored_size']));after=parse(name,phases[name])
            for ref in (0,1,4,16,23,27):
                if before['spans'][before['refs'][ref][1]][0]!=after['spans'][after['refs'][ref][1]][0]:raise ValueError('Protected dialogue changed')
            if before['refs'][27]!=after['refs'][27]:raise ValueError('Reference scene association changed')
            protected.append(dict(resource=name,unchanged_references=[0,1,4,16,23,27],reference_scene_tail_anchor_preserved=True))
    box=(390,244,474,266);target=bytes((v>>3)*255//31 for v in preview.convert('RGB').crop(box).tobytes());captures=[]
    for name,reviewed in (('title_actual',a.reviewed_title_sha256),('main_menu',a.reviewed_menu_sha256)):
        p=Path('work/ui/title/0.1.35')/(name+'.png');im=Image.open(p).convert('RGB');info=json.loads(p.with_suffix('.json').read_text());digest=sha(p.read_bytes())
        if im.size!=(480,272)or info['version']!=m['version']or info['loaded_executable_sha256']!=sha(installed):raise ValueError('Title capture identity differs')
        errors=[abs(x-y)for x,y in zip(im.crop(box).tobytes(),target)]
        if sum(errors)/len(errors)>4 or max(errors)>20:raise ValueError('Version stamp differs')
        if a.write and digest!=reviewed:raise ValueError('Reviewed title/menu hash required')
        captures.append(dict(path=str(p),sha256=digest,reviewed=digest==reviewed,stamp_mean_error=sum(errors)/len(errors)))
    natural=None
    if (UI/'natural_opening.en.json').exists():
        natural=json.loads((UI/'natural_opening.en.json').read_text())
        if natural['iso_sha256']!=m['iso_sha256']or natural['executable_sha256']!=sha(installed)or not natural['custom_geometry_active']:raise ValueError('Natural scene proof differs')
    proof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=sha(installed),
        status='english_bubble_fan_and_single_tip_installed_native_cases_and_startup_passed',changed_archive_rows=changes,other_archive_rows_exact=len(new)-1,
        selected_nested_resources_exact=True,loaded_growth_bytes=0,geometry=prep['english_bubble_layout'],
        native_cases_passed=163,native_evidence=str(UI/'native_installed.en.json'),natural_opening_verified=natural is not None,
        fill_regression=fill,
        current_dialogue_unchanged=True,protected_reference_scenes=protected,title_version_and_credit_verified=True,title_captures=captures,full_game_verified=False,
        limitations=['The reported story scenes have native geometry evidence; natural scene captures remain unverified.',
            'Only supported stationary centered standard bubbles use the custom body; other states restore native layout.',
            'The source text and scene anchors remain unchanged; automatic mouth tracking is not implemented.',
            'Border rails now meet the outline endpoint; the reviewed Serish leaf retains its existing miter.'])
    print(json.dumps(proof,indent=2))
    if not a.write:print('DRY RUN');return
    dest=UI/'validation.en.json'
    if dest.exists():raise ValueError('Fresh evidence required')
    dest.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    m.update(status=proof['status'],runtime_verified_title=True,english_bubble_layout_coverage=dict(
        standard_templates=120,native_cases_passed=163,loaded_growth_bytes=0,new_rewrapped_records=0,
        visible_rows_validated=True,speaker_anchor_preserved=True,reference_scene_preserved=True,
        fan_fill_contained=True,shared_tail_endpoint=True,
        natural_opening_verified=natural is not None,reported_natural_scenes_verified=False,validation=str(dest)))
    m['title_stamp']['runtime_verified']=True;mp.write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
