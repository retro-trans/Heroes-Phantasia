"""Bounded native custom-polygon tests in an isolated debugger; dry first.

Temporary-code mode is preparation evidence, not installed ISO validation.
All borrowed memory, manager state, registers and temporary code are restored.
"""
import argparse,json,struct,math
from pathlib import Path
from ppsspp_debug import Debugger
from live_vwf import gpr,registers,restore_registers,write
from executable_text_patch import Elf
from prepare_relocation_019 import section_load
from prepare_english_bubbles import build,SOURCE,CORE,CORE_BYTES,REGION,REGION_BYTES,sha
from bubble_metrics import load_templates

def definitions():
    cases=[]
    for t in load_templates():
        family=(t['template_id']-3)%10
        if family<8 and t['count']==10:
            lines=t['template_id']//10%4+1
            cases.append((f"standard_{t['template_id']}",t['template_id'],240.,140.,b'\x11'.join([b'A']*lines)+b'\x12\x0e\0',lines,80.,1.,0.,True))
    cases.extend([
      ('kogoro',118,125.,104.,b"If you're in HOLY,\x11then you must be an\x11\x05050\x1603Alter user\x1601, too!\x12\x0e\0",3,66.,1.,0.,True),
      ('serish',8,369.,99.,b'Who will accompany you?\x12\x0e\0',1,82.5,1.,0.,True),
      ('top_clamp',118,125.,40.,b'A\x11B\x11C\x11D\x12\x0e\0',4,80.,1.,0.,True),
      ('right_clamp',118,465.,140.,b'A\x12\x0e\0',1,80.,1.,0.,True),
      ('left_clamp',4,15.,140.,b'A\x12\x0e\0',1,80.,1.,0.,True),
      ('hideo',118,125.,104.,b'Hideo\x0f2Hideo\x0f\x12\x0e\0',1,30.,1.,0.,True),
      ('private_pairs',118,125.,104.,b'A\xf0\x40\xf0\x41\x12\x0e\0',1,30.,1.,0.,True),
      ('mode_controls',118,125.,104.,b'\x1a5\x172A\x12\x0e\0',1,30.,1.,0.,True),
      ('animated',118,125.,104.,b'A\x12\x0e\0',1,30.,.5,0.,False),
      ('rotated',118,125.,104.,b'A\x12\x0e\0',1,30.,1.,1.,False),
      ('native_text',118,125.,104.,b'\x82\xa0\x12\x0e\0',1,30.,1.,0.,False),
      ('malformed_color',118,125.,104.,b'A\x16X1\x12\x0e\0',1,30.,1.,0.,False),
      ('malformed_delay',118,125.,104.,b'A\x050X0\x12\x0e\0',1,30.,1.,0.,False),
      ('unknown_substitution',118,125.,104.,b'A\x01'+b'0\x12\x0e\0',1,30.,1.,0.,False),
      ('other_ruby',118,125.,104.,b'A\x0f1A\x0f\x12\x0e\0',1,30.,1.,0.,False),
      ('star',1,125.,104.,b'A\x12\x0e\0',1,30.,1.,0.,False),
      ('too_wide',118,125.,104.,b'A\x12\x0e\0',1,240.,1.,0.,False),
    ])
    for mode in (0,1,2,3,4):
        cases.append(('alignment_'+str(mode),118,125.,104.,b'A\x12\x0e\0',1,30.,1.,0.,False))
    cases.append(('alignment_mixed',118,125.,104.,b'A\x11B\x12\x0e\0',2,30.,1.,0.,False))
    return cases

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--port',type=int,default=45388)
    ap.add_argument('--manifest',type=Path,default=Path('work/output/0.1.32-title-credit-vwf-4x-candidate/manifest.en.json'))
    ap.add_argument('--temporary-code',action='store_true');ap.add_argument('--run',action='store_true')
    ap.add_argument('--output',type=Path,default=Path('work/ui/dialogue/0.1.33/native_preparation.en.json'));a=ap.parse_args()
    candidate,prep=build();m=json.loads(a.manifest.read_text());defs=definitions()
    print(json.dumps(dict(candidate_sha256=sha(candidate),loaded_build=m['version'],temporary_code=a.temporary_code,cases=len(defs)),indent=2))
    if not a.run:print('DRY RUN');return
    if a.output.exists():raise ValueError('Fresh native evidence required')
    loaded=(a.manifest.parent/'EBOOT.BIN').read_bytes()
    if sha(loaded)!=m['output_elf_sha256'] or (not a.temporary_code and loaded!=candidate):raise ValueError('Loaded/candidate identity differs')
    d=Debugger(a.port);saved=oldmem=oldmanager=None;start=manager=bp=None;replaced=[]
    try:
        if not d.call('cpu.status').get('stepping'):d.call('cpu.stepping',expect='cpu.stepping')
        saved=registers(d);regs=gpr(saved);base=next(x['address']for x in d.call('hle.module.list')['modules']if x['name']=='hp_proj')
        if a.temporary_code:
            memories,_,_,_=section_load(candidate,base)
            for rva,size,seg in ((CORE,CORE_BYTES,2),(REGION,REGION_BYTES,0)):
                old=d.read(base+rva,size);replaced.append((base+rva,old));off=rva-Elf(candidate).ph[seg][2]
                write(d,base+rva,bytes(memories[seg][off:off+size]))
        start=regs['sp']-8192;oldmem=d.read(start,8192)
        window=start+128;owner=start+1100;context=start+1400;container=start+1500;source=start+1600;rows=start+2300;temp_sp=regs['sp']-1024
        manager=base+0x166f2c4;oldmanager=d.read(manager,48);bp=base+0xe4e14
        d.call('cpu.breakpoint.add',address=bp);templates=load_templates();cases=[]
        for name,shape,x,y,raw,lines,halfwidth,scale,rotation,supported in defs:
            t=templates[shape];buf=bytearray(0x360)
            struct.pack_into('<3f',buf,0x2d0,x,y,0.);struct.pack_into('<3f',buf,0x2e0,rotation,0.,0.)
            struct.pack_into('<3f',buf,0x2f0,scale,scale,scale)
            struct.pack_into('<4f',buf,0x304,*t['speaker_offset'],*t['text_offset'])
            struct.pack_into('<H',buf,0x318,shape);struct.pack_into('<I',buf,0x31c,0x12345678);struct.pack_into('<I',buf,0x348,owner)
            write(d,window,buf)
            buf=bytearray(0x100);struct.pack_into('<I',buf,0x98,context);struct.pack_into('<I',buf,0xec,2);write(d,owner,buf)
            buf=bytearray(0x40);struct.pack_into('<I',buf,0x30,3);write(d,context,buf)
            buf=bytearray(0x40);struct.pack_into('<II',buf,8,3,2);struct.pack_into('<4I',buf,0x14,source,lines,lines,0)
            struct.pack_into('<I',buf,4,rows)
            struct.pack_into('<f',buf,0x2c,halfwidth);write(d,container,buf);write(d,source,raw)
            buf=bytearray(4*0xe8)
            for row in range(lines):
                alignment=int(name[-1])if name.startswith('alignment_')and name!='alignment_mixed'else (2 if name=='alignment_mixed'and row==1 else -1)
                struct.pack_into('<i',buf,row*0xe8+0x70,alignment)
            write(d,rows,buf)
            buf=bytearray(oldmanager);struct.pack_into('<I',buf,0,1);struct.pack_into('<II',buf,0x28,1,container);write(d,manager,buf)
            for n,v in [('a0',window),('sp',temp_sp),('pc',base+CORE)]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=bp,expect='cpu.stepping');out=registers(d);actual=gpr(out)
            if actual['pc']!=bp or actual['sp']!=temp_sp-224 or actual['a0']!=window or actual['a1']!=0x12345678:raise ValueError(name+': continuation ABI differs')
            for n,v in regs.items():
                if n not in ('pc','a0','a1','sp')and actual[n]!=v:raise ValueError(name+': GPR clobber '+n)
            for old,now in zip(saved[1:],out[1:]):
                if old['uintValues']!=now['uintValues']:raise ValueError(name+': floating/VFPU ABI differs')
            value=d.read(window,0x360);cx,cy=struct.unpack_from('<2f',value,0x2d0);body=[]
            for off in (0,0xf0,0x1e0):body.append([struct.unpack_from('<2f',value,off+n*8)for n in range(t['count'])])
            if supported:
                tip=(shape-3)%10+1
                expected=[list(t['outline'][tip]),list(t['banks'][0][tip]),list(t['banks'][1][tip])]
                if name=='serish':expected=[[243.-x,134.-y],[246.5-x,133.-y],[239.5-x,135.-y]]
                for points,goal in zip(body,expected):
                    vx,vy=points[tip]
                    if abs(vx+cx-goal[0]-x)>1e-4 or abs(vy+cy-goal[1]-y)>1e-4:raise ValueError(name+': tail endpoint moved')
                for n,(vx,vy)in enumerate(body[0]):
                    if n!=tip and not(8-1e-4<=vx+cx<=472+1e-4 and 36-1e-4<=vy+cy<=252+1e-4):raise ValueError(name+': body outside viewport')
                top=struct.unpack_from('<f',value,0x310)[0]+cy
                if not math.isfinite(top)or top<36 or top+(lines-1)*22+16>max(p[1]+cy for n,p in enumerate(body[0])if n!=tip)-8:
                    raise ValueError(name+': text bands exceed padded body')
                if name=='kogoro'and(abs(cx-125)>1e-4 or abs(top-73.5)>1e-4):raise ValueError('Kogoro reviewed placement differs')
            else:
                if (cx,cy)!=(x,y)or list(struct.unpack_from('<4f',value,0x304))!=t['speaker_offset']+t['text_offset']:
                    raise ValueError(name+': fallback text offsets differ')
                for points,expected in zip(body,[t['outline'],*t['banks']]):
                    if any(abs(a-b)>1e-4 for pair,goal in zip(points,expected)for a,b in zip(pair,goal)):raise ValueError(name+': fallback geometry differs')
            cases.append(dict(case=name,shape=shape,selected=supported,visible_lines=lines,center=[cx,cy],passed=True))
            if name in ('kogoro','serish','top_clamp'):
                cases[-1].update(outline=[list(p)for p in body[0]],fill_banks=[[list(p)for p in bank]for bank in body[1:]],body_text_offset=list(struct.unpack_from('<2f',value,0x30c)))
            restore_registers(d,saved)
        proof=dict(version='0.1.33',loaded_build=m['version'],loaded_iso_sha256=m['iso_sha256'],candidate_sha256=sha(candidate),
            installed_candidate=not a.temporary_code,module_base=base,cases=cases,all_registers_stack_manager_and_temporary_code_restored=True,
            native_instruction_verified=True,natural_story_scene_verified=False,scope='Synthetic associated-window native polygon/ABI tests; natural scene rendering remains unverified.')
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
        print(json.dumps(dict(cases=len(cases),all_passed=True,output=str(a.output)),indent=2))
    finally:
        try:
            if bp is not None:d.call('cpu.breakpoint.remove',address=bp)
            if oldmanager is not None:write(d,manager,oldmanager)
            if oldmem is not None:write(d,start,oldmem)
            for addr,raw in reversed(replaced):write(d,addr,raw)
            if saved is not None:restore_registers(d,saved);d.call('cpu.resume',expect='cpu.resume')
        finally:d.close()
if __name__=='__main__':main()
