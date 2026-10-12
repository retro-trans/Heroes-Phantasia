"""Extract verified menu lists, preserving row separators; default is dry run."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from extract_corpus import controls


# (file, metadata-header index, prose-header index, category)
TABLES = [('menu/LimitedSoundList.bin', 0, 3, 'song_titles'),
          ('menu/LimitedBattle.bin', 0, 3, 'enemy_names'),
          ('menu/LimitedBattle.bin', 4, 7, 'map_names')]
INDEXED_TABLES = [('menu/Gallery/acc/IaHelp.bin', 'accessory_descriptions'),
                  ('menu/Gallery/crm/IoHelpD.bin', 'charm_descriptions'),
                  ('menu/Gallery/crm/IoHelpE.bin', 'charm_effects'),
                  ('menu/Gallery/spi/IsHelp.bin', 'spirit_effects')]


def extract(root):
    rows = []
    sections = []
    for name, metadata_index, text_index, category in TABLES:
        data = (root / name).read_bytes()
        width = struct.unpack_from('<I', data)[0]
        header = struct.unpack_from('<' + str(width // 4) + 'I', data)
        metadata, start, end = header[metadata_index], header[text_index], header[text_index + 1]
        count = struct.unpack_from('<I', data, metadata)[0]
        raw = data[start:end].rstrip(b'\0')
        if not raw.endswith(b'\x0e') or b'\0' in raw:
            raise ValueError('Unexpected list termination: ' + name)
        items = raw[:-1].split(b'\x11\r\n')
        if len(items) != count:
            raise ValueError('Metadata row count disagrees with text list: ' + name)
        offset = start
        for index, item in enumerate(items):
            suffix = b'\x11\r\n' if index + 1 < count else b'\x0e'
            full = item + suffix
            text = full.decode('cp932', errors='strict')
            if any(ord(c) < 32 and c not in '\x11\x0e\r\n' for c in text):
                raise ValueError('Unknown control in ' + name)
            rows.append(dict(id=hashlib.sha256(full).hexdigest()[:20], file=name,
                             row_index=index, offset=offset, byte_length=len(full),
                             encoding='cp932', category=category, source=controls(text),
                             target='', status='untranslated',
                             structure=dict(text_header_offset=4 * text_index,
                                            section_offset=start, section_end=end,
                                            metadata_offset=metadata, separator_hex=suffix.hex())))
            offset += len(full)
        sections.append(dict(file=name, category=category, rows=count,
                             offset=start, end=end, metadata_offset=metadata))
    for name, category in INDEXED_TABLES:
        data = (root / name).read_bytes()
        start, end = struct.unpack_from('<2I', data, 8)
        if not 32 <= start < start + 1024 < end <= len(data):
            raise ValueError('Invalid indexed section: ' + name)
        offsets = struct.unpack_from('<256I', data, start)
        blob = start + 1024
        if offsets[0] != 0 or list(offsets) != sorted(set(offsets)):
            raise ValueError('Indexed offsets not strictly monotonic: ' + name)
        count = 0
        for index, offset in enumerate(offsets):
            stop = offsets[index + 1] if index < 255 else end - blob
            if not offset < stop <= end - blob:
                raise ValueError('Indexed text exceeds section: ' + name)
            raw = data[blob + offset:blob + stop].rstrip(b'\0')
            if not raw.endswith(b'\x0e') or b'\0' in raw:
                raise ValueError('Indexed text has bad termination: ' + name)
            text = raw.decode('cp932', errors='strict')
            if any(ord(c) < 32 and c not in '\x11\x0e\r\n' for c in text):
                raise ValueError('Unknown indexed-text control: ' + name)
            if raw == b'\x0e':
                continue
            count += 1
            rows.append(dict(id=hashlib.sha256(raw).hexdigest()[:20], file=name,
                             row_index=index, offset=blob + offset, byte_length=len(raw),
                             encoding='cp932', category=category, source=controls(text),
                             target='', status='untranslated',
                             structure=dict(text_header_offset=8, section_offset=start,
                                            section_end=end, blob_offset=blob,
                                            reference_offset=start + index * 4, separator_hex='0e')))
        sections.append(dict(file=name, category=category, rows=count,
                             references=256, offset=start, end=end))
    return rows, sections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('work/source/cpk'))
    parser.add_argument('--output', type=Path, default=Path('work/source/table_strings.json'))
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    rows, sections = extract(args.root)
    unique = {}
    for row in rows:
        if row['id'] not in unique:
            unique[row['id']] = {**row, 'occurrences': []}
        unique[row['id']]['occurrences'].append(row['file'] + ':' + str(row['row_index']))
    queue = list(unique.values())
    print(json.dumps(dict(rows=len(rows), unique_translation_rows=len(queue), sections=sections), indent=2))
    print(json.dumps(rows[:3], ensure_ascii=True, indent=2))
    if not args.write:
        print('DRY RUN: no data written. Check the sample before --write.')
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(version='0.1.0', scope='Verified menu text lists',
                                          sections=sections, rows=rows), ensure_ascii=False, indent=2), encoding='utf-8')
    dest = Path('work/translation/en')
    dest.mkdir(parents=True, exist_ok=True)
    prior, order = {}, {}
    for old in sorted(dest.glob('tables_*.json')):
        if old.name.endswith('.en.json'):
            continue
        for row in json.loads(old.read_text(encoding='utf-8'))['rows']:
            prior[row['id']] = row
            order[row['id']] = len(order)
    queue.sort(key=lambda row: order.get(row['id'], len(order)))
    for i in range(0, len(queue), 80):
        batch = queue[i:i + 80]
        for row in batch:
            if row['id'] in prior:
                row.update({k:v for k,v in prior[row['id']].items()
                            if k in ('target', 'status', 'notes', 'context', 'decisions')})
        (dest / ('tables_%04d.json' % (i // 80 + 1))).write_text(
            json.dumps(dict(schema_version=1, language='en', rows=batch), ensure_ascii=False, indent=2), encoding='utf-8')
    print('Wrote', args.output)
    print('Queued', len(queue), 'unique rows in', (len(queue) + 79) // 80, 'table batches')


if __name__ == '__main__':
    main()
