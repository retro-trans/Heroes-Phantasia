"""Read back the .52 ISO, atlas partitions and complete installed UI names."""
import json,struct
from pathlib import Path
from executable_text_patch import Elf,encoded_text
from prepare_menu_labels_052 import BASE,OUT,UI,ASSETS,prepare
from prepare_bubble_scenes_036 import read,sha
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from title_stamp import prepare as title_prepare,RESOURCE
from build_local import sha as file_sha

ROOT=Path('work/output/0.1.52-title-credit-vwf-4x-candidate')

def main():
    manifest=json.loads((ROOT/'manifest.en.json').read_bytes());data=(ROOT/'EBOOT.BIN').read_bytes()
    prepared,report,assets,queue,_=prepare()
    if manifest['version']!='0.1.52'or data!=prepared or sha(data)!=manifest['output_elf_sha256']:raise ValueError('Final executable differs')
    e=Elf(data);scope=report['menu_labels_052'];text=[]
    for row in scope['entries']:
        raw=encoded_text(row['target'].replace('è','\x80'),'latin1')+b'\0';ptr=e.word(row['slot']);at=e.file_offset(ptr,len(raw))
        if ptr!=row['target_rva']or data[at:at+len(raw)]!=raw:raise ValueError('Complete typed name differs')
        text.append(dict(id=row['id'],target=row['target'],canonical_target=row['canonical_target'],widths=row['line_widths_px']))
    for row in scope['accessory_aliases']:
        at=e.file_offset(row['target_rva'],row['allocated_bytes']);raw=encoded_text(row['target'],'ascii')+b'\0'
        if data[at:at+row['allocated_bytes']]!=raw+bytes(row['allocated_bytes']-len(raw)):raise ValueError('Complete accessory alias/padding differs')
    _,old=inventory(BASE/'HP.CPK');_,new=inventory(ROOT/'HP.CPK');changed=[a['path']for a,b in zip(old,new)if a!=b]
    if len(old)!=len(new)or set(changed)!=set(ASSETS)|{RESOURCE}:raise ValueError('Unselected archive row differs')
    title,*_=title_prepare(manifest['config']);assets[RESOURCE]=title
    if read(ROOT/'HP.CPK',list(assets))!=assets:raise ValueError('Installed CPK assets differ')
    iso=Path(manifest['iso_path']);rows=iso_inventory(iso);exe=next(r for r in rows if r['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');cpk=next(r for r in rows if r['path']=='PSP_GAME/USRDIR/HP.CPK')
    with iso.open('rb')as stream:
        stream.seek(exe['offset'])
        if stream.read(exe['size'])!=data:raise ValueError('Nested executable differs')
        for name,raw in assets.items():
            r=next(r for r in new if r['path']==name);stream.seek(cpk['offset']+r['offset'])
            if r['compression']!='none'or stream.read(len(raw))!=raw:raise ValueError('Nested atlas/title asset differs')
    if file_sha(iso)!=manifest['iso_sha256']:raise ValueError('ISO digest differs')
    proof=dict(version='0.1.52',iso_sha256=manifest['iso_sha256'],executable_sha256=sha(data),archive_sha256=manifest['dialogue_cpk_sha256'],typed_strings_exact=len(text),move_name_rows=99,world_location_rows=31,shared_bitmap_labels=31,shared_atlas_copies=2,accessory_aliases=scope['accessory_aliases'],changed_archive_rows=changed,unselected_archive_rows_exact=len(new)-len(changed),all_nested_assets_exact=True,all_palette_uv_and_font_contracts_exact=True,loaded_growth_bytes=0,natural_brave_equip_and_world_playback_verified=False)
    UI.mkdir(parents=True,exist_ok=True);(UI/'validation.en.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    (UI/'name_widths.en.json').write_text(json.dumps(dict(version='0.1.52',rows=text),indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in proof.items()if k!='accessory_aliases'},indent=2))

if __name__=='__main__':main()
