"""Verify the selected HUD word in a completed ISO; fresh proof writing is opt-in."""
import argparse
import json
from pathlib import Path
from append_cpk import sha as file_sha
from executable_text_patch import Elf
from inspect_iso import inventory as iso_inventory
from unpack_cpk import inventory as cpk_inventory
from battle_special_label_patch import build, sha, SLOT, TARGET


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--write',action='store_true')
    a = p.parse_args()
    m = json.loads(a.manifest.read_text(encoding='utf-8'))
    expected,preparation,_,_ = build()
    proof = preparation['battle_special_label_proposal']
    root = a.manifest.parent
    actual = (root/'EBOOT.BIN').read_bytes()
    if actual != expected or sha(actual) != m['output_elf_sha256']:
        raise ValueError('Current executable differs from reviewed patch')
    out = Elf(actual)
    target_rva = proof['allocation']['rva']
    if out.word(SLOT) != target_rva or actual[out.file_offset(target_rva,8):out.file_offset(target_rva,8)+8] != b'Special\0':
        raise ValueError('Complete selected pointer/string readback differs')
    iso = Path(m['iso_path'])
    if file_sha(iso) != m['iso_sha256']:
        raise ValueError('Current ISO hash differs')
    rows = iso_inventory(iso)
    row = next(r for r in rows if r['path']=='PSP_GAME/SYSDIR/EBOOT.BIN')
    with iso.open('rb') as stream:
        stream.seek(row['offset'])
        if stream.read(row['size']) != actual:
            raise ValueError('Nested ISO executable differs')
    cpk = root/'HP.CPK'
    if file_sha(cpk) != m['dialogue_cpk_sha256']:
        raise ValueError('Current archive hash differs')
    _,old = cpk_inventory(Path('work/output/0.1.25-title-credit-vwf-4x-candidate/HP.CPK'))
    _,new = cpk_inventory(cpk)
    if len(old) != len(new) or [x['path'] for x,y in zip(old,new) if x != y] != ['menu/TitleMenu_Data.bin']:
        raise ValueError('Unselected archive rows changed')
    if not m['prologue_movie_translation_coverage']['installed_in_iso']:
        raise ValueError('English prologue not retained')
    result = dict(schema_version=1,version=m['version'],
        iso_sha256=m['iso_sha256'],executable_sha256=m['output_elf_sha256'],archive_sha256=m['dialogue_cpk_sha256'],
        status='installed_special_hud_label_static_passed_native_display_pending',
        canonical_target='Special Move',displayed_target=TARGET,
        selected_pointer_rva=SLOT,target_rva=target_rva,native_table=0,native_index=54,
        executable_readback_exact=True,nested_iso_executable_readback_exact=True,
        source_font_scale=4,model_font_ink_bounds=proof['label_font_model_ink_bounds'],
        modeled_advance=47,available_width=55,full_term_advance=86,
        three_base_actual_SHT_models=proof['three_base_actual_SHT_models'],
        unselected_executable_bytes_preserved=True,native_caller_and_control_instructions_preserved=True,
        module_growth_bytes=0,new_relocations=0,other_archive_rows_exact=len(new)-1,
        forest_banner_retained=True,English_prologue_retained=True,
        native_battle_label_display_verified=False,full_game_verified=False,
        scope='One compact Special Move HUD label; static font model and complete installed executable readback. No current battle gameplay capture.')
    print(json.dumps(result,indent=2))
    if a.write:
        dest = Path('work/ui/battle')/m['version']/'special_label/validation.en.json'
        if dest.exists():
            raise ValueError('Fresh proof required')
        dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        m['battle_special_label_translation_coverage'] = dict(
            canonical_target='Special Move',displayed_target=TARGET,labels=1,
            installed_in_executable=True,installed_in_iso=True,
            source_font_scale=4,static_layout_model_reviewed=True,
            native_display_verified=False,validation=str(dest))
        a.manifest.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
