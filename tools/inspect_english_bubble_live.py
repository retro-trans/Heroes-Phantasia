"""Read one naturally active bubble at the native geometry continuation."""
import argparse,json,struct,time
from pathlib import Path
from ppsspp_debug import Debugger
from bubble_metrics import load_templates
from prepare_english_bubbles import CORE,sha

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',action='store_true')
    ap.add_argument('--port',type=int,default=45389);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--manifest',type=Path,default=Path('work/output/0.1.33-title-credit-vwf-4x-candidate/manifest.en.json'));a=ap.parse_args()
    if not a.run:print('DRY RUN: read active window, associated rows, outline and tail; no game-memory edits.');return
    if a.output.exists():raise ValueError('Fresh evidence required')
    m=json.loads(a.manifest.read_text());d=Debugger(a.port);bp=None
    try:
        base=next(x['address']for x in d.call('hle.module.list')['modules']if x['name']=='hp_proj')
        bp=base+CORE;d.call('cpu.breakpoint.add',address=bp)
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            ev=json.loads(d.ws.recv())
            if ev.get('event')=='cpu.stepping':break
        else:raise TimeoutError('No active geometry window')
        reg=d.call('cpu.getAllRegs')['categories'][0];regs=dict(zip(reg['registerNames'],reg['uintValues']))
        if regs['pc']!=bp:raise ValueError('Unexpected stop')
        window=regs['a0'];before=d.read(window,0x360);shape=struct.unpack_from('<H',before,0x318)[0]
        owner=struct.unpack_from('<I',before,0x348)[0];ctx=struct.unpack('<I',d.read(owner+0x98,4))[0]
        context_key=struct.unpack('<I',d.read(ctx+0x30,4))[0];owner_key=struct.unpack('<I',d.read(owner+0xec,4))[0]
        manager=d.read(base+0x166f2c4,48);count=struct.unpack_from('<I',manager,0x28)[0];container=None
        for n in range(count):
            ptr=struct.unpack_from('<I',manager,0x2c+4*n)[0]if n==0 else struct.unpack('<I',d.read(base+0x166f2f0+4*n,4))[0]
            data=d.read(ptr,0x48)
            if struct.unpack_from('<II',data,8)==(context_key,owner_key):container=ptr;break
        if container is None:raise ValueError('Active associated text missing')
        data=d.read(container,0x48);rows=struct.unpack_from('<I',data,4)[0]
        source,_,lines,first=struct.unpack_from('<4I',data,0x14)
        half=struct.unpack_from('<f',data,0x2c)[0]
        align=[struct.unpack('<i',d.read(rows+(first+n)*0xe8+0x70,4))[0]for n in range(lines)]
        raw=d.read(source,4096).split(b'\0',1)[0]
        d.call('cpu.breakpoint.remove',address=bp);bp=None
        end=base+0xe4e14;d.call('cpu.runUntil',address=end,expect='cpu.stepping');after=d.read(window,0x360)
        center=list(struct.unpack_from('<2f',after,0x2d0));outline=[list(struct.unpack_from('<2f',after,8*n))for n in range(load_templates()[shape]['count'])]
        family=(shape-3)%10;tip=family+1
        top=struct.unpack_from('<f',after,0x310)[0]
        body_top=min(p[1]for n,p in enumerate(outline)if n!=tip)
        if align!=[-1]*lines or abs(top-body_top-10)>1e-4:raise ValueError(f'Custom centered geometry not active: shape={shape}, first={first}, lines={lines}, half={half}, align={align}, top={top}, body_top={body_top}, scale={struct.unpack_from("<3f",after,0x2f0)}, raw={raw[:120].hex()}')
        oldcenter=struct.unpack_from('<2f',before,0x2d0);expected=load_templates()[shape]['outline'][tip]
        if any(abs(outline[tip][k]+center[k]-expected[k]-oldcenter[k])>1e-4 for k in range(2)):raise ValueError('Natural tail endpoint differs')
        proof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=m['output_elf_sha256'],
            natural_story_scene=True,shape=shape,visible_lines=lines,row_alignments=align,measured_halfwidth_px=half,
            body_source_hex=raw.hex(),center=center,outline=outline,body_text_offset=list(struct.unpack_from('<2f',after,0x30c)),
            custom_geometry_active=True,tail_endpoint_preserved=True,game_memory_edits=False)
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps(proof,indent=2))
    finally:
        if bp is not None:d.call('cpu.breakpoint.remove',address=bp)
        if d.call('cpu.status').get('stepping'):d.call('cpu.resume',expect='cpu.resume')
        d.close()
if __name__=='__main__':main()
