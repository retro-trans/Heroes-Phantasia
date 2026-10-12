"""Scoped Special HUD label relocation. Dry-run unless a reviewed write is requested."""
import argparse
import copy
import json
import struct
from pathlib import Path
from PIL import Image, ImageDraw
from executable_text_patch import Elf, ORIGINAL, ORIGINAL_SHA, reference_index
from gallery_label_patch import sha, canonical
from png_tail_allocate import plan
from prepare_relocation_019 import coverage, section_load, pair_shapes
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from font_ram_plan import decode
from inspect_font_assets import unswizzle

SOURCE = Path('work/output/0.1.25-title-credit-vwf-4x-candidate/EBOOT.BIN')
SOURCE_SHA = '17cdb7435ed0a2abdf04fcc453140e6e6cda06b2021e74a4ca527ee869763ccb'
METADATA = Path('work/output/0.1.24-gallery-assets/executable.en.json')
SLOT, SOURCE_RVA, ORDINAL = 0x94838, 0x94cd2, 13519
TARGET = 'Special'


def model_label(data, metadata, text, advances):
    packed = data[metadata['font_compressed_file_offset']:metadata['font_compressed_file_offset']+metadata['font_compressed_bytes']]
    bank = decode(packed, metadata['high_bank_bytes'])
    if sha(bank) != metadata['high_bank_sha256']:
        raise ValueError('Inherited 4x font bank differs')
    canvas = Image.new('RGBA', (128,16))
    cursor = 25
    for char in text:
        off = metadata['high_glyph_offsets'][str(ord(char))]
        glyph = unswizzle(bank[off:off+2048],32,64)
        alpha = bytes(v for byte in glyph for v in ((byte&15)*17,(byte>>4)*17))
        mask = Image.frombytes('L',(64,64),alpha).resize((16,16),Image.Resampling.BILINEAR)
        canvas.paste((0,0,0,255),(cursor,0,cursor+16,16),mask)
        cursor += int(advances[ord(char)])
    return canvas


def build():
    incoming = SOURCE.read_bytes()
    original_bytes = ORIGINAL.read_bytes()
    rawmeta = METADATA.read_bytes()
    before = json.loads(rawmeta)
    if sha(incoming) != SOURCE_SHA or before['output_elf_sha256'] != SOURCE_SHA or sha(original_bytes) != ORIGINAL_SHA:
        raise ValueError('Reviewed input identity changed')
    elf, original = Elf(incoming), Elf(original_bytes)
    source = '必殺技'.encode('cp932')+b'\0'
    off = original.file_offset(SOURCE_RVA,len(source))
    if off != 0x94d92 or original_bytes[off:off+len(source)] != source:
        raise ValueError('Original label source changed')
    references,_ = reference_index(original)
    refs = [r for r in references if r['address'] == SOURCE_RVA]
    if len(refs) != 1 or refs[0]['kind'] != 'R_MIPS_32' or refs[0]['sites'] != [SLOT] or refs[0]['relocation_ordinals'] != [ORDINAL]:
        raise ValueError('Original label has unexpected/interior owners')
    if elf.word(SLOT) != SOURCE_RVA or elf.relocs[ORDINAL] != (SLOT,2):
        raise ValueError('Current typed table0/index54 pointer changed')
    # This getter result is passed directly to 87C18; there is no intervening copy.
    words = {0xb54c8:0x00002825, 0xb54cc:0x0c000000|(0x877f4>>2),
        0xb54d0:0x34060036, 0xb54e0:0x00402825,
        0xb54e4:0x02e03025, 0xb54ec:0x00004825, 0xb54f0:0x340a000d,
        0xb54f8:0x0c000000|(0x87c18>>2), 0xb54fc:0xafa30000,
        0xb53a0:0x26f50128, 0xb53e8:0x26f70141, 0xb5410:0x2a240009}
    for address, expected in words.items():
        if elf.word(address) != expected:
            raise ValueError('Scoped battle caller/widget geometry changed at '+hex(address))
    start,end = 0xb539c,0xb5508
    native = incoming[elf.file_offset(start):elf.file_offset(end)]
    if native != original_bytes[original.file_offset(start):original.file_offset(end)]:
        raise ValueError('Scoped battle caller differs from original')
    oldfont = authoritative_font_metadata(incoming,before)
    oldpng = validate_native_png_metadata(incoming,before)
    lutoff = elf.file_offset(before['float_width_lut_rva'],524)
    advances = struct.unpack('<131f',incoming[lutoff:lutoff+524])
    # The actual generic ASCII cursor adds the LUT advance directly; it does
    # not multiply by nominal Japanese width13/16 on this inherited renderer.
    cursor = incoming[elf.file_offset(0x2a90c0):elf.file_offset(0x2a9108)]
    if elf.word(0x87dc0) != 0x08000000|(0x2a90c0>>2) or elf.word(0x2a90f0) != 0x4600b580:
        raise ValueError('Inherited ASCII cursor route differs')
    full_width = sum(advances[ord(c)] for c in 'Special Move')
    label_width = sum(advances[ord(c)] for c in TARGET)
    if (full_width,label_width) != (86.,47.) or not label_width <= 55 < full_width:
        raise ValueError('Reviewed full/abbreviated width decision changed')
    reservation = plan(before,[dict(name='battle_hud_Special',data=TARGET.encode('ascii')+b'\0',alignment=4)])
    placement = reservation['patches'][0]
    if placement['rva'] != 2791048 or placement['bytes'] != 8 or reservation['remaining_bytes'] != 100:
        raise ValueError('Reviewed free-tail allocation changed')
    for active in before['additional_scopes']['tail_reservations']+before['native_tail_compaction']['chunks']:
        if placement['rva'] < active['rva']+active['bytes'] and active['rva'] < placement['rva']+8:
            raise ValueError('New label overlaps active code/font/data')
    p = elf.file_offset(placement['rva'],8)
    if p != placement['file_offset']:
        raise ValueError('Allocation file backing differs')
    output = bytearray(incoming)
    output[p:p+8] = placement['data']
    ptr = elf.file_offset(SLOT,4)
    struct.pack_into('<I',output,ptr,placement['rva'])
    allowed = set(range(p,p+8))|set(range(ptr,ptr+4))
    output = bytes(output)
    out = Elf(output)
    if len(output) != len(incoming) or out.ph != elf.ph or out.relocs != elf.relocs or pair_shapes(output) != pair_shapes(incoming):
        raise ValueError('Inherited load/relocation contracts changed')
    if any(a != b and i not in allowed for i,(a,b) in enumerate(zip(incoming,output))):
        raise ValueError('Unselected file bytes changed')
    coverage(output)
    models = []
    for base in (0x08804000,0x08900000,0x08fff000):
        old,_,_,_ = section_load(incoming,base)
        new,visited,skipped,_ = section_load(output,base)
        mask = set(range(placement['rva'],placement['rva']+8))|set(range(SLOT,SLOT+4))
        if skipped or len(visited) != len(elf.relocs) or old[1:] != new[1:] or any(a != b and i not in mask for i,(a,b) in enumerate(zip(old[0],new[0]))):
            raise ValueError('Unselected section-loaded memory differs')
        if struct.unpack_from('<I',new[0],SLOT)[0] != base+placement['rva']:
            raise ValueError('Section-loaded label pointer differs')
        models.append(dict(base=base,relocations=len(visited),selected_pointer_exact=True,unselected_loaded_memory_exact=True))
    for entry in before['gallery_current_entries']:
        raw = entry['target'].encode('ascii')+b'\0'
        q = out.file_offset(entry['target_rva'],len(raw))
        if out.word(entry['pointer_slot']) != entry['target_rva'] or output[q:q+len(raw)] != raw:
            raise ValueError('Inherited gallery label differs')
    report = copy.deepcopy(before)
    report.update(version='0.1.26',input_version='0.1.25',input_sha256=SOURCE_SHA,
        output_elf_sha256=sha(output),output_sha256=sha(output),elf_bytes=len(output),
        status='pure_battle_special_label_candidate_runtime_unverified',runtime_verified=False)
    for key in ('output','approved_dry_plan_sha256','written_readback_verified'):
        report.pop(key,None)
    report['trailer_recovery']['free_tail_regions'] = reservation['free_tail_regions']
    report['trailer_recovery']['remaining_tail_bytes'] = reservation['remaining_bytes']
    allocation = {k:v for k,v in placement.items() if k != 'data'}
    report['additional_scopes']['tail_reservations'].append(allocation)
    proof = dict(id='battle_hud_special_move',source_file_offset=off,source_rva=SOURCE_RVA,
        pointer_slot_rva=SLOT,relocation_ordinal=ORDINAL,native_table=0,native_index=54,
        canonical_target='Special Move',displayed_target=TARGET,abbreviation_reason='Full label86px exceeds the native55px text region; Special47px fits.',
        input_metadata_sha256=sha(rawmeta),allocation=allocation,payload_bytes=8,
        loaded_growth_bytes=0,new_relocations=0,remaining_tail_bytes=100,
        native_widget_width=80,native_text_offset_x=25,native_text_region_width=55,
        full_target_native_advance=full_width,displayed_native_advance=label_width,
        native_height=16,native_Japanese_advance=13,ASCII_advance_policy='Unscaled float LUT',
        native_caller=dict(start=start,end=end,sha256=sha(native),getter_site=0xb54cc,draw_site=0xb54f8,local_text_copy=False),
        ASCII_cursor_sha256=sha(cursor),all_nonselected_file_bytes_exact=True,
        all_native_caller_instructions_exact=True,all_relocation_records_exact=True,
        inherited_gallery_labels_exact=25,three_base_actual_SHT_models=models,
        native_display_verified=False,model_only_layout_review=True,
        scope='Only table0/index54 battle HUD label. Other special-move descriptions and contexts are outside this patch.')
    report['battle_special_label_proposal'] = proof
    newfont = authoritative_font_metadata(output,report)
    if {k:v for k,v in newfont.items() if k != 'additional_scopes'} != {k:v for k,v in oldfont.items() if k != 'additional_scopes'}:
        raise ValueError('Authoritative font contract changed')
    if validate_native_png_metadata(output,report) != oldpng:
        raise ValueError('Native PNG triples changed')
    label = model_label(incoming,before,TARGET,advances)
    full = model_label(incoming,before,'Special Move',advances)
    proof['label_font_model_ink_bounds'] = list(label.getbbox())
    if label.getbbox()[2] > 80:
        raise ValueError('Actual inherited glyph model overflows widget')
    proof['font_bank_and_hooks_exact'] = True
    proof['native_PNG_full_triples_exact'] = True
    return output,report,label,full


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write-review',type=Path)
    p.add_argument('--write-assets',type=Path)
    p.add_argument('--approved-plan-sha256')
    a = p.parse_args()
    data,report,label,full = build()
    digest = canonical(report)
    print(json.dumps(dict(version=report['version'],elf_sha256=sha(data),canonical_plan_sha256=digest,
        **report['battle_special_label_proposal']),indent=2))
    if a.write_review and a.write_assets:
        raise ValueError('Review and executable writing are separate operations')
    if a.write_review:
        dest = a.write_review.resolve()
        if dest.exists() or not dest.is_relative_to(Path('work/ui').resolve()):
            raise ValueError('Fresh review directory inside work/ui required')
        dest.mkdir(parents=True)
        sheet = Image.new('RGB',(440,110),'#ddd9be')
        draw = ImageDraw.Draw(sheet)
        draw.text((8,5),'Inherited font model only; not a native battle capture.',fill='black')
        for y,text,im in [(27,'Full term (overflows):',full),(64,'HUD abbreviation:',label)]:
            draw.text((8,y),text,fill='black')
            panel = Image.new('RGB',(128,16),'#fff4be')
            panel.paste(im,(0,0),im.getchannel('A'))
            panel = panel.resize((256,32),Image.Resampling.NEAREST)
            sheet.paste(panel,(176,y-5))
            draw.line((176+160,y-5,176+160,y+26),fill='red',width=1)
        sheet.save(dest/'font_model.png')
        (dest/'proposal.en.json').write_text(json.dumps(report['battle_special_label_proposal'],indent=2)+'\n',encoding='utf-8')
    elif a.write_assets:
        if a.approved_plan_sha256 != digest:
            raise ValueError('Executable differs from reviewed canonical plan')
        dest = a.write_assets.resolve()
        if dest.exists() or not dest.is_relative_to(Path('work/output').resolve()):
            raise ValueError('Fresh executable preparation directory required')
        dest.mkdir(parents=True)
        (dest/'EBOOT.BIN').write_bytes(data)
        if sha((dest/'EBOOT.BIN').read_bytes()) != report['output_elf_sha256']:
            raise ValueError('Executable write/readback differs')
        report.update(status='written_battle_special_label_candidate_runtime_unverified',
            approved_dry_plan_sha256=digest,written_readback_verified=True,output=str(dest/'EBOOT.BIN'))
        (dest/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    else:
        print('DRY RUN: no executable assets or review files written.')


if __name__ == '__main__':
    main()
