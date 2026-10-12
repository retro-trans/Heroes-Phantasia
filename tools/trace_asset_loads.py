"""Bounded read-only asset-load trace, with one normal Circle press; dry by default."""
import argparse, base64, hashlib, json, time
from pathlib import Path
from executable_text_patch import Elf
from ppsspp_debug import Debugger, websocket

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--port',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--write',action='store_true')
    a=p.parse_args();m=json.loads(a.manifest.read_bytes())
    binary=(a.manifest.parent/'EBOOT.BIN').read_bytes();elf=Elf(binary)
    if hashlib.sha256(binary).hexdigest()!=m['output_elf_sha256']:raise ValueError('Manifest executable differs')
    original=Elf(Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf').read_bytes())
    rva=0xf7668
    code=binary[elf.file_offset(rva):elf.file_offset(rva)+96]
    if code!=original.data[original.file_offset(rva):original.file_offset(rva)+96]:raise ValueError('Native loader changed')
    proof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=m['output_elf_sha256'],
        archive_sha256=m['dialogue_cpk_sha256'],loader_rva=rva,loader_code_sha256=hashlib.sha256(code).hexdigest(),
        duration_seconds=20,normal_input='one Circle press, duration4 frames',
        memory_or_register_writes=False,savestate_operations=False,records=[],full_game_verified=False)
    print(json.dumps({k:v for k,v in proof.items() if k!='records'},indent=2))
    if not a.write:print('DRY: no breakpoint, input or output changes.');return
    destination=a.output.resolve()
    if destination.exists() or not destination.is_relative_to(Path('work/ui').resolve()):raise ValueError('Fresh UI evidence output required')
    d=Debugger(a.port);address=None;added=False
    try:
        mod=next(x for x in d.call('hle.module.list')['modules'] if x['name']=='hp_proj')
        address=mod['address']+rva
        if any(x['address']==address for x in d.call('cpu.breakpoint.list')['breakpoints']):raise ValueError('Existing breakpoint at trace site')
        loaded=base64.b64decode(d.call('memory.read',address=address,size=8,replacements=False)['base64'])
        if loaded!=code[:8]:raise ValueError('Loaded native entry differs')
        if d.call('cpu.status').get('stepping'):raise ValueError('Game already paused')
        d.call('cpu.breakpoint.add',address=address);added=True
        # Sending the ordinary press asynchronously avoids awaiting its frame
        # completion while a loader breakpoint is paused; this changes no pad flags directly.
        d.ws.send(json.dumps(dict(event='input.buttons.press',ticket='trace_input',button='circle',duration=4)))
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            d.ws.settimeout(max(.1,deadline-time.monotonic()))
            try:ev=json.loads(d.ws.recv())
            except (TimeoutError,websocket.WebSocketTimeoutException):break
            if ev.get('event')!='cpu.stepping':continue
            reg=d.call('cpu.getAllRegs')['categories'][0];r=dict(zip(reg['registerNames'],reg['uintValues']))
            if r['pc']!=address:raise ValueError('Unexpected stepping site')
            if not 0x08800000<=r['a1']<0x0a000000-256:raise ValueError('Asset path pointer outside RAM')
            raw=d.read(r['a1'],256);end=raw.find(b'\0')
            if end<0:raise ValueError('Unbounded asset path')
            name=raw[:end].decode('ascii')
            proof['records'].append(dict(path=name,manager=r['a0'],path_pointer=r['a1'],return_address=r['ra']))
            d.call('cpu.resume',expect='cpu.resume')
    finally:
        try:
            if added:d.call('cpu.breakpoint.remove',address=address)
            if added and d.call('cpu.status').get('stepping'):d.call('cpu.resume',expect='cpu.resume')
        finally:d.close()
    proof.update(trace_breakpoint_removed=True,status='bounded_native_asset_load_observation')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    print(json.dumps(proof['records'],indent=2))

if __name__=='__main__':main()
