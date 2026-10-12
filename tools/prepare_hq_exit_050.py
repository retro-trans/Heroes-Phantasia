"""Repair the shared plain confirmation renderer without growing loaded memory."""
import argparse, copy, json, struct
from pathlib import Path
from executable_text_patch import Elf
from native_menu_install_plan import cstring
from dialogue_vwf_hooks import Block
from live_vwf import i, j, jal
from font_vram_hooks import instruction_model
from prepare_relocation_019 import sections, section_load, coverage
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from prepare_field_labels_046 import sha

BASE = Path('work/output/0.1.49-title-credit-vwf-4x-candidate')
OUT = Path('work/output/0.1.50-hq-exit-assets')
INPUT_SHA = '5b2fc12a78052c40aa1d499976680b566d2f43ce508ac9d3a58853f814ce3c2f'
DRAW = [0x8e594,0x8e61c,0x8e6c8,0x8e750,0x8e7fc,0x8e82c,
        0x8e8d8,0x8e908,0x8e99c,0x8f2fc,0x906a4,0x906d0,
        0x90758,0x907f4,0x908a0,0x90918,0x909a8,0x90a30,
        0x914c8,0x91574,0x915fc,0x91698,0x91724,0x917c0,0x9184c,0x918f8]
# These strlen results feed only the native /2*13 centered-width calculation.
# 907C0's unused strlen and storage/copy lengths elsewhere are deliberately intact.
CENTER = [0x8e530,0x8e5b8,0x8e664,0x8e6ec,0x8e77c,0x8e858,
          0x90614,0x906e4,0x9083c,0x908b4,0x90938,0x909bc,
          0x91464,0x91510,0x91598,0x91628,0x916bc,0x91750,0x917e4]
LENGTH = 0x2e5c60

def dispatcher():
    h = Block()
    h.branch(4,5,0,'native')
    h.emit(i(36,5,24,0),i(9,24,24,-32),i(11,24,24,95))
    h.branch(5,24,0,'latin')
    h.label('native'); h.emit(j(0xe9f1c),0)
    h.label('latin'); h.emit(j(0x92d70),0)
    return h.finish()

def build():
    incoming=(BASE/'EBOOT.BIN').read_bytes()
    before=json.loads((BASE/'manifest.en.json').read_text())['setup_patch']
    if sha(incoming)!=INPUT_SHA: raise ValueError('Frozen .49 executable differs')
    e=Elf(incoming); result=bytearray(incoming); changes=[]; allowed=set(); mask=set()
    def install(rva,data,name):
        f=e.file_offset(rva,len(data)); old=incoming[f:f+len(data)]
        result[f:f+len(data)]=data; allowed.update(range(f,f+len(data)));mask.update(range(rva,rva+len(data)))
        changes.append(dict(name=name,rva=rva,bytes=len(data),before_sha256=sha(old),after_sha256=sha(data)))
    free=[(r['start'],r['end']) for r in before['field_labels_047']['retired_menu_regions']]+[(0x305dc8,0x3062c8)]
    for row in before['field_labels_047']['placements']+before['dialogue_commands_048']['changes']:
        a,b=row['rva'],row['rva']+row['bytes']
        free=[z for s,t in free for z in ((s,min(t,a)),(max(s,b),t)) if z[0]<z[1]]
    code=dispatcher(); helper=next(((a+3)&-4) for a,b in free if ((a+3)&-4)+len(code)<=b)
    install(helper,code,'plain_confirmation_dispatch')
    actual=[a for a in range(0,0x120000,4) if e.word(a)==jal(0xe9f1c)]
    if actual!=DRAW: raise ValueError('Shared draw caller inventory differs')
    for a in DRAW:
        if (a,4) not in e.relocs:raise ValueError('Caller lacks existing J26 relocation')
        install(a,struct.pack('<I',jal(helper)),'shared_confirmation_draw')
    # Recognize the original trailing 0E as a width terminator. Fit two extra
    # comparisons into existing delay slots; unknown controls/Japanese retain strlen.
    expected=struct.pack('<5I',0,i(11,10,11,32),i(5,11,0,(0x2e5cd8-0x2e5c80-4)//4),0,i(11,10,11,129))
    if incoming[e.file_offset(LENGTH+24,20):][:20]!=expected:raise ValueError('Width helper differs')
    words=[i(13,0,11,14),i(4,10,11,(0x2e5cbc-0x2e5c7c-4)//4),
           i(11,10,11,32),i(5,11,0,(0x2e5cd8-0x2e5c84-4)//4),i(11,10,11,129)]
    install(LENGTH+24,struct.pack('<5I',*words),'width_0E_terminator')
    for a in CENTER:
        if e.word(a)!=jal(0x128b64) or (a,4) not in e.relocs:raise ValueError('Center caller differs')
        install(a,struct.pack('<I',jal(LENGTH)),'confirmation_vwf_center')
    # Only two new J26 records in the dispatcher; preserve all loaded extents.
    ss=sections(incoming);ph=[list(p)for p in e.ph];rp=ph[3];end=rp[1]+rp[4]
    if struct.unpack_from('<I',incoming,32)[0]!=end or end+len(ss)*40!=len(incoming):raise ValueError('Relocation tail differs')
    additions=b''.join(struct.pack('<II',helper+n,4) for n in range(0,len(code),4) if struct.unpack_from('<I',code,n)[0]>>26==2)
    result.extend(bytes(len(additions)+40));result[end:end+len(additions)]=additions
    allowed.update(range(end,len(incoming)))
    ss.append([0,0x700000a0,0,0,end,len(additions),0,1,4,8]); shoff=end+len(additions)
    for n,s in enumerate(ss):struct.pack_into('<10I',result,shoff+n*40,*s)
    rp[4]+=len(additions);po=struct.unpack_from('<I',incoming,28)[0]
    struct.pack_into('<8I',result,po+96,*rp);allowed.update(range(po+96,po+128))
    struct.pack_into('<I',result,32,shoff);allowed.update(range(32,36))
    struct.pack_into('<H',result,48,len(ss));allowed.update(range(48,50))
    data=bytes(result);out=Elf(data);coverage(data)
    if out.ph[:3]!=e.ph[:3] or out.relocs[:len(e.relocs)]!=e.relocs:raise ValueError('Inherited loaded contracts changed')
    if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,data))):raise ValueError('Unselected file bytes changed')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        old,_,_,_=section_load(incoming,base);new,visited,skipped,_=section_load(data,base)
        if skipped or visited!=out.relocs or old[1:]!=new[1:] or any(a!=b and n not in mask for n,(a,b)in enumerate(zip(old[0],new[0]))):raise ValueError('Unselected loaded bytes changed')
        model=instruction_model();model['execute'].__globals__['B']=base
        cases=[]
        for name,raw,latin in [('hq_exit',b'Go to the World Map?\x0e\0',True),('yes',b'Yes\0',True),('space',b' X\0',True),('japanese',b'\x82\xa0\0',False),('control',b'\x0e\0',False),('empty',b'\0',False),('DEL',b'\x7f\0',False),('null',None,False)]:
            regs=[0]+[0x12340000+n for n in range(1,32)];regs[5]=0x230000 if raw else 0;mem={} if raw is None else {0x230000+n:v for n,v in enumerate(raw)}
            pc,after,_=model['execute'](bytes(new[0][helper:helper+len(code)]),regs,mem)
            if pc!=base+(0x92d70 if latin else 0xe9f1c) or any(a!=b for n,(a,b)in enumerate(zip(regs,after)) if n!=24):raise ValueError('Dispatcher ABI differs: '+name)
            cases.append(dict(case=name,latin=latin,passed=True))
        models.append(dict(base=base,unselected_memory_exact=True,dispatch_cases=cases))
    report=copy.deepcopy(before)
    for k in ('output','approved_dry_plan_sha256','written_readback_verified'):report.pop(k,None)
    report.update(version='0.1.50',input_version='0.1.49',input_sha256=INPUT_SHA,output_elf_sha256=sha(data),output_sha256=sha(data),elf_bytes=len(data),total_relocations=len(out.relocs),added_relocations=len(out.relocs)-before['original_relocations'],relocation_table_sha256=sha(data[rp[1]:rp[1]+rp[4]]),runtime_verified=False)
    for chunk in report['native_tail_compaction']['chunks']:
        f,n=chunk['file_offset'],chunk['bytes']
        if data[f:f+n]!=incoming[f:f+n]:chunk['output_sha256']=sha(data[f:f+n]);chunk['current_proof_scope']='Existing setup width helper also accepts the original final 0E terminator.'
    report['hq_exit_050']=dict(prompt='Go to the World Map?',pointer_slot=0x95480,helper_rva=helper,helper_bytes=len(code),changes=changes,draw_callers=DRAW,center_callers=CENTER,loader_models=models,loaded_growth_bytes=0,new_relocations=len(additions)//8,original_Japanese_draw_path_preserved=True,event_bytecode_unchanged=True,centering_policy='Inherited 13px layout units, rounded upward from actual English advances.',natural_gameplay_verified=False)
    authoritative_font_metadata(data,report);validate_native_png_metadata(data,report)
    return data,report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--expected-sha256');a=p.parse_args()
    data,report=build();print(json.dumps(dict(version='0.1.50',sha256=sha(data),helper=report['hq_exit_050']['helper_rva'],draw_callers=26,center_callers=19,loaded_growth_bytes=0),indent=2))
    if not a.write:print('DRY RUN: no assets written.');return
    if a.expected_sha256!=sha(data) or OUT.exists():raise ValueError('Reviewed hash and fresh destination required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data);report['written_readback_verified']=(OUT/'EBOOT.BIN').read_bytes()==data
    (OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
