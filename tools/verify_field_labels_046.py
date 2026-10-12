"""Verify nested build spans and scoped current runtime evidence; dry by default."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from prepare_field_labels_046 import BASE, EVENT, EVENT_SHA, build, sha
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from prepare_bubble_scenes_036 import read
from title_stamp import prepare, RESOURCE

ROOT = Path('work/output/0.1.46-title-credit-vwf-4x-candidate')
UI = Path('work/ui/field_labels/0.1.46')
TITLE = Path('work/ui/title/0.1.46')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--version', choices=['0.1.46','0.1.47'], default='0.1.46')
    ap.add_argument('--reviewed-title-sha256'); ap.add_argument('--reviewed-menu-sha256')
    args = ap.parse_args()
    root = Path('work/output')/(args.version+'-title-credit-vwf-4x-candidate')
    ui = Path('work/ui/field_labels')/args.version
    title_ui = Path('work/ui/title')/args.version
    builder = build
    if args.version == '0.1.47':
        from prepare_field_labels_047 import build as builder
    mp = root/'manifest.en.json'; manifest = json.loads(mp.read_text(encoding='utf8'))
    expected, prep, _ = builder(); installed = (root/'EBOOT.BIN').read_bytes()
    if installed != expected or sha(installed) != manifest['output_elf_sha256']:
        raise ValueError('Installed executable differs from guarded preparation')
    _, old = inventory(BASE/'HP.CPK'); _, new = inventory(root/'HP.CPK')
    changed = [a['path'] for a,b in zip(old,new) if a != b]
    if len(old) != len(new) or changed != [RESOURCE]:
        raise ValueError('Unexpected changed archive rows')
    title, _, _, preview = prepare(manifest['config'])
    selected = read(root/'HP.CPK', [RESOURCE, EVENT])
    if selected[RESOURCE] != title or sha(selected[EVENT]) != EVENT_SHA:
        raise ValueError('Title or untouched event resource differs')
    index = iso_inventory(Path(manifest['iso_path']))
    exe = next(row for row in index if row['path'] == 'PSP_GAME/SYSDIR/EBOOT.BIN')
    archive = next(row for row in index if row['path'] == 'PSP_GAME/USRDIR/HP.CPK')
    with Path(manifest['iso_path']).open('rb') as f:
        f.seek(exe['offset'])
        if f.read(exe['size']) != installed: raise ValueError('Nested executable differs')
        row = next(row for row in new if row['path'] == RESOURCE)
        f.seek(archive['offset']+row['offset'])
        if row['compression'] != 'none' or f.read(len(title)) != title:
            raise ValueError('Nested title stamp differs')
    native = json.loads((ui/'loaded_strings.en.json').read_text(encoding='utf8'))
    for key,value in (('version',manifest['version']),('iso_sha256',manifest['iso_sha256']),
                      ('executable_sha256',manifest['output_elf_sha256']),('archive_sha256',manifest['dialogue_cpk_sha256'])):
        if native[key] != value: raise ValueError('Current runtime evidence identity differs')
    if len(native['labels']) != 28 or len(native['notices']) != 12:
        raise ValueError('Incomplete live string scope')
    captures = []; box = (390,244,474,266)
    pixels = bytes((c>>3)*255//31 for c in preview.convert('RGB').crop(box).tobytes())
    for name, reviewed in (('title_actual',args.reviewed_title_sha256),('main_menu',args.reviewed_menu_sha256)):
        path = title_ui/(name+'.png'); image = Image.open(path).convert('RGB')
        meta = json.loads(path.with_suffix('.json').read_text(encoding='utf8')); digest = sha(path.read_bytes())
        if image.size != (480,272) or meta['version'] != manifest['version'] or meta['loaded_executable_sha256'] != sha(installed):
            raise ValueError('Current capture identity differs')
        errors = [abs(a-b) for a,b in zip(image.crop(box).tobytes(), pixels)]
        if sum(errors)/len(errors) > 4 or max(errors) > 20:
            raise ValueError('Displayed current version/credit differs')
        if args.write and reviewed != digest: raise ValueError('Reviewed capture hash required')
        captures.append(dict(path=str(path), sha256=digest, visually_reviewed=reviewed == digest,
                             mean_stamp_channel_error=sum(errors)/len(errors), max_stamp_channel_error=max(errors)))
    proof = dict(schema_version=1, version=manifest['version'], iso_sha256=manifest['iso_sha256'],
        executable_sha256=sha(installed), archive_sha256=manifest['dialogue_cpk_sha256'],
        status='field_labels_notices_installed_static_loaded_strings_and_startup_passed',
        labels=28, unique_notices=12, event_occurrences=15,
        changed_archive_rows=changed, other_archive_rows_exact=len(new)-1,
        event_bytecode_exact=True, nested_executable_and_title_exact=True,
        native_loaded_strings_verified=True, emitted_instruction_cases=3132,
        title_version_and_credit_verified=True, captures=captures,
        natural_quest_camp_map_and_notice_display_verified=False, full_game_verified=False,
        validation_policy='The builder already checks complete ISO/archive spans and hashes. '
                          'This verifier rechecks selected nested spans, unchanged resource index and current live/capture identities.')
    print(json.dumps(proof, indent=2))
    if not args.write: print('DRY RUN: no evidence or manifest updated.'); return
    dest = ui/'validation.en.json'
    if dest.exists(): raise ValueError('Fresh validation required')
    dest.write_text(json.dumps(proof, indent=2)+'\n', encoding='utf8')
    manifest[f"field_labels_{int(args.version.split('.')[-1]):03}_coverage"] = proof
    manifest.update(status=proof['status'], runtime_verified_title=True, title_validation=str(dest))
    manifest['title_stamp']['runtime_verified'] = True
    mp.write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf8')


if __name__ == '__main__': main()
