"""Audit filled structured gallery prose with measured Latin wrapping.

Reports source-free IDs and layout metrics. Item tables and runtime display
coverage are separate; --write saves a report only after dry-run review.
"""
import argparse
import collections
import datetime
import hashlib
import json
import pathlib

from extract_corpus import controls
from gallery_layout import advances, wrap
from rebuild_dialogue import encode_target
from rebuild_gallery import parse, rebuild


def audit(width=330, glyph_limit=45):
    occurrences = collections.defaultdict(list)
    for occurrence in json.loads(pathlib.Path('work/source/text_occurrences.json').read_text(encoding='utf8')):
        if occurrence['file'].startswith('menu/Gallery/'):
            occurrences[occurrence['translation_id']].append(occurrence)
    widths, reference = advances()
    ready, rejected = [], []
    seen = set()
    for path in sorted(pathlib.Path('work/translation/en').glob('*.json')):
        if path.name.endswith('.en.json'):
            continue
        for row in json.loads(path.read_text(encoding='utf8'))['rows']:
            if row['id'] not in occurrences or not row.get('target'):
                continue
            if row['id'] in seen:
                raise ValueError('Duplicate gallery translation ID')
            seen.add(row['id'])
            occurrence = occurrences[row['id']][0]
            name = occurrence['file']
            original = (pathlib.Path('work/source/cpk') / name).read_bytes()
            parsed = parse(name, original)
            if (hashlib.sha256(parsed['text']).hexdigest()[:20] != row['id'] or
                    controls(parsed['text'].decode('cp932')) != row['source'] or
                    occurrence['offset'] != parsed['prose_start'] or
                    occurrence['byte_length'] != len(parsed['text'])):
                raise ValueError('Gallery source identity/metadata differs')
            item = dict(id=row['id'], resource=name, category=row['category'],
                        source_sha256=hashlib.sha256(original).hexdigest())
            try:
                encoded, mapping = encode_target(row['target'], row['source'], False, True, True)
                wrapped, layout = wrap(encoded, width, widths, glyph_limit)
                result, _ = rebuild(name, original, wrapped)
                item.update(soft_breaks=layout['soft_breaks'], original_bytes=len(original),
                            rebuilt_bytes=len(result), rebuilt_sha256=hashlib.sha256(result).hexdigest(),
                            maximum_destination_extent_px=max(x['destination_extent_px'] for x in layout['lines']),
                            maximum_line_glyphs=max(x['glyphs'] for x in layout['lines']),
                            wording_reconstructed_byte_exact=True,
                            original_font_and_charset_unchanged=True,
                            encoding_mapping=mapping)
                ready.append(item)
            except ValueError as error:
                item['reason'] = str(error)
                rejected.append(item)
    return dict(version='0.1.7', date=datetime.date.today().isoformat(), language='en',
                structured_gallery_drafts=len(seen), structurally_prepared=len(ready),
                require_additional_handling=len(rejected), width_px=width, glyph_limit=glyph_limit,
                font_reference=reference, ready=ready, rejected=rejected,
                scope='Extracted structured gallery prose only; original source/hash/occurrence, explicit encoding, reversible soft-break ledger, font preservation and rebuilt container checks',
                runtime_verified_for_all_gallery_drafts=False,
                limitation='330px and 45 glyphs are observed for the dictionary body. Other gallery layouts must be measured before installation; native symbols/ruby/unknown controls reject. Item/help tables are excluded.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width', type=int, default=330)
    parser.add_argument('--glyph-limit', type=int, default=45)
    parser.add_argument('--output', type=pathlib.Path, default=pathlib.Path('work/ui/vwf/gallery_layout_coverage.en.json'))
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    report = audit(args.width, args.glyph_limit)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if not args.write:
        print('DRY RUN: no report written.')
        return
    output = args.output.resolve()
    if (not output.name.endswith('.en.json') or output.is_relative_to(pathlib.Path('work/source').resolve()) or
            output.is_relative_to(pathlib.Path('work/translation').resolve())):
        raise ValueError('Report must be English-only and outside original sources/translations')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    main()
