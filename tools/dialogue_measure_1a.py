"""Pure bounded 1A decimal-mode width proposal; no executable writer.

ECF38 consumes one selector after1A, while EE968 retains the original prefix
in row+4. Reuse the existing17 one-digit argument path; do not change controls.
"""
import inspect,json,struct,hashlib
from pathlib import Path
import dialogue_measure
from executable_text_patch import Elf
from build_menu_patch import relocate_code
from prepare_relocation_019 import section_load,coverage,pair_shapes
from remaining_label_audit import CURRENT,CURRENT_SHA
from font_vram_hooks import instruction_model

def sha(data):return hashlib.sha256(data).hexdigest()

def measure_1a(lut,hideo_ruby=False):
    source=inspect.getsource(dialogue_measure.measure)
    source=source.replace("f'argument_{control}'", "f'argument_{0x17 if control==0x1a else control}'")
    source=source.replace('for control,count in WIDTH_NEUTRAL_ARGUMENTS.items():',
                         'for control,count in WIDTH_NEUTRAL_ARGUMENTS.items():\n        if control==0x1a:continue')
    env=dialogue_measure.__dict__.copy();env['WIDTH_NEUTRAL_ARGUMENTS']={**dialogue_measure.WIDTH_NEUTRAL_ARGUMENTS,0x1a:1}
    exec(source,env);return env['measure'](lut,True,hideo_ruby)

def instruction_cases(widths,code_override=None,samples_override=None):
    import font_vram_hooks
    definition=inspect.getsource(instruction_model)
    floating="""elif op==49:
            a=(regs[s]+sv)&0xffffffff;reads.extend(range(a,a+4));F[t]=int.from_bytes(bytes(mem[a+n]for n in range(4)),'little')
        elif op==57:
            a=(regs[s]+sv)&0xffffffff
            for n,x in enumerate(F[t].to_bytes(4,'little')):mem[a+n]=x
        elif op==17:
            fmt=s;fd=(w>>6)&31;fs=d;ft=t
            if fmt==4:F[fs]=regs[t]
            elif fmt==20 and (w&63)==32:F[fd]=int.from_bytes(struct.pack('<f',struct.unpack('<i',F[fs].to_bytes(4,'little'))[0]),'little')
            elif fmt==16 and (w&63)==2:F[fd]=int.from_bytes(struct.pack('<f',struct.unpack('<f',F[fs].to_bytes(4,'little'))[0]*struct.unpack('<f',F[ft].to_bytes(4,'little'))[0]),'little')
            else:raise Exception('Unsupported FPU instruction '+hex(w))
        elif op==13:"""
    definition=definition.replace('    scope = dict(struct=struct,B=0x1750000)',
        f'    source = source.replace("elif op==13:", {floating!r})\n    scope = dict(struct=struct,B=0x1750000,F=F)')
    env=font_vram_hooks.__dict__.copy();env['F']=[0]*32;exec(definition,env)
    model=env['instruction_model']();execute=model['execute'];code=code_override or measure_1a(0x240000);cases=[]
    samples=[([b'\x1a5As the combo count rises, damage increases.\x12'],True),
             ([b'\x1a6Use the directional buttons.\x11',b'Front-row characters\x11',b'cannot perform Offense Actions.\x12'],True),
             ([b'\x1a0A\x12'],True),([b'\x1a9A\x12'],True),
             ([b'\x1aXA\x12'],False),([b'\x1a\0'],False),
             ([b'\x1a5\x01'+b'0A\x12'],False),([b'\x1a5A\x0f1A\x0f\x12'],False),
             ([b'\x1a5\xf0\x40\xf0\x41\x12'],True),
             ([b'A'*1022+b'\x1a5\x12'],True),([b'A'*1023+b'\x1a5\x12'],False)]
    if samples_override is not None:samples=samples_override
    for rows,supported in samples:
        regs=[0]+[0x12340000+n for n in range(1,32)];regs[4]=0x210000;regs[20]=0x200000;regs[23]=1;regs[29]=0x250000;before=regs[:]
        F=model['execute'].__globals__['F'];F[:]=[0x3f800000+n for n in range(32)];f_before=F[:]
        F[12]=int.from_bytes(struct.pack('<f',500.5),'little');mem={}
        def put(a,data):mem.update({a+n:x for n,x in enumerate(data)})
        put(0x200004,struct.pack('<I',0x210000));put(0x200018,struct.pack('<I',len(rows)))
        put(0x240000,struct.pack('<131I',*widths));expected=[]
        for n,raw in enumerate(rows):
            put(0x210004+n*0xe8,struct.pack('<I',0x220000+n*0x1000));put(0x210020+n*0xe8,struct.pack('<f',312.0));put(0x220000+n*0x1000,raw+b'\0')
            if supported:
                from dialogue_tokens import tokenize_bytes
                expected.append(sum(widths[t.code]for t in tokenize_bytes(raw,private_latin=True)if t.kind=='latin' and not t.ruby)/2)
        pc,out,reads=execute(code,regs,mem)
        if pc!=0xed164 or out!=before or F[0:2]!=f_before[0:2]:raise ValueError('Width helper ABI mismatch')
        value=lambda a:struct.unpack('<f',bytes(mem[a+n]for n in range(4)))[0]
        actual=[value(0x210020+n*0xe8)for n in range(len(rows))]
        maximum=value(0x20002c)
        if actual!=(expected if supported else [312.0]*len(rows)) or maximum!=(max(expected)if supported else 500.5):raise ValueError('Pinned width/fallback mismatch')
        for n,raw in enumerate(rows):
            if any(a>0x220000+n*0x1000+min(len(raw),1024)for a in reads if 0x220000+n*0x1000<=a<0x220000+(n+1)*0x1000):raise ValueError('Width lookahead exceeds bound')
        cases.append(dict(row_bytes=[len(x)for x in rows],supported=supported,line_halfwidths=actual,parent_maximum_halfwidth=maximum,passed=True))
    return cases

def build():
    incoming=CURRENT.read_bytes()
    if sha(incoming)!=CURRENT_SHA:raise ValueError('Frozen19 source differs')
    before=json.loads(CURRENT.with_name('executable.en.json').read_text(encoding='utf8'))
    elf=Elf(incoming);start=before['font_hooks']['measurement'];end=before['font_hooks']['reveal'];lut=before['body_integer_lut_rva']
    old=bytearray(dialogue_measure.measure(lut,True));old_records=relocate_code(old,0,len(old))
    if incoming[elf.file_offset(start):elf.file_offset(start)+len(old)]!=old:raise ValueError('Current measurement generator differs')
    new=bytearray(measure_1a(lut));new_records=relocate_code(new,0,len(new))
    if len(new)!=len(old)+12 or len(new)!=end-start:raise ValueError('Reviewed12B padding extent differs')
    padding=incoming[elf.file_offset(start)+len(old):elf.file_offset(end)]
    if padding!=bytes(12):raise ValueError('Measurement alignment pad is not zero')
    actual=[(off,flags)for off,flags in elf.relocs if flags>>8&255==0 and start<=off<end]
    expected_old=[(start+off,flags&255)for off,flags in struct.iter_unpack('<II',b''.join(old_records))]
    expected_new=[(start+off,flags&255)for off,flags in struct.iter_unpack('<II',b''.join(new_records))]
    if actual!=expected_old:raise ValueError('Measurement typed relocations differ')
    if any(start+len(old)<=off<end for off,_ in elf.relocs):raise ValueError('Padding has a relocation')
    output=bytearray(incoming);off=elf.file_offset(start,len(new));output[off:off+len(new)]=new
    relph=next(p for p in elf.ph if p[0]==0x700000a0);deltas=[]
    for old_record,new_record in zip(expected_old,expected_new):
        ordinal=elf.relocs.index(old_record)
        if old_record!=new_record:
            struct.pack_into('<II',output,relph[1]+ordinal*8,*new_record)
            deltas.append(dict(ordinal=ordinal,old=old_record,new=new_record))
    result=bytes(output);newelf=Elf(result);coverage(result)
    if len(newelf.relocs)!=len(elf.relocs)or len(deltas)!=1:raise ValueError('Expected sole moved return R26 differs')
    shapes=lambda data:[{k:v for k,v in p.items()if k!='records_sha256'}for p in pair_shapes(data)]
    if shapes(result)!=shapes(incoming):raise ValueError('HI/LO section pairing changed')
    models=[]
    for base in(0x8804000,0x8900000,0x8fff000):
        mem,records,skipped,pairs=section_load(result,base)
        r26=next(off for off,f in expected_new if f==4);w=struct.unpack_from('<I',mem[0],r26)[0]
        if (w&0x3ffffff)*4!=base+0xed164:raise ValueError('Loaded measurement return differs')
        models.append(dict(base=base,records=len(records),skipped=skipped,return_target=base+0xed164))
    proof=dict(status='pure_measure_1A_proposal_no_writer',input_sha256=CURRENT_SHA,output_sha256=sha(result),
        code_rva=start,old_code_bytes=len(old),new_code_bytes=len(new),consumed_zero_padding_bytes=12,
        code_sha256=sha(new),loaded_growth_bytes=0,new_relocations=0,moved_existing_relocations=deltas,
        section_pairing_exact=True,three_base_SHT_models=models,
        native_argument_proof=['ECF88 checks initial1A; ECFA4 decodes one following glyph; ECFC4 advances by its consumed-byte count.',
            'ED028 skips1A plus one selector at line start before native measurement.',
            'ED080 passes original S5 in A2 toEE968; EE980 stores it row+4, so pixel measurement retains1A selector.',
            'Only one ASCII decimal selector is accepted here; malformed/nondecimal/unhandled runtime/ruby retain original native fallback.'],
        parent_and_row_halfwidths_updated_together=True,native_cache_and_line_allocation_unchanged=True,
        emitted_instruction_cases=instruction_cases(list(struct.unpack_from('<131I',incoming,elf.file_offset(lut,524)))),
        runtime_verified=False,remaining='Root review and actual geometry QA before installation; formation long lines may need separate serialized layout ledger.')
    return result,proof

if __name__=='__main__':
    _,proof=build();print(json.dumps(proof,indent=2));print('DRY ONLY: no executable writer.')
