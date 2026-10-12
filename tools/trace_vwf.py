"""Measure observed English menu glyph positions; default prints without saving."""
import argparse, json, pathlib
from ppsspp_debug import Debugger

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    state=json.loads(pathlib.Path('work/source/font_audit/live_vwf_state.json').read_text())
    if not state['status'].startswith('installed'):raise ValueError('Install the menu experiment first')
    d=Debugger();address=state['module_base']+0xea45c;records=[];paused=False
    try:
        for _ in range(76):
            d.call('cpu.runUntil',address=address,expect='cpu.stepping')
            paused=True
            cat=d.call('cpu.getAllRegs')['categories'][0];r=dict(zip(cat['registerNames'],cat['uintValues']))
            if r['pc']!=address:raise RuntimeError('Another breakpoint interrupted trace')
            if 32<=r['t1']<=128 and r['ra']==state['module_base']+0x87dc0:
                records.append({'code':r['t1'],'glyph':chr(r['t1']) if r['t1']!=128 else '\u00e8',
                    'x':r['a1'],'y':r['a2'],'width':r['a3'],'height':r['t0']})
        groups=[]
        for row in records:
            if not groups or row['y']!=groups[-1][0]['y'] or row['x']<=groups[-1][-1]['x']:
                groups.append([])
            groups[-1].append(row)
        lines=[{'text':''.join(r['glyph'] for r in g),'y':g[0]['y'],
                'positions':[r['x'] for r in g],'advances':[b['x']-a['x'] for a,b in zip(g,g[1:])]} for g in groups]
        full=[line for line in lines if line['text'] in state['labels']]
        if set(line['text'] for line in full)!=set(state['labels']):raise ValueError('Not all five labels observed')
        deltas={n for line in full for n in line['advances']}
        if len(deltas)<3:raise ValueError('Expected multiple distinct proportional advances')
        info={'version':'0.1.0','status':'observed_native_menu_vwf_only','screen':[480,272],
            'method':'EA45C glyph draw arguments; interpreter/software renderer',
            'glyph_draws_observed':len(records),'advance_values_px':sorted(deltas),
            'unique_complete_labels':{line['text']:line for line in full},
            'source_strings_relocated':True,'full_game_verified':False,'4x_rendering_verified':False}
        print(json.dumps(info,indent=2))
        if a.write:
            pathlib.Path('work/ui/runtime/main_menu_vwf_trace.en.json').write_text(json.dumps(info,indent=2)+'\n')
        else:print('DRY RUN: no trace file written.')
    finally:
        d.call('cpu.breakpoint.remove',address=address)
        if paused:d.call('cpu.resume',expect='cpu.resume')
        d.close()

if __name__=='__main__':main()
