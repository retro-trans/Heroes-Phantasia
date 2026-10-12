"""Build a fresh local ISO with an automatically versioned title credit.

Preview is the default. --write saves a fresh versioned build, texture previews
and a manifest. Use --base-manifest to inherit a verified candidate's contents.
Optional executable/archive inputs support subsequent translation/font work.
"""
import argparse
import copy
import hashlib
import json
import pathlib
import shutil
import struct

from append_cpk import plan, sha, verify_original_span
from build_menu_patch import ISO, SOURCE_SHA as RESIDENT_SNAPSHOT_SHA, align, record_for
from inspect_iso import inventory as iso_inventory
from unpack_cpk import inventory as cpk_inventory
from title_stamp import prepare, RESOURCE, version_tuple

ISO_SHA = '2c3583f377cdaa9132d349a0039d7f6ffe21cac093476c7746705e8af2b03b40'
DEFAULT_BASE = pathlib.Path('work/output/0.1.7-gallery-vwf-4x-candidate/manifest.en.json')

def prepare_psp_metadata(config):
    """Produce reviewed shell PNGs independently of loaded ELF PNG tails."""
    if not config.get('english_psp_metadata', False):
        return {}, None
    from encode_psp_bitmap_proposal import prepare as prepare_pngs
    candidates, report = prepare_pngs()
    expected = {
        'PSP_GAME/PIC0.PNG': 'efbb190070a2ef843cb7044b4ed14e17711af595137f743b5a24d2b2c3a3332b',
        'PSP_GAME/ICON0.PNG': 'b2bc258a1bef7cb13f5a1db4e9b6a30522a6b0c822dc82ffcbfc05d2435f72a0',
        'PSP_GAME/INSDIR/ICON0.PNG': '6eae74e444b888d40efd6cf75bf9a762f514bc47b55ec803b5ddc829513c487c',
    }
    if set(candidates) != set(expected) or len(report['entries']) != 3:
        raise ValueError('PSP PNG selection differs from reviewed proposal')
    with ISO.open('rb') as stream:
        for entry in report['entries']:
            name = entry['iso_path']; data = candidates[name]
            _, extent, length = record_for(ISO, name)
            stream.seek(extent * 2048); original = stream.read(length)
            if (hashlib.sha256(data).hexdigest() != expected[name] or
                    entry['candidate_sha256'] != expected[name] or
                    len(data) != entry['candidate_bytes'] or
                    hashlib.sha256(original).hexdigest() != entry['source_sha256'] or
                    original != pathlib.Path(entry['source_path']).read_bytes() or
                    not entry['outside_regions_pixel_exact'] or
                    not entry['all_non_idat_chunks_byte_exact'] or
                    entry['elf_png_tail_allocation'] or entry['cpk_resource']):
                raise ValueError('PSP PNG source/candidate contract differs: ' + name)
    report['preparation_code_sha256'] = {
        name: sha(pathlib.Path('tools') / name) for name in
        ('encode_psp_bitmap_proposal.py', 'prepare_psp_bitmap_proposal.py')}
    return candidates, report

def verify_resident_cpl_names(executable, report, cpl_report):
    """Match restored original CPL resources to the exact executable HUD map."""
    from cpl_resident_names import build_table, hud_lookup
    from live_vwf import j
    from build_menu_patch import relocate_code
    if cpl_report.get('name0_storage') != 'resident_hud_lookup':
        return
    metadata = report.get('resident_cpl_names', {})
    if (metadata.get('rows') != 79 or metadata.get('resources') != 424 or
            metadata.get('original_fallback') is not True or
            metadata.get('target_sha256') != cpl_report['resident_name_targets_sha256'] or
            cpl_report.get('name0_translations_installed_in_archive') != 0 or
            not all(a.get('all_original_bytes_restored') is True and
                    a['rebuilt_sha256'] == a['original_sha256'] for a in cpl_report['assets'])):
        raise ValueError('Restored CPL resources require the matching current executable name map')
    data = executable.read_bytes()
    phoff = struct.unpack_from('<I', data, 28)[0]
    programs = [struct.unpack_from('<8I', data, phoff + n * 32)
                for n in range(struct.unpack_from('<H', data, 44)[0])]
    def span(rva, size):
        if type(rva) != int or type(size) != int or size <= 0:
            raise ValueError('Resident CPL coordinates must be explicit and nonempty')
        matches = [p for p in programs if p[0] == 1 and p[2] <= rva and rva + size <= p[2] + p[4]]
        if len(matches) != 1:
            raise ValueError('Resident CPL map/hook outside a unique loaded span')
        p = matches[0]; offset = p[1] + rva - p[2]
        return data[offset:offset + size]
    table, _, _ = build_table()
    if type(metadata.get('table_rva')) != int:
        raise ValueError('Resident CPL table RVA missing')
    helper = bytearray(hud_lookup(metadata['table_rva']))
    relocate_code(helper, 0, len(helper))
    helper = bytes(helper)
    for name, expected in (('table', table), ('helper', helper)):
        if (metadata.get(name + '_bytes') != len(expected) or
                metadata.get(name + '_sha256') != hashlib.sha256(expected).hexdigest() or
                span(metadata.get(name + '_rva'), len(expected)) != expected):
            raise ValueError('Current executable CPL ' + name + ' differs from the reviewed generator')
    if (metadata.get('hook_site') != 0xb06c4 or
            span(0xb06c4, 8) != struct.pack('<II', j(metadata['helper_rva']), 0)):
        raise ValueError('Resident CPL HUD hook bytes differ')

FONT_FIELDS=('high_bank','high_bank_bytes','high_glyph_count','high_codes',
             'high_glyph_offsets','high_lookup_entry_bytes','high_lookup_unit',
             'font_input_sha256','font_asset_sha256','high_bank_sha256')

def authoritative_font_metadata(executable,report):
    """Require proof-backed current font coordinates after payload compaction."""
    if report.get('font_runtime_storage')in('owned_vram_lz4_v1','owned_vram_lz4_trailer_v1'):
        return compressed_font_metadata(executable,report)
    if 'font_runtime_storage'in report or report.get('high_bank_address_kind')=='compressed_source_rva_not_texture':
        raise ValueError('Unknown/inconsistent runtime font storage model')
    if 'memory_compaction' not in report:return {}
    if any(key not in report for key in FONT_FIELDS):
        raise ValueError('Compact executable requires complete authoritative font metadata')
    comp=report['memory_compaction'];bank=report['high_bank'];size=report['high_bank_bytes']
    removed=[int(x,16) for x in comp['removed_range']]
    if type(bank)!=int or type(size)!=int or bank!=removed[0] or size<=0:
        raise ValueError('Compact font bank is stale or does not match the proven shifted address')
    if removed[1]-removed[0]!=comp['removed_bytes']:
        raise ValueError('Compaction removal range disagrees')
    data=executable.read_bytes() if isinstance(executable,pathlib.Path) else executable
    phoff=struct.unpack_from('<I',data,28)[0]
    ph=list(struct.unpack_from('<8I',data,phoff+64))
    if ph[0]!=1 or not ph[2]<=bank or bank+size>ph[2]+ph[4]:
        raise ValueError('Compact bank lies outside its loaded payload')
    raw=data[ph[1]+bank-ph[2]:ph[1]+bank-ph[2]+size]
    if hashlib.sha256(raw).hexdigest()!=report['high_bank_sha256']:
        raise ValueError('Compact high-bank bytes differ from preparation proof')
    if (report['high_lookup_entry_bytes']!=2 or report['high_lookup_unit']!=256 or
            report['high_codes']!=list(range(32,127))+[128] or report['high_glyph_count']!=96):
        raise ValueError('Compact Latin repertoire/lookup format changed')
    lookup=struct.unpack_from('<129H',data,ph[1]+0x600)
    for code in report['high_codes']:
        offset=report['high_glyph_offsets'][str(code)]
        if offset%256 or not 0<=offset<=size-2048 or lookup[code]*256!=offset:
            raise ValueError('Compact glyph offset is stale or invalid')
    for key in ('font_input_sha256','font_asset_sha256','high_bank_sha256'):
        value=report[key]
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Compact font source/hash metadata missing')
    if report['font_input_sha256']!=RESIDENT_SNAPSHOT_SHA:
        raise ValueError('Compact font snapshot source differs from the verified resident source')
    return {key:copy.deepcopy(report[key]) for key in FONT_FIELDS}


def compressed_font_metadata(executable,report):
    """Explicit98-glyph model; compressed ELF source is not a texture pointer."""
    from font_ram_plan import decode
    from private_latin import GLYPH_CODES
    from build_menu_patch import START
    trailer=report.get('font_runtime_storage')=='owned_vram_lz4_trailer_v1'
    native_tail=report.get('native_tail_compaction')
    extra=('font_runtime_storage','high_bank_address_kind','font_compressed_bytes',
           'font_compressed_sha256','font_runtime_state_rva','font_codec_model',
           'high_lookup_rva','font_raster_sha256','font_hooks')
    if trailer:extra+=('font_trailer_offset','font_compressed_file_offset','font_scratch_bytes','font_compressed_crc32','font_hooks_extra','font_descriptor_rva')
    if native_tail:extra+=('font_legacy_initializer_rva','native_tail_compaction','body_integer_lut_rva','body_integer_lut_sha256','float_width_lut_rva')
    if any(k not in report for k in FONT_FIELDS+extra):
        raise ValueError('Compressed font requires complete authoritative metadata')
    if (report['high_bank_address_kind']!=('unloaded_elf_file_offset'if trailer else 'compressed_source_rva_not_texture') or
        report['font_codec_model']!='cp932-pua-f040-f041-v1' or
        report['high_codes']!=GLYPH_CODES or report['high_glyph_count']!=98 or
        report['high_bank_bytes']!=193024 or
        report['high_lookup_entry_bytes']!=2 or report['high_lookup_unit']!=256):
        raise ValueError('Compressed font model/repertoire differs from reviewed98-glyph candidate')
    variant=report.get('font_compression_variant','lz4_last_match_v1')
    reviewed_packets={
        'lz4_last_match_v1':(24790,'21d08968464718013f66604c2798af2b765a1576e62da50118dc884e113dc00e'),
        'lz4_hc1024_v1':(20268,'808b5e9dd52d9822fd2fca9212003378b7f344a848c81cc12913a0feb9e80086')}
    if variant not in reviewed_packets or (report['font_compressed_bytes'],report['font_compressed_sha256'])!=reviewed_packets[variant]:
        raise ValueError('Compressed packet variant/size/hash differs from exact reviewed model')
    if trailer and report['high_bank']is not None:raise ValueError('Trailer model must not publish a loaded font-source RVA')
    for key in (('font_runtime_state_rva','high_lookup_rva')if trailer else ('high_bank','font_runtime_state_rva','high_lookup_rva')):
        if type(report[key])!=int:raise ValueError('Font coordinates must be explicit integer RVAs')
    data=executable.read_bytes() if isinstance(executable,pathlib.Path) else executable
    phoff=struct.unpack_from('<I',data,28)[0];ph=list(struct.unpack_from('<8I',data,phoff+64))
    programs=[struct.unpack_from('<8I',data,phoff+n*32)for n in range(struct.unpack_from('<H',data,44)[0])]
    if native_tail:
        extension=report.get('font_native_tail_loaded_extension_bytes',0)
        if not trailer or ph[4]!=extension or ph[5]!=extension or not native_tail.get('all_active_relative_edges_preserved'):
            raise ValueError('Native-tail font requires explicit reviewed LOAD2 extent/trailer model')
        if extension:
            raw=data[ph[1]:ph[1]+extension]
            if not report.get('additional_scopes') or hashlib.sha256(raw).hexdigest()!=report.get('font_native_tail_loaded_extension_sha256'):
                raise ValueError('Native-tail additional loaded scope extent/hash differs')
        for chunk in native_tail['chunks']:
            raw=data[chunk['file_offset']:chunk['file_offset']+chunk['bytes']]
            if hashlib.sha256(raw).hexdigest()!=chunk['output_sha256']:
                raise ValueError('Native-tail hook chunk differs from preparation proof')
    def span(rva,size):
        allowed=programs[:1] if native_tail else [ph]
        matches=[p for p in allowed if p[0]==1 and p[2]<=rva and rva+size<=p[2]+p[4]]
        if len(matches)!=1:raise ValueError('Font source/state/lookup outside reviewed loaded span')
        if native_tail and not any(c['rva']<=rva and rva+size<=c['rva']+c['bytes'] for c in native_tail['chunks']):
            raise ValueError('Font hook lies outside verified native-tail chunks')
        p=matches[0];off=p[1]+rva-p[2];return data[off:off+size]
    if trailer:
        from font_trailer_hooks import MAGIC
        offset=report['font_trailer_offset'];source=report['font_compressed_file_offset'];size=report['font_compressed_bytes']
        if type(offset)!=int or offset%16 or source!=offset+16 or offset+16+size>len(data):raise ValueError('Trailer exact file bounds differ')
        if data[offset:offset+16]!=MAGIC+struct.pack('<II',size,report['high_bank_bytes']):raise ValueError('Trailer header differs')
        programs=[struct.unpack_from('<8I',data,phoff+n*32)for n in range(struct.unpack_from('<H',data,44)[0])]
        shoff=struct.unpack_from('<I',data,32)[0];sections=[struct.unpack_from('<10I',data,shoff+n*40)for n in range(struct.unpack_from('<H',data,48)[0])]
        def overlap(start,size):return size>0 and start<source+size_packet and offset<start+size
        size_packet=size
        if any(overlap(p[1],p[4])for p in programs)or any(s[1]!=8 and overlap(s[4],s[5])for s in sections)or overlap(shoff,len(sections)*40)or overlap(phoff,len(programs)*32):raise ValueError('Trailer overlaps declared ELF spans')
        if report['font_scratch_bytes']!=20272:raise ValueError('Trailer scratch bound differs')
        packed=data[source:source+size]
        descriptor=report['font_descriptor_rva']
        first=programs[0]
        if type(descriptor)!=int or not first[2]<=descriptor or descriptor+328*12>first[2]+first[4]:raise ValueError('Trailer descriptor outside native LOAD0')
        legacy=report['font_legacy_initializer_rva']if native_tail else START+0x500
        hi,lo=struct.unpack('<2I',span(legacy+0x2c,8))
        actual=((hi&65535)<<16)+struct.unpack('<h',struct.pack('<H',lo&65535))[0]
        if hi>>26!=15 or lo>>26!=9 or actual!=descriptor:raise ValueError('Trailer descriptor metadata/pointer differs')
    else:packed=span(report['high_bank'],report['font_compressed_bytes'])
    if hashlib.sha256(packed).hexdigest()!=report['font_compressed_sha256']:
        raise ValueError('Compressed bank differs from preparation proof')
    bank=decode(packed,report['high_bank_bytes'])
    if hashlib.sha256(bank).hexdigest()!=report['high_bank_sha256']:
        raise ValueError('Decoded bank differs from preparation proof')
    if span(report['font_runtime_state_rva'],8)!=bytes(8):raise ValueError('Owned font state must be initially unpublished')
    if native_tail:
        lut=span(report['body_integer_lut_rva'],524)
        if report['body_integer_lut_sha256']!='72506aefb9b2d208812e15132fc3a3bca8d4ced8c58468b9364a8f1b52200a43' or hashlib.sha256(lut).hexdigest()!=report['body_integer_lut_sha256']:
            raise ValueError('Current body-width LUT differs from reviewed model')
        span(report['float_width_lut_rva'],524)
    if report['font_runtime_state_rva']%16:raise ValueError('Owned font state is unaligned')
    from font_vram_hooks import initialize,uploader,decompress
    from build_menu_patch import START
    hooks=report['font_hooks']
    if not isinstance(hooks,dict)or any(type(hooks.get(k))!=int for k in ('initializer','decompressor','uploader')):
        raise ValueError('Compressed font core hooks missing')
    if trailer:
        import zlib
        from font_trailer_hooks import initialize as trailer_initialize,checksum
        crc=report['font_hooks_extra'].get('checksum')
        if type(crc)!=int or report['font_compressed_crc32']!=zlib.crc32(packed):raise ValueError('Trailer checksum coordinate/value differs')
        if span(crc,len(checksum()))!=checksum():raise ValueError('Trailer checksum code differs')
        path=crc+((len(checksum())+15)&~15)
        expected_path=b'disc0:/PSP_GAME/SYSDIR/EBOOT.BIN\0'
        if span(path,len(expected_path))!=expected_path:raise ValueError('Trailer EBOOT path differs')
        code,_,_=trailer_initialize(legacy,report['font_runtime_state_rva'],path,offset,len(packed),len(bank),hooks['decompressor'],crc,zlib.crc32(packed))
    else:code,_=initialize(START+0x500,report['font_runtime_state_rva'],report['high_bank'],len(packed),len(bank),hooks['decompressor'])
    if span(hooks['initializer'],len(code))!=code:raise ValueError('Owned font initializer/state/source metadata stale')
    code,_=uploader(report['font_runtime_state_rva'],report['high_lookup_rva'])
    if span(hooks['uploader'],len(code))!=code:raise ValueError('Owned font uploader/state/lookup metadata stale')
    code=decompress()
    if span(hooks['decompressor'],len(code))!=code:raise ValueError('Bounded decoder bytes differ')
    lookup=struct.unpack('<131H',span(report['high_lookup_rva'],262))
    for code in GLYPH_CODES:
        offset=report['high_glyph_offsets'][str(code)]
        if type(offset)!=int or offset%256 or not 0<=offset<=len(bank)-2048 or lookup[code]*256!=offset:
            raise ValueError('Compressed glyph lookup/offset differs')
    for code in set(range(131))-set(GLYPH_CODES):
        if lookup[code]!=65535:raise ValueError('Unapproved glyph lookup enabled')
    for key in ('font_input_sha256','font_asset_sha256','high_bank_sha256','font_compressed_sha256','font_raster_sha256'):
        value=report[key]
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ValueError('Font hash metadata invalid')
    if report['font_input_sha256']!=RESIDENT_SNAPSHOT_SHA:raise ValueError('Font resident source changed')
    if (report['high_bank_sha256']!='8c1e561b7279796514a1345bd9c9838e285f7c19cb1677004efc71c5a2dfa192' or
        report['font_raster_sha256']!='d8e6f7c5a1356d41dd82b0c00219febd21c791cc5cd1ecf8a0323cbeafe6496c'):
        raise ValueError('Compressed bank/raster differs from reviewed exact candidate')
    extension_fields={k:copy.deepcopy(report[k])for k in ('font_native_tail_loaded_extension_bytes','font_native_tail_loaded_extension_sha256','additional_scopes')if native_tail and k in report}
    return {**{key:copy.deepcopy(report[key]) for key in FONT_FIELDS+extra},'font_compression_variant':variant,**extension_fields}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=pathlib.Path, default=pathlib.Path('build.json'))
    parser.add_argument('--base-manifest', type=pathlib.Path, default=DEFAULT_BASE)
    parser.add_argument('--executable', type=pathlib.Path)
    parser.add_argument('--archive', type=pathlib.Path)
    parser.add_argument('--executable-report', type=pathlib.Path, help='Verified metadata from the executable preparation tool')
    parser.add_argument('--dialogue-report', type=pathlib.Path, help='Verified rebuilt dialogue resource metadata')
    parser.add_argument('--translation-archive-report', type=pathlib.Path, help='Verified metadata for the indexed dialogue archive')
    parser.add_argument('--prologue-movie', type=pathlib.Path, help='Reviewed standalone English HPMOVE03.PMF')
    parser.add_argument('--prologue-proof', type=pathlib.Path, help='Standalone movie write/readback proof')
    parser.add_argument('--prologue-proof-sha256', help='Expected reviewed standalone proof SHA256')
    parser.add_argument('--prologue-movie-sha256', help='Expected reviewed movie SHA256')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--preview-only', action='store_true', help='With --write, save texture previews only; no ISO')
    args = parser.parse_args()
    prologue_args = (args.prologue_movie,args.prologue_proof,args.prologue_proof_sha256,args.prologue_movie_sha256)
    if any(x is not None for x in prologue_args) and not all(x is not None for x in prologue_args):
        raise ValueError('All four --prologue-* arguments are required together')
    config = json.loads(args.config.read_text(encoding='utf-8'))
    title, stamp, original_image, preview = prepare(config)
    version = config['version']
    base = json.loads(args.base_manifest.read_text(encoding='utf-8'))
    if version_tuple(version) <= version_tuple(base['version']):
        raise ValueError('Every new build must increment the base build version')
    root = pathlib.Path('work/output') / (version + '-title-credit-vwf-4x-candidate')
    ui = pathlib.Path('work/ui/title') / version
    if root.exists():
        raise ValueError('This version already has a build; increment build.json before building again')
    for previous in pathlib.Path('work/output').glob('*/manifest.en.json'):
        old = json.loads(previous.read_text(encoding='utf-8'))
        if old.get('iso_path') and version_tuple(version) <= version_tuple(old['version']):
            raise ValueError('Version must be newer than every existing local ISO build: ' + str(previous))
    if args.preview_only:
        print(json.dumps(stamp, indent=2))
        if args.write:
            if ui.exists():
                raise ValueError('Preview output must be fresh')
            ui.mkdir(parents=True)
            original_image.save(ui / 'original_background.png'); preview.save(ui / 'preview_background.png')
            (ui / 'stamp.en.json').write_text(json.dumps(stamp, indent=2) + '\n', encoding='utf-8')
            print('Saved background-only preview; no game build created.')
        else:
            print('DRY RUN: no preview files written.')
        return
    executable = args.executable or args.base_manifest.parent / 'EBOOT.BIN'
    cpk = args.archive or pathlib.Path(next(x['source'] for x in base['iso_replacements'] if x['path'].endswith('/HP.CPK')))
    exe_sha, cpk_sha = sha(executable), sha(cpk)
    executable_report = None
    if args.executable:
        if not args.executable_report:
            raise ValueError('A new executable requires its preparation report')
        executable_report = json.loads(args.executable_report.read_text(encoding='utf-8'))
        if executable_report['version'] != version or executable_report['output_elf_sha256'] != exe_sha or executable_report['elf_bytes'] != executable.stat().st_size:
            raise ValueError('Executable report does not match this version/input')
    dialogue_report = None
    if args.dialogue_report:
        dialogue_report = json.loads(args.dialogue_report.read_text(encoding='utf-8'))
        _, current_entries = cpk_inventory(cpk)
        entry = next(e for e in current_entries if e['path'] == dialogue_report['resource'])
        with cpk.open('rb') as stream:
            stream.seek(entry['offset']); resource_data = stream.read(entry['stored_size'])
        if entry['compression'] != 'none' or hashlib.sha256(resource_data).hexdigest() != dialogue_report['sha256']:
            raise ValueError('Dialogue report does not match archive resource')
    archive_report = None
    combined_archive_report = None
    if args.translation_archive_report:
        archive_report = json.loads(args.translation_archive_report.read_text(encoding='utf-8'))
        if archive_report.get('status') == 'written_combined_structural_candidate_runtime_unverified':
            combined_archive_report = archive_report
            if (archive_report['version'] != version or archive_report['blocked'] or
                    archive_report['output_archive_sha256'] != cpk_sha or
                    archive_report['archive_plan']['output_bytes'] != cpk.stat().st_size or
                    not archive_report['all_current_nonselected_bytes_verified'] or
                    not archive_report['all_written_replacement_extractions_verified'] or
                    archive_report['indexed']['structural_failures'] or
                    archive_report['indexed']['encoding_blocked_assets'] or
                    archive_report['indexed']['untranslated_unique_rows'] or
                    archive_report['extended']['failures']):
                raise ValueError('Combined translation archive proof differs from input/version')
            selected = (archive_report['indexed']['assets'] + archive_report['extended']['assets'] +
                        archive_report.get('cpl',{}).get('assets',[]))
            verify_resident_cpl_names(executable, executable_report or base.get('setup_patch', {}),
                                      archive_report.get('cpl', {}))
            copyright_report = archive_report.get('copyright_ui')
            if copyright_report:
                if (copyright_report['candidate_sha256'] != 'ced5886c165adf0cdc83af0d8beda5827b4d68e12bc0f80b06cdfc84ea7ffe24' or
                        copyright_report['semantic_records'] != 14 or
                        [x['section'] for x in copyright_report['sections']] != [1,6] or
                        not copyright_report['all_other_bytes_preserved']):
                    raise ValueError('Copyright texture proof differs from reviewed proposal')
                selected.append(dict(resource=copyright_report['resource'],
                    rebuilt_bytes=copyright_report['bytes'],
                    rebuilt_sha256=copyright_report['candidate_sha256']))
            battle_report = combined_archive_report.get('battle_bitmap_ui')
            if battle_report:
                if (battle_report['proposed_resource_sha256'] != '9a8abe108472aba62e9e52f7e0866b86c72ad346e7567e1297f58b411a2e1dad' or
                        battle_report['whole_label_count'] != 20 or battle_report['fragment_label_count'] != 3 or
                        not battle_report['all_nonpixel_bytes_exact'] or not battle_report['unselected_main_pixels_exact']):
                    raise ValueError('Battle bitmap proof differs from reviewed proposal')
                selected.append(dict(resource=battle_report['resource'],
                    rebuilt_bytes=battle_report['resource_bytes'],
                    rebuilt_sha256=battle_report['proposed_resource_sha256']))
            if (len(selected) != archive_report['resources_with_replacements'] or
                    len({asset['resource'] for asset in selected}) != len(selected)):
                raise ValueError('Combined asset counts/ownership differ')
            _, current_entries = cpk_inventory(cpk)
            by_path = {entry['path']: entry for entry in current_entries}
            with cpk.open('rb') as stream:
                for asset in selected:
                    entry = by_path[asset['resource']]
                    if (entry['compression'] != 'none' or
                            entry['stored_size'] != asset['rebuilt_bytes'] or
                            entry['extract_size'] != asset['rebuilt_bytes']):
                        raise ValueError('Combined replacement metadata differs: '+asset['resource'])
                    stream.seek(entry['offset'])
                    if hashlib.sha256(stream.read(entry['stored_size'])).hexdigest() != asset['rebuilt_sha256']:
                        raise ValueError('Combined replacement extraction differs: '+asset['resource'])
            # The indexed subreport keeps its own reference/row counts. This
            # local adapter supplies the already verified current archive proof
            # to the older indexed validation below without changing its file.
            archive_report = copy.deepcopy(combined_archive_report['indexed'])
            archive_report['status'] = 'written_structural_candidate_runtime_untested'
            archive_report['archive'] = dict(output_sha256=cpk_sha,output_bytes=cpk.stat().st_size,
                inventory_and_extraction_verified=True,all_unselected_original_bytes_verified=True)
        archive_meta = archive_report['archive']
        if (archive_report['version'] != version or
                archive_report['status'] != 'written_structural_candidate_runtime_untested' or
                archive_meta['output_sha256'] != cpk_sha or
                archive_meta['output_bytes'] != cpk.stat().st_size or
                archive_report['structural_failures'] or archive_report['encoding_blocked_assets'] or
                not archive_meta['inventory_and_extraction_verified'] or
                not archive_meta['all_unselected_original_bytes_verified']):
            raise ValueError('Translation archive report does not match the input archive/version')
        _, current_entries = cpk_inventory(cpk)
        by_path = {entry['path']: entry for entry in current_entries}
        rebuilt = [asset for asset in archive_report['assets']
                   if asset['status'] == 'structurally_rebuilt_runtime_untested']
        if (len(rebuilt) != archive_report['resources_with_replacements'] or
                len({asset['resource'] for asset in rebuilt}) != len(rebuilt) or
                sum(asset['translated_references'] for asset in rebuilt) !=
                archive_report['planned_references_including_shared_closure']):
            raise ValueError('Translation archive coverage totals disagree')
        with cpk.open('rb') as stream:
            for asset in rebuilt:
                entry = by_path[asset['resource']]
                if (entry['compression'] != 'none' or
                        entry['stored_size'] != asset['rebuilt_bytes'] or
                        entry['extract_size'] != asset['rebuilt_bytes']):
                    raise ValueError('Translation asset metadata differs: ' + asset['resource'])
                stream.seek(entry['offset'])
                if hashlib.sha256(stream.read(entry['stored_size'])).hexdigest() != asset['rebuilt_sha256']:
                    raise ValueError('Translation asset hash differs: ' + asset['resource'])
    if args.executable is None and exe_sha != base['output_elf_sha256']:
        raise ValueError('Inherited executable changed')
    if args.archive is None and cpk_sha != base['dialogue_cpk_sha256']:
        raise ValueError('Inherited archive changed')
    if sha(ISO) != ISO_SHA:
        raise ValueError('Original ISO changed')
    # Plan using an existing source-sized placeholder, then substitute the
    # reviewed generated bytes. All metadata depends only on its exact size.
    from title_stamp import SOURCE
    header, entries, patches, assets, cpk_end = plan(cpk, [(RESOURCE, SOURCE)], cpk_sha)
    asset = assets[0]
    if asset['bytes'] != len(title):
        raise ValueError('Title texture replacement must keep its original size')
    asset.update(data=title, sha256=stamp['output_sha256'], input=str(root / 'TitleMenu_Data.bin'))
    inputs = [('PSP_GAME/SYSDIR/EBOOT.BIN', executable, exe_sha, executable.stat().st_size),
              ('PSP_GAME/USRDIR/HP.CPK', root / 'HP.CPK', None, cpk_end)]
    prologue_coverage = None
    if args.prologue_movie:
        from movie_iso_input import validated_input
        movie_input, prologue_coverage = validated_input(*prologue_args)
        inputs.append(movie_input)
    psp_candidates, psp_report = prepare_psp_metadata(config)
    for name, data in psp_candidates.items():
        inputs.append((name, root / 'iso_assets' / name,
                       hashlib.sha256(data).hexdigest(), len(data)))
    iso_patches = {}; outputs = []; iso_end = ISO.stat().st_size
    for name, source, digest, length in inputs:
        offset = align(iso_end, 2048); iso_end = align(offset + length, 2048)
        rec = record_for(ISO, name)[0]
        iso_patches[rec + 2] = struct.pack('<I', offset // 2048) + struct.pack('>I', offset // 2048)
        iso_patches[rec + 10] = struct.pack('<I', length) + struct.pack('>I', length)
        outputs.append(dict(path=name, source=str(source), offset=offset, size=length, sha256=digest))
    iso_patches[16 * 2048 + 80] = struct.pack('<I', iso_end // 2048) + struct.pack('>I', iso_end // 2048)
    info = copy.deepcopy(base)
    # Every build starts from the original ISO, so inherited movie installation
    # does not carry over unless explicitly supplied and verified again.
    info.pop('prologue_movie_translation_coverage',None)
    if prologue_coverage:
        info['prologue_movie_translation_coverage'] = prologue_coverage
    if psp_report:
        info['psp_metadata_translation'] = psp_report
    for key in ['iso_path', 'iso_sha256', 'gallery_validation', 'gallery_display_qa_passed', 'runtime_verified_gallery_prose_rows', 'structural_validation', 'title_validation', 'setup_validation', 'opening_validation', 'battle_validation']:
        info.pop(key, None)
    if executable_report:
        for key in ['payload_bytes', 'module_growth_bytes']:
            if key in executable_report:
                info[key] = executable_report[key]
        info['module_growth_bytes'] = executable_report.get('module_growth_bytes', executable_report['payload_bytes'])
        info['added_relocations'] = base.get('added_relocations', 0) + executable_report.get('added_relocations', 0)
        info.update(authoritative_font_metadata(executable,executable_report))
        if 'total_relocations' in executable_report and 'original_relocations' in executable_report:
            info['added_relocations']=executable_report['total_relocations']-executable_report['original_relocations']
        info.update(executable_source_version=version, executable_preparation_report=str(args.executable_report),
                    setup_patch=executable_report, runtime_verified_setup=False)
    if dialogue_report:
        indices = dialogue_report.get('translated_row_indices')
        if indices is None:
            if dialogue_report['translated_references'] != dialogue_report['total_references']:
                raise ValueError('Partial dialogue report needs explicit row indices')
            indices = list(range(dialogue_report['total_references']))
        info.update(selected_dialogue_rows=indices, dialogue_preparation_report=str(args.dialogue_report),
                    selected_dialogue_resource=dialogue_report['resource'])
    if archive_report:
        for key in ['selected_dialogue_rows', 'selected_dialogue_resource', 'dialogue_preparation_report']:
            info.pop(key, None)
        info.update(translation_archive_preparation_report=str(args.translation_archive_report),
                    indexed_dialogue_coverage={key: archive_report[key] for key in
                        ['unique_rows', 'planned_unique_rows', 'untranslated_unique_rows',
                         'planned_references_including_shared_closure', 'untranslated_indexed_references',
                         'resources_with_replacements', 'by_category']},
                    translation_review_scope='Archive serialization installs drafts; independent meaning review and runtime proof have separate scopes.')
        if combined_archive_report:
            extended = combined_archive_report['extended']
            info['extended_translation_coverage'] = dict(
                gallery_resources=extended['gallery_resources'],gallery_unique_rows=extended['gallery_unique_rows'],
                table_unique_rows=extended['table_unique_rows'],table_occurrences=extended['table_occurrences'],
                glyph_labels_installed=combined_archive_report['glyph_labels_installed'],
                glyph_labels_blocked=combined_archive_report['glyph_labels_blocked'],runtime_verified=False)
            info['combined_archive_preservation'] = combined_archive_report['preservation']
            copyright_report = combined_archive_report.get('copyright_ui')
            if copyright_report:
                info['copyright_ui_translation_coverage'] = dict(
                    semantic_records=copyright_report['semantic_records'], textures=2,
                    resource=copyright_report['resource'],
                    candidate_sha256=copyright_report['candidate_sha256'],runtime_verified=False)
            if 'cpl' in combined_archive_report:
                cpl = combined_archive_report['cpl']
                info['cpl_translation_coverage'] = dict(resources=cpl['files'],
                    name0_unique=cpl['name0_unique'],name0_occurrences=cpl['name0_occurrences'],
                    name0_storage=cpl.get('name0_storage','appended_cpl_name_block'),
                    name0_translations_installed_in_archive=cpl.get('name0_translations_installed_in_archive',cpl['name0_unique']),
                    name0_translations_installed_in_executable=cpl['name0_unique'] if cpl.get('name0_storage')=='resident_hud_lookup' else 0,
                    later_labels_installed=cpl['later_labels_installed'],
                    later_labels_not_installed=cpl['later_labels_not_installed'],runtime_verified=False)
    info.update(version=version, status='title_credit_candidate_runtime_unverified',
                base_manifest=str(args.base_manifest), base_version=base['version'],
                config=copy.deepcopy(config), title_stamp=stamp,
                output_elf_sha256=exe_sha, elf_bytes=executable.stat().st_size,
                dialogue_cpk_sha256=None, dialogue_cpk_bytes=cpk_end,
                iso_bytes=iso_end, iso_replacements=outputs,
                inherited_validation_scope='Prior evidence refers to the base candidate. Every changed executable/resource and the title/menu require new runtime checks.',
                game_translation_complete=False, runtime_verified_title=False, runtime_verified_setup=False,
                runtime_verified_dialogue_rows_in_this_build=0)
    if stamp.get('title_logo_translation'):
        info['title_logo_translation_coverage'] = dict(unique_records=1, physical_occurrences=2,
            resource=RESOURCE, static_pixels_reviewed=True, runtime_verified=False)
    if combined_archive_report and combined_archive_report.get('battle_bitmap_ui'):
        info['battle_bitmap_translation_coverage'] = dict(resource='btl/sys_all.bin',
            whole_labels=20, fragment_headings=3, installed_in_archive=True,
            static_pixels_reviewed=True, runtime_verified=False)
    print(json.dumps(info, indent=2))
    if not args.write:
        print('DRY RUN: no archive, ISO or manifest written.')
        return
    if args.prologue_movie:
        refreshed_input, refreshed_coverage = validated_input(*prologue_args)
        if refreshed_input != movie_input or refreshed_coverage != prologue_coverage:
            raise ValueError('Movie input/proof changed after dry planning')
    root.mkdir(parents=True)
    for name, data in psp_candidates.items():
        target = root / 'iso_assets' / name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        if sha(target) != hashlib.sha256(data).hexdigest():
            raise ValueError('PSP PNG write/readback differs: ' + name)
    (root / 'TitleMenu_Data.bin').write_bytes(title)
    shutil.copyfile(executable, root / 'EBOOT.BIN')
    dest_cpk = root / 'HP.CPK'; shutil.copyfile(cpk, dest_cpk)
    with dest_cpk.open('r+b') as stream:
        for off, value in patches.items():
            stream.seek(off); stream.write(value)
        stream.seek(0, 2); stream.write(bytes(asset['offset'] - stream.tell())); stream.write(title)
        stream.write(bytes((-stream.tell()) % 2048))
    verify_original_span(cpk, dest_cpk, patches)
    h2, e2 = cpk_inventory(dest_cpk)
    if h2 != dict(header, ContentSize=cpk_end - header['ContentOffset']) or len(entries) != len(e2):
        raise ValueError('Written CPK header/entry count differs')
    for a, b in zip(entries, e2):
        expected = dict(a)
        if a['path'] == RESOURCE:
            expected.update(offset=asset['offset'], stored_size=len(title), extract_size=len(title), compression='none', magic_hex=title[:16].hex())
        if b != expected:
            raise ValueError('Written CPK entry differs: ' + a['path'])
    with dest_cpk.open('rb') as stream:
        stream.seek(asset['offset']); assert stream.read(len(title)) == title
    assert dest_cpk.stat().st_size == cpk_end
    outputs[1]['sha256'] = sha(dest_cpk)
    outputs[0]['source'] = str(root / 'EBOOT.BIN')
    destination = root / ('Heroes-Phantasia-' + version + '-title-credit-vwf-4x-candidate.iso')
    originals = iso_inventory(ISO); shutil.copyfile(ISO, destination)
    with destination.open('r+b') as stream:
        for item in outputs:
            stream.seek(0, 2); stream.write(bytes(item['offset'] - stream.tell()))
            with pathlib.Path(item['source']).open('rb') as source:
                shutil.copyfileobj(source, stream, 8 * 1024 * 1024)
            stream.write(bytes((-stream.tell()) % 2048))
        for off, value in iso_patches.items():
            stream.seek(off); stream.write(value)
    verify_original_span(ISO, destination, iso_patches)
    selected = {x['path']: x for x in outputs}
    expected = [dict(x, offset=selected[x['path']]['offset'], size=selected[x['path']]['size']) if x['path'] in selected else x for x in originals]
    assert iso_inventory(destination) == expected and destination.stat().st_size == iso_end
    with destination.open('rb') as stream:
        for item in outputs:
            stream.seek(item['offset']); remaining = item['size']; digest = hashlib.sha256()
            while remaining:
                chunk = stream.read(min(8 * 1024 * 1024, remaining))
                if not chunk:
                    raise ValueError('Truncated ISO extraction')
                digest.update(chunk); remaining -= len(chunk)
            assert digest.hexdigest() == item['sha256']
    ui.mkdir(parents=True, exist_ok=True)
    original_image.save(ui / 'original_background.png'); preview.save(ui / 'preview_background.png')
    (ui / 'stamp.en.json').write_text(json.dumps(stamp, indent=2) + '\n', encoding='utf-8')
    info.update(dialogue_cpk_sha256=outputs[1]['sha256'], iso_path=str(destination), iso_sha256=sha(destination),
                structural_validation='Title palettes, headers and layout preserved; only reviewed title logo regions and version/credit background pixels changed. CPK/ISO inventories, selected extractions and every untouched original byte verified.' if stamp.get('title_logo_translation') else 'Title palette/headers/layout/other textures and all uncovered pixels preserved; CPK/ISO inventories, selected extractions and every untouched original byte verified.')
    if psp_report:
        info['psp_metadata_translation'].update(native_png_files_written=True,
            installed_in_iso=True, installed_files=3, runtime_verified=False)
    if prologue_coverage:
        info['prologue_movie_translation_coverage']['installed_in_iso'] = True
    (root / 'manifest.en.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')
    print('Verified fresh local build:', destination)


if __name__ == '__main__':
    main()
