"""Installed native geometry tests for bounded name-dependent owner widths."""
import json, sys
from pathlib import Path
import check_english_bubbles_v10_live as check
import dialogue_layout_guard as g
from rebuild_dialogue import parse
from prepare_bubble_scenes_036 import read

ROOT=Path('work/output/0.1.59-title-credit-vwf-4x-candidate')
UI=Path('work/ui/dialogue/0.1.59')

def main():
    data=(ROOT/'EBOOT.BIN').read_bytes()
    manifest=json.loads((ROOT/'manifest.en.json').read_bytes())
    prep=manifest['setup_patch'];records=prep['name_dialogue_059']['records']
    assets=read(ROOT/'HP.CPK',list(dict.fromkeys(r['resource'] for r in records)))
    parsed={n:parse(n,b) for n,b in assets.items()};widths=g.widths_from(ROOT/'EBOOT.BIN')
    chosen={};reported=[];model_cases=0
    for rec in records:
        name,n=rec['resource'],rec['reference_index']
        r=g.inspect(name,assets[name],parsed[name],n,widths)
        if r['status']!='fit':raise ValueError('Prepared name owner does not fit')
        for pi,page in enumerate(r['pages']):
            raw=bytes.fromhex(page['body_hex']);lines=len(page['line_advances'])
            for ki,key in enumerate(r['position_keys']):
                if tuple(key[1:3])==(0.,0.):continue
                for half in g.parent_halves(r['pages']):
                    expected=g.ray_fit(r['shape'],key[1:3],half,lines)
                    case=(f'name_{Path(name).stem}_{n}_p{pi}_k{ki}_h{half}',r['shape'],*key[1:3],raw+b'\0',lines,half,1.,0.,expected)
                    # Include each halfwidth per native style, line count,
                    # side, branch decision and embedded-name/ruby presence.
                    group=(r['shape'],lines,key[1]>=240,expected,half,b'\x01' in raw,b'\x0f' in raw)
                    chosen.setdefault(group,case);model_cases+=1
                    if name in ('phase/bin/p101070.bin','phase/bin/p101071.bin') and n==9:reported.append(case)
    cases=list({v[0]:v for v in list(chosen.values())+reported}.values())
    check.build=lambda:(data,prep);check.definitions=lambda:cases
    sys.argv=['native','--port','45406','--manifest',str(ROOT/'manifest.en.json'),'--run','--output',str(UI/'native_geometry.en.json')]
    check.main()
    path=UI/'native_geometry.en.json';proof=json.loads(path.read_bytes())
    proof.update(version='0.1.59',modeled_native_width_cases=model_cases,reported_scene_cases=len(reported),stratification='Every 13px shared-owner width per shape, rows, screen side, native fallback decision and name/ruby presence; every reported Shinobu page at every authored XY key and every bounded width.',natural_scene_playback_verified=False)
    path.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
