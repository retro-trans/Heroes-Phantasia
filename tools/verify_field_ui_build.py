"""Read back the 0.1.28 field UI install and publish scoped evidence; dry default."""
import argparse,json,struct,shutil
from pathlib import Path
from field_ui_patch import build,sha,LABELS,ACTIONS,QUEUE
from executable_text_patch import Elf
from inspect_iso import inventory as iso_inventory
from unpack_cpk import inventory as cpk_inventory
from append_cpk import sha as file_sha

ROOT=Path('work/output/0.1.28-title-credit-vwf-4x-candidate')
UI=Path('work/ui/field/0.1.28')
REFERENCES=[('episode','25bfc5c3-c2a0-47e8-9b34-f4e0146e23f1'),('talk','6e74069d-c198-4654-8f2c-921f1c1ca6af'),
 ('party','0707fa7d-3b4c-4d4a-bdc6-ca9035bbbb6a'),('catalog','5039a9b8-63f1-4366-a718-067002a676c4'),
 ('tutorial','1910626b-3a59-4b3b-8cfa-9a3b57cb78a6'),('options','1f047e3f-9c38-4931-ac7f-d3373a2cd5b2')]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args()
    mp=ROOT/'manifest.en.json';m=json.loads(mp.read_text());expected,prep,queue=build()
    actual=(ROOT/'EBOOT.BIN').read_bytes()
    if expected!=actual or sha(actual)!=m['output_elf_sha256'] or file_sha(Path(m['iso_path']))!=m['iso_sha256']:
        raise ValueError('Current executable/ISO identity differs')
    rows=iso_inventory(Path(m['iso_path']))
    with Path(m['iso_path']).open('rb') as f:
        r=next(r for r in rows if r['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');f.seek(r['offset'])
        if f.read(r['size'])!=expected:raise ValueError('Nested executable differs')
        r=next(r for r in rows if r['path']=='PSP_GAME/USRDIR/MOVIE/HPMOVE03.PMF');f.seek(r['offset'])
        if sha(f.read(r['size']))!='c2f6dbaa03b713c42ffad7e60c66f8664ea6d1def5bd82513fd75adb076d5946':raise ValueError('English prologue differs')
    if file_sha(ROOT/'HP.CPK')!=m['dialogue_cpk_sha256']:raise ValueError('Archive identity differs')
    _,old=cpk_inventory(Path('work/output/0.1.27-title-credit-vwf-4x-candidate/HP.CPK'));_,new=cpk_inventory(ROOT/'HP.CPK')
    changed=[r['path']for r,s in zip(old,new)if r!=s]
    if len(old)!=len(new) or changed!=['menu/TitleMenu_Data.bin']:raise ValueError('Unselected archive records differ')
    ui=prep['field_ui_patch']
    result=dict(schema_version=1,version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=sha(actual),
      archive_sha256=m['dialogue_cpk_sha256'],status='installed_static_checks_passed_native_field_screens_pending',
      translation_rows=45,relocated_menu_rows=44,episode_banner_rows=1,loaded_growth_bytes=ui['loaded_growth_bytes'],
      new_relocations=ui['new_relocations'],loader_models=ui['loader_models'],entries=ui['entries'],
      episode_banner=ui['episode_inline_banner'],English_prologue_retained=True,source_font_scale=4,
      inherited_LOADED_memory_exact_except_selected_pointers_and_parser_redirect=True,
      nested_iso_executable_readback_exact=True,changed_archive_rows=changed,other_archive_rows_exact=len(new)-1,
      native_options_layout_verified=False,native_party_catalog_tutorial_talk_verified=False,
      natural_episode_banner_interception_verified=False,full_game_verified=False)
    print(json.dumps({k:v for k,v in result.items()if k!='entries'},indent=2))
    if not a.write:print('DRY RUN');return
    dest=UI/'validation.en.json'
    if dest.exists():raise ValueError('Fresh validation required')
    UI.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n')
    refs=[]
    for name,id in REFERENCES:
        source=Path('C:/Users/Binh/AppData/Local/Temp')/('codex-clipboard-'+id+'.png')
        target=UI/('reference_'+name+'.png');shutil.copyfile(source,target)
        refs.append(dict(screen=name,file=str(target),sha256=file_sha(target),source='user screenshot',
          source_build_version_unknown=True,actual_candidate_capture=False))
    layout=dict(schema_version=1,version=m['version'],reference_resolution=[960,544],native_resolution=[480,272],references=refs,
      regions=[dict(screen='episode',native_rect=[0,87,480,99],target='Episode 1 / The First Investigation Request'),
      dict(screen='talk',native_rect=[404,0,76,17],target='Talk'),dict(screen='party',native_rect=[4,30,112,98],
        targets=['Status','Quests','Catalog','Gallery','Tutorial','Options']),
      dict(screen='party_help',native_rect=[0,152,480,48],target='View character stats.'),
      dict(screen='catalog',native_rect=[10,31,100,48],targets=['Spirit','Amulets','Accessories']),
      dict(screen='tutorial',native_rect=[10,31,100,48],targets=['Battle','Field','Menu']),
      dict(screen='options_labels',native_rect=[2,30,198,156],targets=[LABELS[i]for i in range(66,74)]),
      dict(screen='camera_choices',native_rect=[176,110,288,22],targets=['Default','Allies','Enemies','Distant'])],
      estimates_from_reference_screenshots=True,native_field_layout_verified=False)
    (UI/'reference_layout.en.json').write_text(json.dumps(layout,indent=2)+'\n')
    # Keep canonical long terms while recording the width-reviewed UI variants.
    glossary=json.loads(Path('work/glossary/glossary.en.json').read_text(encoding='utf8'))
    canonical={r['ja']:r['en']for r in glossary['entries']};drafts={}
    for p in (Path('work/translation/en/executable_native_menu_0001.json'),Path('work/translation/en/executable_native_menu_0002.json')):
        for r in json.loads(p.read_text(encoding='utf8'))['rows']:
            if r.get('target'):drafts[r['source']]=r['target']
    terms=[]
    for r in queue['rows']:
        if '{' in r['source']:continue
        terms.append(dict(id='field_ui_'+r['id'],category='ui',franchise='Heroes Phantasia',ja=r['source'],
          en=canonical.get(r['source'],drafts.get(r['source'],r['target'])),ui_display=r['target'],
          context='Field menus, options and contextual action labels.',sources=['work/translation/en/executable_field_ui_0001.en.json']))
    for id,ja,en in [('episode_header','エピソード','Episode'),('episode_1_title','始まりの調査依頼','The First Investigation Request')]:
        terms.append(dict(id='field_ui_'+id,category='ui',franchise='Heroes Phantasia',ja=ja,en=en,
          context='Episode heading; preserve the episode number.',sources=['work/translation/en/executable_field_ui_0001.en.json']))
    Path('work/glossary/field_ui_terms.en.json').write_text(json.dumps(dict(schema_version=1,version=m['version'],language='en',entries=terms),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    m['field_ui_translation_coverage']=dict(labels=44,episode_banners=1,installed_in_executable=True,installed_in_iso=True,
      validation=str(dest),native_options_verified=False,native_other_field_screens_verified=False,natural_episode_interception_verified=False)
    mp.write_text(json.dumps(m,indent=2)+'\n')
    print('Validation, user references, glossary terms and manifest coverage written.')

if __name__=='__main__':main()
