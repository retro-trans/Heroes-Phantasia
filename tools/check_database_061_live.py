"""Exercise the installed exact notice remap and reported bubble geometry.

Uses an owned test emulator, borrowing and restoring registers and stack memory.
This verifies native helpers; it does not claim a natural HQ playthrough.
"""
import base64, json, struct, sys
from pathlib import Path
from ppsspp_debug import Debugger
from live_vwf import registers, gpr, restore_registers, write
from prepare_relocation_019 import section_load
from executable_text_patch import Elf
from native_menu_install_plan import cstring
import dialogue_layout_guard as g
from prepare_database_061 import RESOURCES, read
from rebuild_dialogue import parse

ROOT=Path('work/output/0.1.61-title-credit-vwf-4x-candidate')
UI=Path('work/ui/dialogue/0.1.61')


def remap():
    raw=(ROOT/'EBOOT.BIN').read_bytes(); m=json.loads((ROOT/'manifest.en.json').read_bytes())
    if g.sha(raw)!=m['output_elf_sha256']: raise ValueError('Installed executable differs')
    prep=m['setup_patch']; scope=prep['database_notice_061']; e=Elf(raw)
    entries=prep['field_labels_047']['notices']; continuation=prep['field_labels_047']['episode_hook_continuation_rva']
    helper=scope['helper_rva']; sources=[cstring(e,v['source_payload_rva']) for v in entries]
    cases=[('null',None,None),('empty',b'\0',None),('unrelated',b'\x1a2Other notice\x12\x0e\0',None)]
    for n,(entry,source) in enumerate(zip(entries,sources)):
        cases.append(('exact_'+str(n),source,entry['target_payload_rva']))
        altered=bytearray(source); altered[-2]^=1
        cases.append(('mismatch_'+str(n),bytes(altered),None))
        cases.append(('truncated_'+str(n),source[:len(source)//2]+b'\0',None))
    d=Debugger(45406); saved=oldmem=None; start=None; results=[]
    try:
        d.call('cpu.stepping',expect='cpu.stepping')
        base=next(v['address'] for v in d.call('hle.module.list')['modules'] if v['name']=='hp_proj')
        if gpr(registers(d))['pc']!=base+0x1b6cdc:
            d.call('cpu.runUntil',address=base+0x1b6cdc,expect='cpu.stepping')
        saved=registers(d); regs=gpr(saved); start=regs['sp']-8192; oldmem=d.read(start,8192)
        loaded,_,_,_=section_load(raw,base)
        for rva,n in [(helper,scope['allocation_bytes']),*[(v['source_payload_rva'],v['source_payload_bytes']) for v in entries],*[(v['target_payload_rva'],v['target_payload_bytes']) for v in entries]]:
            actual=base64.b64decode(d.call('memory.read',address=base+rva,size=n,replacements=False)['base64'])
            if actual!=bytes(loaded[0][rva:rva+n]): raise ValueError('Loaded notice allocation differs')
        cursor=start+512; pointer=start+1024; stack=start+4096
        for name,payload,dest in cases:
            if payload is not None: write(d,pointer,payload)
            sourceptr=pointer if payload is not None else 0
            write(d,cursor,bytes(64)); write(d,cursor+0x14,struct.pack('<I',sourceptr))
            for reg,value in [('s4',cursor),('sp',stack),('pc',base+helper)]: d.call('cpu.setReg',name=reg,value=value)
            before=gpr(registers(d)); expected=base+dest if dest is not None else sourceptr
            d.call('cpu.runUntil',address=base+continuation,expect='cpu.stepping'); after=gpr(registers(d))
            if after['pc']!=base+continuation or after['a0']!=expected:
                raise ValueError('Native match or continuation differs: '+name)
            if any(before[k]!=after[k] for k in before if k not in ('pc','a0')):
                raise ValueError('Native register ABI differs: '+name)
            if struct.unpack('<I',d.read(cursor+0x14,4))[0]!=expected or struct.unpack('<I',d.read(cursor+0x24,4))[0]!=before['s5']:
                raise ValueError('Native parser cursor differs: '+name)
            results.append(dict(case=name,matched=dest is not None,passed=True))
            restore_registers(d,saved)
        proof=dict(version='0.1.61',iso_sha256=m['iso_sha256'],executable_sha256=g.sha(raw),
            module_base=base,cases=results,installed_helper_and_all_keys_targets_exact=True,
            scratch_registers_and_stack_restored=True,natural_hq_playthrough_verified=False)
        (UI/'native_notice.en.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
        print(json.dumps(dict(native_notice_cases=len(results),all_passed=True)))
    finally:
        try:
            if oldmem is not None: write(d,start,oldmem)
            if saved is not None: restore_registers(d,saved)
            if d.call('cpu.status').get('stepping'): d.call('cpu.resume',expect='cpu.resume')
        finally: d.close()


def bubbles():
    import check_english_bubbles_v10_live as check
    raw=(ROOT/'EBOOT.BIN').read_bytes(); m=json.loads((ROOT/'manifest.en.json').read_bytes())
    selected={name:[11] for name in RESOURCES}
    selected.update({f'phase/bin/p101{branch}.bin':[15,23] for branch in ('140','141')})
    selected.update({f'phase/bin/p101{branch}.bin':[5] for branch in ('150','151')})
    assets=read(ROOT/'HP.CPK',selected); widths=g.widths_from(ROOT/'EBOOT.BIN'); cases=[]
    for name,index in ((name,index) for name in selected for index in selected[name]):
        data=assets[name]
        row=g.inspect(name,data,parse(name,data),index,widths)
        if row['status']!='fit': raise ValueError('Reported bubble fails layout guard')
        for pi,page in enumerate(row['pages']):
            body=bytes.fromhex(page['body_hex']); lines=len(page['line_advances'])
            for ki,key in enumerate(row['position_keys']):
                if tuple(key[1:3])==(0.,0.): continue
                for half in g.parent_halves(row['pages']):
                    cases.append((f'reported_{Path(name).stem}_{index}_p{pi}_k{ki}_h{half}',row['shape'],*key[1:3],body+b'\0',lines,half,1.,0.,g.ray_fit(row['shape'],key[1:3],half,lines)))
    check.build=lambda:(raw,m['setup_patch']); check.definitions=lambda:cases
    sys.argv=['native','--port','45406','--manifest',str(ROOT/'manifest.en.json'),'--run','--output',str(UI/'native_gift.en.json')]
    check.main()
    path=UI/'native_gift.en.json'; proof=json.loads(path.read_bytes())
    proof.update(version='0.1.61',reported_references=selected,natural_hq_playthrough_verified=False)
    path.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')


if __name__=='__main__': remap(); bubbles()
