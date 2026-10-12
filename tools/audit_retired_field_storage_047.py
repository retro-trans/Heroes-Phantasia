"""Check current typed references before reusing retired field storage."""
import argparse
import json
from pathlib import Path
from executable_text_patch import Elf, reference_index
from prepare_field_labels_046 import BASE, SOURCE_SHA, sha


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');args=ap.parse_args()
    root=Path('work/output/0.1.47-field-label-assets')
    report=json.loads((root/'executable.en.json').read_text(encoding='utf8'))
    scope=report['field_labels_047'];incoming=(BASE/'EBOOT.BIN').read_bytes()
    if sha(incoming)!=SOURCE_SHA or sha((root/'EBOOT.BIN').read_bytes())!=report['output_elf_sha256']:
        raise ValueError('Frozen input/output identity differs')
    selected={r['pointer_slot']for r in scope['labels']}
    ranges=[(r['start'],r['end'])for r in scope['retired_menu_regions']]
    bank=scope['retired_notification_bank'];ranges.append((bank['rva'],bank['rva']+bank['bytes']))
    refs,issues=reference_index(Elf(incoming));pending=[]
    for ref in refs:
        if any(a<=ref['address']<b for a,b in ranges):
            if ref['kind']!='R_MIPS_32' or len(ref['sites'])!=1 or ref['sites'][0]not in selected:
                raise ValueError('A live inherited reference still uses retired backing: '+str(ref))
            pending.append(ref['sites'][0])
    if set(pending)!=selected or len(pending)!=28:raise ValueError('Expected exact pending label-owner set differs')
    proof=dict(version='0.1.47',input_executable_sha256=SOURCE_SHA,output_executable_sha256=report['output_elf_sha256'],
        typed_references_examined=len(refs),retired_regions=len(ranges),selected_label_owners_retargeted=28,
        other_inherited_typed_references_into_retired_storage=0,
        unrelated_reference_inventory_issues=len(issues),
        scope='Read-only typed reference audit of the current 0.1.45 input, including existing added helpers; '
              'the only remaining original menu owners are the 28 labels replaced in this build. '
              'This is a relocation-derived audit, not a claim of exhaustive arbitrary runtime pointer analysis.')
    print(json.dumps(proof,indent=2))
    if not args.write:print('DRY RUN: no proof written.');return
    dest=Path('work/ui/field_labels/0.1.47/retired_storage_audit.en.json')
    if dest.exists():raise ValueError('Fresh evidence required')
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
