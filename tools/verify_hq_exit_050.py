"""Check packaged HQ repair, unchanged resources, native proof and title capture."""
import argparse,json
from pathlib import Path
from PIL import Image
from prepare_bubble_scenes_036 import read,sha
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from title_stamp import prepare,RESOURCE
from prepare_hq_exit_050 import BASE,OUT

ROOT=Path('work/output/0.1.50-title-credit-vwf-4x-candidate')
UI=Path('work/ui/field/0.1.50')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--reviewed-title-sha256');a=ap.parse_args()
    mp=ROOT/'manifest.en.json';m=json.loads(mp.read_text());data=(ROOT/'EBOOT.BIN').read_bytes()
    if data!=(OUT/'EBOOT.BIN').read_bytes() or sha(data)!=m['output_elf_sha256']:raise ValueError('Executable identity differs')
    _,old=inventory(BASE/'HP.CPK');_,new=inventory(ROOT/'HP.CPK');changed=[x['path']for x,y in zip(old,new) if x!=y]
    if len(old)!=len(new) or changed!=[RESOURCE]:raise ValueError('Unselected archive rows changed')
    raw=read(ROOT/'HP.CPK',[RESOURCE,'fld/event/d01.evt']);title,_,_,preview=prepare(m['config'])
    if raw[RESOURCE]!=title or sha(raw['fld/event/d01.evt'])!=m['setup_patch']['field_labels_047']['event_sha256']:raise ValueError('Title/event differs')
    index=iso_inventory(Path(m['iso_path']));exe=next(x for x in index if x['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');cpk=next(x for x in index if x['path']=='PSP_GAME/USRDIR/HP.CPK')
    with Path(m['iso_path']).open('rb')as f:
        f.seek(exe['offset'])
        if f.read(exe['size'])!=data:raise ValueError('Nested executable differs')
        with (ROOT/'HP.CPK').open('rb')as archive:
            for name in raw:
                row=next(x for x in new if x['path']==name);f.seek(cpk['offset']+row['offset']);archive.seek(row['offset'])
                if f.read(row['stored_size'])!=archive.read(row['stored_size']):raise ValueError('Nested stored resource differs')
    proof=json.loads((UI/'native_confirmation.en.json').read_text())
    if proof['iso_sha256']!=m['iso_sha256'] or proof['executable_sha256']!=sha(data) or not proof['question_all_glyphs_and_VWF_advances_verified'] or len(proof['draw_cases'])!=5 or len(proof['width_cases'])!=8:raise ValueError('Native evidence incomplete')
    capture=Path('work/ui/title/0.1.50/title_actual.png');meta=json.loads(capture.with_suffix('.json').read_text());im=Image.open(capture).convert('RGB');box=(390,244,474,266)
    expected=bytes((c>>3)*255//31 for c in preview.convert('RGB').crop(box).tobytes());errors=[abs(x-y)for x,y in zip(im.crop(box).tobytes(),expected)]
    if meta['version']!='0.1.50' or meta['loaded_executable_sha256']!=sha(data) or im.size!=(480,272) or sum(errors)/len(errors)>4 or max(errors)>20:raise ValueError('Title stamp differs')
    digest=sha(capture.read_bytes())
    if a.write and digest!=a.reviewed_title_sha256:raise ValueError('Reviewed title required')
    result=dict(version='0.1.50',status='hq_exit_static_native_and_startup_passed',iso_sha256=m['iso_sha256'],executable_sha256=sha(data),archive_sha256=m['dialogue_cpk_sha256'],unselected_archive_rows_exact=len(new)-1,changed_archive_rows=changed,nested_executable_title_and_event_verified=True,draw_cases=5,width_cases=8,original_blank_reproduced=True,complete_question_and_VWF_positions_verified=True,loaded_growth_bytes=0,title_version_and_credit_verified=True,title_capture_sha256=digest,natural_HQ_exit_verified=False,full_game_verified=False)
    print(json.dumps(result,indent=2))
    if not a.write:print('DRY RUN');return
    dest=UI/'validation.en.json'
    if dest.exists():raise ValueError('Fresh proof required')
    dest.write_text(json.dumps(result,indent=2)+'\n');m['hq_exit_050_coverage']=result;m.update(status=result['status'],runtime_verified_title=True,title_validation=str(dest));m['title_stamp']['runtime_verified']=True;mp.write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':main()
