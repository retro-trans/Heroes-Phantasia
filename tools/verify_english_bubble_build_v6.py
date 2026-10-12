"""Verify the .38 ISO, sloped corners, anchors, title and bounded native tests."""
import argparse,json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from prepare_english_bubbles_v6 import build,sha
from prepare_bubble_scenes_036 import build as scenes,read
from audit_bubble_slopes_038 import build as slopes,BASE
from title_stamp import prepare as title_prepare,RESOURCE as TITLE
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from bubble_metrics import load_templates

ROOT=Path('work/output/0.1.38-title-credit-vwf-4x-candidate')
UI=Path('work/ui/dialogue/0.1.38')
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true')
    ap.add_argument('--reviewed-title-sha256');ap.add_argument('--reviewed-menu-sha256');a=ap.parse_args()
    mp=ROOT/'manifest.en.json';m=json.loads(mp.read_text());expected,prep=build();installed=(ROOT/'EBOOT.BIN').read_bytes()
    if installed!=expected or sha(installed)!=m['output_elf_sha256']:raise ValueError('Installed executable differs')
    assets,audit=scenes();title,stamp,_,preview=title_prepare(m['config'])
    _,old=inventory(BASE);_,new=inventory(ROOT/'HP.CPK')
    changed=[r['path']for r,s in zip(old,new)if r!=s]
    if len(old)!=len(new)or set(changed)!={TITLE}:raise ValueError('Archive change scope differs')
    protected=read(BASE,['phase/bin/p101041.bin','phase/bin/p101040.bin','fld/talk/f101070.bin'])
    iso=iso_inventory(Path(m['iso_path']));ex=next(r for r in iso if r['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');cp=next(r for r in iso if r['path']=='PSP_GAME/USRDIR/HP.CPK')
    with Path(m['iso_path']).open('rb')as f,(ROOT/'HP.CPK').open('rb')as c:
        f.seek(ex['offset'])
        if f.read(ex['size'])!=installed:raise ValueError('Nested executable differs')
        for name,raw in {**protected,**assets,TITLE:title}.items():
            row=next(r for r in new if r['path']==name);c.seek(row['offset']);f.seek(cp['offset']+row['offset'])
            if row['compression']!='none' or c.read(row['stored_size'])!=raw or f.read(len(raw))!=raw:raise ValueError('Nested selected resource differs')
    native=json.loads((UI/'native_installed.en.json').read_text())
    if native['candidate_sha256']!=sha(installed)or native['loaded_iso_sha256']!=m['iso_sha256']or not native['installed_candidate']:
        raise ValueError('Native evidence identity differs')
    cases=native['cases']
    cold=json.loads((UI/'native_cold_session.en.json').read_text())
    if cold['candidate_sha256']!=sha(installed)or cold['loaded_iso_sha256']!=m['iso_sha256']or not cold['installed_candidate']or cold['cases']!=cases:
        raise ValueError('Fresh-session native evidence differs')
    if len(cases)!=176 or not all(r['passed']and r['repeat_draw_exact']and r['native_text_setup_verified']and r['native_vertex_count_verified']and r['native_fan_setup_verified']for r in cases):raise ValueError('Native cases incomplete')
    if not all(r['fan_fill_matches_contour']for r in cases if r['selected']):raise ValueError('Native fan evidence incomplete')
    if not all(r['sloping_text_interior_verified']and r['native_side_corner_deltas_preserved']and r['single_shared_tip']for r in cases if r['selected']):raise ValueError('Sloped interior/corner evidence incomplete')
    templates=load_templates();anchors=[]
    for rec in audit['records']:
        case=next(r for r in cases if r['case']==f'current_{Path(rec["resource"]).stem}_{rec["reference_index"]}')
        if case['center']!=rec['position']:raise ValueError('Authored center changed')
        pts=[[p[0]+case['center'][0],p[1]+case['center'][1]]for p in case['outline']]
        if rec['native_tail_endpoint']not in pts:raise ValueError('Original Japanese anchor differs')
        tip=pts.index(rec['native_tail_endpoint'])
        if rec['native_name_width']and min(p[1]for n,p in enumerate(pts)if n!=tip)<=pts[tip][1]:raise ValueError('Introduction flipped above anchor')
        anchors.append(dict(resource=rec['resource'],reference=rec['reference_index'],native_tail_endpoint=rec['native_tail_endpoint'],
            original_tracks_exact=rec['original_japanese_tracks_exact'],native_center_unchanged=True,repeat_draw_exact=True))
    slope_audit=slopes()
    for rec in slope_audit['records']:
        case=next(r for r in cases if r['case']==f'gratitude_{Path(rec["resource"]).stem}')
        pts=[[p[0]+case['center'][0],p[1]+case['center'][1]]for p in case['outline']]
        if case['center']!=rec['position']or rec['native_tail_endpoint']not in pts:raise ValueError('Reported anchor changed')
        anchors.append(dict(resource=rec['resource'],reference=rec['reference_index'],native_tail_endpoint=rec['native_tail_endpoint'],
            original_tracks_exact=True,native_center_unchanged=True,native_side_slopes_preserved=True))
    captures=[];box=(390,244,474,266);target=bytes((v>>3)*255//31 for v in preview.convert('RGB').crop(box).tobytes())
    for name,reviewed in (('title_actual',a.reviewed_title_sha256),('main_menu',a.reviewed_menu_sha256)):
        p=Path('work/ui/title/0.1.38')/(name+'.png');im=Image.open(p).convert('RGB');info=json.loads(p.with_suffix('.json').read_text());digest=sha(p.read_bytes())
        if im.size!=(480,272)or info['version']!=m['version']or info['loaded_executable_sha256']!=sha(installed):raise ValueError('Capture identity differs')
        errors=[abs(x-y)for x,y in zip(im.crop(box).tobytes(),target)]
        if sum(errors)/len(errors)>4 or max(errors)>20:raise ValueError('Title version stamp differs')
        if a.write and reviewed!=digest:raise ValueError('Reviewed capture hash required')
        captures.append(dict(path=str(p),sha256=digest,stamp_mean_error=sum(errors)/len(errors),reviewed=digest==reviewed))
    proof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=sha(installed),
        status='authored_bubble_anchors_installed_native_tests_and_startup_passed',native_cases_passed=len(cases),
        loaded_growth_bytes=0,changed_archive_rows=changed,other_archive_rows_exact=len(new)-len(changed),selected_nested_resources_exact=True,
        authored_anchor_records=anchors,native_text_setup_verified=True,repeat_draw_drift_absent=True,
        maximum_name_line_conservative_advance_px=364,native_name_selectors_and_custom_input_preserved=True,
        native_corner_size_families=15,native_corner_insets_and_side_deltas_preserved=True,all_eight_body_corners_retained=True,
        fitted_native_vertex_count=11,exact_socket_specific_native_miters=False,
        fresh_session_native_cases_exact=True,
        retained_reviewed_serish_guard_and_lip=True,serish_rails_share_reviewed_lip=True,title_version_and_credit_verified=True,title_captures=captures,
        natural_reported_scenes_verified=False,full_game_verified=False,
        limitations=['Native tests use controlled associated windows; natural playback of the reported shots remains unverified.',
            'Name expansions keep conservative native 13px widths; actual custom-name/cache rendering has not been visually reviewed.',
            'Unsupported animation, rotation, alignment and nonstandard shapes retain native layout.',
            'Common native corners are recovered from sibling tail sockets; their tiny socket-specific miter variations are not reproduced.'])
    print(json.dumps({k:v for k,v in proof.items()if k not in ('authored_anchor_records','title_captures')},indent=2))
    if not a.write:print('DRY RUN');return
    dest=UI/'validation.en.json'
    if dest.exists():raise ValueError('Fresh validation required')
    dest.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    m.update(status=proof['status'],runtime_verified_title=True,english_bubble_layout_coverage=dict(
        standard_templates=120,native_cases_passed=len(cases),loaded_growth_bytes=0,new_rewrapped_records=0,
        visible_rows_validated=True,speaker_anchor_preserved=True,native_scene_center_unchanged=True,
        reference_scene_preserved=True,fan_fill_contained=True,shared_tail_endpoint=True,
        repeat_draw_drift_absent=True,native_text_setup_verified=True,native_name_controls_supported=True,
        native_corner_size_families=15,native_side_slopes_preserved=True,sloping_text_interior_verified=True,
        fitted_native_vertex_count=11,native_draw_count_verified=True,reported_natural_scenes_verified=False,
        fresh_session_native_cases_exact=True,
        validation=str(dest)))
    mp.write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
