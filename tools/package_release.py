"""Package the authorized 0.1.45 release with pinned Retro Trans; dry-run by default."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

VERSION='0.1.45'
UPSTREAM_COMMIT='b479fb63821f835ef8e134a6ee6a46c9ed5c911a'
UPSTREAM=Path('work/source/release_045/retro-trans-tools')
ORIGINAL=Path('Heroes Phantasia (Japan).iso')
BASE=Path('work/output/0.1.45-title-credit-vwf-4x-candidate')
TARGET=BASE/'Heroes-Phantasia-0.1.45-title-credit-vwf-4x-candidate.iso'
ORIGINAL_SHA='2c3583f377cdaa9132d349a0039d7f6ffe21cac093476c7746705e8af2b03b40'
TARGET_SHA='5a59a2c07b1de69cac94efcc0d1114d97b0a48c91c08de95d8a55460b6d4b4ac'
OUT=Path('work/output/0.1.45-release')
PRIVATE=Path('work/source/release_045/release-local.json')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-commit',required=True);p.add_argument('--write',action='store_true');a=p.parse_args()
    commit=subprocess.check_output(['git','rev-parse',a.source_commit+'^{commit}'],text=True).strip()
    if commit!=a.source_commit or len(commit)!=40:raise ValueError('Exact source commit required')
    head=subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()
    if head!=UPSTREAM_COMMIT or subprocess.check_output(['git','-C',str(UPSTREAM),'status','--porcelain'],text=True).strip():
        raise ValueError('Pinned release builder changed')
    assert ORIGINAL.stat().st_size==1415020544 and sha(ORIGINAL)==ORIGINAL_SHA
    assert TARGET.stat().st_size==2644776960 and sha(TARGET)==TARGET_SHA
    manifest=json.loads((BASE/'manifest.en.json').read_text(encoding='utf8'))
    assert manifest['version']==VERSION and manifest['iso_sha256']==TARGET_SHA
    assert manifest['status']=='battle_bitmap_category_readability_installed_static_and_startup_passed'
    assert not OUT.exists()
    config=dict(game_id='heroes-phantasia',game_name='Heroes Phantasia',platform='PSP',version=VERSION,source_commit=commit,
        patches=[dict(patch='Heroes-Phantasia-English-0.1.45.xdelta',edition='English',language='en',source_version='original',
        source_format='iso',target_format='iso',source=str(ORIGINAL.resolve()),target=str(TARGET.resolve()))])
    print(json.dumps(dict(version=VERSION,source_commit=commit,pinned_release_builder=UPSTREAM_COMMIT,
        source_sha256=ORIGINAL_SHA,source_bytes=ORIGINAL.stat().st_size,target_sha256=TARGET_SHA,target_bytes=TARGET.stat().st_size,
        patch=config['patches'][0]['patch'],output=str(OUT),actions=['encode xdelta','decode and verify complete target','validate canonical manifest/checksums/report']),indent=2),flush=True)
    if not a.write:print('DRY RUN: no package or private configuration writes.');return
    PRIVATE.write_text(json.dumps(config,indent=2)+'\n',encoding='utf8')
    sys.path.insert(0,str(UPSTREAM.resolve()))
    from retro_trans.release import build_release,validate_directory
    last=None
    def progress(message,fraction=None):
        nonlocal last
        if message!=last:print(message,flush=True);last=message
    result=build_release(PRIVATE,OUT,progress=progress,cache=Path('work/source/release_045/engine-cache'))
    validate_directory(OUT)
    assert result['patches'][0]['source_sha256']==ORIGINAL_SHA and result['patches'][0]['target_sha256']==TARGET_SHA
    print('Verified canonical release package:',OUT,flush=True)

if __name__=='__main__':main()
