"""Audit draft character serialization without changing text or game resources.

Default is a dry run. The report contains English metadata, character codes and
stable row IDs, never original scripts. Serialization eligibility is not proof
that a resource format, font path or layout works in the game.
"""
import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import struct
import unicodedata

from apply_targets import TOKENS
from rebuild_dialogue import encode_target, parse, PUNCTUATION
from inspect_font_assets import bounds


def native_glyph_candidates(codepoints, resource_files):
    """Re-read verified original charsets; a matching bank is only a candidate."""
    index = pathlib.Path('work/source/font_audit/native_font_assets.json')
    candidates = {code: [] for code in codepoints}
    source_root = pathlib.Path('work/source/cpk').resolve()
    assets = json.loads(index.read_text(encoding='utf-8'))['assets'] if index.exists() else []
    inspected_files = {asset['file'] for asset in assets
                       if asset.get('label') in ('gallery', 'field')}
    for name in sorted(set(resource_files)):
        gallery = name.startswith('menu/Gallery/')
        indexed = name.startswith(('phase/bin/', 'fld/talk/'))
        if not (gallery or indexed) or name in inspected_files:
            continue
        source = (source_root / name).resolve()
        if not source.is_relative_to(source_root):
            raise ValueError('Resource font source escapes archive root')
        raw = source.read_bytes()
        if gallery:
            head = struct.unpack_from('<8I', raw)
            if not head[0] == 32 <= head[1] < head[2] < head[3] <= len(raw):
                raise ValueError('Gallery font does not match reviewed packed format')
            start, font_end, charset_end = 32, head[1], head[2]
        else:
            head = parse(name, raw)['head']
            if not head[0] == 32 <= head[1] < head[2] < head[3] < head[4] <= len(raw):
                raise ValueError('Indexed font does not match reviewed packed format')
            start, font_end, charset_end = head[2:5]
        if (font_end - start) % 384:
            raise ValueError('Resource font is not a whole number of packed glyphs')
        charset = raw[font_end:charset_end].rstrip(b'\0').decode('cp932')
        slots = (font_end - start) // 384
        if len(charset) > slots or len(set(charset)) != len(charset):
            raise ValueError('Resource charset does not fit distinct glyph slots')
        codes = [int.from_bytes(char.encode('cp932'), 'big') for char in charset]
        if codes != sorted(codes):
            raise ValueError('Resource charset is not sorted like reviewed font maps')
        if any(raw[start + len(charset) * 384:font_end]):
            raise ValueError('Resource tail glyphs are not verified blank padding')
        assets.append(dict(file=name, label='resource_gallery' if gallery else 'resource_indexed', offset=start,
                           font_end=font_end, charset_end=charset_end, charset_base_slot=0,
                           sha256=hashlib.sha256(raw).hexdigest(),
                           format='packed_alpha4_low_nibble_first_32x24'))
    for asset in assets:
        if asset.get('format') != 'packed_alpha4_low_nibble_first_32x24':
            continue
        source = (source_root / asset['file']).resolve()
        if not source.is_relative_to(source_root):
            raise ValueError('Native font source escapes archive root')
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != asset['sha256']:
            raise ValueError('Original native font asset differs from inspected hash')
        charset = raw[asset['font_end']:asset['charset_end']].rstrip(b'\0').decode('cp932')
        for position, char in enumerate(charset):
            code = f'U+{ord(char):04X}'
            if code not in candidates:
                continue
            slot = position + asset['charset_base_slot']
            offset = asset['offset'] + slot * 384
            glyph = raw[offset:offset + 384]
            if len(glyph) != 384 or offset + 384 > asset['font_end']:
                raise ValueError('Native glyph slot outside verified font range')
            pixels = bytes(v for byte in glyph for v in ((byte & 15) * 17, (byte >> 4) * 17))
            candidates[code].append(dict(file=asset['file'], bank=asset['label'],
                                         source_sha256=asset['sha256'], slot=slot, offset=offset,
                                         ink_bounds=bounds(pixels, 32, 24)))
    return candidates


def audit(root):
    rows = []
    characters = {}
    categories = collections.Counter()
    failures = collections.Counter(ascii=0, vwf_latin=0, vwf_latin_ascii_punctuation=0,
                                   vwf_latin_native_fallback=0)
    for path in sorted(root.glob('*.json')):
        if path.name.endswith('.en.json'):
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        for row in data['rows']:
            target = row.get('target', '')
            if not target:
                continue
            categories[row['category']] += 1
            policies = {}
            errors = {}
            for label, punctuation, latin, native in (
                ('ascii', False, False, False), ('vwf_latin', False, True, False),
                ('vwf_latin_ascii_punctuation', True, True, False),
                ('vwf_latin_native_fallback', False, True, True),
            ):
                try:
                    encode_target(target, row['source'], punctuation, latin, native)
                    policies[label] = True
                except ValueError as error:
                    policies[label] = False
                    errors[label] = str(error)
                    failures[label] += 1
            plain = TOKENS.sub('', target)
            non_ascii = collections.Counter(c for c in plain if not 32 <= ord(c) <= 126)
            for char, count in sorted(non_ascii.items()):
                code = f'U+{ord(char):04X}'
                if code not in characters:
                    if char == '\u00e8':
                        required = 'Explicit VWF Latin policy; private byte 0x80 and matching glyph/advance hooks'
                    elif char in PUNCTUATION:
                        required = 'Explicit punctuation mapping; review semantic and layout changes'
                    elif char in '\u25cb\u00d7\u25b3\u25a1\u2605\u2606':
                        required = 'Symbol font/fallback and resource-format support; preserve the contextual meaning'
                    elif char == '\u3000':
                        required = 'Review original layout padding; default serializer rejects; do not remove automatically'
                    else:
                        required = 'Uncovered character requires explicit serialization and font/layout review'
                    characters[code] = dict(codepoint=code, name=unicodedata.name(char, 'UNNAMED'),
                                            occurrences=0, rows=[], required_work=required)
                item = characters[code]
                item['occurrences'] += count
                item['rows'].append(dict(id=row['id'], file=row['file'], category=row['category'], count=count))
            if non_ascii or not all(policies.values()):
                rows.append(dict(id=row['id'], file=row['file'], category=row['category'],
                                 codepoints=[f'U+{ord(c):04X}' for c in sorted(non_ascii)],
                                 serialization_eligible=policies, serialization_errors=errors))
    candidates = native_glyph_candidates(characters, [row['file'] for row in rows])
    for code, item in characters.items():
        item['native_asset_candidates'] = candidates[code]
    return dict(version='0.1.7', date=datetime.date.today().isoformat(), language='en', drafted_rows=sum(categories.values()),
                drafted_by_category=dict(categories), serialization_failures=dict(failures),
                policy_scope='Character encoding and recognized control/format preservation only; no resource rebuild or display QA',
                ascii_repertoire='U+0020 through U+007E', candidate_private_accent='U+00E8 at byte 0x80',
                affected_rows=rows, non_ascii_characters=list(characters.values()),
                native_mapping_scope='Original packed charsets and glyph bytes re-read and asset hashes verified; active font selection, advance and rendering are unverified',
                runtime_verified_for_all_drafts=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, default=pathlib.Path('work/translation/en'))
    parser.add_argument('--output', type=pathlib.Path,
                        default=pathlib.Path('work/ui/vwf/current_encoding_coverage.en.json'))
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    report = audit(args.root)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if not args.write:
        print('DRY RUN: no report written.')
        return
    destination = args.output.resolve()
    if destination.is_relative_to(args.root.resolve()) or destination.is_relative_to(pathlib.Path('work/source').resolve()):
        raise ValueError('Report must stay outside original sources and translation files')
    if not destination.name.endswith('.en.json'):
        raise ValueError('Use an English-only report filename')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
