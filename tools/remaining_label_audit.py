"""Read-only remaining-label consumer audit; no executable/asset writer.

An optional report contains English findings and hashes, never source scripts.
The proposed Crack Burst bytes are a review sample, not an installation plan.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from executable_text_patch import Elf, reference_index
from decode_glyph_tables import table

ORIGINAL = Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf')
CURRENT = Path('work/output/0.1.19-dialogue-assets/EBOOT.BIN')
CURRENT_SHA = '401c720c9a76e8d89112c9026f5620e0bb0c20217a5753ab15f4c67aed3c33f3'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build():
    original_bytes = ORIGINAL.read_bytes()
    current_bytes = CURRENT.read_bytes()
    if sha(original_bytes) != '03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1':
        raise ValueError('Original hash differs')
    if sha(current_bytes) != CURRENT_SHA:
        raise ValueError('Frozen19 hash differs')
    original, current = Elf(original_bytes), Elf(current_bytes)
    report = json.loads(CURRENT.with_name('executable.en.json').read_text(encoding='utf8'))
    queue_raw = Path('work/translation/en/executable_0001.json').read_bytes()
    rows = json.loads(queue_raw)['rows']
    refs, _ = reference_index(original)
    sources = (0x2eb2be, 0x2eb310)
    entries = []
    for source in sources:
        matches = [r for r in rows if int(r['offset']) == source+192]
        if len(matches) != 1 or matches[0]['target'] != 'Crack Burst':
            raise ValueError('Approved Crack Burst target/source differs')
        selected = [r for r in refs if r['address'] == source]
        if len(selected) != 1 or selected[0]['kind'] != 'R_MIPS_HI16_LO16':
            raise ValueError('Expected unique typed source reference differs')
        sites = selected[0]['sites']
        if any(original.word(s) != current.word(s) for s in sites):
            raise ValueError('Source pointer already changed')
        entries.append(dict(id=matches[0]['id'], source_rva=source,
                            pointer_sites=sites, current_words=[current.word(s) for s in sites],
                            proposed_target='Crack Burst', payload_hex=b'Crack Burst\0'.hex(),
                            payload_bytes=12, destination_capacity=28))
    if [r['pointer_sites'] for r in entries] != [[0x842a4,0x842b0],[0x84324,0x84330]]:
        raise ValueError('Typed caller identity differs')
    draw_sites = []
    for site in range(0, 0x294000, 4):
        if original.word(site) == 0x0c000000 | (0xe9918 >> 2):
            target = (current.word(site) & 0x03ffffff) << 2
            draw_sites.append(dict(site=site, original_target=0xe9918,
                                   current_target=target, latin_bypass=target != 0xe9918))
    if [r['site'] for r in draw_sites] != [0x517c0,0x87d8c,0x8823c,0xebeac,0xee330]:
        raise ValueError('Original cached-name call inventory differs')
    route = (current.word(0xee330) & 0x03ffffff) << 2
    if current.word(0xebeac) != original.word(0xebeac) or current.word(0xebeac) != 0x0c03a646:
        raise ValueError('Remaining cached renderer call changed')
    if sum(off == 0xebeac and flags == 4 for off,flags in current.relocs) != 1:
        raise ValueError('Expected existing native R26 relocation differs')
    proposed_call = 0x0c000000 | (route >> 2)
    relocated = []
    for base in (0x08804000,0x08900000,0x08fff000):
        word = (proposed_call & 0xfc000000) | (((proposed_call & 0x03ffffff)+(base>>2)) & 0x03ffffff)
        destination = ((base+0xebeac+4)&0xf0000000) | ((word&0x03ffffff)<<2)
        if destination != base+route:
            raise ValueError('Proposed R26 target model differs')
        relocated.append(dict(base=base,destination=destination))
    count_sites = (0xeaf4c,0xeafa4,0xeafe0,0xeb024)
    if any((current.word(s) & 0x03ffffff) << 2 != report['font_hooks']['name_count'] for s in count_sites):
        raise ValueError('Current expansion count hook differs')
    native_spans = [(0x84964,0x84a18),(0x84a7c,0x84b74),(0x848a4,0x848f4)]
    cache_proof = []
    for start, end in native_spans:
        old = original_bytes[original.file_offset(start):original.file_offset(end)]
        now = current_bytes[current.file_offset(start):current.file_offset(end)]
        if old != now:
            raise ValueError('Original cache collector/sorter/allocation changed')
        cache_proof.append(dict(start=start,end=end,sha256=sha(now),byte_exact_original=True))
    glyph_raw = Path('work/source/cpk/btl/sys_tbl.bin').read_bytes()
    glyph_rows = table(glyph_raw)
    glyph_queue_raw = Path('work/translation/en/glyph_labels_0001.json').read_bytes()
    glyph_queue = json.loads(glyph_queue_raw)['rows']
    if len(glyph_rows) != 256 or len(glyph_queue) != 67:
        raise ValueError('Original glyph inventory differs')
    return dict(schema_version=1,status='static_proposal_no_asset_writer',
                original_elf_sha256=sha(original_bytes),current_elf_sha256=sha(current_bytes),
                executable_target_snapshot_sha256=sha(queue_raw),
                glyph_target_snapshot_sha256=sha(glyph_queue_raw),
                glyph_index=dict(resource='btl/sys_tbl.bin',source_sha256=sha(glyph_raw),
                    physical_rows=256,unique_draft_labels=67,debug_candidate_rows=list(range(244,256)),
                    path_literal_present_in_original=False,
                    path_literal_check=not any(x in original_bytes for x in (b'sys_tbl','sys_tbl'.encode('utf-16le'))),
                    live_owner_proved=False,renderer_measure_advance_proved=False,
                    proposed_hook=None,original_cache_count_indices_preserved=True,
                    next_evidence='At an actual battle move/status label, identify resource owner, table selector and sprite UV/destination; do not attach a global glyph-ID hook.'),
                crack_burst=dict(entries=entries,unique_payload_bytes=12,existing_relocations_reusable=4,
                    native_destination='protagonist slot+0x381A, stride0x3830, field selector3',
                    cache_original_proofs=cache_proof,
                    cache_constraint='8490C discards single-byte text; 84A7C sorts two-byte pairs; 848AC/848D8 divide byte length by2. Leave these routines/cache layout intact.',
                    current_draw_call_inventory=draw_sites,
                    existing_measurement_count_sites=list(count_sites),
                    scoped_existing_route_proposal=dict(site=0xebeac,expected_word=current.word(0xebeac),
                        proposed_word=proposed_call,route_rva=route,existing_R26_preserved=True,
                        additional_code_bytes=0,three_base_R26_model=relocated,
                        function=0xebc08,sole_static_caller=0xde1b4,
                        font_argument='E928C resident font in A0; T1 decoded glyph, T2 protagonist index; 16px destination',
                        native_continuation='EBEB0 retains A1 computation; EBEB8 retains13px animation slot, EBE80 retains F26+13',
                        native_Japanese_cache_fallback_preserved=True,requires_root_review=True),
                    measurement_contract='Hook returns two units per decoded glyph before native division by2; this is glyph count, not VWF pixel width.',
                    blockers=['The proposed EBEAC existing-route retarget requires root review; 8823C already has an inherited tutorial Latin bypass.',
                              '88274 advances by F26; EBEB8 advances fixed13. Exact caller destination/centering requires a scoped measure/advance audit.',
                              'The 12-byte relocation alone cannot claim all display instances work.'],
                    proposal='Deduplicate one 12-byte Latin string and retarget only two existing typed HI/LO pairs after reviewing the remaining EBEAC draw/count/advance consumer. Use original Japanese/cache fallback; do not change glyph cache/count/indices.',
                    ready_for_installation=False),
                source_assets_changed=False,frozen_builds_changed=False,emulator_operations=False,
                runtime_verified=False,full_game_ui_coverage=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    result=build()
    raw=json.dumps(result,indent=2,ensure_ascii=True)+'\n'
    print(raw)
    if args.report:
        if args.report.exists():
            raise ValueError('Refuse report overwrite')
        args.report.write_text(raw,encoding='utf8')


if __name__=='__main__':
    main()
