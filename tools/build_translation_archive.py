"""Plan all drafted indexed dialogue replacements; no writes unless --write.

Story/field/battle/skit containers only. This is structural integration, not
translation review or runtime certification. Gallery prose, other tables,
executable text and images are explicitly outside this tool's coverage.
Targets are never shortened or modified. Encoding mappings require explicit
options. Untargeted records remain byte-exact Japanese, not counted translated.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct

import append_cpk
from apply_targets import JP, TOKENS
from dialogue_tokens import control_arguments
from extract_corpus import controls
from rebuild_dialogue import parse, rebuild, encode_target, PERCENT
from unpack_cpk import inventory

PREFIXES = ('phase/bin/', 'fld/talk/', 'btl/res/', 'btl/skit/')
TUTORIALS = ('btl/skit/s999910.bin', 'btl/skit/s999911.bin')


def digest(data):
    return hashlib.sha256(data).hexdigest()


class MemoryAsset:
    """The append planner's read-only file interface, without temporary files."""
    def __init__(self, name, data):
        self.name, self.data = name, data

    def read_bytes(self):
        return self.data

    def __str__(self):
        return 'in-memory-rebuilt:' + self.name


def load_targets(directory):
    rows, inputs = {}, []
    for path in sorted(directory.glob('batch_*.json')):
        if path.name.endswith('.en.json'):
            continue
        data = path.read_bytes()
        inputs.append({'path': str(path), 'sha256': digest(data)})
        doc = json.loads(data)
        if doc.get('language') != 'en':
            raise ValueError('Target language is not English: ' + str(path))
        for row in doc['rows']:
            key = row['id']
            if key in rows:
                raise ValueError('Duplicate translation ID: ' + key)
            if row.get('target') and JP.search(row['target']):
                raise ValueError('Japanese retained in claimed English target: ' + key)
            rows[key] = row
    if not rows:
        raise ValueError('No working batch rows found')
    return rows, inputs


def audit_asset(name, original, occurrences, targets, policies, overlay_widths=None):
    """Verify every original reference, and rebuild all drafted references."""
    old = parse(name, original)
    identity, _ = rebuild(name, original, {})
    if identity != original:
        raise ValueError('Identity round-trip failed')
    lookup = {}
    for occ in occurrences:
        index = occ['row_index']
        if index in lookup or not 0 <= index < len(old['refs']):
            raise ValueError('Duplicate/out-of-range occurrence index')
        lookup[index] = occ
        raw = old['spans'][old['refs'][index][1]][0]
        if (digest(raw)[:20] != occ['translation_id'] or
                len(raw) != occ['byte_length'] or
                old['blob'] + old['refs'][index][1] != occ['offset']):
            raise ValueError('Occurrence source hash/offset/length changed')
        structure = occ['structure']
        if (structure['reference_id'] != old['refs'][index][0] or
                structure['reference_offset'] != old['refs_start'] + index * 8 + 4 or
                structure['section_offset'] != old['start'] or
                structure['blob_offset'] != old['blob']):
            raise ValueError('Occurrence table structure changed')

    replacements, rows, errors = {}, [], []
    for index, (ref_id, offset) in enumerate(old['refs']):
        raw = old['spans'][offset][0]
        key = digest(raw)[:20]
        source = controls(raw.decode('cp932'))
        occ = lookup.get(index)
        target = targets.get(key)
        row = {'row_index': index, 'id': key, 'reference_id': ref_id,
               'source_bytes': len(raw), 'source_sha256': digest(raw),
               'inventory_occurrence': occ is not None,
               'status': 'untranslated' if occ else 'nonqueue_unchanged'}
        row['source_control_codes'] = TOKENS.findall(source)
        if target and target.get('target'):
            try:
                if target['source'] != source:
                    raise ValueError('Working source differs from original bytes')
                if occ is None:
                    # Only close an alias of an independently verified queued
                    # reference. Do not invent translations for unindexed text.
                    if not any(o['translation_id'] == key for o in occurrences):
                        raise ValueError('Drafted reference absent from occurrence inventory')
                    row['shared_reference_closure'] = True
                encoded, mappings = encode_target(target['target'], source, **policies)
                if overlay_widths is not None:
                    from battle_overlay_layout import prepare
                    encoded, ledger = prepare(name, key, target['target'], encoded, overlay_widths)
                    if ledger:
                        row['physical_layout_ledger'] = ledger
                replacements[index] = encoded
                row.update(status='rebuildable_draft', target_bytes=len(encoded),
                           target_sha256=digest(encoded), encoding_mappings=mappings,
                           draft_status=target.get('status'), runtime_verified=False,
                           context_note_present=bool(target.get('context')),
                           decision_note_present=bool(target.get('decisions')),
                           controls_sha256=digest('|'.join(TOKENS.findall(source)).encode()),
                           numeric_arguments_sha256=digest('|'.join(control_arguments(source)).encode()),
                           format_placeholders=PERCENT.findall(source))
            except ValueError as error:
                row.update(status='encoding_blocked', reason=str(error))
                errors.append({'row_index': index, 'id': key, 'reason': str(error)})
        rows.append(row)
    report = {'resource': name, 'original_sha256': digest(original),
              'original_bytes': len(original), 'total_references': len(old['refs']),
              'indexed_japanese_references': len(occurrences), 'rows': rows,
              'identity_roundtrip': True, 'encoding_errors': errors,
              'status': 'unchanged_no_targets', 'runtime_verified': False,
              'scene_context_review': 'No human full-scene review performed by integration tool; byte/reference checks only.'}
    if errors:
        report['status'] = 'blocked'
        return None, report
    if not replacements:
        return None, report
    result, new = rebuild(name, original, replacements)
    # Validate bytes independently of the extractor's Japanese-only filtering.
    for index, (_, offset) in enumerate(old['refs']):
        after = new['spans'][new['refs'][index][1]][0]
        if after != replacements.get(index, old['spans'][offset][0]):
            raise ValueError('Post-rebuild reference differs')
        rows[index]['new_offset'] = new['blob'] + new['refs'][index][1]
    report.update(status='structurally_rebuilt_runtime_untested',
                  rebuilt_sha256=digest(result), rebuilt_bytes=len(result),
                  translated_references=len(replacements),
                  validations=['identity round-trip', 'every unchanged reference byte',
                               'group IDs/counts and reference IDs', 'shared reference closure',
                               'downstream suffix bytes and alignment',
                               'nontext prefix bytes except verified offset metadata',
                               'controls, numeric arguments and format placeholders',
                               'original and rebuilt container reparse'])
    return result, report


def build(args):
    targets, inputs = load_targets(args.targets)
    occ_bytes = args.occurrences.read_bytes()
    occurrences = json.loads(occ_bytes)
    byfile = collections.defaultdict(list)
    excluded = collections.Counter()
    for occ in occurrences:
        if occ['file'].startswith(PREFIXES):
            byfile[occ['file']].append(occ)
        else:
            excluded[occ['category']] += 1
    inventory_bytes = args.inventory.read_bytes()
    original_inventory = json.loads(inventory_bytes)
    originals = {e['path']: e for e in original_inventory['entries']}
    policies = dict(map_punctuation=args.ascii_punctuation,
                    vwf_latin=args.vwf_latin, native_fallback=args.native_fallback)
    overlay_widths, overlay_inputs = None, []
    if getattr(args, 'battle_overlay_wrap', False):
        from battle_overlay_layout import widths_input
        overlay_widths, overlay_inputs = widths_input()
    assets, reports, failures = [], [], []
    source_root = args.source_root.resolve()
    for name in sorted(byfile):
        try:
            path = (source_root / name).resolve()
            if not path.is_relative_to(source_root):
                raise ValueError('Resource escapes source root')
            original = path.read_bytes()
            entry = originals[name]
            if len(original) != entry['extract_size'] or digest(original) != entry['sha256']:
                raise ValueError('Original extracted asset does not match inventory SHA/size')
            rebuilt, report = audit_asset(name, original, byfile[name], targets, policies, overlay_widths)
            reports.append(report)
            if rebuilt is not None:
                assets.append((name, MemoryAsset(name, rebuilt)))
        except (ValueError, KeyError, UnicodeError, AssertionError, OSError, struct.error) as error:
            failures.append({'resource': name, 'reason': str(error)})
    planned = {r['id'] for a in reports for r in a['rows']
               if r['status'] == 'rebuildable_draft' and a['status'].startswith('structurally_')}
    scoped = {o['translation_id'] for name in byfile for o in byfile[name]}
    drafted = {key for key in scoped if targets.get(key, {}).get('target')}
    blocked_assets = [r['resource'] for r in reports if r['status'] == 'blocked']
    category_counts = {}
    for category in sorted({o['category'] for name in byfile for o in byfile[name]}):
        subset = [o for name in byfile for o in byfile[name] if o['category'] == category]
        ids = {o['translation_id'] for o in subset}
        category_counts[category] = {'references': len(subset), 'unique_rows': len(ids),
            'drafted_unique_rows': len(ids & drafted),
            'planned_unique_rows': len(ids & planned), 'untranslated_unique_rows': len(ids - drafted)}
    tutorials = []
    for name in TUTORIALS:
        asset = next((r for r in reports if r['resource'] == name), None)
        tutorials.append({'resource': name, 'present': asset is not None,
            'status': asset['status'] if asset else 'absent',
            'indexed_references': len(byfile.get(name, [])),
            'drafted_references': sum(bool(targets.get(o['translation_id'], {}).get('target'))
                                      for o in byfile.get(name, [])),
            'context_requirement': 'Read both complete original scene variants and all shared occurrences before translation; structural parsing is not human context review.',
            'runtime_requirement': 'Battle tutorial decoder, resident/native symbol routing, ruby spans and page/line layout need independent runtime validation.'})
    if all(t['present'] for t in tutorials):
        a, b = (next(r for r in reports if r['resource'] == name) for name in TUTORIALS)
        tutorial_pair = {'left': TUTORIALS[0], 'right': TUTORIALS[1],
            'left_reference_count': len(a['rows']), 'right_reference_count': len(b['rows']),
            'identical_source_row_indices': [i for i, (x, y) in enumerate(zip(a['rows'], b['rows']))
                                             if x['source_sha256'] == y['source_sha256']],
            'changed_source_row_indices': [i for i, (x, y) in enumerate(zip(a['rows'], b['rows']))
                                           if x['source_sha256'] != y['source_sha256']],
            'human_context_review_complete': False}
    else:
        tutorial_pair = {'human_context_review_complete': False, 'reason': 'Missing tutorial asset'}
    planned_references = sum(a.get('translated_references', 0) for a in reports)
    all_scoped_references = sum(len(rows) for rows in byfile.values())
    drafted_references = sum(o['translation_id'] in drafted for rows in byfile.values() for o in rows)
    previews = [{'id': row['id'], 'target': targets[row['id']]['target']}
                for asset in reports for row in asset['rows']
                if row['status'] == 'rebuildable_draft'][:3]
    report = {'schema_version': 1, 'version': args.version,
        'status': 'dry_structural_plan_runtime_untested', 'runtime_verified': False,
        'runtime_verified_dialogue_rows': 0, 'full_game_translation_complete': False,
        'scope': 'Only validated indexed story, field, battle dialogue and battle skit containers',
        'target_input_snapshots': inputs, 'occurrences_sha256': digest(occ_bytes),
        'original_extraction_inventory_sha256': digest(inventory_bytes),
        'encoding_policy': policies, 'by_category': category_counts,
        'physical_overlay_layout_inputs': overlay_inputs,
        'unique_rows': len(scoped), 'drafted_unique_rows': len(drafted),
        'planned_unique_rows': len(planned), 'untranslated_unique_rows': len(scoped - drafted),
        'drafted_but_not_planned_unique_rows': sorted(drafted - planned),
        'resources_examined': len(byfile), 'resources_with_replacements': len(assets),
        'indexed_japanese_references': all_scoped_references,
        'all_container_references': sum(a['total_references'] for a in reports),
        'drafted_indexed_references': drafted_references,
        'planned_references_including_shared_closure': planned_references,
        'untranslated_indexed_references': all_scoped_references - drafted_references,
        'structural_failures': failures, 'encoding_blocked_assets': blocked_assets,
        'excluded_inventory_references': dict(excluded), 'tutorials': tutorials,
        'tutorial_pair_context_plan': tutorial_pair, 'target_preview': previews,
        'assets': reports,
        'limitations': ['Drafts are not automatically independently reviewed translations.',
            'Unfilled rows and nonqueue references remain original bytes.',
            'Coverage is exact indexed references, not all Japanese in archive or game.',
            'VWF renderer/classifier/cursor/layout coverage is not established by serialization.',
            'Private accent slot, native symbols, ruby and expanded player names require runtime QA.',
            'Gallery prose, indexed UI tables, executable/image/movie text excluded.']}
    wrapped = [r for a in reports for r in a['rows'] if r.get('physical_layout_ledger')]
    if overlay_widths is not None and len(wrapped) != 2:
        raise ValueError('Expected exactly two reviewed formation physical wraps')
    report['physical_overlay_wrap_references'] = len(wrapped)
    archive_plan = None
    if assets and not failures and not blocked_assets:
        archive_plan = append_cpk.plan(args.archive, assets, args.expected_sha256)
        header, entries, patches, appended, end = archive_plan
        report['archive'] = {'input': str(args.archive), 'input_sha256': args.expected_sha256,
            'original_bytes': args.archive.stat().st_size, 'output_bytes': end,
            'alignment': 2048, 'replacements': len(appended),
            'metadata_fields': 'Selected TOC FileOffset/FileSize/ExtractSize and verified ContentSize only',
            'all_other_header_fields_preserved': True,
            'shared_original_extents_preserved': True,
            'schema_and_proposed_metadata_reparse_passed': True}
    return report, archive_plan


def write_candidate(args, report, plan):
    if plan is None or report['structural_failures'] or report['encoding_blocked_assets']:
        raise ValueError('Blocked structural plan cannot be written')
    if args.require_complete and report['untranslated_unique_rows']:
        raise ValueError('Complete translation required, but unfilled rows remain')
    if args.output is None:
        raise ValueError('--write requires --output to a fresh directory')
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(Path('work/output').resolve()):
        raise ValueError('Output directory must be fresh and inside work/output')
    # The plan snapshots exact inputs. Refuse a write after another translator
    # or inventory operation changes them while this run is being reviewed.
    for snapshot in report['target_input_snapshots']:
        if digest(Path(snapshot['path']).read_bytes()) != snapshot['sha256']:
            raise ValueError('Target batch changed after planning')
    for snapshot in report.get('physical_overlay_layout_inputs', []):
        if digest(Path(snapshot['path']).read_bytes()) != snapshot['sha256']:
            raise ValueError('Physical overlay layout input changed after planning')
    if digest(args.occurrences.read_bytes()) != report['occurrences_sha256']:
        raise ValueError('Occurrence inventory changed after planning')
    if digest(args.inventory.read_bytes()) != report['original_extraction_inventory_sha256']:
        raise ValueError('Original extraction inventory changed after planning')
    if append_cpk.sha(args.archive) != args.expected_sha256:
        raise ValueError('Input archive changed after planning')
    header, entries, patches, assets, end = plan
    output.mkdir(parents=True)
    for asset in assets:
        path = output / 'assets' / asset['resource']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(asset['data'])
    archive = output / 'HP.CPK'
    shutil.copyfile(args.archive, archive)
    with archive.open('r+b') as stream:
        for offset, value in patches.items():
            stream.seek(offset); stream.write(value)
        for asset in assets:
            stream.seek(0, 2); stream.write(bytes(asset['offset'] - stream.tell()))
            stream.write(asset['data']); stream.write(bytes((-stream.tell()) % 2048))
    newheader, newentries = inventory(archive)
    if len(newentries) != len(entries):
        raise ValueError('Written archive entry count changed')
    if newheader != dict(header, ContentSize=end - header['ContentOffset']):
        raise ValueError('Written archive header changed')
    selected = {a['resource']: a for a in assets}
    for old, new in zip(entries, newentries):
        asset = selected.get(old['path'])
        if asset is None:
            if old != new:
                raise ValueError('Unselected archive metadata changed')
        else:
            if (new['offset'] != asset['offset'] or new['stored_size'] != asset['bytes'] or
                    new['extract_size'] != asset['bytes'] or new['compression'] != 'none'):
                raise ValueError('Appended resource metadata changed')
            with archive.open('rb') as stream:
                stream.seek(new['offset'])
                if stream.read(new['stored_size']) != asset['data']:
                    raise ValueError('Appended extraction differs from rebuilt resource')
    append_cpk.verify_original_span(args.archive, archive, patches)
    if archive.stat().st_size != end:
        raise ValueError('Archive final size changed')
    report['status'] = 'written_structural_candidate_runtime_untested'
    report['archive'].update(output=str(archive), output_sha256=append_cpk.sha(archive),
                            inventory_and_extraction_verified=True,
                            all_unselected_original_bytes_verified=True)
    (output / 'integration.en.json').write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='utf8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets', type=Path, default=Path('work/translation/en'))
    parser.add_argument('--source-root', type=Path, default=Path('work/source/cpk'))
    parser.add_argument('--occurrences', type=Path, default=Path('work/source/text_occurrences.json'))
    parser.add_argument('--inventory', type=Path, default=Path('work/source/cpk_inventory.json'))
    parser.add_argument('--archive', type=Path, default=Path('work/source/PSP_GAME/USRDIR/HP.CPK'))
    parser.add_argument('--expected-sha256', default=append_cpk.ORIGINAL_SHA)
    parser.add_argument('--version', default='0.1.12')
    parser.add_argument('--ascii-punctuation', action='store_true')
    parser.add_argument('--vwf-latin', action='store_true')
    parser.add_argument('--native-fallback', action='store_true')
    parser.add_argument('--require-complete', action='store_true')
    parser.add_argument('--battle-overlay-wrap', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--details', action='store_true', help='Print full English-only per-asset/per-row plan')
    args = parser.parse_args()
    if not re.fullmatch(r'0\.\d+\.\d+', args.version):
        raise ValueError('Version must be 0.x.y')
    report, plan = build(args)
    public = report if args.details else {k: v for k, v in report.items()
             if k not in ('assets', 'target_input_snapshots')}
    if not args.details:
        public['asset_sample'] = [{k: v for k, v in asset.items() if k != 'rows'}
                                  for asset in report['assets'][:3]]
        public['row_sample'] = [r for a in report['assets'] for r in a['rows']
                                if r['status'] == 'rebuildable_draft'][:3]
    print(json.dumps(public, ensure_ascii=True, indent=2))
    if args.write:
        write_candidate(args, report, plan)
        print('Verified fresh candidate archive and English-only integration report.')
    else:
        print('DRY RUN: no archive, resource, report or other data files written.')


if __name__ == '__main__':
    main()
