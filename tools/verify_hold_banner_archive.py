"""Verify the scoped HOLD bitmap; default dry-run, optional fresh proof/ISO."""
import argparse
import json
from pathlib import Path
from append_cpk import sha
from unpack_cpk import inventory, crilayla
from prepare_hold_banner import prepare, digest, RESOURCE


def extract(path, row):
    with path.open('rb') as stream:
        stream.seek(row['offset'])
        data = stream.read(row['stored_size'])
    return crilayla(data, row['extract_size']) if row['compression'] == 'CRILAYLA' else data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--base-archive', type=Path, default=Path('work/output/0.1.31-title-credit-vwf-4x-candidate/HP.CPK'))
    p.add_argument('--append-proof', type=Path, default=Path('work/output/0.1.32-hold-banner-archive/HP.CPK.manifest.en.json'))
    p.add_argument('--iso', type=Path)
    p.add_argument('--write-proof', type=Path)
    a = p.parse_args()
    candidate, proposal, _, _ = prepare()
    append = json.loads(a.append_proof.read_text(encoding='utf-8'))
    base_sha = sha(a.base_archive)
    if base_sha != append['original_sha256'] or append['version'] != '0.1.32':
        raise ValueError('Base/version differs from reviewed append')
    _, old_rows = inventory(a.base_archive)
    _, rows = inventory(a.archive)
    if len(old_rows) != len(rows):
        raise ValueError('Resource count changed')
    changed = [old['path'] for old, new in zip(old_rows, rows) if old != new]
    allowed = {RESOURCE, 'menu/TitleMenu_Data.bin'} if a.iso else {RESOURCE}
    if set(changed) != allowed:
        raise ValueError('Unexpected archive row changes: ' + str(changed))
    old = next(row for row in old_rows if row['path'] == RESOURCE)
    new = next(row for row in rows if row['path'] == RESOURCE)
    if digest(extract(a.base_archive, old)) != proposal['source_sha256']:
        raise ValueError('Baseline compressed source differs from reviewed original')
    if new['compression'] != 'none' or extract(a.archive, new) != candidate:
        raise ValueError('Installed candidate differs')
    archive_sha = sha(a.archive)
    if not a.iso and archive_sha != append['output_sha256']:
        raise ValueError('Append output identity differs')
    if a.iso:
        from inspect_iso import inventory as iso_inventory
        entry = next(row for row in iso_inventory(a.iso) if row['path'] == 'PSP_GAME/USRDIR/HP.CPK')
        with a.iso.open('rb') as stream:
            stream.seek(entry['offset'] + new['offset'])
            if stream.read(len(candidate)) != candidate:
                raise ValueError('Nested ISO candidate differs')
    report = dict(schema_version=1, version='0.1.32', resource=RESOURCE,
        target=proposal['target'], candidate_sha256=proposal['candidate_sha256'],
        archive_sha256=archive_sha, base_archive_sha256=base_sha,
        original_compressed_source_verified=True, archive_readback_exact=True,
        nested_iso_readback_exact=bool(a.iso), changed_resource_rows=changed,
        other_resource_rows_unchanged=len(rows)-len(changed),
        all_nonpixel_bytes_and_palette_exact=True, static_pixels_reviewed=True,
        native_display_verified=False, native_uv_coverage_verified=False,
        banner_inventory_observations=30, English_banner_candidates=2,
        other_banner_assets_pending=28, append_proof=str(a.append_proof),
        iso_path=str(a.iso) if a.iso else None,
        scope='HOLD Headquarters bitmap; existing Forest of Encounters retained. Gameplay display requires a current build capture.')
    print(json.dumps(report, indent=2))
    if a.write_proof:
        dest = a.write_proof.resolve()
        if dest.exists() or not dest.is_relative_to(Path('work/ui').resolve()):
            raise ValueError('Fresh proof inside work/ui required')
        dest.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    else:
        print('DRY RUN: no proof files written.')


if __name__ == '__main__':
    main()
