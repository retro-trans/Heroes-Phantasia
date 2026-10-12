"""Read installed menu/notices in the isolated 0.1.46 emulator; dry by default."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from executable_text_patch import encoded_text
from ppsspp_debug import Debugger

ROOT = Path('work/output/0.1.46-title-credit-vwf-4x-candidate')
UI = Path('work/ui/field_labels/0.1.46')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', type=int, default=45403)
    ap.add_argument('--version', choices=['0.1.46','0.1.47'], default='0.1.46')
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args()
    root = Path('work/output')/(args.version+'-title-credit-vwf-4x-candidate')
    ui = Path('work/ui/field_labels')/args.version
    manifest = json.loads((root/'manifest.en.json').read_text(encoding='utf8'))
    prep = manifest['setup_patch']; scope = prep[f"field_labels_{int(args.version.split('.')[-1]):03}"]
    if hashlib.sha256((root/'EBOOT.BIN').read_bytes()).hexdigest() != manifest['output_elf_sha256']:
        raise ValueError('Built executable identity differs')
    d = Debugger(args.port)
    try:
        module = next(row for row in d.call('hle.module.list')['modules'] if row['name'] == 'hp_proj')
        base = module['address']; labels = []; notices = []
        for row in scope['labels']:
            ptr = struct.unpack('<I', d.read(base+row['pointer_slot'], 4))[0]
            raw = encoded_text(row['target'], 'ascii')+b'\0'
            if ptr != base+row['target_rva'] or d.read(ptr, len(raw)) != raw:
                raise ValueError('Complete native label differs: '+row['target'])
            labels.append(dict(index=row['native_index'], target=row['target'], loaded_pointer=ptr,
                               complete_target_exact=True))
        for row in scope['notices']:
            source = d.read(base+row['source_payload_rva'], row['source_payload_bytes'])
            raw = encoded_text(row['target'], 'ascii')+b'\0'
            if hashlib.sha256(source).hexdigest() != row['source_payload_sha256'] or d.read(base+row['target_payload_rva'], len(raw)) != raw:
                raise ValueError('Complete native notice key/target differs: '+row['id'])
            notices.append(dict(id=row['id'], target=row['target'], complete_key_and_target_exact=True))
        proof = dict(schema_version=1, version=manifest['version'], iso_sha256=manifest['iso_sha256'],
            executable_sha256=manifest['output_elf_sha256'], archive_sha256=manifest['dialogue_cpk_sha256'],
            module_base=base, labels=labels, notices=notices, native_loaded_strings_verified=True,
            event_occurrences=scope['event_occurrences'], natural_menu_or_notice_display_verified=False,
            scope='Read-only live checks of all 28 shared pointers and 12 complete notice keys/targets. '
                  'Instruction-case tests cover exact dispatch separately; natural gameplay placement remains unverified.')
        print(json.dumps(dict(version=proof['version'], module_base=base, labels=len(labels), notices=len(notices),
                             complete_loaded_strings_verified=True, natural_gameplay_verified=False), indent=2))
        if not args.write: print('DRY RUN: no evidence written.'); return
        dest = ui/'loaded_strings.en.json'
        if dest.exists(): raise ValueError('Fresh evidence required')
        ui.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(proof, indent=2)+'\n', encoding='utf8')
    finally:
        d.close()


if __name__ == '__main__': main()
