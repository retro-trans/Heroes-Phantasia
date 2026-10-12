"""Pure approved cast-bank and notification format relocation; no ELF writer."""
import json
from pathlib import Path
from executable_text_patch import Elf, reference_index, digest
from notification_scope import ORIGINAL, SOURCE_SHA

FORMAT_ID = 'exe_002eb1d8_cp932'
FORMAT_SHA = 'cea9601135398cebdc92c39c5bc72a82d8f36b453e2e5d1b2af56b0d98efd449'


def _queue():
    rows = {}
    for path in Path('work/translation/en').glob('executable*.json'):
        if path.name.endswith('.en.json'):
            continue
        for row in json.loads(path.read_text(encoding='utf8')).get('rows', []):
            if row['id'] in rows:
                raise ValueError('Duplicate executable queue ID')
            rows[row['id']] = row
    return rows


def payload():
    original = ORIGINAL.read_bytes()
    if digest(original) != SOURCE_SHA:
        raise ValueError('Original ELF digest differs')
    elf, rows = Elf(original), _queue()
    data, offsets, entries = bytearray(), {}, []
    for index in range(34):
        site = 0x96130 + index * 4
        pointer = elf.word(site)
        offset = elf.file_offset(pointer)
        end = original.index(0, offset, offset + 128)
        raw = original[offset:end]
        row = rows[f'exe_{offset:08x}_cp932']
        if row['status'] != 'draft' or row['offset'] != offset or row['byte_length'] != len(raw):
            raise ValueError('Cast queue source/status differs')
        if digest(raw + b'\0') != row['original_string_sha256']:
            raise ValueError('Cast source digest differs')
        if row['direct_R_MIPS_32_reference_rvas'] != [hex(site)]:
            raise ValueError('Cast typed reference scope differs')
        value = row['target'].encode('ascii') + b'\0'
        if not 1 < len(value) <= 22:
            raise ValueError('Approved cast expansion bound differs')
        if value not in offsets:
            offsets[value] = len(data)
            data.extend(value)
        entries.append({'id': row['id'], 'target': row['target'], 'site': site,
                        'source_rva': pointer, 'source_sha256': digest(raw),
                        'payload_offset': offsets[value], 'bytes_including_nul': len(value)})
    row = rows[FORMAT_ID]
    offset = row['offset']
    raw = original[offset:offset + row['byte_length']]
    if row['status'] != 'draft' or row['target'] != '%s No. %s' or digest(raw + b'\0') != FORMAT_SHA:
        raise ValueError('Reviewed notification format source/target differs')
    return bytes(data), b'%s No. %s\0', entries


def plan(base, report, voice_rva, format_rva):
    if digest(base) != report.get('output_elf_sha256'):
        raise ValueError('Incoming ELF/report digest differs')
    original, incoming = Elf(ORIGINAL.read_bytes()), Elf(base)
    voices, format_data, entries = payload()
    writes = []
    for entry in entries:
        site, expected = entry['site'], entry['source_rva']
        if incoming.word(site) != expected or incoming.relocs.count((site, 2)) != 1:
            raise ValueError('Cast original R32 pointer/relocation differs')
        offset = incoming.file_offset(expected)
        end = base.index(0, offset, offset + 128)
        if digest(base[offset:end]) != entry['source_sha256']:
            raise ValueError('Incoming original cast bytes differ')
        writes.append({'rva': site, 'expected_word': expected,
                       'replacement_word': voice_rva + entry['payload_offset']})
    refs, _ = reference_index(original)
    refs = [r for r in refs if r['sites'] == [0x81244, 0x81254]]
    if len(refs) != 1 or not refs[0]['loader_mate_is_semantic_low'] or refs[0]['shared_high_site']:
        raise ValueError('Format semantic HI/LO pair differs')
    ref = refs[0]
    source = incoming.file_offset(ref['address'])
    end = base.index(0, source, source + 128)
    if digest(base[source:end + 1]) != FORMAT_SHA:
        raise ValueError('Incoming notification format source differs')
    for site, kind in ((0x81244, 5), (0x81254, 6)):
        expected = original.word(site)
        if incoming.word(site) != expected or incoming.relocs.count((site, kind)) != 1:
            raise ValueError('Format native word/relocation differs')
        value = (format_rva + 0x8000) >> 16 if kind == 5 else format_rva
        writes.append({'rva': site, 'expected_word': expected,
                       'replacement_word': (expected & 0xffff0000) | (value & 65535)})
    return voices, format_data, {
        'input_elf_sha256': digest(base), 'voice_rva': voice_rva, 'voice_bytes': len(voices),
        'voice_sha256': digest(voices), 'voice_positions': 34,
        'deduplicated_target_strings': len({e['payload_offset'] for e in entries}),
        'voice_max_bytes': max(e['bytes_including_nul'] - 1 for e in entries),
        'voice_entries': entries, 'native_writes': writes,
        'existing_target0_relocations_preserved': True,
        'format_rva': format_rva, 'format_bytes': len(format_data),
        'format_sha256': digest(format_data), 'format_source_sha256': FORMAT_SHA,
        'format_id': FORMAT_ID, 'format_sites': [0x81244, 0x81254],
        'Hero_Heroine_paths_untouched': True, 'runtime_verified': False}
