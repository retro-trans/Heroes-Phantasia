"""Read four installed strings in the isolated emulator; no game-state writes."""
import argparse, json, struct
from pathlib import Path
from ppsspp_debug import Debugger
from prepare_world_map_ui import build, sha
from executable_text_patch import encoded_text

ROOT = Path('work/output/0.1.32-title-credit-vwf-4x-candidate')
UI = Path('work/ui/world_map/0.1.32')

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', type=int, default=45387)
    ap.add_argument('--write', action='store_true'); a = ap.parse_args()
    m = json.loads((ROOT/'manifest.en.json').read_text())
    expected, prep, _ = build()
    if (ROOT/'EBOOT.BIN').read_bytes() != expected or m['output_elf_sha256'] != sha(expected):
        raise ValueError('Build executable differs from reviewed preparation')
    d = Debugger(a.port)
    try:
        mod = next(x for x in d.call('hle.module.list')['modules'] if x['name'] == 'hp_proj')
        base = mod['address']; rows = []
        for row in prep['world_map_ui_patch']['entries']:
            pointer = struct.unpack('<I', d.read(base+row['pointer_slot'], 4))[0]
            raw = encoded_text(row['target'], 'ascii')+b'\0'
            if pointer != base+row['rva'] or d.read(pointer, len(raw)) != raw:
                raise ValueError('Native loaded pointer or complete target differs')
            rows.append(dict(id=row['name'], target=row['target'], loaded_pointer=pointer,
                complete_target_and_controls_exact=True))
        proof = dict(version=m['version'], iso_sha256=m['iso_sha256'], executable_sha256=m['output_elf_sha256'],
            archive_sha256=m['dialogue_cpk_sha256'], module_base=base, entries=rows,
            native_loaded_strings_verified=True, natural_world_map_display_verified=False,
            scope='Read-only checks of the four relocated pointers and complete targets/controls. Executable font contracts are checked by the preparation tool; JIT-modified instruction memory is outside this readback. Gameplay placement is unverified.')
        print(json.dumps(proof, indent=2))
        if not a.write: print('DRY RUN: no evidence written.'); return
        dest = UI/'loaded_strings.en.json'
        if dest.exists(): raise ValueError('Fresh evidence required')
        UI.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(proof, indent=2)+'\n', encoding='utf8')
    finally: d.close()

if __name__ == '__main__': main()
