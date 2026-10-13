"""Check the real glyph dispatcher in an owned emulator, restoring all state.

The legacy route is stopped before its unsafe lookup. This is a synthetic
renderer regression, not a natural elevator playthrough.
"""
import argparse,base64,json,struct
from pathlib import Path
from ppsspp_debug import Debugger
from live_vwf import registers,gpr,restore_registers,write
from prepare_relocation_019 import section_load
from prepare_elevator_crash_057 import SITE
from prepare_elevator_crash_058 import OUT,HELPER,CAPACITY
from prepare_bubble_scenes_036 import sha

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--temporary',action='store_true');opts=a.parse_args()
    root=Path('work/output/'+('0.1.57' if opts.temporary else '0.1.58')+'-title-credit-vwf-4x-candidate')
    manifest=json.loads((root/'manifest.en.json').read_bytes());candidate=(OUT/'EBOOT.BIN').read_bytes();prep=json.loads((OUT/'executable.en.json').read_bytes())['elevator_crash_057']
    if not opts.temporary and candidate!=(root/'EBOOT.BIN').read_bytes():raise ValueError('Installed executable differs')
    d=Debugger(45406);saved=oldmem=None;start=None;changed=[];breaks=[]
    try:
        d.call('cpu.stepping',expect='cpu.stepping');base=next(x['address']for x in d.call('hle.module.list')['modules']if x['name']=='hp_proj')
        if gpr(registers(d))['pc']!=base+0x1b6cdc:
            d.call('cpu.runUntil',address=base+0x1b6cdc,expect='cpu.stepping')
        saved=registers(d);regs=gpr(saved);start=regs['sp']-8192;oldmem=d.read(start,8192);stack=start+4096;ret=start+128
        loaded,_,_,_=section_load(candidate,base)
        spans=((SITE,4),(prep['helper_rva'],prep['helper_bytes']),(HELPER,CAPACITY))
        for rva,n in spans:
            # Read original MIPS words, excluding the JIT's temporary
            # run-block opcodes (the debugger defaults to replacements=True).
            actual=base64.b64decode(d.call('memory.read',address=base+rva,size=n,replacements=False)['base64']);expected=bytes(loaded[0][rva:rva+n])
            if opts.temporary:changed.append((base+rva,actual));write(d,base+rva,expected)
            elif actual!=expected:raise ValueError('Installed routing differs '+str(dict(rva=hex(rva),actual=actual.hex(),expected=expected.hex())))
        for rva in (0xea45c,0xea718):d.call('cpu.breakpoint.add',address=base+rva);breaks.append(base+rva)
        write(d,stack-32,struct.pack('<8I',*[regs[n]for n in ('s0','s1','s2','s3','s4','s5','s6')],ret))
        cases=[]
        for size,glyph in ((size,glyph) for size in (4,8) for glyph in (*range(32,127),128,129,130,0x82a0,127,31)):
            for n,v in [('s4',100),('s3',110),('s2',size),('s1',4),('s6',glyph),('s0',2),('sp',stack-32),('pc',base+0xee2e4)]:d.call('cpu.setReg',name=n,value=v)
            latin=32<=glyph<131 and glyph!=127;goal=base+(0xea45c if latin else 0xea718)
            d.call('cpu.runUntil',address=goal,expect='cpu.stepping');rr=gpr(registers(d))
            if rr['pc']!=goal or [rr[n]for n in ('a1','a2','a3','t0','t1')]!=[100,110,size,4,glyph]:raise ValueError('Real dispatch or glyph parameters differ '+str(dict(glyph=glyph,pc=hex(rr['pc']),expected=hex(goal),parameters=[rr[n]for n in ('a1','a2','a3','t0','t1')],call_word=d.read(base+SITE,4).hex())))
            if latin:
                d.call('cpu.runUntil',address=ret,expect='cpu.stepping');rr=gpr(registers(d))
                if rr['pc']!=ret or rr['sp']!=stack or any(rr[n]!=regs[n]for n in ('s0','s1','s2','s3','s4','s5','s6','s7','fp')):raise ValueError('Full native glyph return/ABI differs')
            cases.append(dict(font_size=size,glyph=glyph,latin=latin,full_native_draw_completed=latin,native_fallback_entry_preserved=not latin,passed=True));restore_registers(d,saved)
        # Exact original call routes the first elevator letter into the
        # failing function. Stop there, before dereferencing its font table.
        original=base64.b64decode(d.call('memory.read',address=base+SITE,size=4,replacements=False)['base64']);write(d,base+SITE,struct.pack('<I',0x0c000000|((base+0xea718)>>2)))
        try:
            for n,v in [('s4',100),('s3',110),('s2',4),('s1',4),('s6',ord('T')),('s0',2),('sp',stack-32),('pc',base+0xee2e4)]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=base+0xea718,expect='cpu.stepping');rr=gpr(registers(d))
            if rr['pc']!=base+0xea718:raise ValueError('Legacy failing route was not reproduced')
            descriptor=struct.unpack('<I',d.read(rr['a0']+0x10,4))[0]
        finally:write(d,base+SITE,original);restore_registers(d,saved)
        proof=dict(version='0.1.58',loaded_build=manifest['version'],loaded_iso_sha256=manifest['iso_sha256'],candidate_sha256=sha(candidate),installed_candidate=not opts.temporary,module_base=base,cases=cases,legacy_elevator_letter_enters_failing_font_search=True,legacy_font_descriptor_at_checkpoint=descriptor,unsafe_legacy_lookup_not_executed=True,all_native_Latin_glyph_draws_and_ABI_verified=True,native_glyph_fallback_entry_verified=True,natural_elevator_playback_verified=False,scope='Real mode-two dispatch branch, individual native glyph calls (unrelated engine getter skipped), explicit legacy-entry regression; natural event/scene sequence not exercised.')
        dest=Path('work/ui/dialogue/0.1.58');dest.mkdir(parents=True,exist_ok=True);(dest/('elevator_temporary.en.json'if opts.temporary else 'elevator_native.en.json')).write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),all_passed=True,installed=not opts.temporary)))
    finally:
        try:
            for bp in breaks:d.call('cpu.breakpoint.remove',address=bp)
            for address,raw in reversed(changed):write(d,address,raw)
            if oldmem is not None:write(d,start,oldmem)
            if saved is not None:restore_registers(d,saved)
            if d.call('cpu.status').get('stepping'):d.call('cpu.resume',expect='cpu.resume')
        finally:d.close()

if __name__=='__main__':main()
