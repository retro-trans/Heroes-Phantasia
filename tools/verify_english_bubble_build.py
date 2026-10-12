"""Scoped 0.1.33 installed bytes, title captures and native layout evidence."""
import argparse,json
from pathlib import Path
from PIL import Image
from prepare_english_bubbles import build,sha
from prepare_kogoro_layout import build as phase_build
from title_stamp import prepare as title_prepare,RESOURCE as TITLE
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory

ROOT=Path('work/output/0.1.33-title-credit-vwf-4x-candidate')
UI=Path('work/ui/dialogue/0.1.33')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true')
    ap.add_argument('--reviewed-title-sha256');ap.add_argument('--reviewed-menu-sha256');a=ap.parse_args()
    mp=ROOT/'manifest.en.json';m=json.loads(mp.read_text());expected,prep=build()
    installed=(ROOT/'EBOOT.BIN').read_bytes()
    if installed!=expected or sha(installed)!=m['output_elf_sha256']:raise ValueError('Executable differs')
    _,phases,layout=phase_build();title,stamp,_,preview=title_prepare(m['config'])
    _,old=inventory(Path('work/output/0.1.32-title-credit-vwf-4x-candidate/HP.CPK'));_,new=inventory(ROOT/'HP.CPK')
    changes=[r['path']for r,s in zip(old,new)if r!=s]
    if len(new)!=len(old)or set(changes)!=set(phases)|{TITLE}:raise ValueError('Unselected archive row changed')
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
    if native['candidate_sha256']!=sha(installed)or native['loaded_iso_sha256']!=m['iso_sha256']or not native['installed_candidate']or len(native['cases'])!=143 or not all(r['passed']for r in native['cases']):raise ValueError('Native geometry proof differs')
    box=(390,244,474,266);target=bytes((v>>3)*255//31 for v in preview.convert('RGB').crop(box).tobytes());captures=[]
    for name,reviewed in (('title_actual',a.reviewed_title_sha256),('main_menu',a.reviewed_menu_sha256)):
        p=Path('work/ui/title/0.1.33')/(name+'.png');im=Image.open(p).convert('RGB');info=json.loads(p.with_suffix('.json').read_text());digest=sha(p.read_bytes())
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
        status='custom_english_bubbles_installed_native_cases_and_startup_passed',changed_archive_rows=changes,other_archive_rows_exact=len(new)-3,
        selected_nested_resources_exact=True,loaded_growth_bytes=0,geometry=prep['english_bubble_layout'],
        native_cases_passed=143,native_evidence=str(UI/'native_installed.en.json'),natural_opening_verified=natural is not None,
        kogoro_layout=layout,title_version_and_credit_verified=True,title_captures=captures,full_game_verified=False,
        limitations=['Kogoro natural scene rendering and mouth landmark remain unverified.',
            'Only supported stationary centered standard bubbles use the custom body; other states restore native layout.',
            'Only the reported Kogoro record is rewrapped in this build; the offline wrapper does not rewrite the full script.',
            'Tail endpoints remain authored except the previously reviewed Serish shot; automatic mouth tracking is not implemented.'])
    print(json.dumps(proof,indent=2))
    if not a.write:print('DRY RUN');return
    dest=UI/'validation.en.json'
    if dest.exists():raise ValueError('Fresh evidence required')
    dest.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    m.update(status=proof['status'],runtime_verified_title=True,english_bubble_layout_coverage=dict(
        standard_templates=120,native_cases_passed=143,loaded_growth_bytes=0,kogoro_record_variants=2,
        natural_opening_verified=natural is not None,kogoro_natural_scene_verified=False,validation=str(dest)))
    m['title_stamp']['runtime_verified']=True;mp.write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
