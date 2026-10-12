"""Package one measured gallery entry with the verified 0.1.6 VWF executable.

Preview by default. --write creates a fresh 0.1.7 local ISO and manifest.
Every unselected archive/ISO byte remains unchanged; no release is created.
"""
import argparse
import json
import pathlib
import shutil
import struct

from append_cpk import ORIGINAL_SHA, plan, sha, verify_original_span
from build_menu_patch import ISO, align, record_for
from gallery_layout import CANDIDATE, ELF_SHA
from gallery_layout import advances, wrap
from extract_corpus import controls
from rebuild_dialogue import encode_target
from rebuild_gallery import rebuild, parse
from inspect_iso import inventory as iso_inventory
from unpack_cpk import inventory as cpk_inventory

ISO_SHA = '2c3583f377cdaa9132d349a0039d7f6ffe21cac093476c7746705e8af2b03b40'
OPENING_SHA = '35cfda9a01773d74eff35679c79c62ed243a6a7b022279bbb0067c866f055f82'
ORIGINAL_CPK = pathlib.Path('work/source/PSP_GAME/USRDIR/HP.CPK')
ROOT = pathlib.Path('work/output/0.1.7-gallery-vwf-4x-candidate')
GALLERY_ROOT = pathlib.Path('work/output/0.1.7-gallery-candidate')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    cpk = GALLERY_ROOT / 'HP.CPK'
    cpk_report = json.loads(pathlib.Path(str(cpk) + '.manifest.en.json').read_text(encoding='utf8'))
    gallery_report = json.loads((GALLERY_ROOT / 'GgHelp000.en.json').read_text(encoding='utf8'))
    if cpk_report['original_sha256'] != ORIGINAL_SHA or sha(cpk) != cpk_report['output_sha256']:
        raise ValueError('Gallery archive input hashes differ')
    replacements = cpk_report['replacements']
    if {r['resource'] for r in replacements} != {'fld/talk/f101010.bin', 'menu/Gallery/dic/GgHelp000.bin'} or len(replacements) != 2:
        raise ValueError('Gallery candidate must retain the opening and replace exactly one gallery entry')
    if gallery_report['version'] != '0.1.7' or gallery_report['layout']['width_px'] != 330 or gallery_report['layout']['glyph_limit'] != 45:
        raise ValueError('Measured gallery layout differs')
    import hashlib
    original_gallery = (pathlib.Path('work/source/cpk') / 'menu/Gallery/dic/GgHelp000.bin').read_bytes()
    original_prose = parse('menu/Gallery/dic/GgHelp000.bin', original_gallery)['text']
    if hashlib.sha256(original_prose).hexdigest()[:20] != gallery_report['id']:
        raise ValueError('Gallery translation identity differs')
    working_export = json.loads(pathlib.Path('work/translation/en/batch_0008.en.json').read_text(encoding='utf8'))
    targets = [r['target'] for r in working_export['rows'] if r['id'] == gallery_report['id']]
    if targets != [gallery_report['target']]:
        raise ValueError('Gallery target differs from current English export')
    encoded, mapping = encode_target(targets[0], controls(original_prose.decode('cp932')))
    widths, reference = advances()
    wrapped, layout = wrap(encoded, 330, widths, 45)
    layout['font_reference'] = reference
    wanted_gallery, _ = rebuild('menu/Gallery/dic/GgHelp000.bin', original_gallery, wrapped)
    if layout != gallery_report['layout'] or mapping != gallery_report['encoding_mapping']:
        raise ValueError('Gallery layout/encoding ledger differs')
    if (GALLERY_ROOT / 'GgHelp000.bin').read_bytes() != wanted_gallery:
        raise ValueError('Gallery asset differs from current target and measured layout')
    for replacement in replacements:
        expected = OPENING_SHA if replacement['resource'].startswith('fld/') else gallery_report['sha256']
        if replacement['sha256'] != expected or sha(pathlib.Path(replacement['input'])) != expected:
            raise ValueError('Selected replacement bytes differ')
    header, entries, cpk_patches, assets, expected_end = plan(
        ORIGINAL_CPK, [(r['resource'], pathlib.Path(r['input'])) for r in replacements], ORIGINAL_SHA)
    new_header, new_entries = cpk_inventory(cpk)
    if new_header != dict(header, ContentSize=expected_end - header['ContentOffset']) or cpk.stat().st_size != expected_end:
        raise ValueError('Gallery archive header differs')
    selected = {a['resource']: a for a in assets}
    for before, after in zip(entries, new_entries):
        asset = selected.get(before['path'])
        expected = dict(before)
        if asset:
            expected.update(offset=asset['offset'], stored_size=asset['bytes'], extract_size=asset['bytes'], compression='none', magic_hex=asset['data'][:16].hex())
            with cpk.open('rb') as stream:
                stream.seek(after['offset'])
                if stream.read(after['stored_size']) != asset['data']:
                    raise ValueError('Gallery archive selected extraction differs')
        if after != expected:
            raise ValueError('Gallery archive TOC differs')
    if len(entries) != len(new_entries):
        raise ValueError('Gallery archive entry count differs')
    verify_original_span(ORIGINAL_CPK, cpk, cpk_patches)
    executable = CANDIDATE / 'EBOOT.BIN'
    if sha(executable) != ELF_SHA or sha(ISO) != ISO_SHA:
        raise ValueError('Reference executable/original ISO changed')
    originals = iso_inventory(ISO)
    records = {name: record_for(ISO, name) for name in ('PSP_GAME/SYSDIR/EBOOT.BIN', 'PSP_GAME/USRDIR/HP.CPK')}
    patches = {}
    end = ISO.stat().st_size
    outputs = []
    for name, source in [('PSP_GAME/SYSDIR/EBOOT.BIN', executable), ('PSP_GAME/USRDIR/HP.CPK', cpk)]:
        start = align(end, 2048)
        length = source.stat().st_size
        end = align(start + length, 2048)
        rec = records[name][0]
        patches[rec + 2] = struct.pack('<I', start // 2048) + struct.pack('>I', start // 2048)
        patches[rec + 10] = struct.pack('<I', length) + struct.pack('>I', length)
        outputs.append(dict(path=name, source=str(source), offset=start, size=length, sha256=sha(source)))
    patches[16 * 2048 + 80] = struct.pack('<I', end // 2048) + struct.pack('>I', end // 2048)
    info = json.loads((CANDIDATE / 'manifest.en.json').read_text(encoding='utf8'))
    for key in ('validation', 'opening_validation', 'iso_bytes', 'iso_path', 'iso_sha256', 'iso_replacements'):
        info.pop(key, None)
    info.update(version='0.1.7', status='cold_boot_gallery_candidate_unverified',
                executable_source_version='0.1.6', output_elf_sha256=ELF_SHA,
                original_iso_sha256=ISO_SHA, iso_bytes=end, iso_replacements=outputs,
                dialogue_cpk_sha256=cpk_report['output_sha256'], dialogue_cpk_bytes=cpk.stat().st_size,
                selected_gallery_ids=[gallery_report['id']], selected_gallery_resources=[gallery_report['resource']],
                gallery_layout=gallery_report['layout'], gallery_display_qa_passed=False,
                opening_validation_inherited_from='work/ui/runtime/association_candidate_opening_validation.en.json',
                runtime_verified_dialogue_rows_in_this_build=0, game_translation_complete=False,
                structural_validation='Original inputs, every CPK TOC/header field and untouched source byte; two selected raw extractions verified')
    print(json.dumps(info, ensure_ascii=True, indent=2))
    if not args.write:
        print('DRY RUN: no ISO or manifest written.')
        return
    if ROOT.exists():
        raise ValueError('Output directory must be fresh')
    ROOT.mkdir(parents=True)
    shutil.copyfile(executable, ROOT / 'EBOOT.BIN')
    destination = ROOT / 'Heroes-Phantasia-0.1.7-gallery-vwf-4x-candidate.iso'
    shutil.copyfile(ISO, destination)
    with destination.open('r+b') as stream:
        for item in outputs:
            stream.seek(0, 2)
            stream.write(bytes(item['offset'] - stream.tell()))
            with pathlib.Path(item['source']).open('rb') as source:
                shutil.copyfileobj(source, stream, 8 * 1024 * 1024)
            stream.write(bytes((-stream.tell()) % 2048))
        for offset, value in patches.items():
            stream.seek(offset)
            stream.write(value)
    verify_original_span(ISO, destination, patches)
    expected_by_name = {r['path']: r for r in outputs}
    wanted = [dict(row, offset=expected_by_name[row['path']]['offset'], size=expected_by_name[row['path']]['size'])
              if row['path'] in expected_by_name else row for row in originals]
    if iso_inventory(destination) != wanted or destination.stat().st_size != end:
        raise ValueError('Written ISO inventory differs')
    with destination.open('rb') as stream:
        for item in outputs:
            stream.seek(item['offset'])
            remaining = item['size']
            digest = hashlib.sha256()
            while remaining:
                chunk = stream.read(min(8 * 1024 * 1024, remaining))
                if not chunk:
                    raise ValueError('Selected ISO extraction is truncated')
                digest.update(chunk)
                remaining -= len(chunk)
            if digest.hexdigest() != item['sha256']:
                raise ValueError('Selected ISO extraction hash differs')
    info.update(iso_path=str(destination), iso_sha256=sha(destination),
                structural_validation='All archive metadata/unselected bytes, ISO inventory/unselected bytes, both selected ISO extractions and final size verified')
    (ROOT / 'manifest.en.json').write_text(json.dumps(info, ensure_ascii=True, indent=2) + '\n', encoding='utf8')
    print('Verified fresh local gallery candidate:', destination)


if __name__ == '__main__':
    main()
