"""Source-bound, English-only remaining movie queue review; no native asset writer."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

JP = re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare():
    queues = [Path('work/translation/en') / (name + '.json') for name in
              ('media_0001', 'media_0002', 'media_staff_0001', 'media_staff_0002')]
    remaining, staff, guards = [], [], {}
    for path in queues:
        working = json.loads(path.read_bytes())['rows']
        export_path = path.with_suffix('.en.json')
        exported = {r['id']: r for r in json.loads(export_path.read_bytes())['rows']}
        guards[str(path)] = digest(path)
        guards[str(export_path)] = digest(export_path)
        for index, row in enumerate(working):
            target = row.get('target') or ''
            if target:
                assert row['id'] in exported, (path, row['id'])
                clean = exported[row['id']]
                assert clean['target'] == target and clean['status'] == row['status']
            else:
                assert row['id'] in exported and not exported[row['id']].get('target')
                clean = exported[row['id']]
            is_staff = row['category'] == 'movie_staff_credit'
            if not is_staff and row['file'].endswith('HPMOVE03.PMF'):
                continue
            unit = dict(id=row['id'], queue=str(path), queue_index=index,
                        type=row['category'], file=row['file'], target=target,
                        status='meaning_reviewed_draft_not_installed' if target else 'pending_name_reading_not_translated',
                        context=clean.get('context', ''), decisions=clean.get('decisions', ''),
                        source_omission_preserved=bool(clean.get('source_omission_preserved')),
                        representative_frame=row.get('representative_frame'),
                        original_frame_sha256=row.get('frame_sha256'),
                        nominal_seconds=row.get('nominal_seconds', row.get('nominal_frame_time_seconds')),
                        exact_timing_verified=False, runtime_installed=False)
            if is_staff:
                unit.update(role_heading=row.get('role_en_proposed'),
                            glossary_ids=row.get('glossary_ids', []),
                            source_orthography_second_check_pending=bool(row.get('source_orthography_second_check_pending')))
                staff.append(unit)
            else:
                remaining.append(unit)
    assert len(remaining) == 87 and all(r['target'] for r in remaining)
    assert len(staff) == 94 and sum(bool(r['target']) for r in staff) == 77
    report = dict(status='remaining_movie_meaning_reviewed_queue_plan_runtime_unverified',
                  queue_sha256=guards, remaining_media_units=87, remaining_staff_drafts=77,
                  staff_pending_name_blocks=17, counts_by_movie=dict(Counter(r['file'] for r in remaining)),
                  media=remaining, staff=staff,
                  inventory_limits=['These are known human-transcribed units, not an exhaustive all-frame absence proof.',
                                    'Native headings and other physical layers need separate timing/placement ledgers.',
                                    'Seventeen staff blocks remain empty rather than guessing name readings.',
                                    'Only movie03 is installed in build0.1.23; this report installs nothing.',
                                    'Published Latin authority remains provisional where linked glossary records say so.'],
                  native_assets_written=False, whole_movie_text_coverage_complete=False)
    assert not JP.search(json.dumps(report, ensure_ascii=False)), 'English review contains Japanese prose'
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('work/ui/media/remaining_movie_queue_023.en.json'))
    args = parser.parse_args()
    report = prepare()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.write_review:
        args.output.resolve().relative_to(Path('work/ui').resolve())
        assert not args.output.exists(), 'Fresh review path required'
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

if __name__ == '__main__':
    main()
