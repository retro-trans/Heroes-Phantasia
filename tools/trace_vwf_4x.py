"""Verify actual 4x source uploads and native-size sprites; dry-run by default."""
import argparse,json,pathlib,struct
from ppsspp_debug import Debugger

def regs(d):
    c=d.call('cpu.getAllRegs')['categories'][0]
    return dict(zip(c['registerNames'],c['uintValues']))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true')
    p.add_argument('--build-manifest',type=pathlib.Path)
    p.add_argument('--output',type=pathlib.Path,default=pathlib.Path('work/ui/runtime/main_menu_vwf_4x_trace.en.json'));a=p.parse_args()
    d=Debugger()
    if a.build_manifest:
        build=json.loads(a.build_manifest.read_text())
        b=next(m['address'] for m in d.call('hle.module.list')['modules'] if m['name']=='hp_proj')
        s={**build,'status':'installed_cold_boot_candidate','module_base':b,
            'high_bank':b+build['high_bank'],'labels':list(build['label_widths'])}
    else:s=json.loads(pathlib.Path('work/source/font_audit/live_vwf_state.json').read_text())
    if not s['status'].startswith('installed') or s['font_scale']!=4:d.close();raise ValueError('Install 4x experiment first')
    texture_slot=s.get('high_texture_slot',[128,64]);texture_width=texture_slot[0]
    if texture_slot not in ([128,64],[64,64]):d.close();raise ValueError('Unsupported texture layout')
    slot_bytes=texture_width*64//2
    b=s['module_base'];rows=[];paused=False
    try:
        for _ in range(76):
            d.call('cpu.runUntil',address=b+0xea45c,expect='cpu.stepping');paused=True;r=regs(d)
            if not (32<=r['t1']<=128 and r['ra']==b+0x87dc0):continue
            row={'code':r['t1'],'glyph':chr(r['t1']) if r['t1']!=128 else '\u00e8','x':r['a1'],'y':r['a2']}
            d.call('cpu.runUntil',address=b+0x1b7e1c,expect='cpu.stepping');u=regs(d)
            row['texture']={'mip':u['a0'],'width':u['a1'],'height':u['a2'],'pitch_pixels':u['a3'],'pointer':u['t0']}
            d.call('cpu.runUntil',address=b+0xd8e4,expect='cpu.stepping');v=regs(d)
            row['sprite']={'x':v['a1'],'y':v['a2'],'dest_width':v['a3'],'dest_height':v['t0'],
                'u':v['t1'],'v':v['t2'],'source_width':v['t3'],'source_height':struct.unpack('<I',d.read(v['sp'],4))[0]}
            if row['texture']['width']!=texture_width or row['texture']['height']!=64 or row['texture']['pitch_pixels']!=texture_width:
                raise ValueError('Unexpected high-resolution upload')
            if 'high_glyph_offsets' in s:
                if u['t0']!=s['high_bank']+s['high_glyph_offsets'][str(row['code'])]:raise ValueError('Packed glyph pointer differs')
                if u['t0']+slot_bytes>s['high_bank']+s['high_bank_bytes']:raise ValueError('Packed glyph outside owned bank')
            else:
                if not s['high_bank']<=u['t0']<s['high_bank']+s['high_glyph_count']*slot_bytes:raise ValueError('Texture outside owned bank')
                if (u['t0']-s['high_bank'])%slot_bytes:raise ValueError('Texture pointer not slot aligned')
            if any(row['sprite'][k]!=val for k,val in {'dest_width':16,'dest_height':16,'u':0,'v':0,'source_width':64,'source_height':64}.items()):
                raise ValueError('Source/destination sprite sizes changed')
            rows.append(row)
        groups=[]
        for r in rows:
            if not groups or r['y']!=groups[-1][0]['y'] or r['x']<=groups[-1][-1]['x']:groups.append([])
            groups[-1].append(r)
        lines=[{'text':''.join(r['glyph'] for r in g),'y':g[0]['y'],'positions':[r['x'] for r in g],
            'advances':[z['x']-q['x'] for q,z in zip(g,g[1:])]} for g in groups]
        full={r['text']:r for r in lines if r['text'] in s['labels']}
        if set(full)!=set(s['labels']):raise ValueError('Five complete labels not observed')
        info={'version':s.get('version','0.1.0'),'status':'observed_4x_source_menu_vwf_only','screen':[480,272],
            'installation':'cold_boot_executable' if a.build_manifest else 'reversible_debugger_experiment',
            'glyph_draws_observed':len(rows),'unique_complete_labels':full,'glyph_source_scale':4,
            'source_rect':[64,64],'dest_rect':[16,16],'texture_slot':texture_slot,
            'full_game_verified':False,'emulator_4x_internal_resolution_verified':False,
            'texture_filter':'Inherited game state; not measured by this trace','draws':rows}
        print(json.dumps({k:v for k,v in info.items() if k!='draws'},indent=2))
        if a.write:a.output.write_text(json.dumps(info,indent=2)+'\n')
        else:print('DRY RUN: no trace file written.')
    finally:
        if paused:d.call('cpu.resume',expect='cpu.resume')
        d.close()

if __name__=='__main__':main()
