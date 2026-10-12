"""Exercise the memory-neutral tail correction in an isolated native session."""
import argparse,json,struct
from pathlib import Path
from ppsspp_debug import Debugger
from live_vwf import gpr,registers,restore_registers,write
from executable_text_patch import Elf
from prepare_relocation_019 import section_load

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',action='store_true');a=ap.parse_args()
    root=Path('work/output/0.1.31-title-credit-vwf-4x-candidate');m=json.loads((root/'manifest.en.json').read_text())
    prep=json.loads(Path(m['executable_preparation_report']).read_text());p=prep['serish_tail_patch']
    if prep['output_elf_sha256']!=m['output_elf_sha256']:raise ValueError('Preparation identity differs')
    proof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=m['output_elf_sha256'],archive_sha256=m['dialogue_cpk_sha256'],
      scope='Native instruction execution with a synthetic associated window. Natural story scene remains pending.',mouth_reference=[243,134])
    print(json.dumps(proof,indent=2))
    if not a.run:print('DRY RUN');return
    dest=Path('work/ui/dialogue/0.1.31/tail_native_instruction.en.json')
    if dest.exists():raise ValueError('Fresh evidence required')
    d=Debugger(45386);saved=borrowed=manager_old=None;start=manager=bp=None
    try:
        d.call('cpu.stepping',expect='cpu.stepping');saved=registers(d);regs=gpr(saved)
        base=next(x['address']for x in d.call('hle.module.list')['modules']if x['name']=='hp_proj')
        start=regs['sp']-8192;borrowed=d.read(start,8192);window=start+128;owner=start+1100;context=start+1400;container=start+1500;source=start+1600;temp_sp=regs['sp']-1024
        manager=base+0x166f2c4;manager_old=d.read(manager,48);bp=base+0xe4e14
        baseline_data=Path('work/output/0.1.29-save-tutorial-assets/EBOOT.BIN').read_bytes();baseline_elf=Elf(baseline_data)
        loaded_baseline,_,_,_=section_load(baseline_data,base);off=p['old_target']-baseline_elf.ph[2][2]
        baseline_code=bytes(loaded_baseline[2][off:off+p['helper_bytes']]);baseline_address=start+2048
        write(d,baseline_address,baseline_code)
        if d.read(base+0xe4e0c,8)!=struct.pack('<II',0x08000000|((base+p['helper_rva'])>>2&0x3ffffff),0):raise ValueError('Loaded entry differs')
        d.call('cpu.breakpoint.add',address=bp);cases=[]
        definitions=[('serish_mouth',8,369.,99.,b'Who will accompany you?\x12\x0e\0',1.,0.,True),
          ('other_text',8,369.,99.,b'Who will accompany you!\x12\x0e\0',1.,0.,False),
          ('different_center_x',8,370.,99.,b'Who will accompany you?\x12\x0e\0',1.,0.,False),
          ('different_center_y',8,369.,98.,b'Who will accompany you?\x12\x0e\0',1.,0.,False),
          ('other_template',18,369.,99.,b'Who will accompany you?\x12\x0e\0',1.,0.,False),
          ('native_text',8,369.,99.,b'\x82\xa0\x12\x0e\0',1.,0.,False),
          ('animated',8,369.,99.,b'Who will accompany you?\x12\x0e\0',.5,0.,False),
          ('rotated',8,369.,99.,b'Who will accompany you?\x12\x0e\0',1.,1.,False),
          ('repeat_serish',8,369.,99.,b'Who will accompany you?\x12\x0e\0',1.,0.,True)]
        for name,shape,x,y,raw,scale,rotation,selected in definitions:
            results=[]
            for helper_address in (baseline_address,base+p['helper_rva']):
                buf=bytearray(0x360);struct.pack_into('<3f',buf,0x2d0,x,y,0.);struct.pack_into('<3f',buf,0x2e0,rotation,0.,0.);struct.pack_into('<3f',buf,0x2f0,scale,scale,scale)
                struct.pack_into('<H',buf,0x318,shape);struct.pack_into('<I',buf,0x31c,0x12345678);struct.pack_into('<I',buf,0x348,owner);write(d,window,buf)
                buf=bytearray(0x100);struct.pack_into('<I',buf,0x98,context);struct.pack_into('<I',buf,0xec,2);write(d,owner,buf)
                buf=bytearray(0x40);struct.pack_into('<I',buf,0x30,3);write(d,context,buf)
                buf=bytearray(0x40);struct.pack_into('<II',buf,8,3,2);struct.pack_into('<4I',buf,0x14,source,1,1,0);struct.pack_into('<f',buf,0x2c,82.5);write(d,container,buf);write(d,source,raw)
                buf=bytearray(manager_old);struct.pack_into('<I',buf,0,1);struct.pack_into('<II',buf,0x28,1,container);write(d,manager,buf)
                for n,v in [('a0',window),('sp',temp_sp),('pc',helper_address)]:d.call('cpu.setReg',name=n,value=v)
                d.call('cpu.runUntil',address=bp,expect='cpu.stepping');out=registers(d);actual=gpr(out)
                if actual['pc']!=bp or actual['sp']!=temp_sp-224 or actual['a0']!=window or actual['a1']!=0x12345678:raise ValueError('Native continuation ABI differs')
                for n,v in regs.items():
                    if n not in ('pc','a0','a1','sp')and actual[n]!=v:raise ValueError('GPR clobber '+n)
                for old,now in zip(saved[1:],out[1:]):
                    if old['uintValues']!=now['uintValues']:raise ValueError('Floating/VFPU ABI differs')
                results.append(d.read(window,0x360));restore_registers(d,saved)
            aold,anew=results
            allowed={n for off in (48,0x120,0x210)for n in range(off,off+8)}
            diffs=[n for n,(a,b)in enumerate(zip(aold,anew))if a!=b]
            if selected:
                cx,cy=struct.unpack_from('<2f',anew,0x2d0);tips=[struct.unpack_from('<2f',anew,off)for off in (48,0x120,0x210)]
                world=[[vx+cx,vy+cy]for vx,vy in tips];expected=[[243.,134.],[246.5,133.],[239.5,135.]]
                if any(abs(v-e)>1e-4 for pair,goal in zip(world,expected)for v,e in zip(pair,goal))or not diffs or any(n not in allowed for n in diffs):raise ValueError('Tail target or unchanged body differs')
            elif diffs:raise ValueError('Fallback geometry differs from inherited hook')
            cases.append(dict(case=name,selected=selected,changed_window_byte_count=len(diffs),tip_world=world if selected else None,passed=True))
        proof.update(module_base=base,cases=cases,all_registers_stack_and_manager_restored=True,natural_scene_verified=False)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(cases,indent=2))
    finally:
        try:
            if bp is not None:d.call('cpu.breakpoint.remove',address=bp)
            if manager_old is not None:write(d,manager,manager_old)
            if borrowed is not None:write(d,start,borrowed)
            if saved is not None:restore_registers(d,saved);d.call('cpu.resume',expect='cpu.resume')
        finally:d.close()
if __name__=='__main__':main()
