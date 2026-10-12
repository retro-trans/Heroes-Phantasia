"""Preview reviewed opening evidence; --write applies it.

Default retains the 0.1.3 speaker candidate. --compact-font selects 0.1.5
and always records failed layout. --association-fix selects 0.1.6, requiring
passed scoped geometry plus pre-inspected capture metadata for display QA.
"""
import argparse, hashlib, json, math, pathlib, struct
from rebuild_dialogue import parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
UI = ROOT / 'work/ui/runtime'

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

def check_reviewed_capture(path, data):
    if not path.is_file():
        raise ValueError(f'{path.stem}: capture missing')
    if data.get('visually_reviewed') is True or data.get('layout_visual_qa_passed') is True:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if data.get('reviewed_capture_sha256') != digest:
            raise ValueError(f'{path.stem}: reviewed capture hash missing or stale')

def checked_geometry(path, digest, mode):
    data = load(path)
    if data.get('executable_sha256') != digest or data.get('mode') != mode:
        raise ValueError(f'{path.name}: geometry belongs to another executable or text mode')
    checks = data.get('checks', {})
    required = {'native_zero_angles', 'native_unit_scales', 'geometry_matches_model',
                'center_matches_opening_assumption', 'geometry_inside_screen_margins',
                'requested_text_classification'}
    if mode == 'english':
        required.add('opening_record_metrics')
    if (data.get('status') != 'scoped_geometry_probe_passed' or
            not required.issubset(checks) or any(value is not True for value in checks.values())):
        raise ValueError(f'{path.name}: scoped geometry checks have not passed')
    return data

def traced_origin(trace, text, baseline, geometry):
    # The renderer truncates float window translation to pixel coordinates.
    # Observe the actual complete-line origin, then corroborate its shift with
    # the independently measured geometry; never assume a candidate's origin.
    delta = geometry['position'][0] - geometry['model_original_center_assumption']
    expected_x = baseline[0] + delta
    if not math.isfinite(expected_x):
        raise ValueError('Nonfinite geometry-derived origin')
    origins = {(line['x'], line['y']) for line in trace['lines'] if line['text'] == text}
    if len(origins) != 1:
        raise ValueError(f'{text!r}: missing or ambiguous complete-line origin')
    x, y = origins.pop()
    if abs(x - expected_x) > 1 or y != baseline[1]:
        raise ValueError(f'{text!r}: traced origin disagrees with measured geometry')
    return x, y

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--compact-font', action='store_true')
    mode.add_argument('--association-fix', action='store_true')
    args = parser.parse_args()
    version = '0.1.6' if args.association_fix else '0.1.5' if args.compact_font else '0.1.3'
    prefix = 'association_candidate' if args.association_fix else 'compact_candidate' if args.compact_font else 'speaker_candidate'
    manifest_path = ROOT / f'work/output/{version}-opening-vwf-4x-candidate/manifest.en.json'
    manifest = load(manifest_path)
    executable = (manifest_path.parent / 'EBOOT.BIN').read_bytes()
    digest = hashlib.sha256(executable).hexdigest()
    if digest != manifest['output_elf_sha256']:
        raise ValueError('Candidate executable changed')
    traces = {key: load(UI / filename.replace('speaker_candidate', prefix)) for key, filename in {
        'name': 'speaker_candidate_name_trace.en.json',
        'page1': 'speaker_candidate_page1_4x_trace.en.json',
        'page2': 'speaker_candidate_page2_4x_trace.en.json',
        'fallback': 'speaker_candidate_japanese_fallback_trace.en.json',
        'menu': 'speaker_candidate_menu_validation.en.json',
    }.items()}
    geometry = {}
    if args.association_fix:
        geometry = {key: checked_geometry(UI / f'{prefix}_{key}_geometry.en.json', digest, mode)
                    for key, mode in (('page1', 'english'), ('page2', 'english'), ('japanese', 'japanese'))}
    for key, trace in traces.items():
        if trace.get('loaded_executable_sha256', trace.get('executable_sha256')) != digest:
            raise ValueError(f'{key}: evidence belongs to another executable')
    for key in ('name', 'page1', 'page2'):
        if not traces[key]['draws']:
            raise ValueError('Empty glyph trace')
        for draw in traces[key]['draws']:
            texture, sprite = draw['texture'], draw['sprite']
            if [texture['width'], texture['height'], texture['pitch_pixels']] != [64, 64, 64]:
                raise ValueError('Unexpected glyph upload')
            if [sprite['source_width'], sprite['source_height'], sprite['dest_width'], sprite['dest_height']] != [64, 64, 16, 16]:
                raise ValueError('Unexpected glyph rectangle')
    # Tie complete traced lines to the exact rebuilt source record, and derive
    # widths from the executable's actual advance table instead of fixed facts.
    resource = 'fld/talk/f101010.bin'
    source = (ROOT / 'work/source/cpk' / resource).read_bytes()
    parsed = parse(resource, source)
    original_row = parsed['spans'][parsed['refs'][1][1]][0]
    row_id = hashlib.sha256(original_row).hexdigest()[:20]
    if row_id != 'de6e5ee8ded50553cfc3' or manifest['selected_dialogue_rows'] != [1]:
        raise ValueError('Selected dialogue identity changed')
    asset = (ROOT / 'work/output/0.1.1-dialogue-candidate/assets/selected' / resource).read_bytes()
    asset_hash = hashlib.sha256(asset).hexdigest()
    if asset_hash != '35cfda9a01773d74eff35679c79c62ed243a6a7b022279bbb0067c866f055f82':
        raise ValueError('Rebuilt asset changed')
    rebuilt = parse(resource, asset)
    expected = b"\x1cSgt. Keroro\x0eW-where in the world\x11am I?\x12\x10I can't see the\x11dimensional monster, either.\x12\x0e"
    if rebuilt['spans'][rebuilt['refs'][1][1]][0] != expected:
        raise ValueError('Rebuilt dialogue content changed')
    segment = struct.unpack_from('<8I', executable, 0x34 + 64)
    lut_offset = segment[1] + manifest['dialogue_hooks']['integer_advance_lut'] - segment[2]
    lut = struct.unpack_from('<129I', executable, lut_offset)
    def verify_line(key, text, x, y, renderer):
        positions, cursor = [], x
        for char in text:
            positions.append(cursor)
            cursor += lut[ord(char)]
        if not any(line['text'] == text and line['positions'] == positions and line['x'] == x and line['y'] == y for line in traces[key]['lines']):
            raise ValueError(f'{key}: complete expected line and origins not traced')
        draws = traces[key]['draws']
        sequence = [(ord(char), pos, y, renderer) for char, pos in zip(text, positions)]
        actual = [(draw['code'], draw['x'], draw['y'], draw['renderer_return']) for draw in draws]
        if not any(actual[i:i+len(sequence)] == sequence for i in range(len(actual)-len(sequence)+1)):
            raise ValueError(f'{key}: expected contiguous glyph sequence not traced')
        return cursor - x
    expected_lines = (
        ('page1', 'W-where in the world', 168), ('page1', 'am I?', 190),
        ('page2', "I can't see the", 168), ('page2', 'dimensional monster, either.', 190))
    origins = [traced_origin(traces[key], text, (276, y), geometry[key])
               if args.association_fix else (276, y) for key, text, y in expected_lines]
    widths = [verify_line(key, text, x, y, '0xee2dc')
              for (key, text, _), (x, y) in zip(expected_lines, origins)]
    speaker_origin = (traced_origin(traces['name'], 'Sgt. Keroro', (304, 142), geometry['page1'])
                      if args.association_fix else (304, 142))
    speaker_width = verify_line('name', 'Sgt. Keroro', *speaker_origin, '0xec048')
    if traces['fallback']['renderers'] != ['0xe9ff4']:
        raise ValueError('Japanese fallback renderer changed')
    fallback = traces['fallback']['draws']
    advances = [b['x'] - a['x'] for a, b in zip(fallback, fallback[1:]) if b['x'] > a['x'] and b['y'] == a['y']]
    if not advances or set(advances) != {13}:
        raise ValueError('Japanese fallback advances changed')
    if len(traces['menu']['menu_labels_verified']) != 5:
        raise ValueError('Menu verification changed')
    if args.association_fix:
        if traces['menu']['menu_labels_verified'] != ['New Game', 'Load', 'Options', 'Gallery', 'Data Install']:
            raise ValueError('Original menu label validation changed')
        next_record = parsed['spans'][parsed['refs'][2][1]][0]
        if rebuilt['spans'][rebuilt['refs'][2][1]][0] != next_record:
            raise ValueError('Following original Japanese record changed')
        next_start = source.find(next_record)
        if next_start < 0 or source.find(next_record, next_start + 1) >= 0:
            raise ValueError('Following original Japanese record is not unique')
        body_start = next_start + next_record.index(b'\x0e') + 1
        for draw in fallback:
            offset = draw['source_body_offset']
            head = asset[offset:offset + 32]
            if (len(head) != 32 or source.find(head) < 0 or
                    not body_start <= source.find(head) < next_start + len(next_record) or
                    hashlib.sha256(head).hexdigest() != draw['source_prefix_sha256'] or
                    draw['source_file'] != resource or draw['font_mode'] != 1 or
                    draw['draw_rect'] != [16, 16] or draw['renderer_module_offset'] != '0xe9ff4'):
                raise ValueError('Fallback is not the unchanged original Japanese renderer/text')
    proof = {
        'version': '0.1.3', 'status': 'opening_glyphs_observed_layout_failed',
        'loaded_executable_sha256': digest,
        'installation': 'cold boot from local ISO; executable-installed hooks',
        'dialogue_rows_in_build': 1, 'dialogue_reference_index': 1,
        'translation_id': row_id, 'rebuilt_asset_sha256': asset_hash,
        'english_pages_observed': 2, 'speaker_label_observed': 'Sgt. Keroro',
        'glyph_trace_draws': {key: len(traces[key]['draws']) for key in ('name', 'page1', 'page2', 'fallback')},
        'latin_source_rect': [64, 64], 'latin_destination_rect': [16, 16],
        'native_output': [480, 272], 'emulator_internal_4x_verified': False,
        'body_line_advances_pixels': widths,
        'body_line_origins': [[276, 168], [276, 190]],
        'speaker_origin': [304, 142], 'speaker_advance_pixels': speaker_width,
        'speaker_bar_visual_bounds_estimate': [292, 140, 97, 18],
        'body_bubble_visual_bounds_estimate': [276, 157, 180, 59],
        'coordinates_note': 'Origins are traced; panel bounds are visual estimates, not clipping limits.',
        'layout_defects': [
            'Body starts outside the angled left border on both pages.',
            'The final line also extends beyond the right white border.',
            'Measured text width changes placement but does not resize the fixed bubble template.',
        ],
        'japanese_next_record_fallback': {
            'observed': True, 'source_body_offset': fallback[0]['source_body_offset'],
            'renderer': '0xe9ff4', 'advance_pixels': 13,
            'speaker_label_visually_readable': True,
        },
        'dialogue_record_display_qa_passed': False, 'runtime_verified_dialogue_rows': 0,
        'full_game_verified': False, 'save_load_verified': False, 'ruby_verified': False,
        'automatic_wrap_verified': False, 'both_protagonist_variants_verified': False,
        'captures': ['speaker_candidate_english_page1.png', 'speaker_candidate_english_page2.png', 'speaker_candidate_japanese_fallback.png'],
        'traces': ['speaker_candidate_name_trace.en.json', 'speaker_candidate_page1_4x_trace.en.json', 'speaker_candidate_page2_4x_trace.en.json', 'speaker_candidate_japanese_fallback_trace.en.json'],
    }
    classifications = {
        'speaker_candidate_english_page1': 'English opening record, page 1; speaker visible; body crosses left bubble border',
        'speaker_candidate_english_page2': 'English opening record, page 2; speaker visible; body crosses left and right bubble borders',
        'speaker_candidate_japanese_fallback': 'Next original Japanese record after the English record; body and speaker label readable',
    }
    annotations = {}
    for stem, description in classifications.items():
        stem = stem.replace('speaker_candidate', prefix)
        data = load(UI / (stem + '.json'))
        if data['loaded_executable_sha256'] != digest:
            raise ValueError('Screenshot metadata belongs to another build')
        if args.association_fix:
            check_reviewed_capture(UI / (stem + '.png'), data)
        else:
            data.update(game_screen=description, visually_reviewed=True,
                        dialogue_record_display_qa_passed=False)
        annotations[UI / (stem + '.json')] = data
    if prefix != 'speaker_candidate':
        proof.update(version=version,
                     captures=[name.replace('speaker_candidate', prefix) for name in proof['captures']],
                     traces=[name.replace('speaker_candidate', prefix) for name in proof['traces']])
    if args.association_fix:
        inspected = all(data.get('visually_reviewed') is True and data.get('layout_visual_qa_passed') is True
                        for data in annotations.values())
        proof.update(status='selected_opening_record_display_qa_passed' if inspected else 'opening_geometry_observed_visual_qa_pending',
                     geometry_checks={key: data['checks'] for key, data in geometry.items()},
                     geometry_statuses={key: data['status'] for key, data in geometry.items()},
                     complete_english_line_and_name_sequences_verified=True,
                     japanese_native_geometry_restored=True,
                     geometry_traces=[f'{prefix}_{key}_geometry.en.json' for key in geometry],
                     body_line_origins=[list(origin) for origin in origins[:2]],
                     body_line_origins_by_page={key: [list(origin) for (page, _, _), origin in zip(expected_lines, origins) if page == key]
                                                for key in ('page1', 'page2')},
                     speaker_origin=list(speaker_origin), captures_inspected=inspected,
                     layout_defects=[] if inspected else ['Capture inspection and visual layout approval pending.'],
                     dialogue_record_display_qa_passed=inspected,
                     runtime_verified_dialogue_rows=1 if inspected else 0)
        # Legacy visual bounds belong to the unresized template, not this build.
        proof.pop('speaker_bar_visual_bounds_estimate')
        proof.pop('body_bubble_visual_bounds_estimate')
        proof['coordinates_note'] = 'Origins are complete traced sequences corroborated by measured window translation; geometry is scoped to the selected opening record.'
        proof['japanese_next_record_fallback']['speaker_label_visually_readable'] = inspected
        for data in annotations.values():
            data['dialogue_record_display_qa_passed'] = inspected
    ui_path = ROOT / 'work/ui/opening_dialogue.en.json'
    ui = load(ui_path)
    ui['version'] = version
    ui['original_observation_version'] = '0.1.1'
    ui['current_candidate'] = proof
    manifest.update(status=proof['status'], opening_validation=proof,
                    game_translation_complete=False)
    print(json.dumps(proof, indent=2))
    if not args.write:
        print('DRY RUN: no evidence or metadata written.')
        return
    save(UI / f'{prefix}_opening_validation.en.json', proof)
    save(manifest_path, manifest)
    save(ui_path, ui)
    for path, data in annotations.items():
        save(path, data)
    print('Saved partial opening evidence, manifest and three reviewed screenshot annotations.')

if __name__ == '__main__':
    main()
