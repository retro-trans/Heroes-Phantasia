"""Fresh .14 compact HUD/CPL candidate; dry by default, guarded fresh writer."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct

from battle_label_hooks import (SOURCE, SHA, label_decoder, label_renderer,
                                label_advance, label_palette, label_native_skip)
from build_menu_patch import START, align, relocate_code, reloc
from dialogue_vwf_hooks import r
from dialogue_wrap import literal_reveal_cap
from live_vwf import i, j, jal, words

CPLS = ('0001', '0002', '0197', '0198')
MONSTER_SOURCE = bytes.fromhex('838283938358835e815b')
OUTPUT=Path('work/output/0.1.14-dialogue-assets')
APPROVED_SHA='00971b998b817c19221e8744e8deaba736d3186f86dd705ed0877faf6370dbbd'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rebuild_cpl(original, target=b'Monster'):
    if not target or len(target) > 31 or any(c < 32 or c >= 127 for c in target):
        raise ValueError('HUD Latin label must be printable ASCII,1..31 bytes')
    if len(original) < 48:
        raise ValueError('CPL header truncated')
    pointers = struct.unpack_from('<12I', original)
    start, end = pointers[1:3]
    if not 48 <= start < end <= len(original):
        raise ValueError('Unrecognized CPL name/glyph blocks')
    block = original[start:end]
    if not block.startswith(MONSTER_SOURCE + b'\0'):
        raise ValueError('Expected confirmed Monster as name index0')
    # Preserve all other NUL-separated names, empty entries and tail padding.
    replacement = target + block[len(MONSTER_SOURCE):]
    location = align(len(original), 16)
    result = bytearray(original)
    result.extend(bytes(location - len(result)))
    result.extend(replacement)
    struct.pack_into('<I', result, 4, location)
    assert result[:4] == original[:4] and result[8:len(original)] == original[8:]
    assert result[pointers[2]:pointers[3]] == original[pointers[2]:pointers[3]]
    return bytes(result), {
        'name_index': 0, 'target': target.decode('ascii'), 'target_bytes': len(target),
        'pointer_field': 4, 'old_pointer': start, 'new_pointer': location,
        'old_name_block_bytes': len(block), 'new_name_block_bytes': len(replacement),
        'other_names_and_empty_entries_preserved': True,
        'native_cache_block_preserved': True,
        'fixed_header_name_changed': False,
        'input_sha256': digest(original), 'output_sha256': digest(result),
        'original_bytes': len(original), 'output_bytes': len(result),
    }


def build(paired_ruby_cap=False,compact=True):
    if compact:
        from compact_vwf_patch import build as compact_build
        original,report=compact_build()
    else:
        original = SOURCE.read_bytes()
        report = copy.deepcopy(json.loads(SOURCE.with_name('setup_patch.en.json').read_text()))
        if digest(original) != SHA or report['output_elf_sha256'] != SHA:
            raise ValueError('Expected frozen .13 executable and matching report')
    intermediate_sha=digest(original)
    phoff, shoff = struct.unpack_from('<II', original, 28)
    phnum = struct.unpack_from('<H', original, 44)[0]
    shnum = struct.unpack_from('<H', original, 48)[0]
    if phnum != 4:
        raise ValueError('Unexpected inherited segment count')
    ph = [list(struct.unpack_from('<8I', original, phoff + 32*n)) for n in range(phnum)]
    sections = [list(struct.unpack_from('<10I', original, shoff + 40*n)) for n in range(shnum)]
    if ph[2][2] != START or ph[3][0] != 0x700000a0:
        raise ValueError('Unexpected inherited payload/relocations')
    prefix = original[ph[2][1]:ph[2][1]+ph[2][4]]
    previous = original[ph[3][1]:ph[3][1]+ph[3][4]]
    sites = set(struct.iter_unpack('<II', previous))
    patch = bytearray(original); payload = bytearray(prefix)
    additions = []; changes = []; hooks = {}

    def append(name, code):
        while len(payload) % 16:
            payload.append(0)
        offset = len(payload); hooks[name] = START + offset; payload.extend(code)
        additions.extend(relocate_code(payload, offset, len(code)))
        return START + offset

    def replace(site, new, expected, new_relocation=False):
        if original[site+192:site+192+len(expected)] != expected:
            raise ValueError(f'Unexpected original site {site:x}')
        if new_relocation:
            if any(s == site and (f >> 8) & 255 == 0 for s, f in sites):
                raise ValueError('Unexpected existing relocation')
            additions.append(reloc(site, 4, 0))
        elif (site, 4) not in sites:
            raise ValueError(f'Expected inherited R26 at {site:x}')
        patch[site+192:site+192+len(new)] = new
        changes.append({'rva': hex(site), 'expected_hex': expected.hex(),
                        'replacement_hex': new.hex()})

    widths = [round(v) for v in struct.unpack_from('<129f', prefix, 0x800)]
    while len(payload) % 16:
        payload.append(0)
    lut = START + len(payload); payload.extend(words(widths))
    dec = append('battle_label_decoder', label_decoder())
    draw = append('battle_label_renderer', label_renderer())
    advance = append('battle_label_advance', label_advance(lut))
    native_skip = append('battle_label_native_skip', label_native_skip())
    palette = append('battle_label_palette', label_palette())
    replace(0xe9cc8, words([j(dec), 0]),
            words([j(int(report['hooks']['ruby_decoder'], 16)), 0]))
    replace(0xec67c, words([jal(draw)]), words([jal(0xea900)]))
    replace(0xec684, words([j(advance), 0, j(native_skip), 0]),
            words([i(9, 19, 19, 1), r(19, 20, 4, funct=0x2a),
                   i(5, 4, 0, -25), i(9, 17, 17, 13)]), True)
    if any(s == 0xec68c and (f >> 8) & 255 == 0 for s,f in sites):
        raise ValueError('Unexpected relocation at native skip stub')
    additions.append(reloc(0xec68c,4,0))
    expected_branch=words([i(20,4,0,11)])
    if original[0xec658+192:0xec65c+192]!=expected_branch:
        raise ValueError('Expected classifier-false BEQL to EC688')
    replacement_branch=words([i(20,4,0,12)])
    patch[0xec658+192:0xec65c+192]=replacement_branch
    changes.append(dict(rva='0xec658',expected_hex=expected_branch.hex(),
                        replacement_hex=replacement_branch.hex(),
                        decision='Taken BEQL retains its S3 increment delay; separate EC68C stub resumes native13px continuation.'))
    replace(0xea6ac, words([jal(palette)]),
            words([jal(int(report['hooks']['setup_header_palette'], 16))]))
    if paired_ruby_cap:
        cap = append('paired_ruby_reveal_cap', literal_reveal_cap(True))
        replace(0xee984, words([j(cap), 0]),
                words([j(int(report['hooks']['literal_reveal_cap'], 16)), 0]))
    payload_file = align(len(patch), 64)
    patch.extend(bytes(payload_file-len(patch))); patch.extend(payload)
    rel_file = align(len(patch), 16)
    patch.extend(bytes(rel_file-len(patch))); patch.extend(previous+b''.join(additions))
    for section in sections:
        if section[1] == 0x700000a0:
            section[4] = rel_file+(section[4]-ph[3][1])
        elif section[3] == START and section[4] == ph[2][1]:
            section[4] = payload_file; section[5] = len(payload)
    payload_section = next(n for n, s in enumerate(sections)
                           if s[3] == START and s[4] == payload_file)
    sections.append([0, 0x700000a0, 0, 0, rel_file+len(previous),
                     len(additions)*8, 0, payload_section, 4, 8])
    newsh = align(len(patch), 4); patch.extend(bytes(newsh-len(patch)))
    for section in sections:
        patch.extend(struct.pack('<10I', *section))
    ph[2][1] = payload_file; ph[2][4] = ph[2][5] = len(payload)
    ph[3][1] = rel_file; ph[3][4] = len(previous)+len(additions)*8
    for n, header in enumerate(ph):
        struct.pack_into('<8I', patch, phoff+32*n, *header)
    struct.pack_into('<I', patch, 32, newsh)
    struct.pack_into('<H', patch, 48, len(sections))
    assert payload[:len(prefix)] == prefix
    assert patch[rel_file:rel_file+len(previous)] == previous
    spans = sorted((s[4], s[4]+s[5]) for s in sections if s[1] == 0x700000a0)
    assert spans[0][0] == rel_file and spans[-1][1] == rel_file+ph[3][4]
    assert all(a[1] == b[0] for a, b in zip(spans, spans[1:]))
    assert len(set(struct.iter_unpack('<II', previous+b''.join(additions)))) == ph[3][4]//8
    assets = {}; asset_reports = []
    for number in CPLS:
        name = f'btl/cpl/cpl{number}.bin'
        rebuilt, details = rebuild_cpl((Path('work/source/cpk') / name).read_bytes())
        assets[name] = rebuilt; asset_reports.append({'file': name, **details})
    result_hash = digest(patch)
    report.update(version='0.1.14', input_version='0.1.13', input_sha256=SHA,
                  status='battle_label_candidate_runtime_unverified', runtime_verified=False,
                  output_sha256=result_hash, output_elf_sha256=result_hash,
                  elf_bytes=len(patch), payload_bytes=len(payload), module_growth_bytes=len(payload),
                  payload_growth=len(payload)-len(prefix),
                  inherited_added_relocations=report['added_relocations'],
                  added_relocations=len(additions), total_relocations=ph[3][4]//8,
                  inherited_payload_sha256=digest(prefix), inherited_payload_preserved=True,
                  inherited_relocation_table_sha256=digest(previous),
                  relocation_table_sha256=digest(previous+b''.join(additions)),
                  relocation_prefix_unchanged=True)
    report['hooks'].update({name: hex(value) for name, value in hooks.items()})
    report['changed_rvas'].extend(changes)
    report['battle_label_patch'] = {
        'changes': changes, 'hooks': {n: hex(v) for n, v in hooks.items()},
        'advance_lut': hex(lut), 'maximum_encoded_label_bytes': 31,
        'cpl_replacements': asset_reports, 'native_cache_blocks_preserved': True,
        'japanese_fallback_preserved': True, 'paired_ruby_cap': paired_ruby_cap,
        'runtime_verified': False, 'source_assets_rewritten': False,
        'compact_input':compact,'intermediate_executable_sha256':intermediate_sha,
    }
    report['limitations'].append('Battle-label Latin routing and appended CPL name lists require runtime QA; only the four confirmed Monster resources are replaced. Native31-byte label scratch and other HUD paths remain unchanged.')
    return bytes(patch), report, assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paired-ruby-cap', action='store_true')
    parser.add_argument('--write',action='store_true')
    args = parser.parse_args()
    data, report, assets = build(args.paired_ruby_cap)
    print(json.dumps({k: report[k] for k in ('version', 'input_sha256',
                     'output_elf_sha256', 'elf_bytes', 'payload_bytes',
                     'payload_growth', 'added_relocations', 'total_relocations',
                     'battle_label_patch')}, indent=2))
    if not args.write:
        print('DRY RUN: no executable, CPL, report, CPK or ISO written.');return
    if not args.paired_ruby_cap or report['output_elf_sha256']!=APPROVED_SHA:
        raise ValueError('Only the exact independently reviewed compact + HUD + paired-cap candidate is approved')
    if OUTPUT.exists():raise ValueError('Refusing to overwrite a versioned preparation folder')
    # Build/validate every byte before creating any fresh output.
    from build_local import authoritative_font_metadata
    authoritative_font_metadata(data,report)
    if any(digest(assets[a['file']])!=a['output_sha256'] for a in report['battle_label_patch']['cpl_replacements']):
        raise ValueError('CPL preparation hash mismatch')
    OUTPUT.mkdir(parents=True)
    for name,raw in [('EBOOT.BIN',data),*assets.items()]:
        path=OUTPUT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        if path.read_bytes()!=raw:raise ValueError('Written asset readback differs: '+name)
    report['status']='written_compact_battle_label_candidate_runtime_unverified'
    report['prepared_asset_paths']={'EBOOT.BIN':str(OUTPUT/'EBOOT.BIN'),
                                   **{name:str(OUTPUT/name) for name in assets}}
    out=OUTPUT/'setup_patch.en.json';out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    if json.loads(out.read_text(encoding='utf8'))!=report:raise ValueError('Written report readback differs')
    print('Written and read back fresh .14 technical assets only; runtime remains unverified.')


if __name__ == '__main__':
    main()
