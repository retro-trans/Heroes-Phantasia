"""Verify shared battle bitmap category readability and installed preservation."""
import argparse,json
from pathlib import Path
from append_cpk import sha
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from prepare_battle_labels_045 import prepare,extract,BASE,RESOURCE,UI,OUT,QUEUE

ROOT=Path('work/output/0.1.45-title-credit-vwf-4x-candidate')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    mp=ROOT/'manifest.en.json';m=json.loads(mp.read_text(encoding='utf8'))
    base=json.loads((BASE.parent/'manifest.en.json').read_text(encoding='utf8'))
    candidate,proposal,_=prepare()
    assert m['version']=='0.1.45'
    assert sha(ROOT/'HP.CPK')==m['dialogue_cpk_sha256'] and sha(BASE)==base['dialogue_cpk_sha256']
    _,oldrows=inventory(BASE);_,rows=inventory(ROOT/'HP.CPK');assert len(rows)==len(oldrows)
    changed=[q['path'] for q,r in zip(oldrows,rows) if q!=r]
    assert set(changed)=={RESOURCE,'menu/TitleMenu_Data.bin'}
    row=next(r for r in rows if r['path']==RESOURCE)
    assert row['compression']=='none' and extract(ROOT/'HP.CPK',row)==candidate
    assert (OUT/'sys_all.bin').read_bytes()==candidate
    reviewed=json.loads((UI/'proposal.en.json').read_text(encoding='utf8'))
    assert reviewed==proposal
    iso=Path(m['iso_path']);assert sha(iso)==m['iso_sha256']
    iso_cpk=next(r for r in iso_inventory(iso) if r['path']=='PSP_GAME/USRDIR/HP.CPK')
    with iso.open('rb') as f:
        f.seek(iso_cpk['offset']+row['offset']);assert f.read(len(candidate))==candidate
    assert m['output_elf_sha256']==base['output_elf_sha256']==sha(ROOT/'EBOOT.BIN')
    assert m['dungeon_banner_translation_coverage']['bitmap_labels']==30
    assert m['prologue_movie_translation_coverage']['installed_in_iso']
    proof=dict(schema_version=1,version=m['version'],status='battle_bitmap_category_readability_installed_static_checks_passed',
        iso_sha256=m['iso_sha256'],archive_sha256=m['dialogue_cpk_sha256'],executable_sha256=m['output_elf_sha256'],
        resource=RESOURCE,candidate_sha256=proposal['candidate_sha256'],newly_improved_labels=15,
        preserved_improved_stat_badges=8,total_category_labels=23,entries=proposal['entries'],
        archive_readback_exact=True,nested_ISO_readback_exact=True,reviewed_candidate_exact=True,
        all_unselected_atlas_pixels_and_nonpixel_bytes_exact=True,native_geometry_palettes_arrows_preserved=True,
        fragment_model_roundtrip_exact=True,changed_resource_rows=changed,unchanged_resource_rows=len(rows)-2,
        executable_VWF_bubbles_defaults_identical_to_044=True,all_30_location_banners_preserved=True,
        English_prologue_preserved=True,native_battle_display_verified=False)
    print(json.dumps(proof,indent=2))
    print('Queue update: remaining 12 whole labels; full semantic targets retained; display notes added.')
    if not a.write:print('DRY RUN: no proof, manifest or queue writes.');return
    dest=UI/'validation.en.json';assert not dest.exists()
    dest.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    m['battle_bitmap_readability_coverage']=dict(total_category_labels=23,whole_labels=20,fragment_headings=3,
        newly_improved_labels=15,preserved_stat_badges=8,static_pixels_reviewed=True,
        installed_in_archive=True,installed_in_iso=True,native_battle_display_verified=False,
        validation=str(dest),preparation_report=str(OUT/'proposal.en.json'))
    m['battle_bitmap_translation_coverage']['readability_labels']=23
    m['battle_bitmap_translation_coverage']['readability_validation']=str(dest)
    m['status']=proof['status'];mp.write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
    queue=json.loads(QUEUE.read_text(encoding='utf8'))
    for r,e in zip(queue['rows'][8:],proposal['entries'][:12]):
        assert r['id']==e['id'] and r['target']==e['target']
        r['status']='installed_bold_bitmap_static_reviewed_native_display_pending'
        r['notes']='0.1.45 bitmap display: '+e['displayed_text']+'. Full semantic target retained; '+str(e['font_native_pixels'])+'px bold lettering within the existing sprite. Natural battle display remains unverified.'
    QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
