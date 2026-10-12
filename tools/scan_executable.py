"""Inspect PSP binaries; extract heuristic Japanese strings from plain ELF data only.

Defaults to a read-only dry run. Output includes source text and must stay in
ignored local working files. Pointer hits are clues, not verified references.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9d]")
KANA = re.compile(r"[\u3040-\u30ff]")
FULL_JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
SJIS = re.compile(rb"(?:[\x09\x0a\x0d\x20-\x7e]|[\xa1-\xdf]|[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]){2,}\x00")


def elf_sections(data):
    if data[:6] != b"\x7fELF\x01\x01":
        return []
    off = struct.unpack_from('<I', data, 32)[0]
    stride, count, names_index = struct.unpack_from('<HHH', data, 46)
    if stride < 40 or off + stride * count > len(data):
        raise ValueError('Invalid ELF section table')
    raw = [struct.unpack_from('<10I', data, off + i * stride) for i in range(count)]
    strings = raw[names_index]
    names = data[strings[4]:strings[4] + strings[5]]
    return [dict(index=i, name=names[s[0]:].split(b'\x00', 1)[0].decode('ascii', 'replace'),
                 type=s[1], flags=s[2], address=s[3], offset=s[4], size=s[5])
            for i, s in enumerate(raw)]


def inspect(path, text_ranges=()):
    data = path.read_bytes()
    result = dict(path=path.as_posix(), size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                  candidates=[], verified_count=0)
    if not any(data):
        result.update(format='zero_placeholder', scan_status='skipped_no_data')
        return result
    if data[:4] == b'~PSP':
        result.update(format='encrypted_psp', scan_status='requires_decryption',
                      module=data[10:38].split(b'\x00', 1)[0].decode('ascii', 'replace'),
                      elf_size=struct.unpack_from('<I', data, 0x28)[0],
                      psp_size=struct.unpack_from('<I', data, 0x2c)[0],
                      compression_attribute=struct.unpack_from('<H', data, 6)[0],
                      key_tag=hex(struct.unpack_from('<I', data, 0xd0)[0]))
        return result
    sections = elf_sections(data)
    if not sections:
        result.update(format='unknown', scan_status='skipped_unrecognized_format')
        return result
    result.update(format='elf32_le', scan_status='heuristic_scan', sections=sections)
    # Allocated non-executable PROGBITS only: excludes MIPS instructions and relocation tables.
    ranges = [s for s in sections if s['type'] == 1 and s['flags'] & 2 and not s['flags'] & 4
              and s['offset'] + s['size'] <= len(data)]
    seen = set()
    rejected = 0
    for section in ranges:
        block = data[section['offset']:section['offset'] + section['size']]
        for match in SJIS.finditer(block):
            raw = match.group()[:-1]
            offset = section['offset'] + match.start()
            # Only null-delimited starts, not tails after arbitrary binary bytes.
            if match.start() and block[match.start() - 1] != 0:
                continue
            for codec in ('utf-8', 'cp932'):
                try:
                    text = raw.decode(codec)
                except UnicodeDecodeError:
                    continue
                jp_count = len(FULL_JP.findall(text))
                if jp_count < 1 or not all(c.isprintable() or c in '\t\r\n' for c in text):
                    continue
                if len(text) > 512 or jp_count / len(text) < .25:
                    continue
                if text_ranges and (not any(a <= offset < z for a, z in text_ranges)
                                    or re.search(r'[\uff66-\uff9d]', text)):
                    rejected += 1
                    continue
                key = (offset, text)
                if key in seen:
                    continue
                seen.add(key)
                address = section['address'] + offset - section['offset']
                result['candidates'].append(dict(id=f"exe_{offset:08x}_{codec}", offset=offset,
                    offset_hex=hex(offset), module_relative_address=hex(address),
                    encoding=codec, byte_length=len(raw), text=text, section=section['index'],
                    confidence='heuristic_kana' if KANA.search(text) else 'heuristic_cjk_only',
                    verification='not_verified_in_game', pointer_hits=[]))
                # A UTF-8 decoding can ambiguously look like CP932 too; prefer UTF-8.
                if codec == 'utf-8':
                    break
    # Index aligned data words once, then find relative address pointer clues.
    targets = {int(c['module_relative_address'], 16): c for c in result['candidates']}
    for section in ranges:
        start = (section['offset'] + 3) & ~3
        end = section['offset'] + section['size'] - 3
        for at in range(start, end, 4):
            value = struct.unpack_from('<I', data, at)[0]
            if value in targets:
                targets[value]['pointer_hits'].append(hex(at))
    result['heuristic_count'] = len(result['candidates'])
    result['excluded_by_reviewed_pool_or_halfwidth_count'] = rejected
    result['reviewed_text_ranges'] = [[hex(a), hex(z)] for a, z in text_ranges]
    result['confidence_counts'] = dict(Counter(c['confidence'] for c in result['candidates']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--write', type=Path, help='Save JSON locally after reviewing dry run')
    parser.add_argument('--sample', type=int, default=8)
    parser.add_argument('--text-range', action='append', default=[], help='Reviewed start:end file offsets, hex allowed')
    args = parser.parse_args()
    result = dict(schema_version=1, methodology='Null-terminated strings in allocated non-code ELF sections; heuristic only',
                  files=[inspect(p, [tuple(int(n, 0) for n in span.split(':')) for span in args.text_range]) for p in args.files])
    for item in result['files']:
        print(f"{item['path']}: {item['format']}, {item['scan_status']}, {len(item['candidates'])} candidates, 0 verified")
        for row in item['candidates'][:args.sample]:
            print(json.dumps(row, ensure_ascii=True))
    if args.write:
        resolved = args.write.resolve()
        local_root = Path('work/source').resolve()
        if local_root not in resolved.parents:
            raise SystemExit('Source-text output must be under ignored work/source/')
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Wrote {resolved}')


if __name__ == '__main__':
    main()
