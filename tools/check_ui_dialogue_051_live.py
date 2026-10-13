"""Installed .51 geometry and loaded UI checks in an owned isolated emulator."""
import json,struct,sys
from pathlib import Path
import check_english_bubbles_v10_live as check
from executable_text_patch import Elf,encoded_text
from ppsspp_debug import Debugger
from prepare_bubble_reflow_040 import record
from dialogue_tokens import tokenize_bytes

ROOT=Path('work/output/0.1.51-title-credit-vwf-4x-candidate')
ASSETS=Path('work/output/0.1.51-ui-dialogue-assets')
UI=Path('work/ui/dialogue/0.1.51')

def main():
    data=(ROOT/'EBOOT.BIN').read_bytes();manifest=json.loads((ROOT/'manifest.en.json').read_text());prep=manifest['setup_patch'];e=Elf(data)
    check.build=lambda:(data,prep);original=check.definitions
    widths=struct.unpack_from('<131I',data,e.file_offset(prep['body_integer_lut_rva']))
    def definitions():
        defs=[(*row[:9],True)if row[0]=='other_ruby'else row for row in original()]
        for r in prep['lina_reflow_049']['records']:
            name=r['resource'];raw=(Path('work/output/0.1.49-dialogue-command-assets')/name).read_bytes()
            fixture=record(name,raw,0,widths);body=r['new_english'].encode('ascii').split(b'\x0e',1)[1];lines=r['line_advances']
            defs.append(('lina_'+Path(name).stem,fixture['shape'],*fixture['position'],body+b'\0',len(lines),max(lines)/2,1.,0.,True))
        defs.extend([('latin_reading',118,125.,104.,b'hero\x0f2hero\x0f!\x12\x0e\0',1,30.,1.,0.,True),
            ('empty_reading',118,125.,104.,b'A\x0f2\x0f\x12\x0e\0',1,30.,1.,0.,False),
            ('broken_reading',118,125.,104.,b'A\x0f2hero\0',1,30.,1.,0.,False)])
        for name in ('phase/bin/p101020.bin','phase/bin/p101021.bin'):
            fixture=record(name,(ASSETS/name).read_bytes(),21,widths)
            body=bytes.fromhex(fixture['pages'][0]['body_hex']);lines=[0]
            for t in tokenize_bytes(body,True):
                if t.kind=='latin'and not t.ruby:lines[-1]+=widths[t.code]
                elif t.code==0x11:lines.append(0)
            defs.append(('kogoro_span3_'+Path(name).stem,fixture['shape'],*fixture['position'],body+b'\0',len(lines),max(lines)/2,1.,0.,True))
        defs.extend([('span1',118,125.,104.,b'A\x0f1A\x0f\x12\x0e\0',1,30.,1.,0.,True),
            ('span9',118,125.,104.,b'A\x0f9A\x0f\x12\x0e\0',1,30.,1.,0.,True),
            ('span0_rejected',118,125.,104.,b'A\x0f0A\x0f\x12\x0e\0',1,30.,1.,0.,False)])
        return defs
    check.definitions=definitions
    sys.argv=[sys.argv[0],'--port','45406','--manifest',str(ROOT/'manifest.en.json'),'--run','--output',str(UI/'native_geometry.en.json')]
    check.main();path=UI/'native_geometry.en.json';proof=json.loads(path.read_text());proof['version']='0.1.51';path.write_text(json.dumps(proof,indent=2)+'\n')
    d=Debugger(45406)
    try:
        base=next(r['address']for r in d.call('hle.module.list')['modules']if r['name']=='hp_proj');labels=[]
        for row in prep['ui_dialogue_051']['labels']:
            slot=(0x94760 if row['native_table']==0 else 0x95450)+4*row['native_index'];pointer=struct.unpack('<I',d.read(base+slot,4))[0]
            if pointer!=base+e.word(slot)or d.read(pointer,len(encoded_text(row['target'],'ascii'))+1)!=encoded_text(row['target'],'ascii')+b'\0':raise ValueError('Loaded UI differs')
            labels.append(dict(native_table=row['native_table'],native_index=row['native_index'],target=row['target'],complete_loaded_target_exact=True))
        (UI/'loaded_strings.en.json').write_text(json.dumps(dict(version='0.1.51',labels=labels,natural_gameplay_verified=False),indent=2)+'\n')
        print('All17 new party/result labels match installed memory.')
    finally:d.close()

if __name__=='__main__':main()
