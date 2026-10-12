"""Exercise .29 tutorial width instructions in an isolated debugger; dry first.

Temporary text/stack/registers are restored. This proves the measured widths
and ABI, not natural arrival at the reported save-point scene.
"""
import argparse,json,struct
from pathlib import Path
from ppsspp_debug import Debugger
from live_vwf import gpr,registers,restore_registers,write
from field_tutorial_width import CONTINUATION

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',action='store_true');a=ap.parse_args()
    root=Path('work/output/0.1.29-title-credit-vwf-4x-candidate');m=json.loads((root/'manifest.en.json').read_text())
    prep=json.loads(Path(m['executable_preparation_report']).read_text())
    if prep['output_elf_sha256']!=m['output_elf_sha256']:raise ValueError('Preparation identity differs')
    p=prep['save_tutorial_patch']
    d=Debugger(45384);saved=oldbytes=None;address=bp=None
    try:
        d.call('cpu.stepping',expect='cpu.stepping');saved=registers(d);regs=gpr(saved)
        mod=next(x for x in d.call('hle.module.list')['modules']if x['name']=='hp_proj');base=mod['address'];sp=regs['sp']
        if not 0x08001000<sp<0x0a000000:raise ValueError('Unexpected stack')
        address=sp-2048;oldbytes=d.read(address,2048);source=sp-1800;temp_sp=sp-128;bp=base+CONTINUATION
        proof=dict(version=m['version'],iso_sha256=m['iso_sha256'],executable_sha256=m['output_elf_sha256'],archive_sha256=m['dialogue_cpk_sha256'],
          helper_rva=p['helper_rva'],module_base=base,scope='Synthetic native width instruction execution; natural field scene pending.')
        print(json.dumps(proof,indent=2))
        if not a.run:print('DRY RUN');return
        d.call('cpu.breakpoint.add',address=bp);cases=[]
        for name,raw,expected in [('save_body_line1',b'Use this object to save your data.\x11\0',216),
          ('save_body_line2',b'It also restores HP and PP to their maximum values.\x0e\0',338),
          ('blue_title',b'\x1602\x81\x77Save Points\x81\x78\x0e\0',102),
          ('runtime_fallback',b'\x010A\x0e\0',637),('null',None,637)]:
            if raw:write(d,source,raw)
            for n,v in [('s6',source if raw else 0),('s7',49),('sp',temp_sp),('pc',base+p['helper_rva'])]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=bp,expect='cpu.stepping');out=gpr(registers(d))
            if out['pc']!=bp or out['a0']!=expected or out['sp']!=temp_sp or out['s6']!=(source if raw else 0)or out['s7']!=49:raise ValueError('Native width result differs')
            for n in ('s0','s1','s2','s3','s4','s5','fp','ra','t0','t1','t2','t3','t4','t5','t6','t7','t8','t9','a1','a2','a3','v0','v1'):
                if out[n]!=regs[n]:raise ValueError('Native ABI clobber: '+n)
            cases.append(dict(case=name,width_px=out['a0'],passed=True));restore_registers(d,saved)
        proof.update(native_instruction_cases=cases,all_registers_and_stack_restored=True,natural_field_scene_verified=False)
        dest=Path('work/ui/field/0.1.29/tutorial_native_instruction.en.json')
        if dest.exists():raise ValueError('Fresh evidence required')
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(cases,indent=2))
    finally:
        try:
            if bp is not None and a.run:d.call('cpu.breakpoint.remove',address=bp)
            if oldbytes is not None and a.run:write(d,address,oldbytes)
            if saved is not None:restore_registers(d,saved);d.call('cpu.resume',expect='cpu.resume')
        finally:d.close()

if __name__=='__main__':main()
