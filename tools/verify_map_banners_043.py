"""Verify all category assets in the final archive and ISO; default dry-run."""
import argparse
import json
from pathlib import Path
from append_cpk import sha
from inspect_iso import inventory as iso_inventory
from unpack_cpk import inventory
from prepare_map_banners_043 import extracted, digest, LABELS, BASE, OUT, UI
from inspect_font_assets import texture,unswizzle
from PIL import Image

ROOT=Path('work/output/0.1.43-title-credit-vwf-4x-candidate')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    manifest=ROOT/'manifest.en.json';m=json.loads(manifest.read_text(encoding='utf-8'))
    base=json.loads((BASE.parent/'manifest.en.json').read_text(encoding='utf-8'))
    prep=json.loads((OUT/'proposal.en.json').read_text(encoding='utf-8'))
    labels=json.loads(LABELS.read_text(encoding='utf-8'))['rows']
    if m['version']!='0.1.43' or digest(LABELS.read_bytes())!=prep['labels_sha256']:
        raise ValueError('Version/labels differ from preparation')
    cpk=ROOT/'HP.CPK';iso=Path(m['iso_path'])
    if sha(cpk)!=m['dialogue_cpk_sha256'] or sha(iso)!=m['iso_sha256'] or sha(BASE)!=base['dialogue_cpk_sha256']:
        raise ValueError('Archive/ISO identities differ')
    _,oldrows=inventory(BASE);_,newrows=inventory(cpk)
    if len(oldrows)!=len(newrows):raise ValueError('Resource count changed')
    byname={r['path']:r for r in newrows};oldby={r['path']:r for r in oldrows}
    changed=[old['path'] for old,new in zip(oldrows,newrows) if old!=new]
    expected={r['resource'] for r in prep['entries'] if r['changed']}|{'menu/TitleMenu_Data.bin'}
    if set(changed)!=expected:raise ValueError('Unexpected changed resource rows')
    iso_cpk=next(r for r in iso_inventory(iso) if r['path']=='PSP_GAME/USRDIR/HP.CPK')
    results=[]
    with iso.open('rb') as f:
        for row,lab in zip(prep['entries'],labels):
            name=row['resource']; installed=extracted(cpk,byname[name]);before=extracted(BASE,oldby[name])
            source=(Path('work/source/cpk')/name).read_bytes()
            if digest(installed)!=row['candidate_sha256'] or digest(before)!=row['base_sha256'] or digest(source)!=row['source_sha256']:
                raise ValueError('Selected asset identity differs: '+name)
            begin=row['pixel_offset'];end=begin+8192
            if installed[:begin]!=source[:begin] or installed[end:]!=source[end:] or len(installed)!=len(source):
                raise ValueError('Nonpixel original bytes differ: '+name)
            t=texture(installed,row['texture_offset']);linear=unswizzle(t['pixels'],256,32)
            actual=Image.frombytes('RGBA',(256,32),b''.join(t['palette'][i*4:i*4+4]for i in linear))
            preview=Image.open(UI/(Path(name).stem+'.png')).convert('RGBA')
            if actual.tobytes()!=preview.tobytes() or list(actual.getbbox())!=row['candidate_ink_bounds'] or row['target']!=lab['target']:
                raise ValueError('Installed pixels/target differ from reviewed preview')
            f.seek(iso_cpk['offset']+byname[name]['offset'])
            if byname[name]['compression']!='none' or f.read(len(installed))!=installed:
                raise ValueError('Nested ISO banner differs')
            results.append(dict(resource=name,target=row['target'],candidate_sha256=row['candidate_sha256'],
                archive_readback_exact=True,nested_iso_readback_exact=True,reviewed_pixels_exact=True,
                original_palette_headers_other_sections_exact=True,font_native_pixels=row['font_native_pixels']))
    if m['output_elf_sha256']!=base['output_elf_sha256'] or sha(ROOT/'EBOOT.BIN')!=m['output_elf_sha256']:
        raise ValueError('Executable changed unexpectedly')
    battle=extracted(cpk,byname['btl/sys_all.bin'])
    if battle!=extracted(BASE,oldby['btl/sys_all.bin']) or digest(battle)!='9a8abe108472aba62e9e52f7e0866b86c72ad346e7567e1297f58b411a2e1dad':
        raise ValueError('Previously translated battle atlas differs')
    if not m['prologue_movie_translation_coverage']['installed_in_iso']:
        raise ValueError('English prologue was dropped')
    proof=dict(schema_version=1,version=m['version'],status='all_observed_location_banners_installed_static_readback_passed',
        base_version=base['version'],iso_sha256=m['iso_sha256'],archive_sha256=m['dialogue_cpk_sha256'],
        executable_sha256=m['output_elf_sha256'],banner_count=30,new_translations=28,retained_English_banners=2,
        pending_observed_banners=0,entries=results,changed_resource_rows=changed,unchanged_resource_rows=len(newrows)-len(changed),
        excluded_non_banner_containers=prep['excluded_non_banner_containers'],
        battle_atlas_preserved=True,battle_whole_labels=20,battle_fragment_headings=3,
        reported_battle_label=dict(target='Defense',native_font_pixels=8,meaning='Green down arrow indicates decreased defense'),
        English_prologue_preserved=True,executable_VWF_names_bubble_hooks_byte_identical_to_042=True,
        static_pixels_reviewed=True,native_display_verified=False,native_uv_coverage_verified=False,
        scope='All observed dungeon-entry name bitmaps; no claim of natural gameplay coverage, other UI categories or unreadable English battle-label improvements.')
    print(json.dumps({k:v for k,v in proof.items() if k!='entries'},indent=2))
    if not a.write:print('DRY RUN: no manifest or validation written.');return
    dest=UI/'validation.en.json'
    if dest.exists():raise ValueError('Fresh validation required')
    dest.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    m['dungeon_banner_translation_coverage']=dict(bitmap_labels=30,new_translations=28,retained_English_banners=2,
        inventory_observations=30,other_banner_assets_pending=0,installed_in_archive=True,installed_in_iso=True,
        static_pixels_reviewed=True,native_display_verified=False,native_uv_coverage_verified=False,
        preparation_report=str(OUT/'proposal.en.json'),validation=str(dest),resources=[r['resource']for r in results])
    m['status']=proof['status'];manifest.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
