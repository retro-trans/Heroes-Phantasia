"""Scoped world-map ISO readbacks and current native title/loaded-string evidence."""
import argparse, json
from pathlib import Path
from PIL import Image
from prepare_world_map_ui import build, sha
from prepare_hold_banner import prepare as prepare_banner, RESOURCE as BANNER
from title_stamp import prepare as prepare_title, RESOURCE as TITLE
from unpack_cpk import inventory as cpk_inventory, crilayla
from inspect_iso import inventory as iso_inventory

ROOT = Path('work/output/0.1.32-title-credit-vwf-4x-candidate')
UI = Path('work/ui/world_map/0.1.32')

def extract(path, row):
    with path.open('rb') as f:
        f.seek(row['offset']); raw = f.read(row['stored_size'])
    return crilayla(raw, row['extract_size']) if row['compression'] == 'CRILAYLA' else raw

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--reviewed-title-sha256'); ap.add_argument('--reviewed-menu-sha256')
    a = ap.parse_args(); mp = ROOT/'manifest.en.json'; m = json.loads(mp.read_text())
    expected, prep, _ = build(); installed = (ROOT/'EBOOT.BIN').read_bytes()
    if installed != expected or sha(installed) != m['output_elf_sha256']:
        raise ValueError('Current executable differs from guarded preparation')
    banner, bitmap, _, _ = prepare_banner()
    title, stamp, _, preview = prepare_title(m['config'])
    _, old = cpk_inventory(Path('work/output/0.1.31-title-credit-vwf-4x-candidate/HP.CPK'))
    _, new = cpk_inventory(ROOT/'HP.CPK')
    changed = [r['path'] for r,s in zip(old,new) if r != s]
    if len(old) != len(new) or set(changed) != {BANNER, TITLE}:
        raise ValueError('Unselected CPK rows changed')
    before = next(r for r in old if r['path'] == BANNER)
    if sha(extract(Path('work/output/0.1.31-title-credit-vwf-4x-candidate/HP.CPK'), before)) != bitmap['source_sha256']:
        raise ValueError('Original compressed banner source differs')
    iso = iso_inventory(Path(m['iso_path']))
    er = next(r for r in iso if r['path'] == 'PSP_GAME/SYSDIR/EBOOT.BIN')
    ar = next(r for r in iso if r['path'] == 'PSP_GAME/USRDIR/HP.CPK')
    with Path(m['iso_path']).open('rb') as f:
        f.seek(er['offset'])
        if f.read(er['size']) != installed: raise ValueError('Nested executable differs')
        for name, raw in ((BANNER, banner), (TITLE, title)):
            row = next(r for r in new if r['path'] == name)
            if row['compression'] != 'none' or extract(ROOT/'HP.CPK', row) != raw:
                raise ValueError('Installed selected resource differs')
            f.seek(ar['offset']+row['offset'])
            if f.read(len(raw)) != raw: raise ValueError('Nested selected resource differs')
    native_path = UI/'loaded_strings.en.json'; native = json.loads(native_path.read_text())
    for k,v in (('version',m['version']),('iso_sha256',m['iso_sha256']),('executable_sha256',m['output_elf_sha256']),('archive_sha256',m['dialogue_cpk_sha256'])):
        if native[k] != v: raise ValueError('Native proof identity differs')
    if len(native['entries']) != 4 or not all(r['complete_target_and_controls_exact'] for r in native['entries']):
        raise ValueError('Native loaded strings fail')
    box = (390,244,474,266)
    pixels = bytes((c>>3)*255//31 for c in preview.convert('RGB').crop(box).tobytes())
    captures = []
    for name, reviewed in (('title_actual',a.reviewed_title_sha256),('main_menu',a.reviewed_menu_sha256)):
        path = Path('work/ui/title/0.1.32')/(name+'.png')
        im = Image.open(path).convert('RGB'); info = json.loads(path.with_suffix('.json').read_text()); digest = sha(path.read_bytes())
        if im.size != (480,272) or info['version'] != m['version'] or info['loaded_executable_sha256'] != m['output_elf_sha256'] or info['format_name'] != 'RGBA5551':
            raise ValueError('Capture format or identity differs')
        errors = [abs(x-y) for x,y in zip(im.crop(box).tobytes(),pixels)]
        if sum(errors)/len(errors) > 4 or max(errors) > 20:
            raise ValueError('Displayed version or credit differs')
        if a.write and digest != reviewed: raise ValueError('Supply reviewed screenshot hash')
        captures.append(dict(path=str(path),sha256=digest,visually_reviewed=digest==reviewed,
            stamp_region=list(box),mean_channel_error=sum(errors)/len(errors),max_channel_error=max(errors)))
    proof = dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=sha(installed),archive_sha256=m['dialogue_cpk_sha256'],
        status='world_map_translation_installed_startup_and_loaded_string_checks_passed',
        entries=prep['world_map_ui_patch']['entries'],loaded_growth_bytes=0,new_relocations=0,
        three_base_loader_checks_passed=True,native_loaded_strings_verified=True,native_loaded_strings_evidence=str(native_path),
        banner_target=bitmap['target'],banner_sha256=sha(banner),banner_palette_and_nonpixel_data_exact=True,
        nested_executable_title_banner_exact=True,changed_archive_rows=changed,other_archive_rows_exact=len(new)-2,
        title_version_and_credit_verified=True,title_captures=captures,full_game_verified=False,
        natural_world_map_display_verified=False,native_banner_display_verified=False,
        limitations=['Map prompt/menu and headquarters gameplay placement require current native scene captures.',
            'Other Japanese text and unreviewed speech-bubble placements are outside this build scope.'],
        validation_policy='Builder already verified complete ISO/archive spans and hashes; this check rechecks only selected nested bytes and current runtime evidence.')
    print(json.dumps(proof,indent=2))
    if not a.write: print('DRY RUN: no evidence or manifest updated.'); return
    dest = UI/'validation.en.json'
    if dest.exists(): raise ValueError('Fresh validation required')
    dest.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    m.update(status=proof['status'],runtime_verified_title=True,title_validation=str(dest))
    m['title_stamp']['runtime_verified'] = True
    m['world_map_translation_coverage'] = dict(labels_installed=4,unique_texts=4,bitmap_resource=BANNER,
        bitmap_target=bitmap['target'],bitmap_installed=True,static_bitmap_reviewed=True,
        native_loaded_strings_verified=True,natural_world_map_display_verified=False,
        native_banner_display_verified=False,validation=str(dest))
    mp.write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')

if __name__ == '__main__': main()
