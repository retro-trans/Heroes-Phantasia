"""Install four reviewed world-map strings in existing proved PNG tails."""
import argparse, copy, json, struct
from pathlib import Path
from executable_text_patch import Elf, ORIGINAL, ORIGINAL_SHA, reference_index, encoded_text
from native_menu_install_plan import cstring
from field_ui_patch import notation
from gallery_label_patch import sha
from png_tail_allocate import plan
from prepare_relocation_019 import section_load, coverage, pair_shapes
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from dialogue_tokens import validate_controls

SOURCE = Path('work/output/0.1.31-serish-tail-assets/EBOOT.BIN')
SOURCE_SHA = '5c04edcdf39cd5506718da986a57ea20c802b7cae21bd9c564bf3e96a51e4c76'
OUT = Path('work/output/0.1.32-world-map-assets')
QUEUE = Path('work/translation/en/executable_world_map_0001.json')
# Source RVAs and owners come from original PSP R32 records, never integer scans.
TARGETS = (
    ('world_map_prompt', 611456, 612201, 13711, 'Go to the World Map?{0E}', 440),
    ('world_map_headquarters', 617152, 617276, 13925, 'HOLD Headquarters', 208),
    ('world_map_zoom', 608808, 610760, 13643, 'Zoom', 49),
    ('world_map_camp_menu', 608916, 611039, 13670, 'Camp Menu', 104),
)

def build():
    incoming = SOURCE.read_bytes()
    before = json.loads(SOURCE.with_name('executable.en.json').read_text())
    original = ORIGINAL.read_bytes()
    if sha(incoming) != SOURCE_SHA or before['output_elf_sha256'] != SOURCE_SHA or sha(original) != ORIGINAL_SHA:
        raise ValueError('Frozen source identity differs')
    e, o = Elf(incoming), Elf(original)
    refs, _ = reference_index(o)
    font = authoritative_font_metadata(incoming, before)
    png = validate_native_png_metadata(incoming, before)
    lut = struct.unpack('<131f', incoming[e.file_offset(before['float_width_lut_rva'], 524):][:524])
    reservation = plan(before, [dict(name=name, data=encoded_text(target, 'ascii')+b'\0', alignment=4)
        for name, _, _, _, target, _ in TARGETS])
    result = bytearray(incoming)
    allowed, mask, entries, rows = set(), set(), [], []
    for (name, slot, source, ordinal, target, limit), placement in zip(TARGETS, reservation['patches']):
        raw = cstring(o, source)
        source_text = notation(raw[:-1])
        validate_controls(source_text, target)
        owners = [r for r in refs if r['address'] == source]
        if len(owners) != 1 or owners[0]['kind'] != 'R_MIPS_32' or owners[0]['sites'] != [slot] or owners[0]['relocation_ordinals'] != [ordinal]:
            raise ValueError('Selected source has unreviewed owners')
        if e.word(slot) != source or e.relocs[ordinal] != (slot, 2) or cstring(e, source) != raw:
            raise ValueError('Current selected table/source differs')
        width = sum(lut[c] for c in placement['data'] if 32 <= c <= 126)
        if width > limit:
            raise ValueError('Complete target exceeds reviewed screenshot region')
        p, n = placement['file_offset'], placement['bytes']
        if e.file_offset(placement['rva'], n) != p:
            raise ValueError('Tail file backing differs')
        for active in before['additional_scopes']['tail_reservations']+before['native_tail_compaction']['chunks']:
            if placement['rva'] < active['rva']+active['bytes'] and active['rva'] < placement['rva']+n:
                raise ValueError('New string overlaps active code/data')
        result[p:p+n] = placement['data']
        q = e.file_offset(slot, 4)
        struct.pack_into('<I', result, q, placement['rva'])
        allowed.update(range(p, p+n)); allowed.update(range(q, q+4))
        mask.update(range(placement['rva'], placement['rva']+n)); mask.update(range(slot, slot+4))
        entry = {k:v for k,v in placement.items() if k != 'data'}
        entry.update(pointer_slot=slot, source_rva=source, source_sha256=sha(raw), relocation_ordinal=ordinal,
                     target=target, native_advance_px=width, screenshot_available_width_px=limit)
        entries.append(entry)
        rows.append(dict(id=name, file='PSP_GAME/SYSDIR/EBOOT.decrypted.elf', offset=o.file_offset(source),
            byte_length=len(raw)-1, encoding='cp932', category='ui', source=source_text, target=target,
            status='translated', context='User-reported world-map prompt, location and footer labels.',
            decisions='Complete target relocated into proof-backed storage; source controls and native typed pointer retained. HOLD follows the glossary.'))
    result = bytes(result)
    out = Elf(result)
    if len(result) != len(incoming) or out.ph != e.ph or out.relocs != e.relocs or pair_shapes(result) != pair_shapes(incoming):
        raise ValueError('Inherited memory/relocation contracts changed')
    if any(a != b and i not in allowed for i,(a,b) in enumerate(zip(incoming,result))):
        raise ValueError('Unselected executable bytes changed')
    coverage(result)
    models = []
    for base in (0x08804000, 0x08900000, 0x08fff000):
        old, _, _, _ = section_load(incoming, base)
        new, visited, skipped, _ = section_load(result, base)
        if skipped or len(visited) != len(e.relocs) or old[1:] != new[1:] or any(a != b and i not in mask for i,(a,b) in enumerate(zip(old[0],new[0]))):
            raise ValueError('Unselected section-loaded memory differs')
        for row in entries:
            if struct.unpack_from('<I', new[0], row['pointer_slot'])[0] != base+row['rva']:
                raise ValueError('Relocated loaded string pointer differs')
            if cstring(out, row['rva']) != encoded_text(row['target'], 'ascii')+b'\0':
                raise ValueError('Complete installed target differs')
        models.append(dict(base=base, relocations=len(visited), selected_pointers_exact=4, unselected_loaded_memory_exact=True))
    report = copy.deepcopy(before)
    for key in ('output', 'approved_dry_plan_sha256', 'written_readback_verified'):
        report.pop(key, None)
    report.update(version='0.1.32', input_version='0.1.31', input_sha256=SOURCE_SHA,
        output_elf_sha256=sha(result), output_sha256=sha(result), runtime_verified=False,
        status='world_map_labels_candidate_runtime_unverified')
    report['trailer_recovery']['free_tail_regions'] = reservation['free_tail_regions']
    report['trailer_recovery']['remaining_tail_bytes'] = reservation['remaining_bytes']
    report['additional_scopes']['tail_reservations'].extend({k:v for k,v in p.items() if k != 'data'} for p in reservation['patches'])
    report['world_map_ui_patch'] = dict(entries=entries, loaded_growth_bytes=0, new_relocations=0,
        remaining_tail_bytes=reservation['remaining_bytes'], loader_models=models,
        all_unselected_file_bytes_exact=True, all_relocation_records_exact=True,
        font_bank_and_hooks_exact=True, native_ui_verified=False,
        width_policy='Inherited unscaled float advance LUT; screenshot regions measured at native 480x272.')
    if {k:v for k,v in authoritative_font_metadata(result, report).items() if k != 'additional_scopes'} != {k:v for k,v in font.items() if k != 'additional_scopes'} or validate_native_png_metadata(result, report) != png:
        raise ValueError('Inherited font or PNG contracts changed')
    return result, report, dict(schema_version=1, language='en', rows=rows)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true'); ap.add_argument('--expected-sha256')
    a = ap.parse_args(); data, report, queue = build()
    print(json.dumps(dict(version=report['version'], sha256=sha(data), **report['world_map_ui_patch']), indent=2))
    if not a.write:
        print('DRY RUN: no executable or translation files written.'); return
    if a.expected_sha256 != sha(data) or OUT.exists() or QUEUE.exists():
        raise ValueError('Reviewed hash and fresh destinations required')
    OUT.mkdir(parents=True); (OUT/'EBOOT.BIN').write_bytes(data)
    if (OUT/'EBOOT.BIN').read_bytes() != data: raise ValueError('Executable readback differs')
    report['written_readback_verified'] = True
    (OUT/'executable.en.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

if __name__ == '__main__': main()
