"""Package authorized 0.1.50 full/0.1.45-upgrade patches; dry-run by default."""
import argparse,json,subprocess,sys
from pathlib import Path
from package_release import sha,ORIGINAL,ORIGINAL_SHA

VERSION='0.1.50'
PIN='540a61cb6bb50a6ec8f2a52bc4e89a25226c9061'
UPSTREAM=Path('work/source/release_050/retro-trans-tools')
BASE=Path('work/output/0.1.50-title-credit-vwf-4x-candidate')
TARGET=BASE/'Heroes-Phantasia-0.1.50-title-credit-vwf-4x-candidate.iso'
TARGET_SHA='fa420a494942817a7498615716b8b43bbc5ff4a817abb3cdb4354a90e89df8b8'
PREVIOUS=Path('work/output/0.1.45-title-credit-vwf-4x-candidate/Heroes-Phantasia-0.1.45-title-credit-vwf-4x-candidate.iso')
PREVIOUS_SHA='5a59a2c07b1de69cac94efcc0d1114d97b0a48c91c08de95d8a55460b6d4b4ac'
OUT=Path('work/output/0.1.50-release')
PRIVATE=Path('work/source/release_050/release-local.json')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-commit',required=True);p.add_argument('--write',action='store_true');a=p.parse_args()
    commit=subprocess.check_output(['git','rev-parse',a.source_commit+'^{commit}'],text=True).strip()
    if commit!=a.source_commit or len(commit)!=40:raise ValueError('Exact source commit required')
    head=subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()
    if head!=PIN or subprocess.check_output(['git','-C',str(UPSTREAM),'status','--porcelain'],text=True).strip():raise ValueError('Pinned packager differs')
    for path,digest,size in [(ORIGINAL,ORIGINAL_SHA,1415020544),(PREVIOUS,PREVIOUS_SHA,2644776960),(TARGET,TARGET_SHA,2647455744)]:
        if path.stat().st_size!=size or sha(path)!=digest:raise ValueError('Frozen input differs: '+str(path))
    m=json.loads((BASE/'manifest.en.json').read_text())
    proof=json.loads(Path('work/ui/field/0.1.50/validation.en.json').read_text())
    if m['version']!=VERSION or m['iso_sha256']!=TARGET_SHA or m['status']!='hq_exit_static_native_and_startup_passed' or proof!=m['hq_exit_050_coverage']:raise ValueError('Reviewed .50 proof differs')
    if OUT.exists():raise ValueError('Fresh package directory required')
    rows=[]
    for source,version,name in [(ORIGINAL,'original','Heroes-Phantasia-English-0.1.50.xdelta'),(PREVIOUS,'0.1.45','Heroes-Phantasia-English-0.1.45-to-0.1.50.xdelta')]:
        rows.append(dict(patch=name,edition='English',language='en',source_version=version,source_format='iso',target_format='iso',source=str(source.resolve()),target=str(TARGET.resolve())))
    config=dict(game_id='heroes-phantasia',game_name='Heroes Phantasia',platform='PSP',version=VERSION,source_commit=commit,patches=rows)
    print(json.dumps(dict(version=VERSION,source_commit=commit,packager_commit=PIN,patches=[x['patch']for x in rows],target_bytes=TARGET.stat().st_size,target_sha256=TARGET_SHA,roundtrips_required=2),indent=2),flush=True)
    if not a.write:print('DRY RUN: no package writes.');return
    PRIVATE.write_text(json.dumps(config,indent=2)+'\n')
    sys.path.insert(0,str(UPSTREAM.resolve()))
    from retro_trans.release import build_release,validate_directory
    last=None
    def progress(message,fraction=None):
        nonlocal last
        if message!=last:print(message,flush=True);last=message
    result=build_release(PRIVATE,OUT,progress=progress,cache=Path('work/source/release_045/engine-cache'))
    validate_directory(OUT)
    if len(result['patches'])!=2 or any(x['target_sha256']!=TARGET_SHA for x in result['patches']):raise ValueError('Canonical result differs')
    print('Both release patches reproduce the exact reviewed .50 ISO.',flush=True)

if __name__=='__main__':main()
