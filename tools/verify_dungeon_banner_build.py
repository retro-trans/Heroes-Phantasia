"""Check the installed bitmap and preservation; write fresh scoped proof on request."""
import argparse
import json
from pathlib import Path
from append_cpk import sha
from inspect_iso import inventory as iso_inventory
from unpack_cpk import inventory, crilayla
from prepare_dungeon_banner import prepare, digest, RESOURCE


def extracted(path, row):
    with path.open('rb') as stream:
        stream.seek(row['offset'])
        data = stream.read(row['stored_size'])
    return crilayla(data, row['extract_size']) if row['compression'] == 'CRILAYLA' else data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--base-manifest', type=Path, required=True)
    p.add_argument('--append-proof', type=Path, required=True)
    p.add_argument('--write', action='store_true')
    a = p.parse_args()
    m = json.loads(a.manifest.read_text(encoding='utf-8'))
    base = json.loads(a.base_manifest.read_text(encoding='utf-8'))
    append = json.loads(a.append_proof.read_text(encoding='utf-8'))
    candidate, proposal, _, _ = prepare()
    cpk = a.manifest.parent/'HP.CPK'
    old_cpk = a.base_manifest.parent/'HP.CPK'
    if sha(cpk) != m['dialogue_cpk_sha256'] or sha(old_cpk) != base['dialogue_cpk_sha256']:
        raise ValueError('Current/base archive identities differ')
    if append['original_sha256'] != base['dialogue_cpk_sha256'] or append['version'] != m['version']:
        raise ValueError('Append proof differs from base/version')
    intermediate = a.append_proof.parent/'HP.CPK'
    if sha(intermediate) != append['output_sha256']:
        raise ValueError('Append output hash changed')
    old_header, old_rows = inventory(old_cpk)
    header, rows = inventory(cpk)
    if len(rows) != len(old_rows):
        raise ValueError('Resource count changed')
    changed = []
    for old, new in zip(old_rows, rows):
        if old != new:
            changed.append(old['path'])
    if set(changed) != {RESOURCE, 'menu/TitleMenu_Data.bin'}:
        raise ValueError('Unexpected resource row changes: '+str(changed))
    before = next(r for r in old_rows if r['path'] == RESOURCE)
    after = next(r for r in rows if r['path'] == RESOURCE)
    if digest(extracted(old_cpk, before)) != proposal['source_sha256']:
        raise ValueError('Base banner differs from reviewed source')
    if after['compression'] != 'none' or extracted(cpk, after) != candidate:
        raise ValueError('Installed banner differs from reviewed English asset')
    iso = Path(m['iso_path'])
    if sha(iso) != m['iso_sha256']:
        raise ValueError('ISO identity changed')
    iso_row = next(r for r in iso_inventory(iso) if r['path'] == 'PSP_GAME/USRDIR/HP.CPK')
    with iso.open('rb') as stream:
        stream.seek(iso_row['offset']+after['offset'])
        if stream.read(len(candidate)) != candidate:
            raise ValueError('Nested ISO banner readback differs')
    if m['output_elf_sha256'] != base['output_elf_sha256']:
        raise ValueError('Executable/font changed unexpectedly')
    if not m['prologue_movie_translation_coverage']['installed_in_iso']:
        raise ValueError('English prologue was dropped')
    proof = dict(schema_version=1, version=m['version'],
        status='installed_bitmap_and_preservation_passed_runtime_pending',
        iso_sha256=m['iso_sha256'], executable_sha256=m['output_elf_sha256'],
        archive_sha256=m['dialogue_cpk_sha256'], base_version=base['version'],
        resource=RESOURCE, target=proposal['target'],
        candidate_sha256=proposal['candidate_sha256'],
        archive_resource_readback_exact=True, nested_iso_resource_readback_exact=True,
        original_bitmap_source_verified=True, unchanged_other_resource_rows=len(rows)-2,
        changed_resource_rows=changed, executable_and_font_byte_identical_to_base=True,
        English_prologue_preserved=True, append_preservation_proof=str(a.append_proof),
        static_pixels_reviewed=True, original_palette_and_all_nonpixel_bytes_exact=True,
        native_display_verified=False, native_consumer_verified=False,
        banner_inventory_observations=30, banners_installed_in_english=1,
        other_banner_assets_pending=29,
        scope='One map-name image plus updated title stamp. Existing translation extents are retained. No claim of full-game or native banner display QA.')
    print(json.dumps(proof, indent=2))
    if a.write:
        dest = Path('work/ui/map_banners')/m['version']/'validation.en.json'
        if dest.exists():
            raise ValueError('Fresh proof destination required')
        dest.write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
        m['dungeon_banner_translation_coverage'] = dict(
            resource=RESOURCE, target=proposal['target'], installed_in_archive=True,
            installed_in_iso=True, candidate_sha256=proposal['candidate_sha256'],
            bitmap_labels=1, inventory_observations=30, other_banner_assets_pending=29,
            static_pixels_reviewed=True, native_display_verified=False,
            preparation_report='work/output/0.1.25-banner-assets/d06.bin.en.json',
            validation=str(dest))
        a.manifest.write_text(json.dumps(m, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
