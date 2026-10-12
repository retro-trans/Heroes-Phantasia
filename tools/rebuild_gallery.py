"""Relocate gallery prose into a fresh resource; dry-run before --write.

Original packed font/charset bytes remain unchanged. This is a text-container
candidate, requiring resource-font VWF integration and display QA before use.
"""
import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import struct

from apply_targets import TOKENS
from dialogue_tokens import visible_literal_text
from extract_corpus import controls, decode_file
from rebuild_dialogue import encode_target, PERCENT


def parse(name, raw):
    if not name.startswith('menu/Gallery/'):
        raise ValueError('Only gallery resources are supported')
    if len(raw) < 32:
        raise ValueError('Gallery header is truncated')
    head = struct.unpack_from('<8I', raw)
    if head[0] != 32 or any(head[4:]):
        raise ValueError('Gallery header differs from reviewed format')
    font_end, prose_start, prose_end = head[1:4]
    if not 32 < font_end < prose_start < prose_end == len(raw):
        raise ValueError('Gallery section bounds differ from reviewed format')
    if (font_end - 32) % 384 or prose_start % 16 or prose_end % 16:
        raise ValueError('Gallery font/section alignment differs')
    charset = raw[font_end:prose_start].rstrip(b'\0').decode('cp932', errors='strict')
    slots = (font_end - 32) // 384
    if not charset or len(charset) > slots or len(set(charset)) != len(charset):
        raise ValueError('Gallery charset does not fit distinct packed glyphs')
    codes = [int.from_bytes(char.encode('cp932'), 'big') for char in charset]
    if codes != sorted(codes):
        raise ValueError('Gallery charset is not sorted by native codes')
    if any(raw[32 + len(charset) * 384:font_end]):
        raise ValueError('Gallery tail slots are not blank')
    chunk = raw[prose_start:prose_end]
    text = chunk.rstrip(b'\0')
    text.decode('cp932', errors='strict')
    if b'\0' in text or not text:
        raise ValueError('Gallery prose is empty or contains an embedded terminator')
    return dict(head=head, prose_start=prose_start, prose_end=prose_end,
                text=text, padding=chunk[len(text):], charset=charset, font_slots=slots)


def rebuild(name, original, encoded):
    old = parse(name, original)
    if b'\0' in encoded or not encoded:
        raise ValueError('Replacement prose is empty or contains an embedded terminator')
    encoded.decode('cp932', errors='strict')
    result = bytearray(original[:old['prose_start']])
    result.extend(encoded)
    result.extend(old['padding'])
    result.extend(bytes((-len(result)) % 16))
    struct.pack_into('<I', result, 12, len(result))
    result = bytes(result)
    new = parse(name, result)
    if new['text'] != encoded or new['head'][:3] != old['head'][:3] or new['head'][4:] != old['head'][4:]:
        raise ValueError('Rebuilt gallery header/text verification failed')
    if result[32:old['prose_start']] != original[32:old['prose_start']]:
        raise ValueError('Original font or charset changed')
    if len(new['padding']) < len(old['padding']):
        raise ValueError('Original terminator/padding was removed')
    list(decode_file(name, result))
    return result, new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resource', nargs='?')
    parser.add_argument('targets', nargs='?', type=pathlib.Path)
    parser.add_argument('--audit-all', action='store_true', help='Verify every extracted gallery occurrence and byte-exact identity rebuild; optional report only')
    parser.add_argument('--source-root', type=pathlib.Path, default=pathlib.Path('work/source/cpk'))
    parser.add_argument('--occurrences', type=pathlib.Path, default=pathlib.Path('work/source/text_occurrences.json'))
    parser.add_argument('--ascii-punctuation', action='store_true')
    parser.add_argument('--vwf-latin', action='store_true')
    parser.add_argument('--native-fallback', action='store_true')
    parser.add_argument('--wrap-width', type=int, help='Additional soft breaks at English spaces using measured 4x-candidate advances; working target stays unchanged')
    parser.add_argument('--wrap-glyph-limit', type=int, default=45, help='Visible glyph capacity for wrapped lines; observed gallery body object uses 45')
    parser.add_argument('--output', type=pathlib.Path)
    parser.add_argument('--report', type=pathlib.Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if args.wrap_width is None and args.wrap_glyph_limit != 45:
        raise ValueError('--wrap-glyph-limit requires --wrap-width')
    root = args.source_root.resolve()
    if args.audit_all:
        if args.resource or args.targets or args.output or args.ascii_punctuation or args.vwf_latin or args.native_fallback or args.wrap_width is not None:
            raise ValueError('Gallery audit mode takes no replacement or encoding options')
        occurrences = json.loads(args.occurrences.read_text(encoding='utf-8'))
        selected = collections.defaultdict(list)
        for occurrence in occurrences:
            if occurrence['file'].startswith('menu/Gallery/'):
                selected[occurrence['file']].append(occurrence)
        digest = hashlib.sha256()
        passed, errors = [], []
        for name in sorted(selected):
            source = (root / name).resolve()
            if not source.is_relative_to(root):
                raise ValueError('Gallery audit resource escapes source root')
            original = source.read_bytes()
            source_sha = hashlib.sha256(original).hexdigest()
            digest.update((name + '\0' + source_sha + '\n').encode('utf-8'))
            try:
                old = parse(name, original)
                if rebuild(name, original, old['text'])[0] != original:
                    raise ValueError('Gallery identity round-trip differs')
                found = selected[name]
                identity = hashlib.sha256(old['text']).hexdigest()[:20]
                if len(found) != 1 or found[0]['row_index'] != 0 or found[0]['translation_id'] != identity:
                    raise ValueError('Gallery extracted occurrence identity differs')
                if found[0]['offset'] != old['prose_start'] or found[0]['byte_length'] != len(old['text']):
                    raise ValueError('Gallery extracted occurrence bounds differ')
                passed.append(dict(file=name, source_sha256=source_sha))
            except (ValueError, struct.error) as error:
                errors.append(dict(file=name, reason=str(error)))
        report = dict(version='0.1.6', date=datetime.date.today().isoformat(),
                      gallery_files=len(selected), identity_roundtrips=len(passed), errors=errors,
                      source_snapshot_sha256=digest.hexdigest(),
                      source_snapshot_encoding='Sorted resource path, NUL, original SHA256, newline; UTF-8',
                      by_type=dict(collections.Counter(item['file'].split('/')[2] for item in passed)),
                      sample=passed[:3], runtime_verified=False,
                      scope='Extracted gallery prose resources only; original packed-font format, occurrence metadata and byte-exact identity rebuilding; no English rendering proof')
        print(json.dumps(report, ensure_ascii=True, indent=2))
        if errors:
            raise SystemExit('Gallery resource validation failed')
        if not args.write:
            print('DRY RUN: no report written.')
            return
        if not args.report:
            raise ValueError('--audit-all --write requires a fresh --report path')
        destination = args.report.resolve()
        if destination.exists() or destination.is_relative_to(root) or not destination.name.endswith('.en.json'):
            raise ValueError('Gallery audit report must be fresh, English-only and outside source tree')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
        return
    if not args.resource or args.targets is None:
        raise ValueError('Gallery rebuilding requires resource and English targets')
    source = (root / args.resource).resolve()
    if not source.is_relative_to(root):
        raise ValueError('Resource escapes archive source root')
    original = source.read_bytes()
    old = parse(args.resource, original)
    if rebuild(args.resource, original, old['text'])[0] != original:
        raise ValueError('Gallery identity rebuild differs')
    identity = hashlib.sha256(old['text']).hexdigest()[:20]
    matches = [o for o in json.loads(args.occurrences.read_text(encoding='utf-8'))
               if o['file'] == args.resource]
    if len(matches) != 1 or matches[0]['translation_id'] != identity or matches[0]['row_index'] != 0:
        raise ValueError('Gallery occurrence identity differs')
    if matches[0]['offset'] != old['prose_start'] or matches[0]['byte_length'] != len(old['text']):
        raise ValueError('Gallery occurrence offset/length differs')
    targets = json.loads(args.targets.read_text(encoding='utf-8'))['rows']
    if len({row['id'] for row in targets}) != len(targets):
        raise ValueError('Duplicate English target IDs')
    rows = [row for row in targets if row['id'] == identity and row.get('target')]
    if len(rows) != 1:
        raise ValueError('Expected one matching nonempty English target')
    target = rows[0]['target']
    encoded, mapping = encode_target(target, controls(old['text'].decode('cp932')),
                                     args.ascii_punctuation, args.vwf_latin, args.native_fallback)
    layout = None
    if args.wrap_width is not None:
        from gallery_layout import advances, wrap
        widths, reference = advances()
        encoded, layout = wrap(encoded, args.wrap_width, widths, args.wrap_glyph_limit)
        layout['font_reference'] = reference
    result, new = rebuild(args.resource, original, encoded)
    visible = visible_literal_text(PERCENT.sub('', target))
    missing = sorted({f'U+{ord(char):04X}' for char in visible if char not in old['charset']})
    report = dict(version='0.1.7' if layout else '0.1.6', resource=args.resource, id=identity,
                  original_sha256=hashlib.sha256(original).hexdigest(), sha256=hashlib.sha256(result).hexdigest(),
                  original_bytes=len(original), rebuilt_bytes=len(result), prose_offset=old['prose_start'],
                  original_text_bytes=len(old['text']), translated_text_bytes=len(encoded),
                  font_slots=old['font_slots'], charset_characters=len(old['charset']),
                  original_font_and_charset_unchanged=True, original_padding_bytes=len(old['padding']),
                  rebuilt_padding_bytes=len(new['padding']), target=target, encoding_mapping=mapping,
                  missing_target_codepoints_from_resource_font=missing,
                  validation='Identity rebuild, source occurrence/hash, header fields, font/charset bytes, prose, alignment, controls/arguments/placeholders passed',
                  runtime_verified=False, install_ready=False,
                  renderer_requirement='Resource-specific font/Latin classification, proportional advances, measurement and gallery layout still require implementation and display QA')
    if layout:
        report['layout'] = layout
        report['renderer_requirement'] = 'Existing mode-4 Latin route and cursor may support this resource; cold-boot layout, scrolling and font selection still require display QA'
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if not args.write:
        print('DRY RUN: no files written.')
        return
    if args.output is None:
        raise ValueError('--write requires a fresh output path')
    output = args.output.resolve()
    report_path = args.report.resolve() if args.report else None
    for destination in [p for p in (output, report_path) if p is not None]:
        if destination.exists() or destination.is_relative_to(root) or destination == source:
            raise ValueError('Output/report must be fresh and outside source tree')
    if output == report_path:
        raise ValueError('Output and report must be distinct')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
