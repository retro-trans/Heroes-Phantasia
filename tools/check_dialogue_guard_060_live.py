"""Installed native geometry samples across reflow styles and row counts.

Uses only an explicitly owned isolated debugger. Synthetic packets preserve
and restore borrowed memory/registers; they are not natural story playback.
"""
import json, sys
from pathlib import Path
import check_english_bubbles_v10_live as check
import dialogue_layout_guard as g
from rebuild_dialogue import parse
from prepare_bubble_scenes_036 import read

ROOT=Path('work/output/0.1.60-title-credit-vwf-4x-candidate')
UI=Path('work/ui/dialogue/0.1.60')

def main():
    data=(ROOT/'EBOOT.BIN').read_bytes();m=json.loads((ROOT/'manifest.en.json').read_text(encoding='utf8'));prep=m['setup_patch']
    widths=g.widths_from(ROOT/'EBOOT.BIN');reflows=prep['dialogue_guard_055']['records'];chosen={}
    names=list(dict.fromkeys(r['resource'] for r in reflows));assets=read(ROOT/'HP.CPK',names);parsed={n:parse(n,b) for n,b in assets.items()}
    for rec in reflows:
        name,n=rec['resource'],rec['reference_index'];r=g.inspect(name,assets[name],parsed[name],n,widths);half=r['parent_maximum_width']/2
        for pi,page in enumerate(r['pages']):
            raw=bytes.fromhex(page['body_hex']);lines=len(page['line_advances'])
            for ki,key in enumerate(r['position_keys']):
                if tuple(key[1:3])==(0.,0.): continue
                expected=g.ray_fit(r['shape'],key[1:3],half,lines)
                # Exercise the widest parent for each shape/row count and
                # left/right half of the screen, including native fallback.
                group=(r['shape'],lines,key[1]>=240,expected,b'\x0f' in raw)
                case=(f'guard_{Path(name).stem}_{n}_p{pi}_k{ki}',r['shape'],*key[1:3],raw+b'\0',lines,half,1.,0.,expected)
                if group not in chosen or half>chosen[group][6]: chosen[group]=case
    cases=list(chosen.values())
    # The reported scene uses all pages' parent width at both authored poses.
    for name in ('phase/bin/p101050.bin','phase/bin/p101051.bin'):
        r=g.inspect(name,assets[name],parsed[name],30,widths);half=r['parent_maximum_width']/2
        for pi,page in enumerate(r['pages']):
            for ki,key in enumerate(r['position_keys']):
                if tuple(key[1:3])==(0.,0.): continue
                lines=len(page['line_advances']);cases.append((f'zigmarl_{Path(name).stem}_{pi}_{ki}',r['shape'],*key[1:3],bytes.fromhex(page['body_hex'])+b'\0',lines,half,1.,0.,g.ray_fit(r['shape'],key[1:3],half,lines)))
    cases.append(('serish',8,369.,99.,b'Who will accompany you?\x12\x0e\0',1,82.5,1.,0.,True))
    check.build=lambda:(data,prep);check.definitions=lambda:cases
    sys.argv=['native','--port','45406','--manifest',str(ROOT/'manifest.en.json'),'--run','--output',str(UI/'native_geometry.en.json')]
    check.main()
    path=UI/'native_geometry.en.json';proof=json.loads(path.read_text(encoding='utf8'));proof.update(version='0.1.60',stratification='Widest shared parent per shape, visible-row count, side of screen, fallback decision and pronunciation-control presence; all reported Zigmarl pages at both keys; reviewed Serish lip guard.',natural_scene_playback_verified=False)
    path.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')

if __name__=='__main__': main()
