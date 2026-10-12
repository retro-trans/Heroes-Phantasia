"""Capture a native PSP frame through the isolated software-renderer debugger.

Probes the game's verified sceDisplaySetFrameBuf import to obtain address,
stride and format. Default dry-run reports these; --write saves PNG + metadata.
Hardware-renderer VRAM readbacks are not supported by this fallback.
"""
import argparse, array, hashlib, json, pathlib, time
from PIL import Image
from ppsspp_debug import Debugger

EXPECTED_ELF = '03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=pathlib.Path, default=pathlib.Path('work/ui/runtime/frame.png'))
    p.add_argument('--write', action='store_true')
    p.add_argument('--port',type=int,default=45373)
    p.add_argument('--build-manifest',type=pathlib.Path,help='Metadata for the loaded local candidate')
    a = p.parse_args()
    elf = pathlib.Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf')
    if hashlib.sha256(elf.read_bytes()).hexdigest() != EXPECTED_ELF:
        raise ValueError('Import offset requires retracing for this executable')
    d = Debugger(a.port)
    address = None
    try:
        modules = d.call('hle.module.list')['modules']
        mod = next(m for m in modules if m['name'] == 'hp_proj')
        address = mod['address'] + 0x29414c
        d.call('cpu.breakpoint.add', address=address)
        deadline = time.monotonic() + 10
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Display import did not run within 10 seconds')
            d.ws.settimeout(remaining)
            event = json.loads(d.ws.recv())
            if event.get('event') == 'cpu.stepping':
                break
        regs = d.call('cpu.getAllRegs')['categories'][0]
        r = dict(zip(regs['registerNames'], regs['uintValues']))
        if r['pc'] != address:
            raise RuntimeError('Stopped at a different breakpoint')
        frame, stride, fmt = r['a0'], r['a1'], r['a2']
        if not 0x04000000 <= frame < 0x04200000 or stride != 512 or fmt not in range(4):
            raise ValueError('Unexpected framebuffer parameters')
        info = {'version':'0.1.0','capture_method':'software_renderer_emulated_VRAM',
                'game_module_base':hex(mod['address']), 'display_import':hex(address),
                'address':hex(frame),'stride':stride,'format':fmt,
                'format_name':['RGB565','RGBA5551','RGBA4444','RGBA8888'][fmt],
                'width':480,'height':272,'caller_return_address':hex(r['ra']),
                'elf_sha256':EXPECTED_ELF,'game_screen':'unclassified; visually review capture'}
        if a.build_manifest:
            build=json.loads(a.build_manifest.read_text(encoding='utf8'))
            loaded=a.build_manifest.parent/'EBOOT.BIN'
            if hashlib.sha256(loaded.read_bytes()).hexdigest()!=build['output_elf_sha256']:raise ValueError('Candidate hash changed')
            info.update(version=build['version'],loaded_executable_sha256=build['output_elf_sha256'],
                original_elf_hash_role='display import offset reference',build_manifest=str(a.build_manifest))
        print(json.dumps(info, indent=2))
        if not a.write:
            print('DRY RUN: no capture files written.');return
        raw = d.read(frame, stride*272*(4 if fmt == 3 else 2))
        if fmt == 3:
            im = Image.frombytes('RGBA',(stride,272),raw).convert('RGB')
        else:
            rgb=bytearray()
            for v in array.array('H',raw):
                if fmt==0: pixel=((v&31)*255//31,((v>>5)&63)*255//63,((v>>11)&31)*255//31)
                elif fmt==1: pixel=((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31)
                else: pixel=((v&15)*17,((v>>4)&15)*17,((v>>8)&15)*17)
                rgb.extend(pixel)
            im=Image.frombytes('RGB',(stride,272),bytes(rgb))
        a.output.parent.mkdir(parents=True,exist_ok=True)
        im.crop((0,0,480,272)).save(a.output)
        a.output.with_suffix('.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf8')
    finally:
        try:
            if address is not None:
                d.call('cpu.breakpoint.remove',address=address)
                if d.call('cpu.status').get('stepping'):
                    d.call('cpu.resume',expect='cpu.resume')
        finally:
            d.close()


if __name__ == '__main__':
    main()
