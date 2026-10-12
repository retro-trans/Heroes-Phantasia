"""Verify the selected 0.1.7 dictionary prose, scroll captures and glyph traces.

Read-only by default, including live font-bank checks. --write saves a fresh
English-only proof and links it from the candidate manifest after review.
This does not certify other entries, Japanese headings or the whole game.
"""
import argparse
import hashlib
import json
import pathlib
import struct

from append_cpk import sha
from extract_corpus import controls
from gallery_layout import advances, wrap
from ppsspp_debug import Debugger
from rebuild_dialogue import encode_target
from rebuild_gallery import parse, rebuild

BUILD = pathlib.Path('work/output/0.1.7-gallery-vwf-4x-candidate')
ASSET = pathlib.Path('work/output/0.1.7-gallery-candidate')
UI = pathlib.Path('work/ui/runtime')


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reviewed_capture(stem, manifest, review_key):
    path = UI / (stem + '.png')
    info = read(path.with_suffix('.json'))
    require(info['version'] == manifest['version'] and
            info['loaded_executable_sha256'] == manifest['output_elf_sha256'] and
            info[review_key] is True and info['reviewed_capture_sha256'] == sha(path) and
            [info['width'], info['height']] == [480, 272], 'Capture/review mismatch: ' + stem)
    return info, dict(path=str(path), sha256=sha(path), review_scope=info['review_scope'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=pathlib.Path, default=UI / 'gallery_candidate_validation.en.json')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    manifest_path = BUILD / 'manifest.en.json'
    manifest = read(manifest_path)
    require(manifest['version'] == '0.1.7', 'Unexpected candidate version')
    executable = (BUILD / 'EBOOT.BIN').read_bytes()
    require(hashlib.sha256(executable).hexdigest() == manifest['output_elf_sha256'], 'Executable changed')
    resource = manifest['selected_gallery_resources'][0]
    identity = manifest['selected_gallery_ids'][0]
    require(manifest['selected_gallery_resources'] == ['menu/Gallery/dic/GgHelp000.bin'] and
            manifest['selected_gallery_ids'] == ['51ccd5f7a174a1d8e041'], 'Selected scope changed')
    original = (pathlib.Path('work/source/cpk') / resource).read_bytes()
    old = parse(resource, original)
    require(hashlib.sha256(old['text']).hexdigest()[:20] == identity, 'Original identity changed')
    matches = [row for row in read(pathlib.Path('work/translation/en/batch_0008.en.json'))['rows']
               if row['id'] == identity]
    require(len(matches) == 1, 'English export identity differs')
    encoded, _ = encode_target(matches[0]['target'], controls(old['text'].decode('cp932')), True, True, True)
    widths, reference = advances()
    wrapped, layout = wrap(encoded, 330, widths, 45)
    layout['font_reference'] = reference
    require(layout == manifest['gallery_layout'], 'Layout ledger differs from current target')
    require(rebuild(resource, original, wrapped)[0] == (ASSET / 'GgHelp000.bin').read_bytes(), 'Rebuilt prose changed')
    # The final 12/0E controls are delimiters, not extra scroll lines.
    lines = wrapped.split(b'\x12', 1)[0].split(b'\x11')
    require(len(lines) == 15 and sum(bool(line) for line in lines) == 14, 'Physical line count differs')
    expected = []
    for line in lines:
        positions, pen = [], 4
        for code in line:
            positions.append(pen)
            pen += widths[code]
        expected.append(positions)
    covered, captures, traces = set(), [], []
    for stage, scroll in [('top', 0), ('middle', 4), ('bottom', 8)]:
        info, capture = reviewed_capture('gallery_candidate_' + stage, manifest, 'layout_visual_qa_passed')
        require(info['translation_id'] == identity and info['scroll_first_line_index'] == scroll and
                info['text_viewport'] == [4, 72, 330, 154], 'Scroll capture metadata differs')
        capture['scroll_first_line_index'] = scroll
        captures.append(capture)
        path = UI / ('gallery_candidate_' + stage + '_trace.en.json')
        trace = read(path)
        require(trace['version'] == '0.1.7' and trace['loaded_executable_sha256'] == manifest['output_elf_sha256'] and
                trace['gallery_mode4_only'] is True and trace['installation'] == 'cold_boot_executable' and
                trace['source_rect'] == [64, 64] and trace['destination_rect'] == [16, 16] and
                trace['glyph_draws_observed'] == len(trace['draws']) == 512, 'Trace identity/scope differs')
        base = int(trace['module_base'], 16)
        for draw in trace['draws']:
            x, y, code = draw['x'], draw['y'], draw['code']
            require(72 <= y <= 204 and (y - 72) % 22 == 0, 'Draw falls outside the visible rows')
            index = scroll + (y - 72) // 22
            require(index < len(lines) and x in expected[index], 'Draw origin does not match target')
            column = expected[index].index(x)
            require(code == lines[index][column] and draw['glyph'] == chr(code) and
                    4 <= x and x + 16 <= 334 and draw['renderer_return'] == '0xee364', 'Glyph or bounds differ')
            require(draw['texture'] == dict(width=64, height=64, pitch_pixels=64,
                    pointer=base + manifest['high_bank'] + manifest['high_glyph_offsets'][str(code)]) and
                    draw['sprite'] == dict(dest_width=16, dest_height=16, u=0, v=0,
                                          source_width=64, source_height=64), 'Glyph upload/sprite differs')
        groups = []
        for draw in trace['draws']:
            if not groups or draw['y'] != groups[-1][0]['y'] or draw['x'] <= groups[-1][-1]['x']:
                groups.append([])
            groups[-1].append(draw)
        observed_lines = [dict(text=''.join(d['glyph'] for d in group),
                               x=group[0]['x'], y=group[0]['y'],
                               positions=[d['x'] for d in group],
                               advances=[b['x'] - a['x'] for a, b in zip(group, group[1:])])
                          for group in groups]
        require(observed_lines == trace['lines'], 'Line groups differ from actual draws')
        complete = set()
        for group in trace['lines']:
            require(72 <= group['y'] <= 204 and (group['y'] - 72) % 22 == 0, 'Line group bounds differ')
            index = scroll + (group['y'] - 72) // 22
            if group['text'] == lines[index].decode('ascii') and group['positions'] == expected[index]:
                require(group['advances'] == [widths[c] for c in lines[index][:-1]], 'Line advances differ')
                complete.add(index)
        wanted = {i for i in range(scroll, min(scroll + 7, len(lines))) if lines[i]}
        require(wanted <= complete, 'Missing complete visible line: ' + stage)
        covered.update(complete)
        traces.append(dict(path=str(path), sha256=sha(path), glyph_draws=512,
                           complete_line_indices=sorted(complete)))
    require(covered == {i for i, line in enumerate(lines) if line}, 'Complete scroll coverage differs')
    native_path = UI / 'gallery_candidate_native_trace.en.json'
    native = read(native_path)
    native_resource = 'menu/Gallery/dic/GgHelp001.bin'
    native_bytes = (pathlib.Path('work/source/cpk') / native_resource).read_bytes()
    native_old = parse(native_resource, native_bytes)
    require(native['status'] == 'selected_native_gallery_font_and_advances_verified' and
            native['version'] == '0.1.7' and native['executable_sha256'] == manifest['output_elf_sha256'] and
            native['resource'] == native_resource and native['source_sha256'] == hashlib.sha256(native_bytes).hexdigest() and
            native['bank']['all_original_font_bytes_verified'] is True and native['observed_advance_px'] == 13 and
            native['glyph_draws_observed'] == len(native['draws']) == 32, 'Native regression trace differs')
    native_font = native_bytes[32:native_old['head'][1]]
    require(native['bank']['packed_font_sha256'] == hashlib.sha256(native_font).hexdigest(), 'Native bank differs')
    native_codes = [int.from_bytes(c.encode('cp932'), 'big') for c in native_old['charset']]
    for draw in native['draws']:
        slot = draw['bank_slot']
        require(0 <= slot < len(native_codes) and draw['code'] == native_codes[slot] and
                draw['glyph_sha256'] == hashlib.sha256(native_font[slot * 384:(slot + 1) * 384]).hexdigest() and
                draw['texture_pointer'] == native['bank']['pixels'] + slot * 384 and draw['upload'] == [32, 24, 32] and
                draw['nominal_rectangle'] == [16, 16] and draw['native_sprite_routine'] == '0xd7fc', 'Native glyph differs')
    deltas = [b['x'] - a['x'] for a, b in zip(native['draws'], native['draws'][1:])
              if b['y'] == a['y'] and b['x'] > a['x']]
    require(deltas and all(delta == 13 for delta in deltas), 'Native advances differ')
    native_info, native_capture = reviewed_capture('gallery_candidate_japanese', manifest, 'native_font_visual_qa_passed')
    require(native_info['resource'] == native_resource, 'Native capture resource differs')
    ph = struct.unpack_from('<8I', executable, 0x34 + 64)
    start, address = ph[1:3]
    bank_offset = start + manifest['high_bank'] - address
    bank = executable[bank_offset:bank_offset + manifest['high_bank_bytes']]
    require(hashlib.sha256(bank).hexdigest() == reference['bank_sha256'], '4x bank differs')
    d = Debugger()
    try:
        base = next(m['address'] for m in d.call('hle.module.list')['modules'] if m['name'] == 'hp_proj')
        require(d.call('cpu.breakpoint.list')['breakpoints'] == [], 'Unexpected remaining CPU breakpoint')
        require(d.read(base + manifest['high_bank'], len(bank)) == bank, 'Live 4x bank differs')
        require(d.read(base + address + 0x600, 258) == executable[start + 0x600:start + 0x702], 'Live lookup differs')
        integer = struct.unpack('<129I', d.read(base + manifest['dialogue_hooks']['integer_advance_lut'], 516))
        require(all(integer[c] == width for c, width in widths.items()), 'Live integer advances differ')
        for offset in (0xee35c, 0xee8d4):
            on_disk = struct.unpack_from('<2I', executable, offset + 0xc0)
            live = struct.unpack('<2I', d.read(base + offset, 8))
            # Loader relocates the J target by module base; the delay instruction remains.
            require(on_disk[0] >> 26 in (2, 3) and live ==
                    (((on_disk[0] >> 26) << 26 | (((on_disk[0] & 0x3ffffff) * 4 + base) >> 2) & 0x3ffffff), on_disk[1]),
                    'Live gallery hook differs')
        require(d.call('cpu.status')['stepping'] is False, 'CPU is still stopped')
    finally:
        d.close()
    require(sha(pathlib.Path(manifest['iso_path'])) == manifest['iso_sha256'], 'ISO changed')
    require(sha(ASSET / 'HP.CPK') == manifest['dialogue_cpk_sha256'], 'Archive changed')
    proof = dict(version='0.1.7', status='selected_gallery_prose_display_qa_passed',
                 selected_resource=resource, translation_id=identity,
                 iso_sha256=manifest['iso_sha256'], executable_sha256=manifest['output_elf_sha256'],
                 archive_sha256=manifest['dialogue_cpk_sha256'],
                 runtime_verified_gallery_prose_rows=1, gallery_record_display_qa_passed=True,
                 wording_reconstructed_byte_exact=True, original_controls_preserved=True,
                 physical_lines=15, nonempty_lines=14, complete_line_indices=sorted(covered),
                 visible_glyphs=sum(map(len, lines)), glyph_draws_observed=1536,
                 glyph_source_scale=4, source_rect=[64, 64], destination_rect=[16, 16],
                 live_bank_sha256=reference['bank_sha256'], live_lookup_and_integer_advances_verified=True,
                 live_gallery_hooks_verified=True, text_viewport=[4, 72, 330, 154], glyph_limit=45,
                 scroll_captures=captures, scroll_traces=traces,
                 native_following_entry=dict(resource=native_resource, trace=str(native_path), trace_sha256=sha(native_path),
                     glyph_draws=32, original_font_bytes_verified=True, advance_px=13, capture=native_capture),
                 gallery_heading_translation_verified=False, full_game_verified=False,
                 emulator_internal_4x_resolution_verified=False, native_output=[480, 272],
                 scope='Complete selected dictionary prose only; three scroll positions and one original Japanese font regression',
                 opening_evidence_inherited_from=manifest['opening_validation_inherited_from'],
                 opening_retested_in_this_build=False)
    print(json.dumps(proof, indent=2))
    if not args.write:
        print('DRY RUN: no proof or manifest written.')
        return
    destination = args.output.resolve()
    require(not destination.exists() and destination.name.endswith('.en.json') and
            not destination.is_relative_to(pathlib.Path('work/source').resolve()), 'Proof must be fresh and outside sources')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(proof, indent=2) + '\n', encoding='utf8')
    manifest.update(status=proof['status'], gallery_display_qa_passed=True,
                    runtime_verified_gallery_prose_rows=1, gallery_validation=str(args.output))
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    main()
