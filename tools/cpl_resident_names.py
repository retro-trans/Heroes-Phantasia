"""Pure original-CPL HUD name lookup proposal. No asset or executable writer."""
import hashlib
import json
import struct
from pathlib import Path

from dialogue_vwf_hooks import Block, address, r
from live_vwf import i, j


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_table():
    inventory_path = Path('work/source/cpl_text_inventory.json')
    inventory_bytes = inventory_path.read_bytes()
    inventory = json.loads(inventory_bytes)
    targets = {}
    snapshots = []
    for path in sorted(Path('work/translation/en').glob('cpl_[0-9][0-9][0-9][0-9].json')):
        raw = path.read_bytes()
        snapshots.append({'path': str(path), 'sha256': sha(raw)})
        for row in json.loads(raw)['rows']:
            if row['id'] in targets:
                raise ValueError('Duplicate CPL ID')
            targets[row['id']] = row
    rows = [row for row in inventory['rows'] if row['row_index'] == 0]
    if len(rows) != 79:
        raise ValueError('Expected reviewed 79 unique name-index0 rows')
    originals = {}
    for asset in inventory['files']:
        raw = (Path('work/source/cpk') / asset['resource']).read_bytes()
        if len(raw) != asset['bytes'] or sha(raw) != asset['sha256']:
            raise ValueError('Original CPL asset digest differs')
        originals[asset['resource']] = raw
    if len(originals) != 424:
        raise ValueError('Expected 424 guarded original CPL resources')
    records = []
    pairs = []
    sources = set()
    for row in rows:
        target = targets[row['id']]
        for key in ('source', 'occurrences', 'original_bytes_sha256', 'structure'):
            if target[key] != row[key]:
                raise ValueError('Immutable CPL queue metadata differs')
        source = row['source'].encode('cp932') + b'\0'
        latin = target['target'].encode('ascii') + b'\0'
        if source in sources or len(source) > 17:
            raise ValueError('Duplicate or excessive source key')
        if target['status'] != 'draft' or not 2 <= len(latin) <= 32:
            raise ValueError('HUD target must be reviewed 1..31 ASCII bytes')
        sources.add(source)
        for occurrence in row['occurrences']:
            raw = originals[occurrence['file']]
            start = occurrence['offset']
            if struct.unpack_from('<I', raw, 4)[0] != start:
                raise ValueError('Original CPL name-pointer field differs')
            if raw[start:start + len(source)] != source:
                raise ValueError('Original CPL name key differs')
            if sha(source) != occurrence['original_bytes_sha256']:
                raise ValueError('Original name-key digest differs')
        pairs.append((source, latin))
        records.append({'id': row['id'], 'target': target['target'],
                        'source_key_sha256': sha(source), 'source_bytes': len(source),
                        'target_bytes': len(latin), 'occurrences': len(row['occurrences'])})
    if sum(row['occurrences'] for row in records) != 424:
        raise ValueError('Expected 424 original CPL name occurrences')
    table = bytearray(4 + 8 * len(pairs))
    struct.pack_into('<I', table, 0, len(pairs))
    pooled = {}
    for index, pair in enumerate(pairs):
        offsets = []
        for value in pair:
            if value not in pooled:
                pooled[value] = len(table)
                table.extend(value)
            offsets.append(pooled[value])
        struct.pack_into('<II', table, 4 + 8 * index, *offsets)
    table.extend(bytes((-len(table)) % 4))
    target_sha = sha(json.dumps({row['id']: row['target'] for row in records},
                               sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf8'))
    if target_sha != '8c63b07f0c6d296815a3479b1f62bce9ffef229336efcb81014d51c5aa618aa7':
        raise ValueError('Reviewed resident CPL target bank changed')
    return bytes(table), pairs, {'records': records, 'inventory_sha256': sha(inventory_bytes),
                                'queue_snapshots': snapshots, 'table_bytes': len(table),
                                'table_sha256': sha(table), 'max_key_bytes': 17,
                                'original_resources_guarded': len(originals),
                                'target_sha256': target_sha,
                                'runtime_verified': False}


def hud_lookup(table_rva):
    """B06C4 tail hook. Preserve every temporary except native overwritten A0/A1."""
    h = Block()
    h.emit(i(9, 29, 29, -48))
    registers = (6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
    for index, register in enumerate(registers):
        h.emit(i(43, 29, register, index * 4))
    h.branch(4, 2, 0, 'done')
    address(h, 8, table_rva)
    h.emit(i(35, 8, 9, 0), i(9, 8, 10, 4))
    h.label('record')
    h.branch(4, 9, 0, 'done')
    h.emit(i(35, 10, 11, 0), r(8, 11, 11), r(2, 0, 12), i(13, 0, 15, 17))
    h.label('compare')
    h.emit(i(36, 11, 13, 0), i(36, 12, 14, 0))
    h.branch(5, 13, 14, 'next')
    h.branch(4, 13, 0, 'match')
    h.emit(i(9, 15, 15, -1))
    h.branch(4, 15, 0, 'next')
    h.emit(i(9, 11, 11, 1), i(9, 12, 12, 1))
    h.branch(4, 0, 0, 'compare')
    h.label('next')
    h.emit(i(9, 9, 9, -1), i(9, 10, 10, 8))
    h.branch(4, 0, 0, 'record')
    h.label('match')
    h.emit(i(35, 10, 11, 4), r(8, 11, 2))
    h.label('done')
    for index, register in enumerate(registers):
        h.emit(i(35, 29, register, index * 4))
    h.emit(i(9, 29, 29, 48), i(13, 0, 4, 0x12), r(16, 0, 5, funct=0x25), j(0xb06cc), 0)
    return h.finish()


def lookup_model(table, source):
    """Byte-exact bounded comparison includes CP932 trail bytes and final NUL."""
    count = struct.unpack_from('<I', table)[0]
    for index in range(count):
        key, value = struct.unpack_from('<II', table, 4 + 8 * index)
        for offset in range(17):
            if offset >= len(source) or source[offset] != table[key + offset]:
                break
            if source[offset] == 0:
                return table[value:table.index(0, value)], True
    return source.rstrip(b'\0'), False
