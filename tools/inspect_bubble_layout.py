"""Read-only bounded runtime bubble probe. Default prints JSON; --write saves fresh evidence.

Requires exclusive ownership of the isolated PPSSPP debugger. Does not modify
RAM, registers, settings, saves, or loaded assets. English validation targets
the control-light opening record, not arbitrary dialogue or animated geometry.
"""
import argparse
import hashlib
import json
import math
import pathlib
import struct

from bubble_metrics import load_templates, model, TEMPLATE_BASE, TEMPLATE_STRIDE
from ppsspp_debug import Debugger

TOLERANCE = 0.0001
STOP = 0xE4E14
# F1058/F105C and F1064/F1070 target original LOAD1 (PSPREL1
# flags 0x10005/0x10006), whose vaddr 0x47AF58 must be added.
MANAGER_FLAG = 0x166F2C4
MANAGER = 0x166F2C8


def japanese_center_baseline():
    path = pathlib.Path(__file__).resolve().parents[1] / 'work/ui/runtime/speaker_candidate_japanese_fallback_trace.en.json'
    raw = path.read_bytes()
    evidence = json.loads(raw)
    expected_sha = '2ac481e5f51f7f5a48a369079738c090ee5ce11ecc9f2eb473f16235528c25dc'
    if evidence['version'] != '0.1.3' or evidence['loaded_executable_sha256'] != expected_sha:
        raise ValueError('Native Japanese baseline executable identity changed')
    first = evidence['draws'][0]
    if (first['x'] != 323 or first['object_layout_float20'] != 52.0 or
            first['font_mode'] != 1 or first['renderer_module_offset'] != '0xe9ff4' or
            first['object_alignment_mode'] != 0xFFFFFFFF):
        raise ValueError('Native Japanese baseline centering evidence changed')
    center = first['x'] + first['object_layout_float20']
    return center, dict(kind='native Japanese fallback draw baseline', path=str(path),
                        evidence_sha256=hashlib.sha256(raw).hexdigest(),
                        baseline_executable_sha256=expected_sha, baseline_version='0.1.3',
                        baseline_first_glyph_x=first['x'], baseline_half_width=first['object_layout_float20'],
                        derivation='Centered renderer origin X plus measured native half-width',
                        derived_window_center_x=center)


def pointer(value, size=4, aligned=True):
    return (0x08800000 <= value < 0x0A000000 and
            value + size <= 0x0A000000 and (not aligned or value % 4 == 0))


def uints(d, address, count):
    if not pointer(address, count * 4):
        raise ValueError('RAM pointer outside guarded user memory')
    return struct.unpack('<' + 'I' * count, d.read(address, count * 4))


def floats(d, address, count):
    values = struct.unpack('<' + 'f' * count, d.read(address, count * 4))
    if not all(math.isfinite(v) and abs(v) < 100000 for v in values):
        raise ValueError('Unsafe geometry floats')
    return values


def classify_text(d, address):
    if not pointer(address, aligned=False):
        raise ValueError('Text pointer outside user memory')
    raw = bytearray()
    # Stop before dereferencing past RAM, or after the first terminator.
    for pos in range(0, 4096, 128):
        size = min(128, 0x0A000000 - address - pos)
        if size <= 0:
            raise ValueError('Text extends outside user memory')
        for value in d.read(address + pos, size):
            if value in (0, 14):
                rejected = next(((n, c) for n, c in enumerate(raw)
                                 if c not in (16, 17, 18, 128) and not 32 <= c <= 126), None)
                return dict(bytes_before_terminator=len(raw), terminator=value,
                            sha256=hashlib.sha256(raw).hexdigest(),
                            numeric_prefix_bytes=list(raw[:32]),
                            source_line_count=(1 + raw.count(16) + raw.count(17)
                                               if raw and rejected is None else None),
                            ascii_guard_reject=(dict(byte_offset=rejected[0], code=rejected[1],
                                                    reason='Byte outside supported ASCII and controls 10/11/12')
                                                if rejected else None),
                            has_high_bytes=any(c >= 0x80 and c != 128 for c in raw),
                            control_light_ascii=bool(raw) and all(
                                c in (16, 17, 18, 128) or 32 <= c <= 126 for c in raw))
            raw.append(value)
    raise ValueError('Text exceeded the bounded 4096-byte scan')


def association(d, base, window):
    owner = uints(d, window + 0x348, 1)[0]
    if not pointer(owner, 0xF0):
        return None
    context = uints(d, owner + 0x98, 1)[0]
    if not pointer(context, 0x34):
        return None
    context_key = uints(d, context + 0x30, 1)[0]
    record_key = uints(d, owner + 0xEC, 1)[0]
    if not uints(d, base + MANAGER_FLAG, 1)[0]:
        return None
    count = uints(d, base + MANAGER + 0x24, 1)[0]
    # F1640 reads manager+28 directly; F1668 increments the manager
    # cursor by four. This is an embedded pointer array, not indirection.
    array = base + MANAGER + 0x28
    if not 1 <= count <= 1024 or not pointer(array, count * 4):
        return None
    for container in uints(d, array, count):
        if not pointer(container, 0x30):
            continue
        if uints(d, container + 8, 2) == (context_key, record_key):
            return container, owner, context, context_key, record_key
    return None


def compare_geometry(template, banks, ratio):
    expected = [template['outline'], *template['banks']]
    x_error = max(abs(actual[0] - native[0] * ratio)
                  for actual_bank, native_bank in zip(banks, expected)
                  for actual, native in zip(actual_bank, native_bank))
    y_error = max(abs(actual[1] - native[1])
                  for actual_bank, native_bank in zip(banks, expected)
                  for actual, native in zip(actual_bank, native_bank))
    midpoint_error = max(abs(banks[0][n][axis] -
                            (banks[1][n][axis] + banks[2][n][axis]) / 2)
                         for n in range(template['count']) for axis in (0, 1))
    return dict(max_x_error=x_error, max_y_error=y_error,
                max_outline_midpoint_error=midpoint_error)


def probe(d, base, templates, mode):
    q = d.call('cpu.getAllRegs')['categories'][0]
    regs = dict(zip(q['registerNames'], q['uintValues']))
    if regs['pc'] != base + STOP:
        raise ValueError('Stopped outside the post-hook checkpoint')
    window = regs['a0']
    if not pointer(window, 0x350):
        return None
    shape = struct.unpack('<H', d.read(window + 0x318, 2))[0]
    # Scoped opening sequence: translated first record uses template79;
    # the immediately following native Japanese record uses template68.
    expected_shape = 79 if mode == 'english' else 68
    if shape != expected_shape or not uints(d, window + 0x31C, 1)[0]:
        return None
    found = association(d, base, window)
    if found is None:
        return dict(mode=mode, window=hex(window), template_id=shape,
                    status='association_not_found', owner_pointer=hex(uints(d, window + 0x348, 1)[0]),
                    manager_initialized_flag=uints(d, base + MANAGER_FLAG, 1)[0],
                    manager_count=uints(d, base + MANAGER + 0x24, 1)[0],
                    manager_embedded_array_address=hex(base + MANAGER + 0x28),
                    verified_dialogue_records=0, full_game_verified=False)
    container, owner, context, context_key, record_key = found
    text, total, visible, start = uints(d, container + 0x14, 4)
    if not 1 <= total <= 32 or not 1 <= visible <= 4 or start + visible > 32:
        return None
    half = floats(d, container + 0x2C, 1)[0]
    classification = classify_text(d, text)
    template = templates[shape]
    # E4E68 and E5368 load count from immutable template header, never
    # window+31C. E4E3C treats +31C solely as a nonzero activity gate.
    count = struct.unpack('<H', d.read(base + TEMPLATE_BASE + shape * TEMPLATE_STRIDE, 2))[0]
    if count != template['count'] or not 1 <= count <= 30:
        raise ValueError('Loaded template vertex count differs from original template')
    active_state = uints(d, window + 0x31C, 1)[0]
    banks = []
    for offset in (0, 0xF0, 0x1E0):
        xy = floats(d, window + offset, count * 2)
        banks.append(list(zip(xy[::2], xy[1::2])))
    position = floats(d, window + 0x2D0, 3)
    angles = floats(d, window + 0x2E0, 3)
    scales = floats(d, window + 0x2F0, 3)
    prediction = model(template, visible, half * 2, 369.0) if mode == 'english' else None
    if prediction is not None and not prediction['supported']:
        raise ValueError('Opening model does not support observed line count')
    ratio = prediction['ratio'] if prediction else 1.0
    if prediction:
        expected_center = prediction['clamped_center']
        provenance = dict(kind='scoped English opening model', original_center_x=369.0)
    else:
        expected_center, provenance = japanese_center_baseline()
    errors = compare_geometry(template, banks, ratio)
    bounds = [position[0] + min(p[0] for bank in banks for p in bank),
              position[0] + max(p[0] for bank in banks for p in bank)]
    checks = dict(native_zero_angles=all(v == 0 for v in angles),
                  native_unit_scales=all(v == 1 for v in scales),
                  geometry_matches_model=all(v < TOLERANCE for v in errors.values()),
                  center_matches_opening_assumption=abs(position[0] - expected_center) < TOLERANCE,
                  geometry_inside_screen_margins=bounds[0] >= 8 - TOLERANCE and bounds[1] <= 472 + TOLERANCE)
    checks['requested_text_classification'] = (classification['control_light_ascii']
                                               if mode == 'english' else classification['has_high_bytes'])
    if mode == 'english':
        checks['visible_range_inside_source_lines'] = (classification['source_line_count'] is not None and
                                                       start + visible <= classification['source_line_count'])
        # +18 describes the initialized line set at this instant, not the
        # number of all source-record lines across pages. The opening can
        # present two initialized lines per page while keeping global width.
        checks['opening_record_metrics'] = abs(half - 92.5) < TOLERANCE
    return dict(mode=mode, window=hex(window), owner=hex(owner), context=hex(context),
                container=hex(container), text_pointer=hex(text), context_key=context_key,
                record_key=record_key, template_id=shape, vertex_count=count,
                active_state_word=active_state,
                vertex_count_source='immutable template header; E4E68/E5368',
                field18_current_page_line_count=total,
                source_line_count=classification['source_line_count'],
                visible_lines=visible, page_start_line=start,
                maximum_half_width=half, text_classification=classification,
                position=position, angles=angles, native_scales=scales,
                geometry_banks=banks, screen_bounds=bounds, expected_ratio=ratio,
                expected_center=expected_center, errors=errors, checks=checks,
                expected_center_provenance=provenance,
                status='scoped_geometry_probe_passed' if all(checks.values()) else 'scoped_geometry_probe_failed',
                model_original_center_assumption=369.0 if prediction else expected_center,
                tail_exact_shape_preserved=False,
                verified_dialogue_records=0, full_game_verified=False,
                notes=('Probe checks geometry only. English model starts at center X=369; '
                       'the following native Japanese center X=375 derives from the saved unresized 0.1.3 draw trace. '
                       'Y is observed without a fixed expectation. Japanese source line counts are not decoded. '
                       'Selected scope is template79 English then template68 Japanese in the opening sequence. '
                       'Full dialogue, animation, and broader window reuse QA remain pending.'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('english', 'japanese'), required=True)
    p.add_argument('--build-manifest', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path)
    p.add_argument('--write', action='store_true')
    args = p.parse_args()
    if args.write and (args.output is None or args.output.exists()):
        raise ValueError('--write requires a fresh --output path')
    manifest = json.loads(args.build_manifest.read_text(encoding='utf8'))
    executable = (args.build_manifest.parent / 'EBOOT.BIN').read_bytes()
    sha = hashlib.sha256(executable).hexdigest()
    if sha != manifest['output_elf_sha256']:
        raise ValueError('Candidate executable hash differs from manifest')
    hook_bytes = executable[0xE4E0C + 0xC0:0xE4E14 + 0xC0]
    templates = load_templates()
    d = Debugger()
    try:
        module = next(m for m in d.call('hle.module.list')['modules'] if m['name'] == 'hp_proj')
        base = module['address']
        hook_word, delay = struct.unpack('<2I', hook_bytes)
        if hook_word >> 26 != 2 or delay != 0:
            raise ValueError('Candidate lacks the expected geometry entry jump')
        # The installed entry J uses PSPREL1 R_MIPS_26: module base is
        # added to its encoded module-relative target by the PRX loader.
        relocated = (hook_word & 0xFC000000) | ((((hook_word & 0x3FFFFFF) << 2) + base) >> 2 & 0x3FFFFFF)
        expected_hook = struct.pack('<2I', relocated, delay)
        if d.read(base + 0xE4E0C, 8) != expected_hook:
            raise ValueError('Loaded geometry hook differs from local candidate')
        result = None
        for attempt in range(1, 33):
            d.call('cpu.runUntil', address=base + STOP, expect='cpu.stepping')
            result = probe(d, base, templates, args.mode)
            if result is not None:
                break
        if result is None:
            raise RuntimeError('No matching active opening window after 32 checkpoints')
        result.update(version=manifest['version'], executable_sha256=sha,
                      module_base=hex(base), checkpoint_module_offset=hex(STOP),
                      loaded_hook_words=[hex(relocated), hex(delay)],
                      attempts=attempt, validation_kind='live_read_only_geometry_probe',
                      tolerance=TOLERANCE,
                      manager_flag_module_offset=hex(MANAGER_FLAG),
                      manager_module_offset=hex(MANAGER),
                      manager_count_module_offset=hex(MANAGER + 0x24),
                      manager_embedded_array_module_offset=hex(MANAGER + 0x28))
        print(json.dumps(result, indent=2))
        if args.write:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x', encoding='utf8') as f:
                f.write(json.dumps(result, indent=2) + '\n')
        else:
            print('DRY RUN: no evidence file written.')
    finally:
        if d.call('cpu.status')['stepping']:
            d.call('cpu.resume', expect='cpu.resume')
        d.close()


if __name__ == '__main__':
    main()
