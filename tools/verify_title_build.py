"""Verify generated title stamp and reviewed native title/menu captures.

Preview by default. --write saves evidence and updates the candidate manifest.
Capture hashes must be supplied after visually reviewing both images.
"""
import argparse
import hashlib
import json
import pathlib

from PIL import Image
from append_cpk import sha
from inspect_iso import inventory as iso_inventory
from unpack_cpk import inventory as cpk_inventory
from title_stamp import prepare, RESOURCE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=pathlib.Path, default=pathlib.Path('work/output/0.1.8-title-credit-vwf-4x-candidate/manifest.en.json'))
    parser.add_argument('--title', type=pathlib.Path, default=pathlib.Path('work/ui/title/0.1.8/title.png'))
    parser.add_argument('--menu', type=pathlib.Path, default=pathlib.Path('work/ui/title/0.1.8/menu.png'))
    parser.add_argument('--reviewed-title-sha256')
    parser.add_argument('--reviewed-menu-sha256')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    title, stamp, original, preview = prepare(manifest['config'])
    assert manifest['version'] == manifest['config']['version'] == stamp['version']
    assert {k:v for k,v in manifest['title_stamp'].items() if k != 'runtime_verified'} == {k:v for k,v in stamp.items() if k != 'runtime_verified'}
    root = args.manifest.parent
    assert (root / 'TitleMenu_Data.bin').read_bytes() == title
    assert sha(root / 'EBOOT.BIN') == manifest['output_elf_sha256']
    cpk = root / 'HP.CPK'; assert sha(cpk) == manifest['dialogue_cpk_sha256']
    h, rows = cpk_inventory(cpk); row = next(r for r in rows if r['path'] == RESOURCE)
    with cpk.open('rb') as f:
        f.seek(row['offset']); assert f.read(row['stored_size']) == title
    iso = pathlib.Path(manifest['iso_path']); assert sha(iso) == manifest['iso_sha256']
    inventory = iso_inventory(iso)
    with iso.open('rb') as f:
        for replacement in manifest['iso_replacements']:
            r = next(r for r in inventory if r['path'] == replacement['path'])
            assert (r['offset'],r['size']) == (replacement['offset'],replacement['size'])
            f.seek(r['offset']); remaining=r['size']; digest=hashlib.sha256()
            while remaining:
                data=f.read(min(8*1024*1024,remaining)); assert data
                digest.update(data);remaining-=len(data)
            assert digest.hexdigest()==replacement['sha256']
    captures=[]
    box=(390,244,474,266)
    expected=preview.convert('RGB').crop(box)
    # Exact format conversion used by the native RGBA5551 framebuffer capture.
    expected_bytes=bytes((c>>3)*255//31 for c in expected.tobytes())
    for name,path,reviewed in [('title',args.title,args.reviewed_title_sha256),('menu',args.menu,args.reviewed_menu_sha256)]:
        im=Image.open(path).convert('RGB'); assert im.size==(480,272)
        meta=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        assert meta['version']==manifest['version'] and meta['loaded_executable_sha256']==manifest['output_elf_sha256']
        assert meta['capture_method']=='software_renderer_emulated_VRAM' and meta['format_name']=='RGBA5551'
        actual=im.crop(box).tobytes()
        differences=[abs(a-b) for a,b in zip(actual,expected_bytes)]
        mean=sum(differences)/len(differences)
        if mean>4 or max(differences)>20:
            raise ValueError('Displayed stamp/background differs from generated texture: '+name)
        digest=sha(path)
        if args.write and reviewed!=digest:
            raise ValueError('Visually review '+name+' and supply its exact screenshot SHA256')
        captures.append(dict(screen=name,path=str(path),sha256=digest,stamp_region=list(box),mean_channel_error=mean,max_channel_error=max(differences),visually_reviewed=reviewed==digest))
    proof=dict(version=manifest['version'],status='title_credit_and_menu_display_qa_passed',
               iso_sha256=manifest['iso_sha256'],executable_sha256=manifest['output_elf_sha256'],
               archive_sha256=manifest['dialogue_cpk_sha256'],runtime_verified_title=True,
               title_asset_sha256=stamp['output_sha256'],credit=stamp['credit'],lines=stamp['lines'],
               captures=captures,scope='Bottom-right title stamp, native title screen and transition to main menu. Other changed content requires its separate runtime evidence.',
               full_game_verified=False)
    print(json.dumps(proof,indent=2))
    if not args.write:
        print('DRY RUN: no evidence or manifest written.');return
    out=args.title.parent/'validation.en.json'
    if out.exists():raise ValueError('Evidence output must be fresh')
    out.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    manifest.update(status=proof['status'],runtime_verified_title=True,title_validation=str(out))
    manifest['title_stamp']['runtime_verified']=True
    args.manifest.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Saved reviewed title/menu display evidence.')


if __name__=='__main__':main()
