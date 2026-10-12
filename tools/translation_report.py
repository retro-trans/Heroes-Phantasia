"""Verify translation structure and write an English-only inventory/progress report."""
import argparse, collections, datetime, json, pathlib, re
from apply_targets import TOKENS, JP
from dialogue_tokens import validate_controls
from build_glossary import canonical_key
from rebuild_dialogue import format_placeholders

def current_validation(kind, version, manifest, filename='validation.en.json'):
    """Use only versioned proof tied to all three current build hashes."""
    path=pathlib.Path('work/ui')/kind/version/filename
    if not path.exists():return {}, str(path), ['current proof missing']
    proof=json.loads(path.read_text(encoding='utf-8'))
    errors=[]
    if proof.get('version')!=version or manifest.get('version')!=version:
        errors.append('proof or manifest version mismatch')
    for proof_key,manifest_key in [('iso_sha256','iso_sha256'),
                                  ('executable_sha256','output_elf_sha256'),
                                  ('archive_sha256','dialogue_cpk_sha256')]:
        if not manifest.get(manifest_key) or proof.get(proof_key)!=manifest[manifest_key]:
            errors.append(proof_key+' missing or mismatched')
    return proof, str(path), errors

def installed_media(version, manifest):
    """Read current installed coverage; proposal runtime flags are not proof."""
    valid=manifest.get('version')==version and all(manifest.get(k) for k in
        ('iso_sha256','output_elf_sha256','dialogue_cpk_sha256'))
    battle=manifest.get('battle_bitmap_translation_coverage',{}) if valid else {}
    copyright=manifest.get('copyright_ui_translation_coverage',{}) if valid else {}
    psp=manifest.get('psp_metadata_translation',{}) if valid else {}
    gallery=manifest.get('gallery_label_proposal',{}) if valid else {}
    preparation_path=pathlib.Path(manifest.get('executable_preparation_report',''))
    if valid and preparation_path.is_file():
        preparation=json.loads(preparation_path.read_text(encoding='utf-8'))
        if preparation.get('output_elf_sha256')==manifest.get('output_elf_sha256'):
            gallery=preparation.get('gallery_label_proposal',gallery)
            if 'gallery_current_entries' in preparation:
                gallery={'entries':preparation['gallery_current_entries']}
    prologue=manifest.get('prologue_movie_translation_coverage',{}) if valid else {}
    banners=manifest.get('dungeon_banner_translation_coverage',{}) if valid else {}
    special=manifest.get('battle_special_label_translation_coverage',{}) if valid else {}
    replacements={r['path']:r.get('sha256') for r in manifest.get('iso_replacements',[])}
    prologue_installed=prologue.get('installed_in_iso') is True and bool(prologue.get('candidate_sha256')) and replacements.get(prologue.get('asset'))==prologue.get('candidate_sha256')
    psp_files=[r['iso_path'] for r in psp.get('entries',[])
        if psp.get('installed_in_iso') is True and r.get('candidate_sha256')
        and replacements.get(r.get('iso_path'))==r['candidate_sha256']]
    return {
        'installed_special_move_hud_labels':special.get('labels',0) if special.get('installed_in_iso') is True else 0,
        'special_move_hud_displayed_target':special.get('displayed_target'),
        'special_move_hud_static_validation':special.get('validation'),
        'special_move_hud_native_display_verified':False,
        'installed_dungeon_banner_labels':banners.get('bitmap_labels',0) if banners.get('installed_in_iso') is True else 0,
        'dungeon_banner_inventory_observations':banners.get('inventory_observations',0),
        'other_dungeon_banner_assets_pending':banners.get('other_banner_assets_pending',0),
        'dungeon_banner_static_validation':banners.get('validation'),
        'dungeon_banner_native_display_verified':False,
        'installed_battle_whole_labels':battle.get('whole_labels',0) if battle.get('installed_in_archive') is True else 0,
        'installed_battle_fragment_groups':battle.get('fragment_headings',0) if battle.get('installed_in_archive') is True else 0,
        'battle_static_pixels_reviewed':battle.get('static_pixels_reviewed') is True,
        'installed_copyright_records':copyright.get('semantic_records',0),
        'installed_copyright_textures':copyright.get('textures',0),
        'installed_external_psp_metadata_files':len(psp_files),
        'external_psp_metadata_paths':psp_files,
        'installed_gallery_typed_labels':len(gallery.get('entries',[])),
        'installed_prologue_primary_captions':prologue.get('primary_caption_rows',0) if prologue_installed else 0,
        'installed_prologue_superseding_fields':prologue.get('superseding_staggered_fields',0) if prologue_installed else 0,
        'installed_prologue_moving_signs':prologue.get('moving_sign',0) if prologue_installed else 0,
        'installed_movie_assets':[prologue.get('asset')] if prologue_installed else [],
        'copyright_runtime_verified':False,
        'external_psp_metadata_runtime_verified':False,
        'runtime_scope_note':'Installation and static review do not establish current display QA. Copyright and external PSP metadata require separate current scoped evidence.',
        'archive_preparation_evidence':manifest.get('translation_archive_preparation_report') if valid else None,
        'counting_scope':'Image records and physical files remain separate from the structured Japanese-bearing headline.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true')
    p.add_argument('--preview-dir',type=pathlib.Path,help='Write review copies only beneath ignored work/source; published docs remain unchanged.')
    a=p.parse_args()
    if a.write and a.preview_dir:p.error('--write and --preview-dir are mutually exclusive')
    if a.preview_dir:
        try:a.preview_dir.resolve().relative_to(pathlib.Path('work/source').resolve())
        except ValueError:p.error('--preview-dir must be beneath work/source')
    primary=json.loads(pathlib.Path('work/source/text_inventory.json').read_text(encoding='utf-8'))
    archive=json.loads(pathlib.Path('work/source/cpk_inventory.json').read_text(encoding='utf-8'))
    tables=json.loads(pathlib.Path('work/source/table_strings.json').read_text(encoding='utf-8'))
    table_unique={r['id']:r for r in tables['rows']}
    table_jp=[r for r in tables['rows'] if JP.search(r['source'])]
    table_jp_unique=[r for r in table_unique.values() if JP.search(r['source'])]
    glyph_path=pathlib.Path('work/source/font_audit/sys_tbl_names.json')
    glyphs=json.loads(glyph_path.read_text(encoding='utf-8'))['rows'] if glyph_path.exists() else []
    glyph_jp=[r for r in glyphs if JP.search(r['source'])]
    glyph_unique={r['source'] for r in glyph_jp}
    queue=[]; filled_files=[];bad=[];by_cat=collections.Counter();status=collections.Counter()
    for path in sorted(pathlib.Path('work/translation/en').glob('*.json')):
        if path.name.endswith('.en.json'):continue
        data=json.loads(path.read_text(encoding='utf-8'));filled=False
        for row in data['rows']:
            queue.append(row);status[row.get('status','untranslated')]+=1
            target=row.get('target','')
            if not target:continue
            filled=True;by_cat[row['category']]+=1
            try:
                if row.get('encoding') == 'baked_raster_source_transcription':
                    # These are transcribed pixels, not native byte streams.
                    # Newlines describe visual wrapping and may be reflowed.
                    for value in (row['source'], target):
                        if re.search(r'\{[0-9A-Fa-f]{2}\}', value) or any(ord(c)<32 and c not in '\n\r' for c in value):
                            raise ValueError('Unexpected control notation in raster transcription')
                else:
                    validate_controls(row['source'],target)
            except ValueError as error:bad.append([row['id'],'controls: '+str(error)])
            if format_placeholders(row['source'])!=format_placeholders(target,row['source']):bad.append([row['id'],'percent placeholders'])
            if JP.search(target):bad.append([row['id'],'Japanese remains in target'])
        if filled:filled_files.append(str(path))
    if len({r['id'] for r in queue})!=len(queue):bad.append(['queue','Duplicate IDs'])
    unfilled_breakdown=collections.Counter()
    for row in queue:
        if row.get('target'):continue
        if row.get('status')=='excluded_binary':kind='excluded_technical_candidates'
        elif row.get('id')=='exe_002eb740_cp932':kind='held_Mao_formatter'
        elif row.get('encoding')=='baked_raster_source_transcription' and row.get('category')=='movie_staff_credit':kind='held_staff_credit_blocks'
        elif row.get('category')=='executable_native_menu_ui':kind='held_native_menu_labels'
        else:kind='other_unfilled'
        unfilled_breakdown[kind]+=1
    menu_ui=[r for r in queue if r['category']=='executable_menu_ui']
    executable_sources={r['source'] for r in queue if 'EBOOT' in r.get('file','') and r.get('target')}
    cpl_name_sources={r['source'] for r in queue if r.get('category')=='battle_entity_name'}
    setup_ui=[r for r in queue if r['category']=='executable_setup_ui']
    gallery_ui=[r for r in queue if r['category']=='executable_gallery_ui']
    cpl_path=pathlib.Path('work/source/cpl_text_inventory.json')
    cpl=json.loads(cpl_path.read_text(encoding='utf-8')) if cpl_path.exists() else None
    from audit_gallery_layout import audit as gallery_layout_audit
    layout=gallery_layout_audit()
    proof_path=pathlib.Path('work/ui/runtime/cold_boot_menu_validation.en.json')
    proof=json.loads(proof_path.read_text()) if proof_path.exists() else {}
    verified_menu=set(proof.get('menu_labels_verified',[])) & {r.get('target') for r in menu_ui}
    if proof.get('status')!='cold_boot_menu_verified_only':verified_menu=set()
    gloss=[];gloss_files=[]
    for path in sorted(pathlib.Path('work/glossary').glob('*.en.json')):
        if path.name=='glossary.en.json':continue
        data=json.loads(path.read_text(encoding='utf-8'));gloss.extend(data['entries']);gloss_files.append(str(path))
    opening_path=pathlib.Path('work/ui/runtime/association_candidate_opening_validation.en.json')
    if not opening_path.exists():opening_path=pathlib.Path('work/ui/runtime/compact_candidate_opening_validation.en.json')
    if not opening_path.exists():opening_path=pathlib.Path('work/ui/runtime/speaker_candidate_opening_validation.en.json')
    opening=json.loads(opening_path.read_text()) if opening_path.exists() else {}
    historical_verified_dialogue=opening.get('runtime_verified_dialogue_rows',0) if opening.get('version')=='0.1.6' and opening.get('status')=='selected_opening_record_display_qa_passed' and opening.get('dialogue_record_display_qa_passed') is True else 0
    gallery_path=pathlib.Path('work/ui/runtime/gallery_candidate_validation.en.json')
    gallery=json.loads(gallery_path.read_text()) if gallery_path.exists() else {}
    verified_gallery=gallery.get('runtime_verified_gallery_prose_rows',0) if gallery.get('version')=='0.1.7' and gallery.get('status')=='selected_gallery_prose_display_qa_passed' and gallery.get('gallery_record_display_qa_passed') is True else 0
    build_config_path=pathlib.Path('build.json')
    build_config=json.loads(build_config_path.read_text(encoding='utf-8')) if build_config_path.exists() else {}
    title_path=pathlib.Path('work/output')/(build_config.get('version','0.1.7')+'-title-credit-vwf-4x-candidate')/'manifest.en.json'
    title=json.loads(title_path.read_text(encoding='utf-8')) if title_path.exists() else {}
    current_version=build_config.get('version',title.get('version','0.1.7'))
    current_opening,current_opening_path,opening_identity_errors=current_validation('opening',current_version,title)
    current_setup,current_setup_path,setup_identity_errors=current_validation('setup',current_version,title)
    current_title,current_title_path,title_identity_errors=current_validation('title',current_version,title)
    current_field,current_field_path,field_identity_errors=current_validation('field',current_version,title)
    field_entries=current_field.get('entries',[]) if not field_identity_errors else []
    field_installed_indices={r['native_index'] for r in field_entries if r.get('table')==0}
    native_menu_installed=sum(r.get('category')=='executable_native_menu_ui' and bool(r.get('target'))
        and r.get('native_index') in field_installed_indices for r in queue)
    current_battle,current_battle_path,battle_identity_errors=current_validation('battle',current_version,title)
    current_save,current_save_path,save_identity_errors=current_validation('save',current_version,title)
    current_gallery,current_gallery_path,gallery_identity_errors=current_validation('gallery',current_version,title)
    if not current_gallery:
        partial,partial_path,partial_errors=current_validation('gallery',current_version,title,'partial_display_qa.en.json')
        if partial:
            current_gallery,current_gallery_path,gallery_identity_errors=partial,partial_path,partial_errors
    current_media,current_media_path,media_identity_errors=current_validation('media',current_version,title)
    previous_battle={}
    previous_battle_path=None
    historical_manifest=pathlib.Path('work/output/0.1.23-title-credit-vwf-4x-candidate/manifest.en.json')
    if current_version!='0.1.23' and historical_manifest.exists():
        previous,previous_path,previous_errors=current_validation('battle','0.1.23',json.loads(historical_manifest.read_text(encoding='utf-8')))
        if not previous_errors:
            previous_battle={k:previous.get(k) for k in ('version','status','scope','first_encounter_completed','next_scene_English_Louie_dialogue_observed','limitations')}
            previous_battle_path=previous_path
    current_restart,current_restart_path,restart_identity_errors=current_validation('save',current_version,title,'save_restart.en.json')
    save_passed=not save_identity_errors and current_save.get('save_display_qa_passed') is True
    battle_passed=not battle_identity_errors and current_battle.get('battle_display_qa_passed') is True
    installed=installed_media(current_version,title)
    title_passed=not title_identity_errors and current_title.get('runtime_verified_title') is True
    media_path=pathlib.Path('work/source/media_audit/visual_scope_sampled.en.json')
    media=json.loads(media_path.read_text(encoding='utf-8')) if media_path.exists() else {}
    battle_media_path=pathlib.Path('work/source/media_audit/battle_atlas_scope.en.json')
    battle_media=json.loads(battle_media_path.read_text(encoding='utf-8')) if battle_media_path.exists() else {}
    startup_path=pathlib.Path('work/ui/runtime')/current_version/'startup_failure.en.json'
    startup=json.loads(startup_path.read_text(encoding='utf-8')) if startup_path.exists() else {}
    startup_matches=all(startup.get(k)==title.get(v) and title.get(v) for k,v in
        [('iso_sha256','iso_sha256'),('executable_sha256','output_elf_sha256'),
         ('archive_sha256','dialogue_cpk_sha256')]) and startup.get('version')==current_version
    opening_passed=not opening_identity_errors and current_opening.get('opening_display_qa_passed') is True
    claimed_rows=current_opening.get('runtime_verified_dialogue_rows',0)
    if not isinstance(claimed_rows,int) or isinstance(claimed_rows,bool) or claimed_rows<0:
        opening_identity_errors.append('invalid verified dialogue row count');opening_passed=False
    selected_rows=title.get('selected_dialogue_rows')
    indexed_count=title.get('indexed_dialogue_coverage',{}).get('unique_rows',0)
    installed_count=len(selected_rows) if isinstance(selected_rows,list) else indexed_count
    if opening_passed and (not isinstance(installed_count,int) or isinstance(installed_count,bool) or claimed_rows>installed_count):
        opening_identity_errors.append('verified row count exceeds installed selection');opening_passed=False
    verified_dialogue=claimed_rows if opening_passed else 0
    selected_opening_records=current_opening.get('runtime_verified_selected_record_count',0) if not opening_identity_errors else 0
    if not isinstance(selected_opening_records,int) or isinstance(selected_opening_records,bool) or not 0<=selected_opening_records<=installed_count:
        selected_opening_records=0
    setup_passed=not setup_identity_errors and current_setup.get('setup_display_qa_passed') is True
    summary={'version':current_version,'inventory_baseline_version':'0.1.0','language':'en','date':datetime.date.today().isoformat(),
        'archive_files':len(archive['entries']),'primary_occurrences':primary['occurrence_rows'],
        'primary_unique_rows':primary['unique_translation_rows'],'table_occurrences':len(tables['rows']),
        'table_unique_rows':len(table_unique),'table_japanese_occurrences':len(table_jp),
        'table_japanese_unique_rows':len(table_jp_unique),
        'glyph_label_occurrences':len(glyph_jp),'glyph_label_unique_rows':len(glyph_unique),
        'glyph_labels_matching_drafted_executable_sources':len(glyph_unique & executable_sources),
        'glyph_labels_matching_CPL_entity_names':len(glyph_unique & cpl_name_sources),
        'glyph_label_counting_scope':'Decoded resource observations, not new missing translation rows. Matching executable/CPL sources do not prove this glyph-index resource is drawn.',
        'runtime_observed_executable_menu_labels':len(menu_ui),
        'supplemental_executable_setup_ui_records':len(setup_ui),
        'supplemental_setup_source_japanese_records':sum(bool(JP.search(r['source'])) for r in setup_ui),
        'supplemental_setup_source_non_japanese_records':sum(not JP.search(r['source']) for r in setup_ui),
        'supplemental_setup_counting_scope':'Separate queue records; excluded from confirmed Japanese-bearing headline pending executable-pool overlap reconciliation.',
        'supplemental_gallery_ui_records':len(gallery_ui),
        'supplemental_gallery_generic_labels':sum(r.get('native_table')==0 and r.get('native_index') not in range(82,88) for r in gallery_ui),
        'supplemental_gallery_knowledge_categories':sum(r.get('native_table')==0 and r.get('native_index') in range(82,88) for r in gallery_ui),
        'supplemental_gallery_franchise_season_titles':sum(r.get('native_table')==2 and r.get('native_index')!=11 for r in gallery_ui),
        'supplemental_gallery_original_category_labels':sum(r.get('native_table')==2 and r.get('native_index')==11 for r in gallery_ui),
        'supplemental_gallery_counting_scope':'Separate typed-pointer records; not added to the confirmed Japanese-bearing headline until pool overlap reconciliation.',
        'supplemental_battle_hud_ui_records':sum(r.get('category')=='executable_battle_hud_ui' for r in queue),
        'supplemental_battle_hud_counting_scope':'Typed embedded executable HUD labels; separate from structured-text headline pending source-pool overlap reconciliation.',
        'supplemental_native_menu_records':sum(r.get('category')=='executable_native_menu_ui' for r in queue),
        'supplemental_native_menu_drafts':sum(r.get('category')=='executable_native_menu_ui' and bool(r.get('target')) for r in queue),
        'supplemental_native_menu_held':sum(r.get('category')=='executable_native_menu_ui' and not r.get('target') for r in queue),
        'supplemental_native_menu_installed_drafts':native_menu_installed,
        'supplemental_native_menu_scope':'Working typed-menu drafts; selected labels are installed through the current field UI proof. Other consumer routes and display layouts remain unproved.',
        'supplemental_field_ui_records':sum(r['id'].startswith('field_table') or r['id']=='field_episode_1_banner' for r in queue),
        'field_ui_installed_labels':len(field_entries),
        'supplemental_save_ui_records':sum(r['id'].startswith('save_table') for r in queue),
        'save_ui_installed_records':current_field.get('save_ui_translation_rows',0) if not field_identity_errors else 0,
        'field_tutorial_native_width_verified':not field_identity_errors and current_field.get('native_tutorial_width_verified') is True,
        'field_tutorial_panel_display_verified':not field_identity_errors and current_field.get('native_tutorial_panel_display_verified') is True,
        'field_tutorial_panel_display_scope':'Debugger-triggered native Save Points resource panel; natural guild arrival remains unverified.',
        'field_ui_episode_banner_remaps':int(bool(current_field.get('episode_banner'))) if not field_identity_errors else 0,
        'field_ui_options_display_verified':not field_identity_errors and current_field.get('native_options_layout_verified') is True,
        'field_ui_other_screens_verified':not field_identity_errors and current_field.get('native_party_catalog_tutorial_talk_verified') is True,
        'field_ui_natural_episode_interception_verified':not field_identity_errors and current_field.get('natural_episode_banner_interception_verified') is True,
        'field_ui_evidence':current_field_path if current_field else None,
        'field_ui_proof_identity_errors':field_identity_errors,
        'field_ui_counting_scope':'Supplemental installation records overlap existing draft sources; these are not additional distinct Japanese-bearing records in the confirmed headline.',
        'gallery_display_qa_passed':not gallery_identity_errors and current_gallery.get('gallery_display_qa_passed') is True,
        'latest_gallery_candidate_version':current_version,
        'gallery_candidate_status':current_gallery.get('status','runtime_qa_pending') if not gallery_identity_errors else 'runtime_qa_pending',
        'gallery_candidate_evidence':current_gallery_path if current_gallery else None,
        'gallery_proof_identity_errors':gallery_identity_errors,
        'gallery_verification_scope':current_gallery.get('scope',current_gallery.get('coverage_note','none')) if not gallery_identity_errors else 'none',
        'gallery_selected_label_count':current_gallery.get('selected_label_count',0) if not gallery_identity_errors else 0,
        'gallery_fully_reviewed_label_count':current_gallery.get('reviewed_label_count',0) if not gallery_identity_errors else 0,
        'gallery_remaining_limitations':current_gallery.get('limitations',[]) if not gallery_identity_errors else ['Current native gallery display/layout proof pending.'],
        'media_display_qa_passed':not media_identity_errors and current_media.get('media_display_qa_passed') is True,
        'media_candidate_status':current_media.get('status','runtime_qa_pending') if not media_identity_errors else 'runtime_qa_pending',
        'media_candidate_evidence':current_media_path if current_media else None,
        'media_proof_identity_errors':media_identity_errors,
        'media_verification_scope':current_media.get('scope','none') if not media_identity_errors else 'none',
        'media_remaining_limitations':current_media.get('limitations',[]) if not media_identity_errors else ['Current native prologue/media display proof pending.'],
        'confirmed_japanese_occurrences':primary['occurrence_rows']+len(table_jp)+len(glyph_jp)+len(menu_ui),
        'confirmed_distinct_japanese_rows':primary['unique_translation_rows']+len(table_jp_unique)+len(glyph_unique)+len(menu_ui),
        'japanese_characters_occurrences':primary['japanese_characters_occurrences']+sum(len(JP.findall(r['source'])) for r in table_jp+glyph_jp+menu_ui),
        'executable_candidates':sum(r['category']=='executable_ui' for r in queue),
        'queue_rows':len(queue),'drafted_rows':sum(bool(r.get('target')) for r in queue),
        'unfilled_rows':sum(not r.get('target') for r in queue),
        'unfilled_breakdown':dict(unfilled_breakdown),
        'unfilled_count_scope':'Includes excluded technical extraction candidates and held formatter/staff records; not a count of confirmed untranslated player-facing dialogue.',
        'supplemental_cpl_inventory':cpl['summary'] if cpl else None,
        'supplemental_cpl_counting_scope':'Separate CP932-NUL resource records. Name index0 has a statically proved HUD selector; later selectors and duplicate player-facing text remain unproved. Not added to the confirmed headline.',
        'media_audit_scope':{
            **installed,
            'sampled_movie_assets':media.get('movie_assets',0),
            'sampled_movie_frames':media.get('movie_frames_reviewed',0),
            'movies_with_japanese_observed':media.get('movies_with_Japanese_observed',[]),
            'installed_movie_translations':len(installed['installed_movie_assets']),
            'japanese_battle_atlases_observed':battle_media.get('japanese_bearing_atlases_observed',0),
            'complete_text_count_verified':False,
            'evidence':[str(media_path),str(battle_media_path),str(title_path)]},
        'latest_battle_candidate_version':current_version,
        'battle_candidate_status':current_battle.get('status','runtime_qa_pending') if not battle_identity_errors else 'runtime_qa_pending',
        'battle_display_qa_passed':battle_passed,
        'battle_candidate_evidence':current_battle_path if current_battle else None,
        'battle_proof_identity_errors':battle_identity_errors,
        'battle_verification_scope':current_battle.get('scope','See current proof for the specific encounter/screens observed; this does not certify every installed bitmap label.') if not battle_identity_errors else 'none',
        'battle_observations':{k:current_battle[k] for k in ('first_battle_transition_passed','first_encounter_completed','English_enemy_HUD_observed','English_Defense_bitmap_observed','English_100AP_tutorial_fully_visible','next_scene_English_Louie_dialogue_observed') if k in current_battle} if not battle_identity_errors else {},
        'battle_display_defects':current_battle.get('defects',[]) if not battle_identity_errors else [],
        'battle_remaining_limitations':current_battle.get('limitations',[]) if not battle_identity_errors else ['Current battle proof pending; all-label visibility and broader battle coverage remain unverified.'],
        'historical_023_battle_observation':previous_battle,
        'historical_023_battle_evidence':previous_battle_path,
        'latest_save_candidate_version':current_version,
        'save_candidate_status':current_save.get('status','runtime_qa_pending') if not save_identity_errors else 'runtime_qa_pending',
        'save_display_qa_passed':save_passed,
        'system_save_creation_passed':not save_identity_errors and current_save.get('system_save_creation_passed') is True,
        'system_save_restart_load_passed':not restart_identity_errors and current_restart.get('system_save_restart_load_passed') is True,
        'save_restart_candidate_status':current_restart.get('status','runtime_qa_pending') if not restart_identity_errors else 'runtime_qa_pending',
        'save_restart_evidence':current_restart_path if current_restart else None,
        'save_restart_identity_errors':restart_identity_errors,
        'save_restart_scope':current_restart.get('scope','none') if not restart_identity_errors else 'none',
        'save_restart_remaining_limitations':current_restart.get('limitations',[]) if not restart_identity_errors else ['System-save restart proof pending.'],
        'game_save_load_restart_verified':not save_identity_errors and current_save.get('game_save_load_restart_verified') is True,
        'save_candidate_evidence':current_save_path if current_save else None,
        'save_proof_identity_errors':save_identity_errors,
        'save_verification_scope':current_save.get('scope','none') if not save_identity_errors else 'none',
        'save_remaining_limitations':current_save.get('limitations',[]) if not save_identity_errors else ['Current save proof pending.'],
        'current_startup_failure':startup.get('failure') if startup_matches else None,
        'current_startup_failure_evidence':str(startup_path) if startup_matches else None,
        'gallery_structural_layout_audit':{k:layout[k] for k in ('structured_gallery_drafts','structurally_prepared','require_additional_handling','width_px','glyph_limit','font_reference','limitation')},
        'drafted_by_category':dict(by_cat),'statuses':dict(status),
        'glossary_entries':len({canonical_key(g,gloss) for g in gloss}),'glossary_source_records':len(gloss),
        'glossary_files':gloss_files,'filled_files':filled_files,
        'validation_errors':bad,
        'numeric_argument_validation_scope':'Native fixed-byte arguments: 01=1,02=4,03=4,05=3,06=6,0C=2,13=1,16=2,17=1,19=2,1A=1; paired 0F ruby opener=1 and closer=0; CP932 glyphs parsed atomically.',
        'runtime_verified_translations':len(verified_menu),
        'runtime_verification_scope':'five main-menu labels only' if verified_menu else 'none',
        'local_menu_test_iso_verified':bool(verified_menu),
        'latest_opening_candidate_version':current_version,
        'opening_candidate_status':current_opening.get('status','runtime_qa_pending') if not opening_identity_errors else 'runtime_qa_pending',
        'opening_display_qa_passed':opening_passed,
        'opening_proof_identity_errors':opening_identity_errors,
        'last_completed_opening_observation_version':current_version if opening_passed else opening.get('version'),
        'last_completed_opening_observation_status':current_opening.get('status') if opening_passed else opening.get('status'),
        'historical_opening_observation_version':opening.get('version'),
        'historical_opening_observation_status':opening.get('status'),
        'historical_runtime_verified_dialogue_rows':historical_verified_dialogue,
        'historical_opening_candidate_evidence':str(opening_path) if opening else None,
        'runtime_verified_dialogue_rows':verified_dialogue,
        'runtime_verified_selected_opening_records':selected_opening_records,
        'opening_candidate_evidence':current_opening_path if current_opening else None,
        'opening_verification_scope':current_opening.get('scope','Selected installed dialogue rows only') if opening_passed else 'none',
        'opening_remaining_limitations':current_opening.get('limitations',[]) if not opening_identity_errors else ['Current opening proof pending.'],
        'latest_setup_candidate_version':current_version,
        'setup_candidate_status':current_setup.get('status','runtime_qa_pending') if not setup_identity_errors else 'runtime_qa_pending',
        'setup_display_qa_passed':setup_passed,
        'setup_candidate_evidence':current_setup_path if current_setup else None,
        'setup_proof_identity_errors':setup_identity_errors,
        'setup_verification_scope':current_setup.get('scope','none') if not setup_identity_errors else 'none',
        'setup_observations':{k:current_setup[k] for k in ('both_protagonist_Latin_defaults_observed','female_seven_English_customization_labels_observed','English_start_confirmation_observed') if k in current_setup} if not setup_identity_errors else {},
        'setup_remaining_limitations':current_setup.get('limitations',[]) if not setup_identity_errors else ['Current setup proof pending; broader runtime-name contexts also require verification.'],
        'historical_gallery_candidate_version':'0.1.7',
        'historical_gallery_candidate_status':gallery.get('status','runtime_qa_pending'),
        'runtime_verified_gallery_prose_rows':verified_gallery,
        'gallery_observation_historical':True,
        'historical_gallery_candidate_evidence':str(gallery_path) if gallery else None,
        'historical_gallery_verification_scope':gallery.get('scope','none'),
        'gallery_heading_translation_verified':False,
        'title_credit_candidate_version':title.get('version'),
        'title_screen_stamp_display_qa_passed':title_passed,
        'title_screen_validation':current_title_path if title_passed else None,
        'glyph_source_scale':4,
        'emulator_internal_4x_resolution_verified':False,
        'playable_build':False}
    print(json.dumps(summary,indent=2))
    if bad:raise SystemExit('Translation validation failed; correct rows before export.')
    if not a.write and not a.preview_dir:print('DRY RUN: no report written.');return
    root=a.preview_dir if a.preview_dir else pathlib.Path('docs');root.mkdir(parents=True,exist_ok=True)
    (root/'translation_progress.en.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    lines=[f'# Japanese text inventory and progress — {current_version}','',
        f"Verified structured resources contain **{summary['confirmed_japanese_occurrences']:,} Japanese-bearing record occurrences** and **{summary['confirmed_distinct_japanese_rows']:,} distinct Japanese-bearing records** to translate. The executable contributes another **{summary['executable_candidates']:,} heuristic candidates**, counted separately. Another {len(setup_ui)} supplemental setup records are queued separately ({summary['supplemental_setup_source_japanese_records']} Japanese-bearing, {summary['supplemental_setup_source_non_japanese_records']} non-Japanese); they do not increase the headline pending executable-pool overlap reconciliation. This is a lower bound, not a complete on-screen text count.",'',
        '| Category | Resource occurrences | Distinct records assigned to category |',
        '| --- | ---: | ---: |']
    for cat,n in primary['by_category_occurrences'].items():lines.append(f"| {cat.replace('_',' ')} | {n:,} | {primary['by_category_unique'].get(cat,0):,} |")
    table_counts=collections.Counter(r['category'] for r in tables['rows'])
    unique_counts=collections.Counter(r['category'] for r in table_unique.values())
    for cat,n in table_counts.items():lines.append(f"| {cat.replace('_',' ')} | {n:,} | {unique_counts[cat]:,} |")
    lines.append(f"| Glyph-index battle/system labels | {len(glyph_jp):,} | {len(glyph_unique):,} |")
    lines.append(f"| Runtime-observed executable UI labels | {len(menu_ui):,} | {len(menu_ui):,} |")
    lines.extend(['',f"Tables contain {len(tables['rows'])} records ({len(table_unique)} distinct); {len(tables['rows'])-len(table_jp)} are already English song titles in fullwidth characters, so they are excluded from the Japanese-bearing headline and queued for normalization.",'',
        'Counts use validated table references, not raw string guesses. A record is one original dialogue reference, prose entry, or item/list entry; it can contain several lines or pages. Exact-byte duplicates share one English target while every original occurrence keeps its file, offset and references. Category assignment for shared records follows the first archive occurrence, so distinct category counts are exclusive rather than totals of every usage.', '',
        f"Japanese-character occurrences total {summary['japanese_characters_occurrences']:,}; these count kana and CJK characters, including inline speaker names and ruby readings. They are not words and exclude digits, Latin text and most punctuation. Sorted font character maps and texture noise are excluded.",'',
        '## Translation progress','',f"{summary['drafted_rows']:,} English drafts are written across the queued categories; {summary['unfilled_rows']:,} queued records remain unfilled. The total queue of {summary['queue_rows']:,} includes the heuristic executable candidates, supplemental setup records and English-title normalization. Unfilled breakdown: {summary['unfilled_breakdown'].get('excluded_technical_candidates',0)} excluded technical candidates, {summary['unfilled_breakdown'].get('held_Mao_formatter',0)} held Mao formatter record, {summary['unfilled_breakdown'].get('held_staff_credit_blocks',0)} held staff-credit blocks, {summary['unfilled_breakdown'].get('held_native_menu_labels',0)} held native-menu labels and {summary['unfilled_breakdown'].get('other_unfilled',0)} other records. These include excluded technical candidates and held formatter/staff records, rather than a count of confirmed untranslated player texts. See `translation_progress.en.json` for current per-category counts and statuses.",'',
        f"The glossary contains {summary['glossary_entries']} entries across {len(gloss_files)} files. Source-backed franchise spellings are distinguished from provisional game-original names. Unknown gender and traits remain explicit.",'',
        f"All drafts pass control-order, recognized numeric-argument (including fixed-width glossary-link and color arguments), percent-placeholder and Japanese-in-target checks. English-only `*.en.json` exports contain no Japanese script. Draft statuses remain provisional. {len(verified_menu)} main-menu labels have separate cold-boot rendering evidence; dialogue drafts still require meaning review, complete-scene context, measured layout, ruby-span rebuilding and in-game testing.", '',
        '## Remaining audit and build work','',
        f"- Title credit candidate: {title.get('version','not built')}; bottom-right version/credit display QA: {title_passed}. New builds regenerate the stamp from build.json and require an incremented version. See TITLE_SCREEN.md.",
        '- The 417 MB HP.DNS installer is PGD-encrypted; duplication with the main archive has not been established.',
        f"- btl/sys_tbl.bin contributes {len(glyph_jp)} decoded glyph-label occurrences and {len(glyph_unique)} distinct labels, with exact byte round trips. {summary['glyph_labels_matching_drafted_executable_sources']} match drafted executable sources and {summary['glyph_labels_matching_CPL_entity_names']} match CPL entity-name sources. These are overlapping resource observations, not additional missing translations. This glyph-index resource's native visibility remains unproved; other glyph-index tables still need audit.",
        f'- Media audit sampled {media.get("movie_assets",0)} movies / {media.get("movie_frames_reviewed",0)} frames and observed Japanese in {len(media.get("movies_with_Japanese_observed",[]))} movies. Sampled observations do not establish an exhaustive text count. Current {current_version} installs {len(installed["installed_movie_assets"])} translated movie asset(s), with {installed["installed_prologue_primary_captions"]} primary prologue captions, {installed["installed_prologue_superseding_fields"]} superseding fields and {installed["installed_prologue_moving_signs"]} moving sign(s). Other movie translations remain outside installation. It also installs {installed["installed_battle_whole_labels"]} whole battle labels and {installed["installed_battle_fragment_groups"]} fragment groups, {installed["installed_copyright_records"]} copyright/notice records in {installed["installed_copyright_textures"]} textures, and {installed["installed_external_psp_metadata_files"]} external PSP metadata images. Installation/static pixel review is separate from runtime display proof; copyright and external PSP metadata display QA remain pending. These counts stay separate from the structured-text headline.',
        f"- Supplemental gallery labels: {summary['supplemental_gallery_ui_records']} records ({summary['supplemental_gallery_generic_labels']} generic UI labels, {summary['supplemental_gallery_franchise_season_titles']} franchise/season titles, {summary['supplemental_gallery_knowledge_categories']} Knowledge categories and {summary['supplemental_gallery_original_category_labels']} Original category label). They remain separate from the confirmed Japanese-bearing headline pending overlap reconciliation. Current installation: {installed['installed_gallery_typed_labels']} typed labels. Native gallery QA: {summary['gallery_display_qa_passed']}; status {summary['gallery_candidate_status']}. Scope: {summary['gallery_verification_scope']}. Evidence: {summary['gallery_candidate_evidence']}. Remaining limitations: {summary['gallery_remaining_limitations']}.",
        f"- Broader typed-menu working queue: {summary['supplemental_native_menu_drafts']} drafts and {summary['supplemental_native_menu_held']} held records. Of the drafts, {summary['supplemental_native_menu_installed_drafts']} source labels are installed through the current field UI patch, including compact display variants. Other drafts remain uninstalled; broader native visibility and consumer routes remain unproved. They are separate from the structured Japanese-bearing headline.",
        f"- Current field UI patch: {summary['field_ui_installed_labels']} relocated labels/help/action prompts and {summary['field_ui_episode_banner_remaps']} guarded episode-banner replacement. Shared Options display QA: {summary['field_ui_options_display_verified']}. Other field screens verified: {summary['field_ui_other_screens_verified']}. Natural Episode 1 interception verified: {summary['field_ui_natural_episode_interception_verified']}. Evidence: {summary['field_ui_evidence']}. The {summary['supplemental_field_ui_records']} supplemental queue records overlap earlier source drafts and do not add to the distinct Japanese-bearing headline.",
        f'- Supplemental battle HUD labels: {summary["supplemental_battle_hud_ui_records"]} typed executable record(s); {installed["installed_special_move_hud_labels"]} installed Special Move label, displayed as {installed["special_move_hud_displayed_target"]}. The inherited unscaled ASCII advances measure Special at47px and the full term at86px within a55px region; only the abbreviation fits. Static proof: {installed["special_move_hud_static_validation"]}. Native battle appearance remains unverified. This record stays separate from the structured-text headline.',
        f'- Dungeon-name image banners: {installed["dungeon_banner_inventory_observations"]} separate native texture observations; {installed["installed_dungeon_banner_labels"]} English bitmap installed and {installed["other_dungeon_banner_assets_pending"]} other banner assets pending. Forest of Encounters uses the existing glossary spelling and 4x lettering rasterization within its unchanged 256x32 allocation. Static installation proof: {installed["dungeon_banner_static_validation"]}. Native banner display/UV remain unverified. These image observations stay outside the structured-text headline; 26 encoded map-name records do not cover these separate images.',
        f"- Current native prologue/media QA: {summary['media_display_qa_passed']}; status {summary['media_candidate_status']}. Scope: {summary['media_verification_scope']}. Evidence: {summary['media_candidate_evidence']}. Remaining limitations: {summary['media_remaining_limitations']}. PC decoding and prepared timing do not establish PSP playback or full-movie readability.",
        '- Executable scanning deliberately omits some ASCII/numeric runtime fragments; those must be preserved and accounted for when rebuilding prompts. Installed executable scopes and supplemental cast-bank integration are recorded in the current build manifest; broader consumer and runtime expansion coverage remains unproved.',
        '- Title/main-menu screenshots and framebuffer metadata are captured. Measure additional dialogue boxes, line counts and runtime name expansions. Original byte slots are not the English text budget; relocation is required.',
        f'- All 420 extracted gallery resources pass byte-identical identity rebuilding and original occurrence/hash checks. Historical 0.1.7 selected-prose display QA: {verified_gallery} passed, covering one complete Red Shield target with six measured soft breaks in three scroll positions. Current wrapping audit: {layout["structured_gallery_drafts"]} drafts, {layout["structurally_prepared"]} structurally prepared and {layout["require_additional_handling"]} requiring additional handling at 330px / 45 glyphs using the historical 0.1.6 font metrics. This is the observed dictionary geometry; other layouts still require measurement. It does not certify current executable display or install the wrapping. See GALLERY_BUILD.md and VWF.md.',
        f'- Supplemental CPL battle resources: {cpl["summary"]["occurrences"] if cpl else 0} byte-string occurrences / {cpl["summary"]["unique_rows"] if cpl else 0} distinct queue records. The name-index0 selector is statically proved; later skill/action consumers and debug visibility remain unresolved. These counts stay separate from the Japanese headline until player-facing overlaps are reconciled.',
        '- The 0.1.3 opening candidate cold-boots with all 96 supported Latin glyphs loaded in compact 64×64 source slots. Twelve hook sites and all loaded glyph pixels/lookup entries passed checks; 76 actual menu uploads/sprites verify the five labels. Earlier menu-only builds remain separate under work/output.',
        f"- Current {current_version} selected opening text: {selected_opening_records} records have scoped native display evidence; selected opening display QA: {opening_passed}, status {summary['opening_candidate_status']}. Scope: {summary['opening_verification_scope']}. This evidence does not certify broader dialogue or gameplay. Only matching version/ISO/executable/archive proofs contribute. Historical 0.1.6 separately verified {historical_verified_dialogue} relocated record, both pages and speaker, with traced proportional draws. See DIALOGUE_BUILD.md and the version-specific opening proof for the latest scope.",
        f"- Current {current_version} setup display QA: {setup_passed}; status {summary['setup_candidate_status']}. Scope: {summary['setup_verification_scope']}. Setup fields use Latin defaults and resident 4x VWF; ASCII OSK limits remain subordinate to saved CP932 byte capacities. Remaining setup limitations: {summary['setup_remaining_limitations']}. See SETUP_BUILD.md. Verified setup screens do not establish every later game-name expansion or cached-name context.",
        f"- Current {current_version} battle display QA: {battle_passed}; status {summary['battle_candidate_status']}. Scope: {summary['battle_verification_scope']}. Observations: {summary['battle_observations']}. Display defects: {summary['battle_display_defects']}. Remaining limitations: {summary['battle_remaining_limitations']}. Encounter evidence does not establish visibility/readability of all installed atlas labels or full-game battle coverage.",
        f"- Historical0.1.23 battle follow-up: {previous_battle.get('scope','No matching historical proof available.')} Evidence: {previous_battle_path}. This is a separate previous-build observation and does not establish current encounter completion.",
        f"- Current {current_version} save display QA: {save_passed}; system-save creation: {summary['system_save_creation_passed']}; status {summary['save_candidate_status']}. Scope: {summary['save_verification_scope']}. Remaining limitations: {summary['save_remaining_limitations']}. This is the historical creation observation; restart loading is reported separately below.",
        f"- Current {current_version} system-save restart loading: {summary['system_save_restart_load_passed']}; status {summary['save_restart_candidate_status']}. Scope: {summary['save_restart_scope']}. Evidence: {summary['save_restart_evidence']}. Remaining limitations: {summary['save_restart_remaining_limitations']}. System-save proofs do not certify game-save creation/loading.",
        '- The 0.1.4 geometry experiment failed movie AudioThread creation with NO_MEMORY. The 0.1.5 replacement saved 11,328 loaded bytes and cold-boots successfully, but its manager lookup left the native bubble unchanged. Version 0.1.6 corrects target-segment address relocation, embedded-array lookup and page-range validation. Scope remains stationary, unrotated centered control-light Latin pages. Wider scene/template/animation coverage still needs testing.',
        '- Output is native 480×272. Historical 4× glyph-source observations cover menu, opening body/speaker and selected dictionary body draws; current setup/opening/battle/save proof scopes are stated separately above. Increased emulator internal resolution, complete font/measurement coverage, wrapping outside the selected gallery path, ruby, broader runtime-name expansions, both protagonist variants outside the reviewed setup, game-save/load/restart, broader battles and native hardware remain unverified. The supplied original ISO is unchanged; local candidates are separate and no release was created.', '',
        '## Reproduce','',
        'Use tools/inspect_iso.py, tools/unpack_cpk.py, tools/decrypt_executable.ps1, tools/extract_corpus.py, tools/extract_tables.py and tools/scan_executable.py. tools/rebuild_gallery.py --audit-all reproduces the gallery identity/occurrence checks; tools/audit_translation_encoding.py audits draft serialization. Every writer has an explicit opt-in after dry-run review. Source data and translation working files stay ignored. Existing translation IDs/targets are retained when corpus extraction is rerun. Run tools/strip_jp.py on completed working batches before future commits. The folder currently has no project Git history; no commit or GitHub release was made.',''])
    (root/'TEXT_INVENTORY.md').write_text('\n'.join(lines),encoding='utf-8')
    if a.preview_dir:print('DRY PREVIEW: review copies written beneath work/source; published docs unchanged.')

if __name__=='__main__':main()
