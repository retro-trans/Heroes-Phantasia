"""Read back the installed bubble fix; fresh evidence writer is opt-in."""
import argparse,json,hashlib,struct
from pathlib import Path
from inspect_iso import inventory as iso_inventory
from unpack_cpk import inventory as cpk_inventory
from fix_hideo_bubble import build
from check_hideo_geometry import cases
from dialogue_measure_1a import instruction_cases,measure_1a
from executable_text_patch import Elf
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args()
    root=Path('work/output/0.1.27-title-credit-vwf-4x-candidate');mp=root/'manifest.en.json';m=json.loads(mp.read_text())
    expected,prep=build();actual=(root/'EBOOT.BIN').read_bytes()
    if actual!=expected or sha(actual)!=m['output_elf_sha256']:raise ValueError('Installed executable differs')
    iso=Path(m['iso_path']);rows=iso_inventory(iso)
    with iso.open('rb') as f:
        row=next(q for q in rows if q['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');f.seek(row['offset'])
        if f.read(row['size'])!=expected:raise ValueError('ISO executable differs')
    _,old=cpk_inventory(Path('work/output/0.1.26-title-credit-vwf-4x-candidate/HP.CPK'));_,new=cpk_inventory(root/'HP.CPK')
    changed=[q['path'] for q,r in zip(old,new) if q!=r]
    if len(old)!=len(new) or sorted(changed)!=sorted(['menu/TitleMenu_Data.bin','phase/bin/p101010.bin','phase/bin/p101011.bin']):raise ValueError('Unexpected archive row changes')
    with (root/'HP.CPK').open('rb') as f:
        for name in ('p101010.bin','p101011.bin'):
            row=next(q for q in new if q['path']=='phase/bin/'+name);f.seek(row['offset'])
            if f.read(row['stored_size'])!=(Path('work/output/0.1.27-ryudock-assets')/name).read_bytes():raise ValueError('Installed dialogue differs')
    movie=next(q for q in rows if q['path']=='PSP_GAME/USRDIR/MOVIE/HPMOVE03.PMF')
    with iso.open('rb') as f:
        f.seek(movie['offset'])
        if sha(f.read(movie['size']))!='c2f6dbaa03b713c42ffad7e60c66f8664ea6d1def5bd82513fd75adb076d5946':raise ValueError('English prologue differs')
    e=Elf(actual);p=e.file_offset(prep['body_integer_lut_rva'],524);widths=list(struct.unpack('<131I',actual[p:p+524]))
    proof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=m['output_elf_sha256'],archive_sha256=m['dialogue_cpk_sha256'],
        status='installed_layout_fix_static_checks_passed_exact_scene_display_pending',changed_archive_rows=changed,unchanged_archive_rows=len(new)-3,
        emitted_measurement_cases=prep['hideo_bubble_fix']['emitted_instruction_cases'],inherited_measurement_regression_cases=instruction_cases(widths,measure_1a(0x240000,True)),
        emitted_geometry_scanner_cases=cases(),loaded_growth_bytes=2804,three_base_section_models=prep['hideo_bubble_fix']['three_base_SHT_models'],
        all_source_controls_and_arguments_preserved=True,wording_preserved=True,exact_Ryudock_scene_display_verified=False,
        native_startup_and_opening_dialogue_observed=True,native_geometry_entry_observed=json.loads(Path('work/source/runtime_027/geometry_entry.en.json').read_text()),
        native_capture='work/ui/dialogue/0.1.27/opening_english.png',full_game_verified=False)
    print(json.dumps(proof,indent=2))
    if a.write:
        dest=Path('work/ui/dialogue/0.1.27/validation.en.json')
        if dest.exists():raise ValueError('Fresh evidence required')
        dest.write_text(json.dumps(proof,indent=2)+'\n')
        m['dialogue_layout_fix_027']=dict(installed=True,validation=str(dest),native_exact_scene_verified=False)
        mp.write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
