"""Read-only opening dialogue draw trace in the isolated software emulator.

Default previews the currently drawn object. --write records a bounded trace;
it does not install font patches, change text, or alter the game image.
"""
import argparse, hashlib, json, pathlib, struct
from ppsspp_debug import Debugger
from live_vwf import registers, gpr

ROOT=pathlib.Path(__file__).resolve().parents[1]
EXPECTED='64e18adc27557d42f6733e4636054e3b29c81d4a0b4e28011330469ddf2f45df'
DISPATCH={0:0xea45c,1:0xe9ff4,2:0xea718,3:0xe9918,4:0xeab10}

def inspect(d,base,source_asset):
    d.call('cpu.runUntil',address=base+0xee208,expect='cpu.stepping')
    r=gpr(registers(d))
    if r['pc']!=base+0xee208 or r['ra']!=base+0xee8d0:raise ValueError('Unexpected dialogue caller')
    raw=d.read(r['a0'],160); source=struct.unpack_from('<I',raw,4)[0]
    head=d.read(source,32)
    original=source_asset.read_bytes()
    off=original.find(head)
    if off<0 or original.find(head,off+1)>=0:raise ValueError('Opening scene text location not unique')
    return r,{'object':hex(r['a0']),'text_pointer':hex(source),'source_file':'fld/talk/f101010.bin',
        'source_body_offset':off,'source_prefix_sha256':hashlib.sha256(head).hexdigest(),
        'font_mode':r['t2'],'draw_rect':[r['a3'],r['t0']],
        'x':r['a1'],'y':r['a2'],'character_code':r['t1'],
        'object_max_visible_glyphs':struct.unpack_from('<I',raw,12)[0],
        'object_visible_glyphs':struct.unpack_from('<I',raw,16)[0],
        'object_layout_float20':struct.unpack_from('<f',raw,32)[0],
        'object_layout_float24':struct.unpack_from('<f',raw,36)[0],
        'object_alignment_mode':struct.unpack_from('<I',raw,112)[0]}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true')
    p.add_argument('--draws',type=int,default=64)
    p.add_argument('--output',type=pathlib.Path,default=ROOT/'work/ui/runtime/opening_dialogue_trace.en.json')
    p.add_argument('--build-manifest',type=pathlib.Path)
    p.add_argument('--source-asset',type=pathlib.Path,default=ROOT/'work/source/cpk/fld/talk/f101010.bin')
    a=p.parse_args()
    if not 1<=a.draws<=128:raise ValueError('Trace is bounded to 128 glyphs')
    info=json.loads(a.build_manifest.read_text()) if a.build_manifest else {'version':'0.1.0','output_elf_sha256':EXPECTED}
    exe=a.build_manifest.parent/'EBOOT.BIN' if a.build_manifest else ROOT/'work/output/0.1.0-menu-vwf-4x-candidate/EBOOT.BIN'
    if hashlib.sha256(exe.read_bytes()).hexdigest()!=info['output_elf_sha256']:raise ValueError('Retrace executable offsets')
    d=Debugger()
    try:
        mod=next(m for m in d.call('hle.module.list')['modules'] if m['name']=='hp_proj');base=mod['address']
        if d.read(base+0xee208,8)!=struct.pack('<II',0x27bdffe0,0xafb00000):raise ValueError('Dialogue entry changed')
        # Confirm executable-specific patched call sites in loaded memory.
        executable=exe.read_bytes()
        for off in (0xee2d4,0xee35c,0xee8d4,0xed15c):
            word=struct.unpack_from('<I',executable,off+0xc0)[0]
            if word>>26 in (2,3):word=(word&0xfc000000)|((((word&0x03ffffff)*4+base)>>2)&0x03ffffff)
            if d.read(base+off,4)!=struct.pack('<I',word):raise ValueError('Loaded executable differs from selected manifest')
        r,first=inspect(d,base,a.source_asset)
        print(json.dumps({'mode':'read_only','sample':first,'draws_planned':a.draws},indent=2))
        if not a.write:print('DRY RUN: no trace file written.');return
        draws=[]
        for n in range(a.draws):
            if n:r,sample=inspect(d,base,a.source_asset)
            else:sample=first
            mode=r['t2']
            if mode not in DISPATCH:raise ValueError('Unaudited font dispatch mode')
            site=DISPATCH[mode]
            if info.get('dialogue_hooks') and mode in (1,4) and 32<=r['t1']<=128 and r['t1']!=127:site=0xea45c
            d.call('cpu.runUntil',address=base+site,expect='cpu.stepping')
            gr=gpr(registers(d))
            if gr['pc']!=base+site or [gr[k] for k in ('a1','a2','a3','t0','t1')]!=[r[k] for k in ('a1','a2','a3','t0','t1')]:
                raise ValueError('Font dispatch arguments differ')
            sample.update(index=n,renderer_module_offset=hex(site),renderer_manager=hex(gr['a0']),renderer_return=hex(gr['ra']-base))
            draws.append(sample)
        summary={'version':info['version'],'scope':'opening dialogue draw trace',
            'loaded_executable_sha256':info['output_elf_sha256'],'module_base':hex(base),'draws':draws,
            'renderers':sorted({x['renderer_module_offset'] for x in draws}),
            'dialogue_english_verified':False,'installed_runtime_patch':False}
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
        print(json.dumps({'saved':str(a.output),'draws':len(draws),'renderers':summary['renderers']},indent=2))
    finally:
        d.call('cpu.resume',expect='cpu.resume');d.close()

if __name__=='__main__':main()
