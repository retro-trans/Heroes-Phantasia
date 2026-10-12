"""Pure guarded notification-bank and Gold termination proposal. No ELF writer."""
import json
import struct
from pathlib import Path

from executable_text_patch import Elf, reference_index, digest
from notification_hooks import gold_terminate
from live_vwf import j

ORIGINAL = Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf')
SOURCE_SHA = '03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1'
START, SIZE = 0x305dc8, 1280
POOL_SHA = '39457d20992e78d32cd4db44b322994bbc16f284197f212836c124c3693aadd3'


def payload():
    original = ORIGINAL.read_bytes()
    if digest(original) != SOURCE_SHA:
        raise ValueError('Original executable digest differs')
    elf = Elf(original)
    pool = original[elf.file_offset(START, SIZE):elf.file_offset(START, SIZE) + SIZE]
    if digest(pool) != POOL_SHA:
        raise ValueError('Original notification pool differs')
    approved = json.loads(Path('work/source/executable_notification_pool_gold_dry.en.json').read_text(encoding='utf8'))
    slots = {row['pool_offset']: row for row in approved['translated_slots']}
    slots[1216] = {'id': 'exe_00306348_cp932', 'target': 'GOLD', 'pool_offset': 1216,
                   'slot_bytes': 32, 'original_slot_sha256': digest(pool[1216:1248])}
    if len(slots) != 16:
        raise ValueError('Expected complete 16-slot bank')
    ids = {row['id'] for row in slots.values()}
    queue = {}
    for path in Path('work/translation/en').glob('executable*.json'):
        if path.name.endswith('.en.json'):
            continue
        for row in json.loads(path.read_text(encoding='utf8')).get('rows', []):
            if row['id'] in ids:
                if row['id'] in queue:
                    raise ValueError('Duplicate notification queue ID')
                queue[row['id']] = row
    result = bytearray(pool)
    guards = []
    for offset, proposal in sorted(slots.items()):
        row = queue[proposal['id']]
        if row['status'] != 'draft' or row['target'] != proposal['target']:
            raise ValueError('Reviewed notification meaning changed')
        length = proposal['slot_bytes']
        old = pool[offset:offset + length]
        if digest(old) != proposal['original_slot_sha256']:
            raise ValueError('Original notification slot digest differs')
        encoded = row['target'].encode('ascii') + b'\0'
        if len(encoded) > length:
            raise ValueError('Fixed notification slot overflow')
        # Preserve every byte after the new terminator, including original padding.
        result[offset:offset + len(encoded)] = encoded
        guards.append({'id': row['id'], 'target': row['target'], 'pool_offset': offset,
                       'slot_bytes': length, 'bytes_including_nul': len(encoded),
                       'source_slot_sha256': digest(old), 'target_utf8_sha256': digest(row['target'].encode())})
    return bytes(result), guards


def plan(incoming_bytes, inherited_report, pool_rva, gold_rva):
    """Return guarded native writes and relocation requirements for a composer."""
    if digest(incoming_bytes) != inherited_report.get('output_elf_sha256'):
        raise ValueError('Incoming executable/report digest differs')
    original = Elf(ORIGINAL.read_bytes())
    incoming = Elf(incoming_bytes)
    bank, slots = payload()
    fresh_banks = []
    for family in ('title', 'item', 'amulet', 'knowledge', 'entity'):
        evidence = json.loads(Path('work/source/media_audit/notification_' + family + '_name_bounds.json').read_text(encoding='utf8'))
        maximum = 0
        longest = None
        for record in evidence['records']:
            slot = int(record['slot'], 16)
            pointer = incoming.word(slot)
            offset = incoming.file_offset(pointer)
            end = incoming_bytes.index(0, offset, offset + 256)
            raw = incoming_bytes[offset:end]
            if raw != bytes.fromhex(record['hex']):
                raise ValueError('Active notification name bank differs: ' + family)
            if len(raw) > maximum:
                maximum, longest = len(raw), record['index']
        fresh_banks.append({'family': family, 'physical_slots_previously_inventoried': evidence['slots'],
                            'current_records_verified': len(evidence['records']),
                            'max_bytes': maximum, 'longest_index': longest})
    from notification_auxiliary_scope import payload as auxiliary_payload
    _, _, approved_voice_entries = auxiliary_payload()
    voice_max = 0
    for index in range(34):
        pointer = incoming.word(0x96130 + index * 4)
        offset = incoming.file_offset(pointer)
        end = incoming_bytes.index(0, offset, offset + 128)
        raw = incoming_bytes[offset:end]
        if raw != approved_voice_entries[index]['target'].encode('ascii'):
            raise ValueError('Approved English voice-name bank not installed exactly')
        voice_max = max(voice_max, len(raw))
    if voice_max != max(e['bytes_including_nul'] - 1 for e in approved_voice_entries):
        raise ValueError('Reviewed 34-entry voice-name bank bound changed')
    format_hi, format_lo = incoming.word(0x81244), incoming.word(0x81254)
    if ((format_hi & 0xffff0000) != (original.word(0x81244) & 0xffff0000)
            or (format_lo & 0xffff0000) != (original.word(0x81254) & 0xffff0000)):
        raise ValueError('Notification format pointer register/opcode differs')
    signed_low = (format_lo & 65535) - (65536 if format_lo & 32768 else 0)
    format_pointer = ((format_hi & 65535) << 16) + signed_low
    format_offset = incoming.file_offset(format_pointer, 10)
    if incoming_bytes[format_offset:format_offset + 10] != b'%s No. %s\0':
        raise ValueError('Approved English notification format not installed exactly')
    references, _ = reference_index(original)
    selected = [ref for ref in references if START <= ref['address'] < START + SIZE]
    if len(selected) != 14:
        raise ValueError('Notification typed-reference scope differs')
    writes, proofs = [], []
    for ref in selected:
        if ref['kind'] != 'R_MIPS_HI16_LO16' or not ref['loader_mate_is_semantic_low'] or ref['shared_high_site']:
            raise ValueError('Unsafe notification reference')
        hi, lo = ref['sites']
        if not all(0x80a74 <= site < 0x812a0 for site in (hi, lo)):
            raise ValueError('Unexpected notification consumer')
        target = pool_rva + ref['address'] - START
        for site, kind in ((hi, 5), (lo, 6)):
            expected = original.word(site)
            if incoming.word(site) != expected or incoming.relocs.count((site, kind)) != 1:
                raise ValueError('Notification native word/relocation changed')
            value = (target + 0x8000) >> 16 if kind == 5 else target
            replacement = (expected & 0xffff0000) | (value & 65535)
            writes.append({'rva': site, 'expected_word': expected, 'replacement_word': replacement})
        proofs.append({'source_rva': ref['address'], 'pool_offset': ref['address'] - START,
                       'target_rva': target, 'sites': [hi, lo], 'existing_target0_HI_LO_preserved': True})
    if incoming.word(0x81074) != 0x27c50100:
        raise ValueError('Native Gold completion instruction differs')
    writes.append({'rva': 0x81074, 'expected_word': 0x27c50100, 'replacement_word': j(gold_rva)})
    writes.append({'rva': 0x81078, 'expected_word': original.word(0x81078), 'replacement_word': 0})
    if incoming.word(0x81078) != original.word(0x81078):
        raise ValueError('Native Gold jump delay instruction differs')
    return bank, gold_terminate(), {
        'status': 'pure_guarded_notification_proposal', 'input_elf_sha256': digest(incoming_bytes),
        'pool_bytes': len(bank), 'pool_sha256': digest(bank), 'pool_rva': pool_rva,
        'gold_helper_bytes': 16, 'gold_helper_rva': gold_rva, 'slots': slots,
        'active_incoming_name_bank_checks': fresh_banks,
        'voice_name_bank_positions_verified': 34, 'voice_name_max_bytes': voice_max,
        'voice_protagonist_names': 'Literal Hero/Heroine; custom setup names do not expand here.',
        'nine_case_bounds_including_nul': [55,51,45,70,68,71,32,31,38],
        'native_capacity_bytes': 72,
        'context_accounting': {'fresh_human_meaning_rows': 0, 'reused_approved_slot_meanings': 16,
                               'automated_name_bank_position_reads': 1314,
                               'complete_native_switch_reused': '80C4C..8129C, all9 cases'},
        'native_writes': writes, 'typed_pointer_proofs': proofs,
        'new_native_R26_required': [0x81074], 'gold_helper_tail_R26_required': True,
        'format8_relocated_by_auxiliary_scope': True, 'Mao_unfilled_and_uninstalled': True,
        'format8_active_rva_verified': format_pointer,
        'Crack_Burst_measurement_uninstalled': True, 'runtime_verified': False,
        'limitations': ['Nine-case byte bounds cover valid source IDs; malformed IDs/NULL expansions remain unproved.',
                        'Existing notification draw encoding and centering require native runtime QA.',
                        'Composer must preserve incoming font storage, trailer, loaded spans, and relocation conventions.']}
