"""Bounded read-only gallery drawing observations; dry by default."""
import argparse,base64,hashlib,json,time,struct
from pathlib import Path
from executable_text_patch import Elf
from ppsspp_debug import Debugger,websocket

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--port',type=int,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--write',action='store_true')
    p.add_argument('--discovery',action='store_true');p.add_argument('--callsites',action='store_true')
    p.add_argument('--first-button',choices=('circle','cross'));a=p.parse_args()
    first_button=a.first_button or ('circle' if a.callsites else 'cross')
    if a.discovery and a.callsites:raise ValueError('Choose one observation mode')
    m=json.loads(a.manifest.read_bytes());binary=(a.manifest.parent/'EBOOT.BIN').read_bytes();elf=Elf(binary)
    if hashlib.sha256(binary).hexdigest()!=m['output_elf_sha256']:raise ValueError('Executable identity mismatch')
    original=Elf(Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf').read_bytes())
    sites=(0x68cd0,0x1f0d8) if a.callsites else (0xe9c64,0x877f4) if a.discovery else (0x87c18,0x880c8)
    codes={r:binary[elf.file_offset(r):elf.file_offset(r)+96] for r in sites}
    for r,c in codes.items():
        if a.callsites:
            expected={0x68cd0:'2d364de0385ef1b69ca508bb971cc692dc516d40bd2ec1924df45cbbcf23100d',
                      0x1f0d8:'fc04971063f8c0a353e24b79e36b1184386ca726554f762e4574d162803b6c25'}
            if hashlib.sha256(c).hexdigest()!=expected[r]:raise ValueError('Reviewed callsite changed')
        elif a.discovery:
            expected={0xe9c64:'a1f00d101bac0315fccacea7d20f87549caef5ceed3fe72f972bf249efa4601d',
                      0x877f4:'e4e85ae54652bcb292d635dd39ca423351f864ffafa984ce719cb1a5bdc2df31'}
            if hashlib.sha256(c).hexdigest()!=expected[r]:raise ValueError('Reviewed discovery entry changed')
        elif c!=original.data[original.file_offset(r):original.file_offset(r)+96]:raise ValueError('Native drawing entry changed')
    pointers={0x94d1d,0x94d26,0x94d2f,0x94b86,0x94b8b,0x9506c,0x951c1,
              0x95fe4,0x95ff5,0x96004,0x9602b,0x96036,0x96041,0x9604e,0x9605b,0x9608c,0x960bd,0x960de,0x96101}
    proof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=m['output_elf_sha256'],
               archive_sha256=m['dialogue_cpk_sha256'],sites=list(sites),duration_seconds=20,maximum_hits=600,
               normal_inputs=first_button+' at trace start, Cross after two seconds, each duration4 frames',
               code_sha256={str(r):hashlib.sha256(c).hexdigest() for r,c in codes.items()},
               discovery=a.discovery,callsites=a.callsites,normal_inputs_sent=[],memory_or_register_writes=False,savestate_operations=False,records=[],initial_samples=[])
    print(json.dumps(proof,indent=2))
    if not a.write:print('DRY: no input, breakpoint or output changes.');return
    out=a.output.resolve()
    if out.exists() or not out.is_relative_to(Path('work/ui').resolve()):raise ValueError('Fresh UI output required')
    d=Debugger(a.port);added=[];seen=set();hits=0
    try:
        base=next(x['address'] for x in d.call('hle.module.list')['modules'] if x['name']=='hp_proj')
        existing={x['address'] for x in d.call('cpu.breakpoint.list')['breakpoints']}
        if d.call('cpu.status').get('stepping'):raise ValueError('Already paused')
        for r in sites:
            address=base+r
            if address in existing:raise ValueError('Existing drawing breakpoint')
            loaded=base64.b64decode(d.call('memory.read',address=address,size=8,replacements=False)['base64'])
            expected_loaded=codes[r][:8]
            if a.callsites:
                # These typed JAL relocation sites target the loaded native draw function.
                expected_loaded=struct.pack('<I',0x0c000000|(((base+0x87c18)>>2)&0x03ffffff))+codes[r][4:8]
            if loaded!=expected_loaded:raise ValueError('Loaded drawing entry mismatch')
        for r in sites:d.call('cpu.breakpoint.add',address=base+r);added.append(base+r)
        def press(ticket,button='cross'):
            d.ws.send(json.dumps(dict(event='input.buttons.press',ticket=ticket,button=button,duration=4)))
            proof['normal_inputs_sent'].append(dict(ticket=ticket,button=button))
        press('gallery_first',first_button);start=time.monotonic();second=False
        while time.monotonic()-start<20 and hits<600:
            if not second and time.monotonic()-start>=2:press('gallery_back_2');second=True
            d.ws.settimeout(min(.25,max(.1,20-(time.monotonic()-start))))
            try:ev=json.loads(d.ws.recv())
            except (TimeoutError,websocket.WebSocketTimeoutException):continue
            if ev.get('event')!='cpu.stepping':continue
            regs=d.call('cpu.getAllRegs')['categories'][0];r=dict(zip(regs['registerNames'],regs['uintValues']));hits+=1
            if r['pc'] not in added:raise ValueError('Unexpected stepping site')
            row={k:r[k] for k in ('pc','a0','a1','a2','a3','t1','t2','s0','s1','s2','s3','s4','s5','s6','s7','ra')}
            if len(proof['initial_samples'])<12:proof['initial_samples'].append(row)
            matched=(r['a0']-base in pointers if r['pc']==base+0xe9c64 else
                     (r['a1']==0 and r['a2'] in (14,15,63,64,65,144,177) or r['a1']==2 and r['a2']<12) if r['pc']==base+0x877f4 else
                     r['a1']-base in pointers)
            if matched:
                if r['pc']!=base+0x877f4:row['text_rva']=r['a0']-base if r['pc']==base+0xe9c64 else r['a1']-base
                if a.callsites and r['pc']==base+0x68cd0:
                    row['descriptor_14_19_hex']=base64.b64decode(d.call('memory.read',address=r['s3']+14,size=6,replacements=False)['base64']).hex()
                key=tuple(row.values())
                if key not in seen:seen.add(key);proof['records'].append(row)
            d.call('cpu.resume',expect='cpu.resume')
    finally:
        try:
            for address in added:d.call('cpu.breakpoint.remove',address=address)
            if added and d.call('cpu.status').get('stepping'):d.call('cpu.resume',expect='cpu.resume')
        finally:d.close()
    proof.update(hits=hits,trace_breakpoints_removed=True,status='bounded_gallery_entry_observation')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    print(json.dumps(proof['records'],indent=2))

if __name__=='__main__':main()
