"""Observe original mode-4 gallery glyphs after English gallery use.

Only temporary breakpoints are used; no font, text, executable or registers are
patched. Preview first, then --write saves a source-free bounded draw report.
"""
import argparse
import hashlib
import json
import pathlib
import struct

from ppsspp_debug import Debugger
from rebuild_gallery import parse
from trace_vwf_4x import regs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resource', default='menu/Gallery/dic/GgHelp001.bin')
    parser.add_argument('--build-manifest', type=pathlib.Path, required=True)
    parser.add_argument('--draws', type=int, default=32)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if not 2 <= args.draws <= 128:
        raise ValueError('Native trace must be bounded to 2 through 128 draws')
    root = pathlib.Path('work/source/cpk').resolve()
    source = (root / args.resource).resolve()
    if not source.is_relative_to(root):
        raise ValueError('Native resource escapes source root')
    original = source.read_bytes()
    old = parse(args.resource, original)
    native_font = original[32:old['head'][1]]
    codes = [int.from_bytes(c.encode('cp932'), 'big') for c in old['charset']]
    slots = dict(zip(codes, range(len(codes))))
    manifest = json.loads(args.build_manifest.read_text(encoding='utf8'))
    executable = (args.build_manifest.parent / 'EBOOT.BIN').read_bytes()
    if hashlib.sha256(executable).hexdigest() != manifest['output_elf_sha256']:
        raise ValueError('Candidate executable differs')
    d = Debugger()
    base = None
    owned = set()
    rows = []
    try:
        base = next(m['address'] for m in d.call('hle.module.list')['modules'] if m['name'] == 'hp_proj')
        for offset in (0xeab10, 0x1b7e1c, 0xd7fc):
            if any(b['address'] == base + offset for b in d.call('cpu.breakpoint.list')['breakpoints']):
                raise ValueError('An existing breakpoint conflicts with this trace')
        if d.read(base + 0xeab10, 8) != executable[0xeab10 + 0xc0:0xeab18 + 0xc0]:
            raise ValueError('Native renderer entry differs')
        if d.read(base + 0xd7fc, 8) != executable[0xd7fc + 0xc0:0xd804 + 0xc0]:
            raise ValueError('Native sprite routine entry differs')
        bank = None
        for _ in range(args.draws * 4):
            owned.add(base + 0xeab10)
            d.call('cpu.runUntil', address=base + 0xeab10, expect='cpu.stepping')
            r = regs(d)
            if r['ra'] != base + 0xee364:
                continue
            if r['t1'] not in slots or r['a3'] != 16 or r['t0'] != 16:
                raise ValueError('Draw does not match the selected native gallery font')
            descriptor = struct.unpack('<I', d.read(r['a0'] + 0x18, 4))[0]
            count, table, pixels = struct.unpack('<3I', d.read(descriptor, 12))
            if bank is None:
                if count not in (len(codes), len(codes) - 1):
                    raise ValueError('Native gallery descriptor count differs')
                records = d.read(table, len(codes) * 12)
                for slot, code in enumerate(codes):
                    if (struct.unpack_from('<H', records, slot * 12)[0] != code or
                            struct.unpack_from('<f', records, slot * 12 + 4)[0] != slot):
                        raise ValueError('Loaded native glyph map differs')
                if d.read(pixels, len(native_font)) != native_font:
                    raise ValueError('Loaded native font bytes differ')
                bank = dict(descriptor=descriptor, descriptor_field=count,
                            mapped_characters=len(codes), table=table, pixels=pixels,
                            all_original_font_bytes_verified=True,
                            packed_font_sha256=hashlib.sha256(native_font).hexdigest())
            elif bank['pixels'] != pixels or bank['table'] != table:
                raise ValueError('Native font changed during the trace')
            slot = slots[r['t1']]
            owned.add(base + 0x1b7e1c)
            d.call('cpu.runUntil', address=base + 0x1b7e1c, expect='cpu.stepping')
            upload = regs(d)
            if [upload['a1'], upload['a2'], upload['a3']] != [32, 24, 32] or upload['t0'] != pixels + slot * 384:
                raise ValueError('Native texture upload differs')
            glyph = original[32 + slot * 384:32 + (slot + 1) * 384]
            if d.read(upload['t0'], 384) != glyph:
                raise ValueError('Native uploaded glyph bytes differ')
            owned.add(base + 0xd7fc)
            d.call('cpu.runUntil', address=base + 0xd7fc, expect='cpu.stepping')
            sprite = regs(d)
            if (sprite['ra'] != base + 0xeacf4 or
                    [sprite['a1'], sprite['a2'], sprite['a3'], sprite['t0'], sprite['t1'], sprite['t2']] !=
                    [r['a1'], r['a2'], 0, 0, 16, 16]):
                raise ValueError('Native sprite dimensions differ')
            rows.append(dict(code=r['t1'], x=r['a1'], y=r['a2'], bank_slot=slot,
                             renderer_return='0xee364',
                             glyph_sha256=hashlib.sha256(glyph).hexdigest(),
                             texture_pointer=upload['t0'], upload=[32, 24, 32],
                             native_sprite_routine='0xd7fc', source_origin=[0, 0],
                             nominal_rectangle=[16, 16]))
            if len(rows) == args.draws:
                break
        if len(rows) != args.draws:
            raise ValueError('Required native gallery draws were not observed')
        deltas = [b['x'] - a['x'] for a, b in zip(rows, rows[1:]) if b['y'] == a['y'] and b['x'] > a['x']]
        if not deltas or any(delta != 13 for delta in deltas):
            raise ValueError('Native gallery advance differs')
        report = dict(version=manifest['version'], status='selected_native_gallery_font_and_advances_verified',
                      resource=args.resource, source_sha256=hashlib.sha256(original).hexdigest(),
                      executable_sha256=manifest['output_elf_sha256'], module_base=hex(base),
                      glyph_draws_observed=len(rows), observed_advance_px=13,
                      native_sprite_routine='0xd7fc', nominal_rectangle=[16, 16], bank=bank,
                      sprite_scope='Original D7FC call arguments, paired with each EAB10 glyph/upload; no D8E4 or GU-vertex claim',
                      original_resource_unchanged=True, full_game_verified=False, draws=rows)
        print(json.dumps({k: v for k, v in report.items() if k != 'draws'}, indent=2))
        if not args.write:
            print('DRY RUN: no native trace written.')
            return
        destination = args.output.resolve()
        if (destination.exists() or not destination.name.endswith('.en.json') or
                destination.is_relative_to(pathlib.Path('work/source').resolve())):
            raise ValueError('Native trace output must be fresh, English-only and outside sources')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    finally:
        for address in owned:
            d.call('cpu.breakpoint.remove', address=address)
        if d.call('cpu.status')['stepping']:
            d.call('cpu.resume', expect='cpu.resume')
        d.close()


if __name__ == '__main__':
    main()
