"""Installed .49 bubble regression/Latin ruby checks in an isolated emulator."""
import json, struct, sys
from pathlib import Path
import check_english_bubbles_v10_live as check
from executable_text_patch import Elf, encoded_text
from ppsspp_debug import Debugger
from prepare_bubble_reflow_040 import record
from dialogue_tokens import tokenize_bytes

ROOT=Path('work/output/0.1.49-title-credit-vwf-4x-candidate')
UI=Path('work/ui/dialogue/0.1.49')


def main():
    data=(ROOT/'EBOOT.BIN').read_bytes(); m=json.loads((ROOT/'manifest.en.json').read_text())
    prep=m['setup_patch'];e=Elf(data)
    check.build=lambda:(data,prep)
    original=check.definitions
    def definitions():
        defs=original();widths=struct.unpack_from('<131I',data,e.file_offset(prep['body_integer_lut_rva']))
        for r in prep['lina_reflow_049']['records']:
            name=r['resource']; raw=(Path('work/output/0.1.49-dialogue-command-assets')/name).read_bytes()
            fixture=record(name,raw,0,widths);body=r['new_english'].encode('ascii').split(b'\x0e',1)[1]
            lines=r['line_advances'];defs.append(('lina_'+Path(name).stem,fixture['shape'],*fixture['position'],body+b'\0',len(lines),max(lines)/2,1.,0.,True))
        defs.extend([
            ('latin_reading',118,125.,104.,b'hero\x0f2hero\x0f!\x12\x0e\0',1,30.,1.,0.,True),
            ('empty_reading',118,125.,104.,b'A\x0f2\x0f\x12\x0e\0',1,30.,1.,0.,False),
            ('broken_reading',118,125.,104.,b'A\x0f2hero\0',1,30.,1.,0.,False)])
        return defs
    check.definitions=definitions
    sys.argv=[sys.argv[0],'--port','45405','--manifest',str(ROOT/'manifest.en.json'),
              '--run','--output',str(UI/'native_geometry.en.json')]
    check.main()
    p=UI/'native_geometry.en.json';proof=json.loads(p.read_text());proof['version']='0.1.49';p.write_text(json.dumps(proof,indent=2)+'\n')
    d=Debugger(45405)
    try:
        base=next(r['address']for r in d.call('hle.module.list')['modules']if r['name']=='hp_proj')
        labels=[]
        for row in prep['dialogue_commands_048']['labels']+prep['field_labels_047']['labels']:
            pointer=struct.unpack('<I',d.read(base+row['pointer_slot'],4))[0];target=encoded_text(row['target'],'ascii')+b'\0'
            if pointer!=base+row['target_rva']or d.read(pointer,len(target))!=target:raise ValueError('Live label differs: '+row['target'])
            labels.append(dict(native_index=row['native_index'],target=row['target'],complete_loaded_target_exact=True))
        notices=[]
        for row in prep['field_labels_047']['notices']:
            source=d.read(base+row['source_payload_rva'],row['source_payload_bytes']);target=encoded_text(row['target'],'ascii')+b'\0'
            if check.sha(source)!=row['source_payload_sha256']or d.read(base+row['target_payload_rva'],len(target))!=target:raise ValueError('Inherited notice changed')
            notices.append(row['id'])
        loaded=dict(version='0.1.49',iso_sha256=m['iso_sha256'],executable_sha256=check.sha(data),archive_sha256=m['dialogue_cpk_sha256'],labels=labels,notices=notices,native_loaded_strings_verified=True,natural_gameplay_verified=False)
        (UI/'loaded_strings.en.json').write_text(json.dumps(loaded,indent=2)+'\n')
        print('36 live labels and12 inherited notice keys/targets match.')
    finally:d.close()

if __name__=='__main__':main()
