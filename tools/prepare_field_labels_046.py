"""Install missing quest/Camp/map labels and headquarters notices; dry by default.

Native menu pointers retain their typed R32 owners. Exact complete event strings
are remapped before the existing Episode 1 parser hook; event bytes never change.
"""
import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path

from executable_text_patch import Elf, ORIGINAL, ORIGINAL_SHA, reference_index, encoded_text
from native_menu_install_plan import cstring
from field_ui_patch import notation
from dialogue_tokens import validate_controls
from dialogue_vwf_hooks import Block, address, r
from live_vwf import i, j
from font_vram_hooks import instruction_model
from build_menu_patch import align, relocate_code
from prepare_relocation_019 import sections, section_load, coverage, pair_shapes
from compact_vwf_patch import loaded
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from prepare_bubble_scenes_036 import read

BASE = Path('work/output/0.1.45-title-credit-vwf-4x-candidate')
SOURCE_SHA = 'aca51ffd5358cdb594d70c25bc2e1ce34a25094616a06a826c32ea7ad2a6a621'
CPK_SHA = '307f25d307c8ec78d45b1e20b8e04e1b8b16e4079e002b933a66c16bddd93c81'
EVENT = 'fld/event/d01.evt'
EVENT_SHA = 'a10243f0d63320512937c4902b3b1002e989f9dbf2d573708fe2a13a3613db41'
OUT = Path('work/output/0.1.46-field-label-assets')
QUEUE = Path('work/translation/en/field_labels_046.json')
SITE = 0xecf48
# Shared table0 entries also cover matching labels on other screens. Names and
# complete menu drafts were reviewed against the existing English glossary.
LABELS = {
    106: 'Switch View', 107: 'Main Quests', 108: 'Subquests',
    131: 'Buy', 132: 'Sell', 134: 'Sold Out', 135: 'Shop',
    136: 'Buy Spirit', 137: 'Buy Amulets', 138: 'Buy Accessories',
    139: 'Sell Accessories', 140: 'Buy Voice Data',
    164: 'Scroll', 190: 'Switch Category', 191: 'Switch Character',
    196: 'Switch Page', 197: 'Save Point', 198: 'Heal Point',
    199: 'Generator', 200: 'Main Event', 201: 'Side Event',
    202: 'Jump', 203: 'Elevator', 204: 'World', 206: 'Switch Map',
    207: 'Return to Title', 230: 'Reset', 231: 'Help',
}
# Each tuple starts at the complete styled payload, immediately after opcode
# 07 00. Duplicate offsets are the source-authored protagonist/event branches.
NOTICES = (
    ((0xf4f3, 0xf722), 'The elevator seems to be out of service...'),
    ((0x11ada,), 'Lina and Gourry have joined the party!'),
    ((0x11be4,), '{01}1 checked the database.'),
    ((0x12dfd,), 'Destination "Mining Site" has been unlocked.'),
    ((0x132c7,), 'Destination "HOLD Headquarters" has been unlocked.'),
    ((0x13929,), 'Saya, Yomiko, Mai and the others have joined the party!'),
    ((0x13c0e,), 'Suou has joined the party!'),
    ((0x13fc8,), 'Corporal Giroro, Private Second Class Tamama{11}and Hei have joined the party!'),
    ((0x142ef,), 'Cougar has joined the party!'),
    ((0x14431, 0x144fd), 'I need to head to the Data Room to get more information!'),
    ((0x1447b, 0x14547), 'I need to escape as quickly as possible!'),
    ((0x145b8,), 'I need to head to the Data Room before escaping!'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def hook(entries, continuation):
    """Replay the native entry, preserve scratch registers, then chain old hook."""
    h = Block()
    h.emit(i(35, 20, 4, 0x14), i(9, 29, 29, -32))
    regs = (8, 9, 10, 11, 24)
    for n, reg in enumerate(regs):
        h.emit(i(43, 29, reg, n*4))
    h.branch(4, 4, 0, 'restore')
    for n, entry in enumerate(entries):
        h.emit(r(4, 0, 8))
        address(h, 9, entry['source_payload_rva'])
        h.emit(i(13, 0, 10, entry['source_payload_bytes']))
        h.label(f'compare{n}')
        h.emit(i(36, 8, 11, 0), i(36, 9, 24, 0))
        h.branch(5, 11, 24, f'next{n}')
        h.emit(i(9, 8, 8, 1), i(9, 9, 9, 1), i(9, 10, 10, -1))
        h.branch(5, 10, 0, f'compare{n}')
        address(h, 4, entry['target_payload_rva'])
        h.emit(i(43, 20, 4, 0x14))
        h.branch(4, 0, 0, 'restore')
        h.label(f'next{n}')
    h.label('restore')
    for n, reg in enumerate(regs):
        h.emit(i(35, 29, reg, n*4))
    h.emit(i(9, 29, 29, 32), i(43, 29, 21, 0x24), j(continuation), 0)
    return h.finish()


def instruction_cases(code, base, entries, sources, continuation, episode):
    model = instruction_model()
    model['execute'].__globals__['B'] = base
    exact = {raw: entry['target_payload_rva'] for raw, entry in zip(sources, entries)}
    samples = [('null', None), ('empty', b'\0'), ('episode_passthrough', episode),
               ('unrelated_styled', b'\x1a5Unrelated notice\x12\x0e\0')]
    for n, raw in enumerate(sources):
        samples.append((f'exact{n}', raw))
        for pos in range(len(raw)):
            altered = bytearray(raw); altered[pos] ^= 1
            samples.append((f'mismatch{n}_{pos}', bytes(altered)))
        for pos in range(1, len(raw)-1):
            samples.append((f'truncated{n}_{pos}', raw[:pos]+b'\0'))
    for name, raw in samples:
        regs = [0]+[0x12340000+n for n in range(1, 32)]
        regs[20] = 0x220000; regs[29] = 0x250000
        original = regs[:]; memory = {}; pointer = 0x230000 if raw is not None else 0
        def put(addr, data):
            memory.update({addr+n: value for n, value in enumerate(data)})
        put(0x220014, struct.pack('<I', pointer))
        if raw is not None: put(pointer, raw)
        for entry, source in zip(entries, sources): put(entry['source_payload_rva'], source)
        pc, out, reads = model['execute'](code, regs, memory)
        expected = original[:]; expected[4] = exact.get(raw, pointer)
        if pc != continuation or out != expected:
            raise ValueError('Remap ABI/continuation differs: '+name)
        if bytes(memory[0x220014+n] for n in range(4)) != struct.pack('<I', expected[4]):
            raise ValueError('Native cursor differs: '+name)
        if raw is not None and any(pointer+len(raw) <= a < pointer+0x1000 for a in reads):
            raise ValueError('Read past complete input: '+name)
    return dict(cases=len(samples), matches=len(exact), all_passed=True,
                null_empty_prefix_mutation_and_episode_passthrough_checked=True)


def build():
    incoming = (BASE/'EBOOT.BIN').read_bytes()
    manifest = json.loads((BASE/'manifest.en.json').read_text(encoding='utf8'))
    before = manifest['setup_patch']
    original = ORIGINAL.read_bytes()
    if sha(incoming) != SOURCE_SHA or before['output_elf_sha256'] != SOURCE_SHA or sha(original) != ORIGINAL_SHA:
        raise ValueError('Frozen executable differs')
    if next(x['sha256'] for x in manifest['iso_replacements'] if x['path'].endswith('HP.CPK')) != CPK_SHA:
        raise ValueError('Frozen archive manifest differs')
    event = Path('work/source/cpk')/EVENT
    raw_event = event.read_bytes()
    if sha(raw_event) != EVENT_SHA or read(BASE/'HP.CPK', [EVENT])[EVENT] != raw_event:
        raise ValueError('Event differs between original and current archive')
    e, o = Elf(incoming), Elf(original)
    refs, _ = reference_index(o)
    ph = [list(p) for p in e.ph]; ss = sections(incoming)
    old_payload = incoming[ph[2][1]:ph[2][1]+ph[2][4]]
    payload = bytearray(old_payload); result = bytearray(incoming)
    floats = struct.unpack('<131f', incoming[e.file_offset(before['float_width_lut_rva'], 524):][:524])
    allowed = set(); mask = set(); labels = []; rows = []
    for index, target in LABELS.items():
        slot = 0x94760+index*4; source = o.word(slot); raw = cstring(o, source)
        owners = [ref for ref in refs if ref['address'] == source]
        if len(owners) != 1 or owners[0]['kind'] != 'R_MIPS_32' or owners[0]['sites'] != [slot]:
            raise ValueError('Label owner scope differs')
        ordinal, = owners[0]['relocation_ordinals']
        if e.word(slot) != source or e.relocs[ordinal] != (slot, 2) or cstring(e, source) != raw:
            raise ValueError('Selected label already changed')
        validate_controls(notation(raw[:-1]), target)
        target_rva = ph[2][2]+len(payload); encoded = encoded_text(target, 'ascii')+b'\0'
        payload.extend(encoded); offset = e.file_offset(slot, 4)
        struct.pack_into('<I', result, offset, target_rva)
        allowed.update(range(offset, offset+4)); mask.update(range(slot, slot+4))
        width = sum(floats[c] for c in encoded if 32 <= c <= 126)
        limit = 84 if index in (164, 196, 206, 230, 231) else 200
        if width > limit: raise ValueError('Label exceeds reviewed region: '+target)
        labels.append(dict(native_index=index, pointer_slot=slot, source_rva=source,
            relocation_ordinal=ordinal, source_sha256=sha(raw), target=target,
            target_rva=target_rva, native_advance_px=width, available_width_px=limit))
        rows.append(dict(id=f'field_label_046_{index:03}', file='PSP_GAME/SYSDIR/EBOOT.decrypted.elf',
            offset=o.file_offset(source), byte_length=len(raw)-1, encoding='cp932', category='ui',
            source=notation(raw[:-1]), target=target, status='translated',
            context='Shared quest, Camp/Shop, map footer and map legend labels reported by the player.',
            decisions='Preserve typed table0/index identity; full target relocated without a source byte budget.'))
    notices = []; sources = []
    for n, (offsets, target_body) in enumerate(NOTICES):
        raw = raw_event[offsets[0]:raw_event.index(0, offsets[0])+1]
        for offset in offsets:
            if raw_event[offset-2:offset] != b'\x07\0' or raw_event[offset:offset+len(raw)] != raw:
                raise ValueError('Complete event/opcode boundaries differ')
        target = '{1A}5'+target_body+'{12}{0E}'
        source_text = notation(raw[:-1])
        # A single reviewed line break fits the complete rank-bearing announcement;
        # every semantic control and argument otherwise remains byte-for-byte.
        validate_controls(source_text, target.replace('{11}', ''))
        encoded = encoded_text(target, 'ascii')+b'\0'
        # Dynamic protagonist names retain their original selector. Charge the
        # reviewed seventeen-character given-name bound at 13px per native glyph.
        name_bound = before['default_name_storage']['osk_character_limits']['male_given_name']*13
        visible = encoded[2:-3].replace(b'\x011', b'')
        line_widths = [sum(floats[c] for c in line if 32 <= c <= 126)+(name_bound if b'\x011' in encoded else 0)
                       for line in visible.split(b'\x11')]
        width = max(line_widths)
        if width > 440: raise ValueError('Complete notice needs reviewed reflow: '+target_body)
        key_rva = ph[2][2]+len(payload); payload.extend(raw)
        target_rva = ph[2][2]+len(payload); payload.extend(encoded)
        notices.append(dict(id=f'field_notice_046_{n:02}', offsets=list(offsets),
            source_payload_rva=key_rva, source_payload_bytes=len(raw), source_payload_sha256=sha(raw),
            target_payload_rva=target_rva, target_payload_bytes=len(encoded), target=target,
            native_advance_px_with_dynamic_bound=width, line_widths_px=line_widths,
            added_layout_line_breaks=target.count('{11}'), available_width_px=440))
        sources.append(raw)
        rows.append(dict(id=f'field_notice_046_{n:02}', file=EVENT, offset=offsets[0],
            byte_length=len(raw)-1, encoding='cp932', category='field_notices',
            source=source_text, target=target, status='translated', occurrences=[f'{EVENT}:{x:x}' for x in offsets],
            context='Headquarters centered system notices and protagonist movement restrictions in source-authored event branches.',
            decisions='First-person movement prompts address the controlled protagonist; party and destination messages are system narration. Glossary names retained. Complete exact payload remap preserves semantic controls, selectors and event commands. Only the rank-bearing party announcement adds one layout line break.'))
    old_hook = before['field_ui_patch']['episode_inline_banner']
    old_helper = old_hook['helper_rva']
    if incoming[e.file_offset(SITE, 8):][:8] != struct.pack('<II', j(old_helper), 0) or e.relocs.count((SITE, 4)) != 1:
        raise ValueError('Existing parser hook and typed jump differ')
    payload.extend(bytes(align(len(payload), 16)-len(payload)))
    hoff = len(payload); helper = ph[2][2]+hoff
    code = hook(notices, old_helper); payload.extend(code)
    additions = relocate_code(payload, hoff, len(code))
    sitefile = e.file_offset(SITE, 8); struct.pack_into('<II', result, sitefile, j(helper), 0)
    allowed.update(range(sitefile, sitefile+8)); mask.update(range(SITE, SITE+8))
    pf = len(result)+((ph[2][2]-len(result)) % ph[2][7])
    result.extend(bytes(pf-len(result))); result.extend(payload)
    ph[2][1] = pf; ph[2][4] = ph[2][5] = len(payload)
    if ss[55][3] != ph[2][2]: raise ValueError('Inherited payload section differs')
    ss[55][4] = pf; ss[55][5] = len(payload)
    rp = e.ph[3]; relfile = align(len(result), 16); result.extend(bytes(relfile-len(result)))
    oldrel = incoming[rp[1]:rp[1]+rp[4]]; result.extend(oldrel+b''.join(additions))
    for section in ss:
        if section[1] == 0x700000a0: section[4] = relfile+section[4]-rp[1]
    ss.append([0, 0x700000a0, 0, 0, relfile+len(oldrel), len(additions)*8, 0, 55, 4, 8])
    ph[3][1] = relfile; ph[3][4] = len(oldrel)+len(additions)*8
    shoff = align(len(result), 4); result.extend(bytes(shoff-len(result)))
    for section in ss: result.extend(struct.pack('<10I', *section))
    phoff = struct.unpack_from('<I', incoming, 28)[0]
    for n in (2, 3):
        struct.pack_into('<8I', result, phoff+n*32, *ph[n]); allowed.update(range(phoff+n*32, phoff+(n+1)*32))
    struct.pack_into('<I', result, 32, shoff); allowed.update(range(32, 36))
    struct.pack_into('<H', result, 48, len(ss)); allowed.update(range(48, 50))
    result = bytes(result); out = Elf(result)
    if any(a != b and n not in allowed for n, (a,b) in enumerate(zip(incoming, result))):
        raise ValueError('Unselected inherited file bytes changed')
    if out.relocs[:len(e.relocs)] != e.relocs or pair_shapes(result)[:len(pair_shapes(incoming))] != pair_shapes(incoming):
        raise ValueError('Inherited relocation semantics differ')
    coverage(result); models = []
    episode = cstring(e, old_hook['source_payload_rva'])
    for base in (0x08804000, 0x08900000, 0x08fff000):
        a, _, _, _ = section_load(incoming, base); b, visited, skipped, _ = section_load(result, base)
        independent, _, _ = loaded(result, base)
        if skipped or visited != out.relocs or independent != [b[n][:out.ph[n][4]] for n in range(3)]:
            raise ValueError('Independent loader models differ')
        if a[1] != b[1] or a[2] != b[2][:len(a[2])] or any(x != y and n not in mask for n,(x,y) in enumerate(zip(a[0],b[0]))):
            raise ValueError('Unselected loaded memory changed')
        for entry in labels:
            if struct.unpack_from('<I', b[0], entry['pointer_slot'])[0] != base+entry['target_rva'] or cstring(out, entry['target_rva']) != encoded_text(entry['target'], 'ascii')+b'\0':
                raise ValueError('Complete loaded label differs')
        mapped = [dict(entry, source_payload_rva=base+entry['source_payload_rva'], target_payload_rva=base+entry['target_payload_rva']) for entry in notices]
        checks = instruction_cases(bytes(b[2][hoff:hoff+len(code)]), base+helper, mapped, sources, base+old_helper, episode)
        if struct.unpack_from('<II', b[0], SITE) != (j(base+helper), 0): raise ValueError('Loaded new parser jump differs')
        models.append(dict(base=base, relocations=len(visited), labels=len(labels), unselected_memory_exact=True, instruction_checks=checks))
    report = copy.deepcopy(before)
    for key in ('output', 'approved_dry_plan_sha256', 'written_readback_verified'): report.pop(key, None)
    report.update(version='0.1.46', input_version='0.1.45', input_sha256=SOURCE_SHA,
        output_elf_sha256=sha(result), output_sha256=sha(result), elf_bytes=len(result),
        payload_bytes=len(payload), module_growth_bytes=len(payload),
        font_native_tail_loaded_extension_bytes=len(payload), font_native_tail_loaded_extension_sha256=sha(payload),
        total_relocations=len(out.relocs), added_relocations=len(out.relocs)-before['original_relocations'],
        relocation_table_sha256=sha(oldrel+b''.join(additions)), runtime_verified=False,
        status='field_labels_and_headquarters_notices_candidate')
    forecast = report['memory_forecast']; old_size = forecast['proposed_module_bytes']
    forecast['proposed_module_bytes'] = ph[2][2]+align(len(payload), 64)
    forecast['forecast_after_both_requests'] -= forecast['proposed_module_bytes']-old_size
    report['field_labels_046'] = dict(labels=labels, notices=notices, event=EVENT, event_sha256=EVENT_SHA,
        event_occurrences=sum(len(row['offsets']) for row in notices), event_bytecode_exact=True,
        hook_site=SITE, helper_rva=helper, helper_bytes=len(code), helper_sha256=sha(payload[hoff:hoff+len(code)]),
        episode_hook_continuation_rva=old_helper, loaded_growth_bytes=len(payload)-len(old_payload),
        new_relocations=len(additions), loader_models=models, natural_gameplay_verified=False,
        inherited_bubble_and_font_code_exact=True, archive_resources_unchanged=True)
    authoritative_font_metadata(result, report); validate_native_png_metadata(result, report)
    return result, report, dict(schema_version=1, language='en', rows=rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true'); ap.add_argument('--expected-sha256')
    args = ap.parse_args(); data, report, queue = build(); scope = report['field_labels_046']
    print(json.dumps(dict(version=report['version'], sha256=sha(data),
        label_count=len(scope['labels']), notices=len(scope['notices']), occurrences=scope['event_occurrences'],
        growth=scope['loaded_growth_bytes'], loader_models=scope['loader_models'],
        sample_labels=scope['labels'][:3], sample_notices=[scope['notices'][n] for n in (0,9)],
        memory_forecast=report['memory_forecast']['forecast_after_both_requests']), indent=2))
    if not args.write: print('DRY RUN: no executable or translations written.'); return
    if args.expected_sha256 != sha(data) or OUT.exists() or QUEUE.exists():
        raise ValueError('Reviewed hash and fresh destinations required')
    OUT.mkdir(parents=True); (OUT/'EBOOT.BIN').write_bytes(data)
    if (OUT/'EBOOT.BIN').read_bytes() != data: raise ValueError('Executable readback differs')
    report['written_readback_verified'] = True
    (OUT/'executable.en.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


if __name__ == '__main__': main()
