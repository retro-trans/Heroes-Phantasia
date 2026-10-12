"""Verify the installed larger stat labels and preservation; dry-run by default."""
import argparse,json
from pathlib import Path
from PIL import Image
from append_cpk import sha
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from prepare_battle_badges_044 import prepare,digest,extract,BASE,RESOURCE,UI,OUT,QUEUE

ROOT=Path('work/output/0.1.44-title-credit-vwf-4x-candidate')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    mp=ROOT/'manifest.en.json';m=json.loads(mp.read_text(encoding='utf-8'))
    base=json.loads((BASE.parent/'manifest.en.json').read_text(encoding='utf-8'))
    candidate,proposal,old,new=prepare()
    if m['version']!='0.1.44' or sha(ROOT/'HP.CPK')!=m['dialogue_cpk_sha256'] or sha(BASE)!=base['dialogue_cpk_sha256']:
        raise ValueError('Build/archive identity differs')
    _,oldrows=inventory(BASE);_,rows=inventory(ROOT/'HP.CPK')
    if len(rows)!=len(oldrows):raise ValueError('Resource count differs')
    changed=[q['path']for q,r in zip(oldrows,rows)if q!=r]
    if set(changed)!={RESOURCE,'menu/TitleMenu_Data.bin'}:raise ValueError('Unexpected changed archive rows')
    row=next(r for r in rows if r['path']==RESOURCE)
    if row['compression']!='none' or extract(ROOT/'HP.CPK',row)!=candidate:
        raise ValueError('Installed candidate differs')
    if Image.open(UI/'atlas_after.png').convert('RGBA').tobytes()!=new.tobytes():
        raise ValueError('Installed pixels differ from reviewed asset')
    if (OUT/'sys_all.bin').read_bytes()!=candidate:raise ValueError('Prepared candidate changed')
    iso=Path(m['iso_path'])
    if sha(iso)!=m['iso_sha256']:raise ValueError('ISO identity differs')
    iso_cpk=next(r for r in iso_inventory(iso)if r['path']=='PSP_GAME/USRDIR/HP.CPK')
    with iso.open('rb')as f:
        f.seek(iso_cpk['offset']+row['offset'])
        if f.read(len(candidate))!=candidate:raise ValueError('Nested ISO candidate differs')
    if m['output_elf_sha256']!=base['output_elf_sha256'] or sha(ROOT/'EBOOT.BIN')!=m['output_elf_sha256']:
        raise ValueError('Executable changed')
    if m['dungeon_banner_translation_coverage']['bitmap_labels']!=30 or not m['prologue_movie_translation_coverage']['installed_in_iso']:
        raise ValueError('Previous translation coverage was dropped')
    proof=dict(schema_version=1,version=m['version'],status='larger_bold_battle_stat_badges_installed_static_checks_passed',
        iso_sha256=m['iso_sha256'],archive_sha256=m['dialogue_cpk_sha256'],executable_sha256=m['output_elf_sha256'],
        resource=RESOURCE,candidate_sha256=proposal['candidate_sha256'],entries=proposal['entries'],
        archive_readback_exact=True,nested_ISO_readback_exact=True,reviewed_pixels_exact=True,
        unselected_atlas_pixels_and_all_nonpixel_bytes_exact=True,native_rectangles_palette_and_arrows_preserved=True,
        changed_resource_rows=changed,unchanged_resource_rows=len(rows)-2,executable_VWF_bubbles_defaults_identical_to_043=True,
        all_30_location_banners_preserved=True,English_prologue_preserved=True,native_battle_display_verified=False,
        scope='Eight stat-badge lettering rectangles only; native battle animation/sampling and full-game visual coverage remain unverified.')
    print(json.dumps(proof,indent=2))
    print('Queue status update: first 8 bitmap rows; full semantic targets unchanged; compact display notes added.')
    if not a.write:print('DRY RUN: no proof, manifest or queue writes.');return
    dest=UI/'validation.en.json'
    if dest.exists():raise ValueError('Fresh proof required')
    dest.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    m['battle_badge_readability_coverage']=dict(labels=8,reported_label='Defense',displayed_label='DEF',
        font_native_pixels=16,previous_font_native_pixels=8,ink_height=12,previous_ink_height=6,
        static_pixels_reviewed=True,installed_in_archive=True,installed_in_iso=True,native_battle_display_verified=False,
        validation=str(dest),preparation_report=str(OUT/'proposal.en.json'))
    m['battle_bitmap_translation_coverage']['compact_stat_labels']=8
    m['battle_bitmap_translation_coverage']['readability_validation']=str(dest)
    m['status']=proof['status'];mp.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
    queue=json.loads(QUEUE.read_text(encoding='utf-8'))
    for r,entry in zip(queue['rows'][:8],proposal['entries']):
        r['status']='installed_compact_bold_bitmap_static_reviewed_native_display_pending'
        r['notes']='0.1.44 compact bitmap display: '+entry['displayed_text']+'. Full semantic target retained; '+str(entry['font_native_pixels'])+'px bold lettering inside the original 32x14 rectangle. Natural battle display remains unverified.'
    QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
