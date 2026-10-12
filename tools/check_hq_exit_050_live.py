"""Exercise installed question routing, glyphs and widths in an owned emulator.

Synthetic native calls do not claim a natural HQ exit playthrough. Borrowed
stack memory, registers, breakpoints and font color are restored.
"""
import json, struct
from pathlib import Path
from ppsspp_debug import Debugger
from live_vwf import registers,gpr,restore_registers,write,kernel_call
from executable_text_patch import Elf
from prepare_relocation_019 import section_load
from prepare_hq_exit_050 import BASE,OUT,LENGTH,sha

ROOT=Path('work/output/0.1.50-title-credit-vwf-4x-candidate')
UI=Path('work/ui/field/0.1.50')

def main():
    m=json.loads((ROOT/'manifest.en.json').read_text());data=(ROOT/'EBOOT.BIN').read_bytes();p=m['setup_patch'];e=Elf(data)
    if data!=(OUT/'EBOOT.BIN').read_bytes() or sha(data)!=m['output_elf_sha256']:raise ValueError('Installed identity differs')
    d=Debugger(45405);saved=oldmem=None;start=None;glyph=None;color=None;context=None
    try:
        d.call('cpu.stepping',expect='cpu.stepping')
        base=next(x['address']for x in d.call('hle.module.list')['modules']if x['name']=='hp_proj')
        d.call('cpu.runUntil',address=base+0x1b6cdc,expect='cpu.stepping')
        saved=registers(d);regs=gpr(saved);ret=regs['pc'];start=regs['sp']-8192;oldmem=d.read(start,8192);text=start+6000;temp_sp=start+4000
        loaded,_,_,_=section_load(data,base)
        for row in p['hq_exit_050']['changes']:
            if d.read(base+row['rva'],row['bytes'])!=bytes(loaded[0][row['rva']:row['rva']+row['bytes']]):raise ValueError('Installed code mismatch')
        lut=struct.unpack_from('<131I',data,e.file_offset(p['body_integer_lut_rva']))
        widths=[]
        samples=[b'Go to the World Map?\x0e\0',b'Yes\0',b'No\0',b'Are you sure?\0',b'Return to the title screen?\x0e\0',b'\0',b'\x82\xa0\x0e\0',b'A\x11B\0']
        for raw in samples:
            write(d,text,raw)
            for n,v in [('a0',text),('sp',temp_sp),('ra',ret),('pc',base+LENGTH)]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=ret,expect='cpu.stepping');out=gpr(registers(d))
            native=any(c<32 and c not in (0,14) or c>=129 for c in raw)
            expected=len(raw)-1 if native else 2*((sum(lut[c]for c in raw if 32<=c<129)+12)//13)
            if out['v0']!=expected or out['sp']!=temp_sp:raise ValueError('Width/stack differs '+repr(raw))
            widths.append(dict(bytes_hex=raw.hex(),native_fallback=native,result=out['v0'],passed=True));restore_registers(d,saved)
        context=kernel_call(d,base,0xe928c,[]);color=d.read(context+0x3a0,4);write(d,context+0x3a0,struct.pack('<I',4))
        glyph=base+0xea45c;d.call('cpu.breakpoint.add',address=glyph)
        cases=[]
        question=struct.unpack('<I',d.read(base+0x95480,4))[0];yes=struct.unpack('<I',d.read(base+0x9493c,4))[0];no=struct.unpack('<I',d.read(base+0x94940,4))[0]
        fixtures=[('legacy_blank_reproduction',0xe9f1c,question,b'Go to the World Map?',False),
                  ('hq_question',p['hq_exit_050']['helper_rva'],question,b'Go to the World Map?',True),
                  ('yes',p['hq_exit_050']['helper_rva'],yes,b'Yes',True),
                  ('no',p['hq_exit_050']['helper_rva'],no,b'No',True),
                  ('japanese',p['hq_exit_050']['helper_rva'],text,b'\x82\xa0',True)]
        for name,fn,ptr,raw,visible in fixtures:
            if ptr==text:write(d,text,raw+b'\x0e\0')
            for n,v in [('a0',context),('a1',ptr),('a2',100),('a3',110),('sp',temp_sp),('ra',ret),('pc',base+fn)]:d.call('cpu.setReg',name=n,value=v)
            drawn=[]
            for _ in range(100):
                d.call('cpu.runUntil',address=ret,expect='cpu.stepping');rr=gpr(registers(d))
                if rr['pc']==ret:break
                if rr['pc']!=glyph:raise ValueError('Unexpected glyph checkpoint')
                drawn.append(dict(code=rr['t1'],x=rr['a1'],y=rr['a2']))
            else:raise ValueError('Glyph loop bound exceeded')
            if rr['sp']!=temp_sp or any(rr[n]!=v for n,v in regs.items() if n in ('s0','s1','s2','s3','s4','s5','s6','s7','fp')):raise ValueError('Draw ABI differs')
            if name=='japanese':
                if len(drawn)!=1 or drawn[0]['code']!=0x82a0:raise ValueError('Japanese fallback differs')
            elif visible:
                if [v['code']for v in drawn]!=list(raw):raise ValueError('Missing or extra English glyph: '+name+' '+repr(drawn))
                pos=100
                for c,v in zip(raw,drawn):
                    if v['x']!=pos or v['y']!=110:raise ValueError('English VWF position differs')
                    pos+=lut[c]
            elif drawn:raise ValueError('Legacy path no longer reproduces reported blank')
            cases.append(dict(case=name,glyphs=drawn,passed=True));restore_registers(d,saved)
        proof=dict(version='0.1.50',iso_sha256=m['iso_sha256'],executable_sha256=sha(data),installed_code_verified=True,width_cases=widths,draw_cases=cases,legacy_blank_reproduced=True,question_all_glyphs_and_VWF_advances_verified=True,Japanese_native_fallback_verified=True,natural_HQ_exit_verified=False)
        UI.mkdir(parents=True,exist_ok=True);(UI/'native_confirmation.en.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(width_cases=len(widths),draw_cases=len(cases),all_passed=True)))
    finally:
        try:
            if glyph is not None:d.call('cpu.breakpoint.remove',address=glyph)
            if color is not None:write(d,context+0x3a0,color)
            if oldmem is not None:write(d,start,oldmem)
            if saved is not None:restore_registers(d,saved)
            if d.call('cpu.status').get('stepping'):d.call('cpu.resume',expect='cpu.resume')
        finally:d.close()

if __name__=='__main__':main()
