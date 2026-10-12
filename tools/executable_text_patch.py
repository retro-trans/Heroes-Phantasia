"""Read-only PSP executable text relocation inventory. Never writes executable bytes.

References come exclusively from PSP relocation records, not integer scans.
Encoding evidence is restricted to inherited, hash-verified renderer routes.
Unproved callers and interior pointers require independent review before integration.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import re
from dialogue_tokens import text_bytes, validate_controls
from private_latin import encode_character

ORIGINAL = Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf')
ORIGINAL_SHA = '03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def number(value):
    return int(value, 0) if isinstance(value, str) else value


def encoded_text(text, codec):
    # Queue notation stands for actual control bytes, not printed braces.
    if codec == 'engine-private-latin':
        if any(ord(c)>126 and c!='\u00e8' for c in text):
            raise ValueError('Target requires glyph outside proved ASCII/private è engine repertoire')
        return text_bytes(text, private_latin=True)
    return re.sub(r'\{([0-9A-Fa-f]{2})\}', lambda m: chr(int(m[1], 16)), text).encode(codec)


class Elf:
    def __init__(self, data):
        self.data = data
        if data[:7] != b'\x7fELF\x01\x01\x01':
            raise ValueError('Expected ELF32 little-endian version 1')
        if struct.unpack_from('<H', data, 18)[0] != 8:
            raise ValueError('Expected MIPS')
        phoff = struct.unpack_from('<I', data, 28)[0]
        entsize, count = struct.unpack_from('<HH', data, 42)
        if entsize != 32:
            raise ValueError('Unexpected program-header size')
        self.ph = [struct.unpack_from('<8I', data, phoff + n*32) for n in range(count)]
        self.loads = [p for p in self.ph if p[0] == 1]
        rels = [p for p in self.ph if p[0] == 0x700000a0]
        if len(rels) != 1:
            raise ValueError('Expected one PSP relocation program header')
        p = rels[0]
        if p[4] % 8 or p[1] + p[4] > len(data):
            raise ValueError('Invalid relocation extent')
        self.relocs = list(struct.iter_unpack('<II', data[p[1]:p[1]+p[4]]))

    def file_offset(self, rva, size=1):
        matches = [p[1]+rva-p[2] for p in self.loads if p[2] <= rva and rva+size <= p[2]+p[4]]
        if len(matches) != 1:
            raise ValueError(f'RVA not uniquely file-backed: {rva:#x}')
        return matches[0]

    def rva(self, offset, size=1):
        matches = [p[2]+offset-p[1] for p in self.loads if p[1] <= offset and offset+size <= p[1]+p[4]]
        if len(matches) != 1:
            raise ValueError(f'File offset not uniquely load-backed: {offset:#x}')
        return matches[0]

    def word(self, rva):
        return struct.unpack_from('<I', self.data, self.file_offset(rva, 4))[0]


def signed16(value):
    return value-0x10000 if value & 0x8000 else value


def address_pair(high, low):
    """Only signed PSP HI16/LO16 LUI + register-compatible low instructions.

    ORI is deliberately unsupported: adding a signed load base has different
    carry semantics. Loads/stores produce an effective address, not a pointer
    held in their destination register.
    """
    if high >> 26 != 15 or (high >> 21) & 31:
        raise ValueError('HI16 is not LUI')
    op = low >> 26
    if op not in (9, 32, 33, 35, 36, 37, 40, 41, 43, 49, 57):
        raise ValueError('Unsupported LO16 opcode')
    if (high >> 16) & 31 != (low >> 21) & 31:
        raise ValueError('HI16/LO16 base-register mismatch')
    return (((high & 65535) << 16) + signed16(low & 65535)) & 0xffffffff


def reaching_lui(elf, low_site, register, limit=128):
    """Bounded straight-line backwards trace; stop at control flow or clobber.

    This is semantic register evidence, separate from the PSP loader's forward
    HI relocation mate. It never infers a base across a branch or function call.
    """
    for site in range(low_site-4, max(-1, low_site-limit-4), -4):
        word = elf.word(site)
        op, rs, rt, rd, funct = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word & 63
        if op == 15 and rt == register:
            return site
        if op in (1,2,3,4,5,6,7,16,17,18,19,20,21,22,23,28,31):
            return None
        if op == 0:
            if funct in (8,9,12,13):
                return None
            if funct not in (17,19,24,25,26,27) and rd == register:
                return None
        elif op in (8,9,10,11,12,13,14,15,32,33,34,35,36,37,38,48,55) and rt == register:
            return None
        elif op not in (8,9,10,11,12,13,14,15,32,33,34,35,36,37,38,40,41,42,43,46,47,48,49,53,55,57,61,63):
            return None
    return None


def reference_index(elf):
    refs, issues, pending = [], [], defaultdict(list)
    high_sites = {}
    for ordinal, (off, flags) in enumerate(elf.relocs):
        storage = flags >> 8 & 255
        if flags & 255 == 5 and storage < len(elf.loads):
            high_sites[elf.loads[storage][2]+off] = ordinal, flags
    for ordinal, (off, flags) in enumerate(elf.relocs):
        typ, storage, target = flags & 255, flags >> 8 & 255, flags >> 16 & 255
        if typ not in (2, 5, 6):
            continue
        if flags >> 24 or storage >= len(elf.loads) or target >= len(elf.loads):
            issues.append(dict(ordinal=ordinal, reason='Unsupported relocation segment/flags'))
            continue
        site = elf.loads[storage][2] + off
        word = elf.word(site)
        if typ == 2:
            refs.append(dict(kind='R_MIPS_32', sites=[site], address=(word+elf.loads[target][2]) & 0xffffffff,
                             storage_segment=storage, target_segment=target, relocation_ordinals=[ordinal]))
        elif typ == 5:
            pending[(storage, target, word >> 16 & 31)].append((site, word, ordinal))
        else:
            key = storage, target, word >> 21 & 31
            candidates = pending.pop(key, [])
            if not candidates:
                previous = reaching_lui(elf, site, word >> 21 & 31)
                evidence = high_sites.get(previous)
                if evidence and evidence[1] >> 8 == flags >> 8:
                    candidates = [(previous, elf.word(previous), evidence[0])]
                else:
                    issues.append(dict(ordinal=ordinal, site=hex(site), reason='LO16 reused base unresolved by bounded straight-line register trace'))
            for hs, hw, ho in candidates:
                try:
                    addr = (address_pair(hw, word)+elf.loads[target][2]) & 0xffffffff
                    refs.append(dict(kind='R_MIPS_HI16_LO16', sites=[hs, site], address=addr,
                                     storage_segment=storage, target_segment=target, relocation_ordinals=[ho, ordinal]))
                except ValueError as exc:
                    issues.append(dict(ordinal=ordinal, site=hex(site), reason=str(exc)))
    for group in pending.values():
        for site, _, ordinal in group:
            issues.append(dict(ordinal=ordinal, site=hex(site), reason='Unpaired HI16'))
    # Loader carry pairing is not necessarily the register-compatible semantic
    # address pair. Preserve both, including HIs shared by multiple LO sites.
    high_counts = Counter(r['sites'][0] for r in refs if r['kind']=='R_MIPS_HI16_LO16')
    for ref in refs:
        if ref['kind'] != 'R_MIPS_HI16_LO16':
            continue
        high_ordinal = ref['relocation_ordinals'][0]
        mate = next((n for n in range(high_ordinal+1, len(elf.relocs)) if elf.relocs[n][1] & 255 != 5), None)
        ref['loader_forward_mate_ordinal'] = mate
        ref['loader_mate_is_semantic_low'] = mate == ref['relocation_ordinals'][1]
        ref['shared_high_site'] = high_counts[ref['sites'][0]] > 1
    return refs, issues


def select_rows(directory):
    files = [directory/f'executable_{n:04}.json' for n in range(1, 9)]
    files += [directory/'executable_supplement_0001.json']
    files += [directory/f for f in ('menu_ui_0001.json', 'setup_osk_0001.json', 'setup_defaults_0001.json')]
    rows, counts, conflicts, reused, identities = {}, {}, [], [], {}
    for path in files:
        data = json.loads(path.read_text(encoding='utf-8'))
        counts[path.name] = Counter(r.get('status', 'unknown') for r in data['rows'])
        authoritative = path.name in ('menu_ui_0001.json', 'setup_osk_0001.json', 'setup_defaults_0001.json')
        for row in data['rows']:
            if not row.get('target') or row.get('status') != 'draft':
                continue
            key = row['offset'], row['encoding'].replace('-', '').lower()
            identity = row['id']
            if identity in identities and identities[identity] != key:
                raise ValueError(f'ID/source identity conflict: {identity}')
            identities[identity] = key
            old = rows.get(key)
            if old:
                if old['row']['source'] != row['source'] or old['row']['byte_length'] != row['byte_length']:
                    raise ValueError(f'Duplicate source extent conflict: {identity}')
                reused.append(dict(id=identity, offset=hex(row['offset']), authoritative=authoritative))
                if old['row']['target'] != row['target']:
                    conflicts.append(dict(id=identity, offset=hex(row['offset']), earlier_target=old['row']['target'],
                                          authoritative_target=row['target'] if authoritative else None,
                                          resolved_by_authoritative_queue=authoritative))
                if not authoritative:
                    continue
            rows[key] = dict(row=row, queue=str(path), authoritative=authoritative)
    return list(rows.values()), {k:dict(v) for k,v in counts.items()}, conflicts, reused


def inherited_entries(report):
    result = {number(r['original_file_offset']): dict(r, route='installed_osk_utf16' if r.get('encoding') == 'utf-16-le' else 'installed_ascii_setup') for r in report.get('strings', [])}
    for r in report.get('save_ui_patch', {}).get('labels', []):
        result[number(r['original_file_offset'])] = dict(r, route='sceUtility_savedata_utf8')
    return result


def installed_check(base, entry):
    address = number(entry['payload_rva'])
    codec = entry.get('encoding', 'utf-8')
    encoded = entry['target'].encode(codec) + (b'\0\0' if codec == 'utf-16-le' else b'\0')
    off = base.file_offset(address, len(encoded))
    if base.data[off:off+len(encoded)] != encoded:
        raise ValueError(f'Inherited payload differs at {address:#x}')
    sites = [number(r) for r in entry.get('pointer_rvas', [])]
    sites += [base.rva(number(r), 4) for r in entry.get('pointer_file_offsets', [])]
    for site in sites:
        if base.word(site) != address:
            raise ValueError(f'Inherited pointer differs at {site:#x}')
    for pair in entry.get('address_pairs', []):
        hi, lo = map(number, pair)
        if address_pair(base.word(hi), base.word(lo)) != address:
            raise ValueError(f'Inherited address pair differs at {hi:#x}')
    return dict(payload_rva=hex(address), target=entry['target'], route=entry['route'],
                verified_pointer_sites=[hex(s) for s in sites], verified_address_pairs=entry.get('address_pairs', []))


def payload_models(target):
    models = {}
    def engine_latin():
        if any(ord(c) > 126 and c != '\u00e8' for c in target):
            raise ValueError('Glyph outside established ASCII plus private è repertoire')
        return text_bytes(target, private_latin=True)
    for name, encode in (('utf8', lambda: encoded_text(target, 'utf-8')),
                         ('engine_private_latin', engine_latin)):
        try:
            raw = encode()
            models[name] = dict(bytes_including_nul=len(raw)+1, payload_sha256=digest(raw+b'\0'),
                                selected=False, note='Hypothetical only; caller proof required')
        except (UnicodeEncodeError, ValueError) as exc:
            models[name] = dict(selected=False, unsupported=str(exc))
    return models


def mao_analysis(original):
    source_rva = original.rva(0x2eb740, 12)
    if original.word(0x3073f8) != source_rva:
        raise ValueError('Mao entity pointer changed')
    dispatch = original.word(0x2ef2d0+15*4)
    if dispatch != 0xeae94:
        raise ValueError('Native measure ruby dispatch changed')
    if original.word(0x2f1220+15*4) != 0xefc80 or original.word(0x2f1430+15*4) != 0xf0cb4:
        raise ValueError('Native drawing ruby dispatch changed')
    return dict(status='specific_Mao_display_caller_unresolved_target_remains_empty', entity_pointer_rva='0x3073f8',
                table_base_rva='0x3071d0', stride=28, name_field_offset=20, entity_index=19,
                table_setup_code=['0xead58','0xead60','0xead6c'],
                entity_expansion_code=['0xeb11c','0xeb120','0xeb124','0xeb128','0xeb12c','0xeb134'],
                expansion_reentry_code=['0xeb5c0','0xeb5cc','0xeb5d0'],
                measure_function='0xead20', measure_ruby_dispatch='0xeae94',
                measure_ruby_code=['0xeaec0','0xeaec4','0xeaed0','0xeaed8'],
                finding='Measure/name expansion follows the entity pointer and skips the reading up to closing ruby marker; decimal span digits are optional in this measure path.',
                native_skip_reading_draw_function='0xeed34', skip_reading_entity_expansion=['0xeefbc','0xeefc8','0xef6f8'],
                skip_reading_ruby_handler='0xefc80', skip_reading_ruby_dispatch_table='0x2f1220',
                native_render_reading_draw_function='0xefee0', render_reading_entity_expansion=['0xf0178','0xf0184','0xf08b4'],
                render_reading_ruby_dispatch_table='0x2f1430',
                finding_draw='The first drawing handler skips the entire reading without a digit; the second draws ruby and consumes a span byte. Both handlers access this entity table.',
                limitation='The particular UI/caller that displays Mao is not established. F0CB4 consumes a following span byte unconditionally. No span digit may be invented.',
                native_drawing_ruby_handler='0xf0cb4')


def save_episode_route(original, matched):
    # The indexed source pointer is copied directly to sfo.savedataTitle.
    # This differs from engine labels and is independent of extraction encoding.
    table_sites = set(range(0x471674, 0x4716ec, 4)) | {0x4716f4}
    if not any(r['kind']=='R_MIPS_32' and r['sites'][0] in table_sites for r in matched):
        return None
    expected = {0x115c10:0x26110080, 0x115cf8:0x3c050047,
                0x115d00:0x24a51674, 0x115d08:0x8c850000,
                0x115d10:0x0c04a35b, 0x115d14:0x3406007f}
    # Verify actual instruction fields rather than trusting a table-range name.
    for site, word in expected.items():
        if original.word(site) != word:
            raise ValueError(f'Savedata caption caller differs at {site:#x}')
    return dict(route='sceUtility_savedata_episode_utf8_static', encoding='utf-8',
                native_capacity_including_nul=128, copy_max_bytes=127,
                caller='0x115bc8', table_rva='0x471674', pointer_load='0x115d08', copy_call='0x115d10',
                destination='SFO savedataTitle at parameter+0x114',
                sources=['https://github.com/pspdev/pspsdk/blob/master/src/utility/psputility_savedata.h',
                         'https://github.com/hrydgard/ppsspp/blob/master/Core/Dialog/PSPSaveDialog.cpp'],
                runtime_verified=False)


def engine_table_route(matched):
    # These six typed name fields are consumed by both native control02 drawing
    # handlers. They are not UTF8 savedata fields or anonymous integer matches.
    families = [('entity',0x3071d0,28,20,0xeefbc,0xf0178),
                ('dictionary',0x308dd0,16,8,0xeef50,0xf010c),
                ('knowledge',0x309dd0,16,8,0xeef80,0xf013c),
                ('amulet',0x30add0,84,76,0xef074,0xf0230),
                ('item',0x3101d0,92,80,0xef038,0xf01f4),
                ('title',0x315dd0,108,100,0xeeffc,0xf01b8)]
    for name, table, stride, field, draw_skip, draw_ruby in families:
        for ref in matched:
            if ref['kind'] != 'R_MIPS_32':
                continue
            slot = ref['sites'][0]
            if table+field <= slot < table+256*stride and (slot-table-field)%stride == 0:
                return dict(route='native_control02_name_table_engine_latin_static', encoding='engine-private-latin',
                            family=name, table_rva=hex(table), stride=stride, name_field_offset=field,
                            record_index=(slot-table-field)//stride, pointer_slot=hex(slot),
                            measure_function='0xead20', decoder='0xe9c64',
                            draw_handlers=['0xeed34','0xefee0'], table_draw_setup=[hex(draw_skip),hex(draw_ruby)],
                            current_Latin_decoder_gate='0xe9cc8', private_e_grave_code=128,
                            runtime_verified=False, all_consumers_verified=False,
                            limitation='Encoding is proved for native control02 expansion. Other table consumers, layout, runtime widths and all screen instances still require QA.')
    return None


def scoped_template(report):
    """Propose payloads and exact typed R32 slots; never mutate ELF bytes.

    Shared pool strings may have other consumers. Those references are retained,
    rather than transferring a single route's encoding proof to every consumer.
    The font assembler must supply the candidate accent bank before installing.
    """
    entries, retained, cursor = [], [], number(report['allocation_model']['candidate_append_rva'])
    occupied = set()
    save_slots = set(range(0x471674, 0x4716ec, 4)) | {0x4716f4}
    for row in report['rows']:
        if row['inherited']:
            continue
        route = row['renderer_evidence']
        if route not in ('native_control02_name_table_engine_latin_static', 'sceUtility_savedata_episode_utf8_static'):
            continue
        selected, untouched = [], []
        for ref in row['references']:
            native = dict(ref, sites=[number(s) for s in ref['sites']])
            eligible = (ref['kind']=='R_MIPS_32' and not ref['interior_source_byte_offset']
                        and not ref['already_changed'] and
                        (engine_table_route([native]) if route.startswith('native_') else native['sites'][0] in save_slots))
            (selected if eligible else untouched).append(ref)
        if not selected:
            continue
        text = re.sub(r'\{([0-9A-Fa-f]{2})\}', lambda m: chr(int(m[1], 16)), row['target'])
        if route.startswith('native_'):
            if any(ord(c)>126 and c not in '\u00e8\u00e1\u00e9' for c in text):
                raise ValueError(f"Unapproved native glyph in scoped template: {row['id']}")
            payload = b''.join(encode_character(c) for c in text)+b'\0'
            codec, prerequisite = 'engine-private-latin', 'cp932-pua-f040-f041-v1 candidate font/decoder integration'
        else:
            payload = text.encode('utf-8')+b'\0'
            if len(payload)>128:
                raise ValueError(f"Savedata caption exceeds native capacity: {row['id']}")
            codec, prerequisite = 'utf-8', None
        writes = []
        for ref in selected:
            site = ref['sites'][0]
            if site in occupied:
                raise ValueError(f'Duplicate typed pointer slot: {site}')
            occupied.add(site)
            if number(ref['base_words'][0]) != number(row['source_rva']):
                raise ValueError(f"Scoped pointer source differs: {row['id']}")
            writes.append(dict(pointer_rva=site, expected_word=ref['base_words'][0],
                               proposed_resolved_rva=hex(cursor), relocation_kind='R_MIPS_32',
                               required_target_segment='new_payload_load_segment',
                               proposed_stored_offset=hex(cursor-number(report['allocation_model']['candidate_append_rva'])),
                               pointer_proof=engine_table_route([dict(ref, sites=[number(site)])]) if route.startswith('native_') else row['caller_evidence']))
        entries.append(dict(id=row['id'], target=row['target'], encoding=codec, payload_hex=payload.hex(),
                            payload_sha256=digest(payload), payload_bytes=len(payload), proposed_rva=hex(cursor),
                            pointer_writes=writes, required_font_model=prerequisite, runtime_verified=False))
        cursor += len(payload)
        retained.extend(dict(id=row['id'], reference=ref, reason='Outside proved typed pointer scope; keep original route and bytes') for ref in untouched)
    return dict(mode='dry_scoped_pointer_template_no_elf_writer', base_sha256=report['base_sha256'],
                original_sha256=report['original_sha256'], base_version=report['version'],
                proposed_append_rva=report['allocation_model']['candidate_append_rva'],
                selected_records=len(entries), typed_pointer_writes=len(occupied), payload_bytes=sum(e['payload_bytes'] for e in entries),
                route_counts=dict(Counter(e['encoding'] for e in entries)), entries=entries,
                untouched_other_consumers=retained, inherited_entries_preserved=report['inherited_entries_verified'],
                install_ready=False, runtime_verified=False,
                limitations=['Hypothetical append address must be reconciled with the font assembler final load extent.',
                             'Use consistent R32 storage: explicit payload target segment stores offset within that segment. Target-zero/full module RVA is also valid but is not this template convention. Preserve inherited conventions.',
                             'No HI/LO instructions or other consumers are retargeted by this template.',
                             'Mao remains empty and excluded. Runtime layout and all display instances remain unverified.'])


def plan(original_path, manifest_path, directory):
    original_bytes = original_path.read_bytes()
    if digest(original_bytes) != ORIGINAL_SHA:
        raise ValueError('Original executable hash differs')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    base_path = manifest_path.with_name('EBOOT.BIN')
    base_bytes = base_path.read_bytes()
    if digest(base_bytes) != manifest['output_elf_sha256']:
        raise ValueError('Current executable/manifest hash mismatch')
    inherited_path = Path(manifest['executable_preparation_report'])
    inherited = json.loads(inherited_path.read_text(encoding='utf-8'))
    if inherited['output_elf_sha256'] != digest(base_bytes):
        raise ValueError('Inherited preparation report hash differs from current executable')
    original, base = Elf(original_bytes), Elf(base_bytes)
    refs, issues = reference_index(original)
    selected, counts, conflicts, reused = select_rows(directory)
    installed = inherited_entries(inherited)
    preserved = {offset: installed_check(base, entry) for offset, entry in installed.items()}
    records = []
    # Menu pointers are installed ASCII VWF routes, identified by the existing
    # five-slot table, not by an arbitrary match of integer values.
    menu_sites = dict(zip((0x94f43,0x94f50,0x94f57,0x94f62,0x94f6d), range(0x948d4,0x948e8,4)))
    for selection in selected:
        row = selection['row']; off, size = row['offset'], row['byte_length']
        codec = row['encoding']; source = encoded_text(row['source'], codec)
        if len(source) != size or original_bytes[off:off+size] != source:
            raise ValueError(f'Original source bytes differ: {row["id"]}')
        errors = validate_controls(row['source'], row['target'])
        if errors:
            raise ValueError(f'Control mismatch {row["id"]}: {errors}')
        start = original.rva(off, size)
        matched = [r for r in refs if start <= r['address'] < start+size]
        blockers, route, encoding, previous = [], None, None, preserved.get(off)
        if previous:
            route = previous['route']; encoding = {'sceUtility_savedata_utf8':'utf-8', 'installed_osk_utf16':'utf-16-le'}.get(route, 'ascii')
            if previous['target'] != row['target']:
                blockers.append('Draft differs from installed inherited target; preserve installed bytes until separately reviewed')
        elif off in menu_sites:
            site = menu_sites[off]; address = base.word(site)
            payload = row['target'].encode('ascii')+b'\0'
            at = base.file_offset(address, len(payload))
            if base.data[at:at+len(payload)] != payload:
                blockers.append('Installed menu target differs')
            else:
                route, encoding = 'installed_menu_ascii_vwf', 'ascii'
                previous = dict(payload_rva=hex(address), target=row['target'], route=route, verified_pointer_sites=[hex(site)])
        elif save_episode_route(original, matched):
            route, encoding = 'sceUtility_savedata_episode_utf8_static', 'utf-8'
            if len(encoded_text(row['target'], encoding)) >= 128:
                blockers.append('Native savedata title destination needs expansion; 127-byte copy would truncate')
        elif engine_table_route(matched):
            route, encoding = 'native_control02_name_table_engine_latin_static', 'engine-private-latin'
            if 128 not in inherited.get('high_codes', []):
                blockers.append('Current font bank does not establish private è glyph128')
            if base.word(0xe9cc8) == original.word(0xe9cc8):
                blockers.append('Current executable lacks the visible-Latin decoder hook')
        elif codec.replace('-', '').lower() == 'utf16le':
            blockers.append('OSK UTF16 route needs current inherited extent/pointer verification; not an engine Latin route')
        else:
            blockers.append('Renderer/caller route unproved: do not choose UTF8 or private-Latin by source encoding')
        if not matched and not previous:
            blockers.append('No relocation-backed source reference; table-derived/inline reference discovery required')
        output_refs = []
        for ref in matched:
            delta = ref['address']-start
            item = dict(ref, sites=[hex(s) for s in ref['sites']], address=hex(ref['address']), interior_source_byte_offset=delta)
            current = [base.word(s) for s in ref['sites']]
            item['base_words'] = [hex(w) for w in current]
            item['original_words'] = [hex(original.word(s)) for s in ref['sites']]
            item['already_changed'] = current != [original.word(s) for s in ref['sites']]
            if delta:
                blockers.append('Interior reference requires reviewed semantic target offset; byte delta is not transferable')
            if item['already_changed'] and not previous:
                blockers.append('Reference already changed in inherited executable without matching text proof; preserve')
            if ref.get('shared_high_site'):
                blockers.append('Shared LUI base requires reviewed rewrite/group placement; do not independently retarget HI halves')
            output_refs.append(item)
        try:
            payload_bytes = len(encoded_text(row['target'], encoding))+(2 if encoding == 'utf-16-le' else 1) if encoding else None
        except (UnicodeEncodeError, ValueError):
            payload_bytes = None; blockers.append('Target not representable in proved encoding; additional glyph route required')
        records.append(dict(id=row['id'], queue=selection['queue'], original_file_offset=hex(off), source_rva=hex(start),
                            source_byte_length=size, source_encoding=codec, target=row['target'], target_encoding=encoding,
                            renderer_evidence=route, proposed_payload_bytes_including_nul=payload_bytes, inherited=previous,
                            caller_evidence=save_episode_route(original, matched) if route=='sceUtility_savedata_episode_utf8_static' else engine_table_route(matched) if route=='native_control02_name_table_engine_latin_static' else None,
                            hypothetical_encoding_models=payload_models(row['target']) if not encoding else None,
                            references=output_refs, blockers=sorted(set(blockers)), action='preserve_inherited' if previous else 'dry_candidate_pending_integration_review' if route and not blockers else 'blocked_pending_caller_proof'))
    after_loads = max(p[2]+p[5] for p in base.loads)
    append_rva = (after_loads+63)//64*64
    return dict(schema_version=1, mode='dry_only_no_executable_writer', version=manifest['version'],
                original_sha256=digest(original_bytes), base_sha256=digest(base_bytes),
                base_manifest=str(manifest_path), inherited_report=str(inherited_path), queues=counts,
                selected_unique_drafts=len(records), authoritative_reuses=reused, dedup_target_conflicts=conflicts,
                original_relocation_records=len(original.relocs), decoded_reference_candidates=len(refs),
                selected_reference_counts=dict(Counter(ref['kind'] for r in records for ref in r['references'])),
                rows_without_decoded_references=sum(not r['references'] for r in records),
                rows_with_interior_references=sum(any(ref['interior_source_byte_offset'] for ref in r['references']) for r in records),
                reference_coverage_complete=False,
                reference_parser_limitations=issues, inherited_entries_verified=len(preserved),
                relocation_issue_counts=dict(Counter(i['reason'] for i in issues)),
                renderer_routes=dict(Counter(r['renderer_evidence'] or 'unproved' for r in records)),
                mao_formatter_analysis=mao_analysis(original),
                allocation_model=dict(candidate_append_rva=hex(append_rva), alignment=64,
                    current_load_extents=[dict(rva=hex(p[2]), file_bytes=p[4], memory_bytes=p[5]) for p in base.loads],
                    selected_payload_bytes=sum(r['proposed_payload_bytes_including_nul'] or 0 for r in records if not r['inherited']),
                    install_ready=False, note='No unproved encoding is selected; no allocation, relocation-table extension, or segment is emitted.'),
                blocked_rows=sum(bool(r['blockers']) for r in records), rows=records,
                limitations=['No ELF bytes are emitted or changed.', 'No appended-segment placement or installation is authorized.',
                             'A relocation candidate is not full caller/dataflow proof.',
                             'Unpaired/unsupported relocation instructions remain explicit; no generic integer replacement.',
                             'Raw Mao ruby source remains untranslated; formatter path not proved.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, default=ORIGINAL)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--queue', type=Path, default=Path('work/translation/en'))
    parser.add_argument('--report', type=Path, help='Optional English-only dry report; never an executable')
    args = parser.parse_args()
    version = json.loads(Path('build.json').read_text())['version']
    manifest = args.manifest or Path(f'work/output/{version}-title-credit-vwf-4x-candidate/manifest.en.json')
    report = plan(args.original, manifest, args.queue)
    report['scoped_integration_template'] = scoped_template(report)
    if args.report:
        if args.report.suffix != '.json' or not args.report.name.endswith('.en.json'):
            parser.error('Dry report must use .en.json, never an executable path')
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('mode','version','selected_unique_drafts','inherited_entries_verified',
        'renderer_routes','blocked_rows','selected_reference_counts','rows_without_decoded_references',
        'rows_with_interior_references','relocation_issue_counts','reference_coverage_complete')}, indent=2))


if __name__ == '__main__':
    main()
