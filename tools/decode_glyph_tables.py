"""Decode native u16 glyph tables using an explicitly reviewed character map.

Defaults to a dry run. Never interpret glyph IDs as Unicode or CP932 directly.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct


def table(data):
    start,end = struct.unpack_from('<2I',data,4)
    if not 32 <= start < start + 1024 < end <= len(data):
        raise ValueError('Invalid indexed name section')
    offsets = struct.unpack_from('<256I',data,start)
    if list(offsets) != sorted(set(offsets)) or offsets[0] != 1028:
        raise ValueError('Unknown table offset layout')
    rows = []
    for index, offset in enumerate(offsets):
        stop = offsets[index + 1] if index < 255 else end - start
        raw = data[start + offset:start + stop]
        if len(raw) % 2:
            raise ValueError('Odd-length glyph sequence')
        ids = list(struct.unpack('<' + str(len(raw) // 2) + 'H',raw))
        if 0 not in ids:
            raise ValueError('Unterminated glyph sequence')
        end_index = ids.index(0)
        if any(ids[end_index:]):
            raise ValueError('Nonzero bytes after glyph terminator')
        rows.append(dict(row_index=index, offset=start+offset, reference_offset=start+index*4,
                         glyph_ids=ids[:end_index], byte_length=len(raw)))
    return rows


def decode(rows, evidence):
    mapping = {}
    witnesses = collections.defaultdict(list)
    for key,text in evidence['seeds'].items():
        index = int(key)
        ids = rows[index]['glyph_ids']
        if len(ids) != len(text):
            raise ValueError('Seed length mismatch at row %d: %s vs %s' % (index,ids,text))
        for glyph,char in zip(ids,text):
            if glyph in mapping and mapping[glyph] != char:
                raise ValueError('Seed mapping conflict at row %d, glyph %d: %s vs %s' % (index,glyph,mapping[glyph],char))
            mapping[glyph] = char
            witnesses[glyph].append(index)
    if len(set(mapping.values())) != len(mapping):
        raise ValueError('Character map is not one-to-one; review ambiguous glyph seeds')
    for row in rows:
        row['source'] = ''.join(mapping.get(glyph,'{GLYPH_%03d}' % glyph) for glyph in row['glyph_ids'])
        row['unresolved_glyphs'] = sorted(set(row['glyph_ids']) - set(mapping))
        row['status'] = 'decoded' if not row['unresolved_glyphs'] else 'unresolved'
        row['encoding'] = 'local-glyph-id-u16le'
        row['runtime_visibility'] = 'unverified'
        row['role'] = 'debug_label_candidate' if row['row_index'] >= 244 else 'battle_name_label'
    return mapping,witnesses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds',type=Path,default=Path('work/source/font_audit/glyph_seeds.json'))
    parser.add_argument('--write',action='store_true')
    args = parser.parse_args()
    evidence = json.loads(args.seeds.read_text(encoding='utf-8'))
    name = evidence['file']
    data = (Path('work/source/cpk')/name).read_bytes()
    rows = table(data)
    mapping,witnesses = decode(rows,evidence)
    inverse = {char:glyph for glyph,char in mapping.items()}
    for row in rows:
        if row['unresolved_glyphs']:
            continue
        rebuilt = b''.join(struct.pack('<H',inverse[char]) for char in row['source'])
        rebuilt += bytes(row['byte_length'] - len(rebuilt))
        if rebuilt != data[row['offset']:row['offset'] + row['byte_length']]:
            raise ValueError('Glyph round trip failed at row %d' % row['row_index'])
    summary = dict(file=name, rows=len(rows), nonempty_rows=sum(bool(r['glyph_ids']) for r in rows),
                   sha256=hashlib.sha256(data).hexdigest(),
                   mapping_method=evidence['method'], round_trip_verified=True,
                   decoded_nonempty_rows=sum(bool(r['glyph_ids']) and r['status']=='decoded' for r in rows),
                   referenced_glyphs=len(set(g for r in rows for g in r['glyph_ids'])),
                   mapped_glyphs=len(mapping), unresolved_glyphs=sorted(set(g for r in rows for g in r['unresolved_glyphs'])),
                   unique_decoded_labels=len(set(r['source'] for r in rows if r['glyph_ids'] and r['status']=='decoded')))
    print(json.dumps(summary,indent=2))
    print(json.dumps(rows[:12],ensure_ascii=True,indent=2))
    if not args.write:
        print('DRY RUN: no decoded inventory written.');return
    root=Path('work/source/font_audit');root.mkdir(parents=True,exist_ok=True)
    (root/'sys_tbl_glyph_map.json').write_text(json.dumps(dict(file=name, method=evidence['method'],
        glyphs=[dict(id=i,character=mapping[i],seed_rows=sorted(set(witnesses[i]))) for i in sorted(mapping)]),
        ensure_ascii=False,indent=2),encoding='utf-8')
    (root/'sys_tbl_names.json').write_text(json.dumps(dict(summary=summary,rows=rows),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Wrote reviewed map and decoded names to',root)


if __name__=='__main__':main()
