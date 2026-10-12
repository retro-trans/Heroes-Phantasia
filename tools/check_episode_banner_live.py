"""Exercise the installed banner remap in the isolated 0.1.28 debugger.

Dry mode inspects only. --run uses a temporary stack object, restores every
register and stack byte, and resumes. This is not a natural field-scene trace.
"""
import argparse,json,struct,hashlib
from pathlib import Path
from ppsspp_debug import Debugger
from live_vwf import gpr,registers,restore_registers,write
from episode_banner_hook import SITE,source_payload

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',action='store_true');a=ap.parse_args()
    prep=json.loads(Path('work/output/0.1.28-field-ui-assets/executable.en.json').read_text());info=prep['field_ui_patch']['episode_inline_banner']
    d=Debugger(45383);saved=None;oldbytes=None;address=None;bp=None
    try:
        d.call('cpu.stepping',expect='cpu.stepping');saved=registers(d);regs=gpr(saved)
        mod=next(m for m in d.call('hle.module.list')['modules']if m['name']=='hp_proj');base=mod['address'];sp=regs['sp']
        if not 0x08000400<sp<0x0a000000:raise ValueError('Unexpected PSP user stack')
        address=sp-512;oldbytes=d.read(address,512);context=sp-384;temp_sp=sp-128
        source=base+info['source_payload_rva'];target=base+info['target_payload_rva'];bp=base+SITE+8
        if d.read(source,info['source_payload_bytes'])!=source_payload():raise ValueError('Loaded source signature differs')
        report=dict(version='0.1.28',executable_sha256=prep['output_elf_sha256'],module_base=base,source_rva=info['source_payload_rva'],
          target_rva=info['target_payload_rva'],helper_rva=info['helper_rva'],scope='Synthetic native parser object; natural episode scene remains unverified.')
        print(json.dumps(report,indent=2))
        if not a.run:print('DRY RUN: no PSP memory/register changes.');return
        tests=[]
        d.call('cpu.breakpoint.add',address=bp)
        for name,ptr,expected in [('exact',source,target),('English_fallback',target,target),('null',0,0)]:
            write(d,context+20,struct.pack('<I',ptr))
            for n,v in [('s4',context),('sp',temp_sp),('pc',base+info['helper_rva'])]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=bp,expect='cpu.stepping')
            out=gpr(registers(d));cursor=struct.unpack('<I',d.read(context+20,4))[0]
            if out['pc']!=bp or out['a0']!=expected or cursor!=expected or out['sp']!=temp_sp:raise ValueError('Native remap/cursor/stack mismatch')
            for n in ('s0','s1','s2','s3','s5','s6','s7','fp','ra','t0','t1','t2','t3','t4','t5','t6','t7','t8','t9','a1','a2','a3','v0','v1'):
                if out[n]!=regs[n]:raise ValueError('Native ABI clobber '+n)
            tests.append(dict(case=name,passed=True,source_pointer=ptr,result_pointer=cursor))
            restore_registers(d,saved)
        report.update(native_instruction_cases=tests,all_registers_and_stack_restored=True,natural_scene_interception_verified=False)
        path=Path('work/ui/field/0.1.28/banner_native_instruction.en.json')
        if path.exists():raise ValueError('Fresh evidence required')
        path.write_text(json.dumps(report,indent=2)+'\n')
        print('Native exact-match, English fallback and null cases pass.')
    finally:
        try:
            if bp is not None and a.run:d.call('cpu.breakpoint.remove',address=bp)
            if oldbytes is not None and a.run:write(d,address,oldbytes)
            if saved is not None:restore_registers(d,saved);d.call('cpu.resume',expect='cpu.resume')
        finally:d.close()

if __name__=='__main__':main()
