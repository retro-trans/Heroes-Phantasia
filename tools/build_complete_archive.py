"""Guarded combined CPK integration. Default dry-run; no ISO/executable writer.

Rebuilds indexed dialogue and gallery/table prose from original guarded assets,
then append-retargets onto a explicitly hashed current archive. Existing CPL,
cache and other nonselected current modifications are retained. Local atlas-ID
labels remain audited but blocked; this is never a full-game coverage claim.
"""
import argparse
import json
from pathlib import Path
import re
import shutil

import append_cpk
import build_translation_archive as indexed
import table_translation_patch as extended
import cpl_translation_patch as cpl
from rebuild_dialogue import format_placeholders
from unpack_cpk import inventory


def report_bytes(report):
    return (json.dumps(report,ensure_ascii=True,sort_keys=True,indent=2)+'\n').encode('utf8')


def copyright_proposal(args):
    import copylogo_pixel_proposal as pixels
    paths=dict(source=args.source_root/'menu/CopyLogo_Data.bin',
               queue=args.targets/'copyright_0001.json',
               layout=Path('work/source/copyright_audit/copylogo_layout_proposal.en.json'),
               font=Path('work/source/ppsspp/assets/Roboto_Condensed-Regular.ttf'))
    inputs={name:path.read_bytes() for name,path in paths.items()}
    candidate,report,_=pixels.prepare(inputs['source'],inputs['queue'],inputs['layout'],paths['font'])
    if report['candidate_sha256']!='ced5886c165adf0cdc83af0d8beda5827b4d68e12bc0f80b06cdfc84ea7ffe24':
        raise ValueError('Independently reviewed native copyright pixels changed')
    report['input_snapshots']=[dict(path=str(path),sha256=indexed.digest(inputs[name])) for name,path in paths.items()]
    for name in ('copylogo_pixel_proposal','inspect_font_assets','title_stamp'):
        path=Path('tools')/(name+'.py')
        report['input_snapshots'].append(dict(path=str(path),sha256=indexed.digest(path.read_bytes())))
    return report,(report['resource'],indexed.MemoryAsset(report['resource'],candidate))


def battle_bitmap_proposal():
    import prepare_battle_atlas_proposal as pixels
    candidate, report, _, _, _ = pixels.prepare()
    if report['proposed_resource_sha256'] != '9a8abe108472aba62e9e52f7e0866b86c72ad346e7567e1297f58b411a2e1dad':
        raise ValueError('Reviewed battle bitmap candidate changed')
    if report['whole_label_count'] != 20 or report['fragment_label_count'] != 3 or not report['all_nonpixel_bytes_exact']:
        raise ValueError('Reviewed battle bitmap scope changed')
    from prepare_title_logo_proposal import FONT
    paths = [pixels.SOURCE, pixels.QUEUE, FONT,
        Path(report['fragment_native_reader_proof']['path'])]
    paths.extend(Path('tools')/(name+'.py') for name in ('prepare_battle_atlas_proposal',
        'prepare_battle_fragment_proposal', 'inspect_font_assets', 'prepare_title_logo_proposal'))
    report['input_snapshots'] = [dict(path=str(path), sha256=indexed.digest(path.read_bytes())) for path in paths]
    report['resource'] = 'btl/sys_all.bin'
    return report, (report['resource'], indexed.MemoryAsset(report['resource'], candidate))


def build(args):
    if not re.fullmatch(r'0\.\d+\.\d+',args.version):raise ValueError('Invalid build version')
    if not re.fullmatch(r'[0-9a-f]{64}',args.expected_sha256):raise ValueError('Explicit current archive SHA required')
    base_manifest_raw=args.base_manifest.read_bytes()
    base_manifest=json.loads(base_manifest_raw)
    if base_manifest.get('dialogue_cpk_sha256')!=args.expected_sha256:
        raise ValueError('Current archive SHA differs from base build manifest')
    base_version=base_manifest.get('version','')
    if not re.fullmatch(r'0\.\d+\.\d+',base_version) or tuple(map(int,base_version.split('.')))>=tuple(map(int,args.version.split('.'))):
        raise ValueError('New version must follow the current archive base version')
    base,baseplan=indexed.build(args)
    supplement_args=argparse.Namespace(**vars(args));supplement_args.archive=None
    extra,extras=extended.build(supplement_args)
    prior_cpl=None
    prior_archive_snapshot=None
    if base_manifest.get('translation_archive_preparation_report'):
        prior_path=Path(base_manifest['translation_archive_preparation_report'])
        prior_raw=prior_path.read_bytes();prior=json.loads(prior_raw)
        if prior.get('cpl'):
            prior_cpl=prior['cpl']['assets']
            prior_archive_snapshot=dict(path=str(prior_path),sha256=indexed.digest(prior_raw))
    cpl_report,cpl_assets=cpl.build(args.archive,prior_cpl,resident_names=getattr(args,'resident_cpl_names',False))
    replacements=[]
    if baseplan:
        replacements.extend((asset['resource'],indexed.MemoryAsset(asset['resource'],asset['data']))
                            for asset in baseplan[3])
    replacements.extend(extras)
    replacements.extend(cpl_assets)
    copyright_report=None
    if getattr(args,'copyright_ui',False):
        copyright_report,copyright_asset=copyright_proposal(args)
        replacements.append(copyright_asset)
    battle_report = None
    if getattr(args, 'battle_bitmap_ui', False):
        battle_report, battle_asset = battle_bitmap_proposal()
        replacements.append(battle_asset)
    names=[name for name,_ in replacements]
    if len(names)!=len(set(names)):raise ValueError('Overlapping indexed/gallery/table replacement owner')
    # Rebuilt resources already installed byte-for-byte need no new extent.
    # Keep their logical coverage proof; append only actual changed candidates.
    _, current_entries = inventory(args.archive)
    current = {entry['path']: entry for entry in current_entries}
    changed, identical = [], []
    with args.archive.open('rb') as stream:
        for name, asset in replacements:
            entry = current[name]; data = asset.read_bytes()
            same = False
            if entry['compression'] == 'none' and entry['stored_size'] == len(data):
                stream.seek(entry['offset']); same = stream.read(len(data)) == data
            if same: identical.append(name)
            else: changed.append((name, asset))
    blocked=bool(base['structural_failures'] or base['encoding_blocked_assets'] or extra['failures'])
    plan=None if blocked else append_cpk.plan(args.archive,changed,args.expected_sha256)
    # Source-aware percent checking also governs the exact metadata ledger.
    for asset in base['assets']:
        for row in asset['rows']:
            # The encoder already checked original-vs-target via this helper;
            # do not scan an English literal percentage as an invented printf.
            if 'format_placeholders' in row:
                row['format_placeholder_policy']='format_placeholders(source) == format_placeholders(target, source)'
    report={'schema_version':1,'version':args.version,'status':'dry_combined_archive_plan',
            'runtime_verified':False,'runtime_verified_dialogue_rows':0,
            'full_game_translation_complete':False,'input_archive':str(args.archive),
            'input_archive_sha256':args.expected_sha256,
            'base_manifest':str(args.base_manifest),'base_manifest_sha256':indexed.digest(base_manifest_raw),
            'base_version':base_version,
            'prior_archive_preparation_snapshot':prior_archive_snapshot,
            'indexed':base,'extended':extra,'cpl':cpl_report,'blocked':blocked,
            'copyright_ui':copyright_report,
            'battle_bitmap_ui':battle_report,
            'resources_with_replacements':len(replacements),
            'resources_with_actual_new_extents':len(changed),
            'resources_reused_byte_exact':len(identical),
            'byte_exact_reuse_resources':identical,
            'planned_indexed_unique_rows':base['planned_unique_rows'],
            'planned_gallery_unique_rows':extra['gallery_unique_rows'] if not extra['failures'] else None,
            'planned_table_unique_rows':extra['table_unique_rows'] if not extra['failures'] else None,
            'planned_cpl_name0_unique_rows':cpl_report['name0_unique'],
            'glyph_labels_installed':0,'glyph_labels_blocked':extra['glyph_asset']['unique_rows'],
            'preservation':'All nonselected current TOC entries and archive bytes remain unchanged; selected resources rebuild from original guarded references/font/nontext metadata.',
            'limits':['No ISO or executable integration performed.',
                      'Current-font, ruby, wrapping, names and all table/gallery renderer routes still require independent validation.',
                      'Glyph atlas labels are not counted installed.',
                      'Meaning review and runtime completeness are not implied by full target coverage.']}
    if plan:
        report['archive_plan']={'original_bytes':args.archive.stat().st_size,'output_bytes':plan[4],
                               'alignment':2048,'replacements':len(plan[3]),
                               'shared_extents_preserved':True,'metadata_schema_reparse':True,
                               'unknown_header_counts_unchanged':True}
    return report,plan,supplement_args


def verify_inputs(args,report,supplement_args):
    if indexed.digest(args.base_manifest.read_bytes())!=report['base_manifest_sha256']:
        raise ValueError('Base archive manifest changed after plan')
    if report.get('prior_archive_preparation_snapshot'):
        item=report['prior_archive_preparation_snapshot']
        if indexed.digest(Path(item['path']).read_bytes())!=item['sha256']:
            raise ValueError('Prior archive preparation evidence changed after plan')
    extended.verify_inputs(supplement_args,report['extended'])
    for item in (report.get('copyright_ui') or {}).get('input_snapshots',[]):
        if indexed.digest(Path(item['path']).read_bytes())!=item['sha256']:
            raise ValueError('Reviewed copyright input changed after plan')
    for item in (report.get('battle_bitmap_ui') or {}).get('input_snapshots',[]):
        if indexed.digest(Path(item['path']).read_bytes())!=item['sha256']:
            raise ValueError('Reviewed battle bitmap input changed after plan')
    for item in report['cpl']['target_input_snapshots']:
        if indexed.digest(Path(item['path']).read_bytes())!=item['sha256']:
            raise ValueError('CPL targets changed after plan')
    for asset in report['cpl']['assets']:
        if indexed.digest((args.source_root/asset['resource']).read_bytes())!=asset['original_sha256']:
            raise ValueError('CPL original changed after plan')
    base=report['indexed']
    for item in base.get('physical_overlay_layout_inputs',[]):
        if indexed.digest(Path(item['path']).read_bytes())!=item['sha256']:
            raise ValueError('Physical overlay layout input changed after plan')
    for item in base['target_input_snapshots']:
        if indexed.digest(Path(item['path']).read_bytes())!=item['sha256']:
            raise ValueError('Indexed targets changed after plan')
    for path,key in [(args.occurrences,'occurrences_sha256'),(args.inventory,'original_extraction_inventory_sha256')]:
        if indexed.digest(path.read_bytes())!=base[key]:raise ValueError('Indexed evidence changed after plan')
    for asset in base['assets']:
        if indexed.digest((args.source_root/asset['resource']).read_bytes())!=asset['original_sha256']:
            raise ValueError('Indexed original changed after plan')
    if append_cpk.sha(args.archive)!=report['input_archive_sha256']:
        raise ValueError('Current archive changed after plan')


def write(args,report,plan,supplement_args):
    if report['blocked'] or plan is None:raise ValueError('Blocked combined plan cannot be written')
    if report['indexed']['untranslated_unique_rows']:raise ValueError('Combined writer requires complete indexed drafts')
    checksum=indexed.digest(report_bytes(report))
    if args.approved_plan_sha256!=checksum:
        raise ValueError('Exact dry plan hash must be reviewed before writer; current '+checksum)
    verify_inputs(args,report,supplement_args)
    output=args.output.resolve() if args.output else None
    if output is None or output.exists() or not output.is_relative_to(Path('work/output').resolve()):
        raise ValueError('Output must be a fresh folder within work/output')
    before,entries,patches,assets,end=plan
    output.mkdir(parents=True)
    archive=output/'HP.CPK';shutil.copyfile(args.archive,archive)
    with archive.open('r+b') as stream:
        for offset,value in patches.items():stream.seek(offset);stream.write(value)
        for asset in assets:
            stream.seek(0,2);stream.write(bytes(asset['offset']-stream.tell()))
            stream.write(asset['data']);stream.write(bytes((-stream.tell())%2048))
    after,newentries=inventory(archive)
    if after!=dict(before,ContentSize=end-before['ContentOffset']) or len(entries)!=len(newentries):
        raise ValueError('Written archive header/count differs')
    selected={asset['resource']:asset for asset in assets}
    with archive.open('rb') as stream:
        for old,new in zip(entries,newentries):
            asset=selected.get(old['path'])
            if asset is None:
                if old!=new:raise ValueError('Unselected current resource metadata changed')
                continue
            expected=dict(old,offset=asset['offset'],stored_size=asset['bytes'],extract_size=asset['bytes'],compression='none')
            # The parser's leading bytes are expected to reflect replacement
            # content; all other resource identity/metadata fields must match.
            for key in old:
                if key=='magic_hex':continue
                if new[key]!=expected[key]:raise ValueError('Selected resource metadata differs: '+key)
            stream.seek(new['offset']);data=stream.read(new['stored_size'])
            if data!=asset['data']:raise ValueError('Written selected extraction differs')
    append_cpk.verify_original_span(args.archive,archive,patches)
    if archive.stat().st_size!=end:raise ValueError('Written archive size differs')
    report.update(status='written_combined_structural_candidate_runtime_unverified',
                  approved_dry_plan_sha256=checksum,output_archive=str(archive),
                  output_archive_sha256=append_cpk.sha(archive),
                  all_current_nonselected_bytes_verified=True,
                  all_written_replacement_extractions_verified=True)
    (output/'integration.en.json').write_bytes(report_bytes(report))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--targets',type=Path,default=Path('work/translation/en'))
    p.add_argument('--source-root',type=Path,default=Path('work/source/cpk'))
    p.add_argument('--inventory',type=Path,default=Path('work/source/cpk_inventory.json'))
    p.add_argument('--occurrences',type=Path,default=Path('work/source/text_occurrences.json'))
    p.add_argument('--table-inventory',type=Path,default=Path('work/source/table_strings.json'))
    p.add_argument('--glyph-seeds',type=Path,default=Path('work/source/font_audit/glyph_seeds.json'))
    p.add_argument('--archive',type=Path,default=Path('work/output/0.1.15-title-credit-vwf-4x-candidate/HP.CPK'))
    p.add_argument('--base-manifest',type=Path,default=Path('work/output/0.1.15-title-credit-vwf-4x-candidate/manifest.en.json'))
    p.add_argument('--expected-sha256',default='45c9872a83602a173644f2bcac99031b7dde9861d17cf3c9077d56b4c99863c5')
    p.add_argument('--version',default='0.1.16')
    p.add_argument('--ascii-punctuation',action='store_true');p.add_argument('--vwf-latin',action='store_true');p.add_argument('--native-fallback',action='store_true');p.add_argument('--native-original-symbols',action='store_true')
    p.add_argument('--require-complete',action='store_true')
    p.add_argument('--battle-overlay-wrap',action='store_true')
    p.add_argument('--battle-bitmap-ui',action='store_true')
    p.add_argument('--dictionary-wrap',action='store_true')
    p.add_argument('--long-dictionary-wraps',action='store_true')
    p.add_argument('--copyright-ui',action='store_true',help='Include two independently reviewed native startup notice/copyright textures')
    p.add_argument('--resident-cpl-names',action='store_true',help='Restore original CPL structures; translated HUD names require the matching executable lookup')
    p.add_argument('--output',type=Path);p.add_argument('--write',action='store_true');p.add_argument('--approved-plan-sha256')
    p.add_argument('--details',action='store_true');a=p.parse_args()
    report,plan,supplement=build(a)
    print(json.dumps(report if a.details else {k:v for k,v in report.items() if k not in ('indexed','extended','cpl')},ensure_ascii=True,indent=2))
    print('DRY PLAN SHA256',indexed.digest(report_bytes(report)))
    if a.write:write(a,report,plan,supplement)
    else:print('DRY RUN: no resource/archive/report files written.')


if __name__=='__main__':main()
