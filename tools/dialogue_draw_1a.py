"""Scoped decimal1A drawing/reveal preparation; dry by default, guarded fresh writer."""
import argparse,json,struct,hashlib,inspect,copy
from pathlib import Path
from executable_text_patch import Elf
from dialogue_vwf_hooks import Block
from live_vwf import i,j
from png_tail_allocate import plan
from build_menu_patch import relocate_code
from prepare_relocation_019 import sections,coverage,section_load,pair_shapes
from font_vram_hooks import instruction_model

SOURCE=Path('work/output/0.1.21-save-logo-assets/EBOOT.BIN')
SOURCE_SHA='63998e6e446d2209724ebc39c5258487e699040e3d1cf7558e1b4b4998645e92'
SITE=0xeff2c
def sha(data):return hashlib.sha256(data).hexdigest()

def cap_layout():
    import dialogue_wrap
    source=inspect.getsource(dialogue_wrap.literal_reveal_cap)
    source=source.replace('h=Block();','h=Block();capture.append(h);',1)
    env=dialogue_wrap.__dict__.copy();env['capture']=[];exec(source,env)
    code=env['literal_reveal_cap'](True,True,True);h=env['capture'][0]
    sites=[pos*4 for pos,op,rs,rt,label in h.fixups if op==4 and rs==rt==0 and label=='native']
    if len(sites)!=1:raise ValueError('Cap unsupported-control branch changed')
    return code,sites[0],h.labels['arg1']*4,h.labels['native']*4

def cap_handler(cap):
    _,_,arg1,native=cap_layout();h=Block()
    h.emit(i(13,0,12,0x1a));h.branch(5,11,12,'native')
    h.emit(j(cap+arg1),0);h.label('native');h.emit(j(cap+native),0)
    return h.finish()

def native_consumption_cases(original):
    model=instruction_model();results=[]
    def execute_at(start,end,regs,memory):
        model['B']=start
        return model['execute'](original.data[original.file_offset(start):original.file_offset(end)],regs,memory)
    for style in range(48,58):
        for entry,continuation,oldreg in ((0xf0e18,0xf0e20,17),(0xefeac,0xefeb8,18)):
            regs=[0]*32;regs[4]=0x1a;regs[16]=0x210000;regs[29]=0x230000
            memory={0x210000+n:b for n,b in enumerate(struct.pack('<I',0x220000))};memory[0x220000]=style
            pc,regs,_=execute_at(entry,continuation,regs,memory)
            if pc!=0xe9c04 or regs[oldreg]!=0x220000:raise ValueError('Native argument call/delay differs')
            table=0x2ef1c0+25*4;word=original.word(table)
            memory.update({table+n:b for n,b in enumerate(struct.pack('<I',word))})
            pc,regs,_=execute_at(0xe9c04,0xe9c30,regs,memory)
            if pc!=0xe9c38:raise ValueError('Native1A width is not one')
            pc,regs,_=execute_at(0xe9c38,0xe9c40,regs,memory)
            if pc!=continuation or regs[2]!=1:raise ValueError('Native argument count/return differs')
            end=0xf0e30 if entry==0xf0e18 else 0xefec0
            pc,regs,_=execute_at(continuation,end,regs,memory)
            pointer=struct.unpack('<I',bytes(memory[0x210000+n]for n in range(4)))[0]
            if pointer!=0x220001:raise ValueError('Native pointer did not skip one selector')
            if entry==0xf0e18 and(pc!=0xf0f3c or regs[19]!=1):raise ValueError('Native draw non-glyph completion differs')
            results.append(dict(style=chr(style),entry_rva=entry,source_advance=1,native_count=1,passed=True))
    return results

def handler():
    h=Block();h.emit(i(9,29,29,-16),i(43,29,24,0),i(43,29,25,4))
    h.branch(5,5,0,'dispatch')
    h.emit(i(13,0,24,0x1a));h.branch(5,4,24,'fallback')
    h.emit(i(35,16,24,0),i(36,24,25,0),i(9,25,25,-48),i(11,25,25,10))
    h.branch(4,25,0,'fallback')
    for label,target in(('consume',0xf0e18),('dispatch',0xeff34),('fallback',0xf0f3c)):
        h.label(label);h.emit(i(35,29,24,0),i(35,29,25,4),i(9,29,29,16),j(target),0)
    return h.finish()

def cases():
    model=instruction_model();code=handler();results=[]
    for control,arg,target in[(0x1a,bytes([x]),0xf0e18)for x in range(48,58)]+[(0x1a,b'\0',0xf0f3c),(0x1a,b'X',0xf0f3c),(0x1a,b'\x80',0xf0f3c),(0x1a,b'\xf0',0xf0f3c),(0x1b,b'5',0xf0f3c),(0x1f,b'5',0xf0f3c),(0x19,b'5',0xeff34),(5,b'100',0xeff34),(0x17,b'2',0xeff34)]:
        regs=[0]+[0x43210000+n for n in range(1,32)];regs[4]=control;regs[5]=int(control<0x1a);regs[16]=0x200000;regs[18]=1;regs[29]=0x230000
        before=regs[:];memory={0x200000+n:b for n,b in enumerate(struct.pack('<I',0x210000))}
        memory.update({0x210000+n:b for n,b in enumerate(arg)})
        pc,out,reads=model['execute'](code,regs,memory)
        if pc!=target or out!=before:raise ValueError('Scoped dispatch ABI/target differs')
        source_reads=[a for a in reads if 0x210000<=a<0x220000]
        if source_reads not in([], [0x210000])or(control!=0x1a and source_reads):raise ValueError('Unexpected argument probe')
        results.append(dict(control=control,argument_hex=arg.hex(),target_rva=target,
            decimal_argument_consumed=target==0xf0e18,all_registers_preserved=True,argument_probe_bytes=len(source_reads)))
    return results

def overlay_records():
    from rebuild_dialogue import encode_target
    from dialogue_tokens import tokenize_bytes
    from battle_overlay_layout import prepare,widths_input
    widths,_=widths_input();records=[];samples=[]
    for path in (Path('work/translation/en/batch_0203.json'),Path('work/translation/en/batch_0204.json')):
        for row in json.loads(path.read_bytes())['rows']:
            if not row['target'].startswith('{1A}'):continue
            raw,_=encode_target(row['target'],row['source'],vwf_latin=True)
            raw,ledger=prepare(row['file'],row['id'],row['target'],raw,widths)
            counts=[]
            for line in raw[:-2].split(b'\x11'):
                count=sum(t.kind=='latin' and not t.ruby for t in tokenize_bytes(line,private_latin=True))
                counts.append(count);samples.append((line+b'\x12',count,max(45,count+1)))
            records.append(dict(id=row['id'],target_sha256=sha(row['target'].encode('utf8')),
                physical_sha256=sha(raw),occurrences=row['occurrences'],physical_visible_counts=counts,
                physical_layout_ledger=ledger,all_logical_controls_preserved=True))
    if len(records)!=7 or sum(len(r['occurrences'])for r in records)!=14:raise ValueError('Reviewed7/14 styled overlay coverage differs')
    return records,samples

def cap_cases(cap,helper,extra=()):
    template,offset,_,_=cap_layout();code=bytearray(template)
    struct.pack_into('<I',code,offset,j(helper));small=cap_handler(cap)
    samples=[(bytes([0x1a,x])+b'A'*46+b'\x12',46,47)for x in range(48,58)]
    samples += [(b'\x1a5???\x12',3,45),(b'\x1a5'+b'A'*45+b'\x12',45,46),
        (b'\x1a6'+b'A'*46+b'\x12',45,45),(b'\x1aX'+b'A'*46+b'\x12',46,45),
        (b'\x1a\0',0,45),(b'\x1a5\x12',0,45),
        (b'\x1a5'+b'A'*46+b'\x0f2Reading\x0f\x12',46,47),
        (b'\x1a5'+b'A'*46+b'\x010\x12',46,45),
        (b'\x1a5'+b'\xf0\x40'*46+b'\x12',46,47),
        (b'A'*1022+b'\x1a5\x12',1022,1023),
        (b'A'*1023+b'\x1a5\x12',1023,45)]
    samples.extend(extra);results=[]
    for raw,count,expected in samples:
        model=instruction_model();regs=[0]+[0x43210000+n for n in range(1,32)]
        regs[6]=0x210000;regs[7]=count;regs[17]=0x220000;regs[29]=0x230000;before=regs[:]
        memory={0x210000+n:b for n,b in enumerate(raw+b'\0')};pc=cap;reads=[]
        for _ in range(20):
            model['B']=helper if pc==helper else cap
            pc,regs,newreads=model['execute'](small if pc==helper else bytes(code),regs,memory,pc)
            reads.extend(newreads)
            if pc==0xee98c:break
        else:raise ValueError('Cap continuation model did not finish')
        if regs[6]!=expected or any(regs[n]!=before[n]for n in range(8,16))or regs[29]!=before[29]:raise ValueError('Cap result/ABI differs')
        stream=[x for x in reads if 0x210000<=x<0x220000]
        if max(stream,default=0x210000)>0x210000+min(len(raw),1024):raise ValueError('Cap read exceeds bounded terminal probe')
        results.append(dict(source_sha256=sha(raw),source_bytes=len(raw),body_count=count,cap=expected,
            terminal_room=expected>45,passed=True))
    return results

def build():
    incoming=SOURCE.read_bytes();metadata=json.loads(SOURCE.with_name('executable.en.json').read_bytes());elf=Elf(incoming)
    if sha(incoming)!=SOURCE_SHA or metadata['output_elf_sha256']!=SOURCE_SHA:raise ValueError('Frozen21 executable differs')
    original=Elf(Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf').read_bytes())
    for a,b in((0xeff14,0xeff4c),(0xf0e18,0xf0e30),(0xf0f3c,0xf0f6c),(0xeed58,0xeed88),(0xefeac,0xefee0),(0xed04c,0xed088)):
        if incoming[elf.file_offset(a):elf.file_offset(b)]!=original.data[original.file_offset(a):original.file_offset(b)]:raise ValueError('Native dispatch/continuation differs')
    if any(off==SITE and f>>8&255==0 for off,f in elf.relocs):raise ValueError('Native conditional unexpectedly relocated')
    if elf.word(SITE)!=i(4,5,0,(0xf0f3c-SITE-4)//4)or elf.word(SITE+4)!=i(13,0,18,1):raise ValueError('Original branch/delay differs')
    cap=metadata['font_hooks']['reveal'];capcode,capoffset,_,_=cap_layout();capsite=cap+capoffset
    if incoming[elf.file_offset(cap):elf.file_offset(cap)+len(capcode)]!=capcode:raise ValueError('Active cap differs from reviewed generator')
    if any(off==capsite and f>>8&255==0 for off,f in elf.relocs):raise ValueError('Cap conditional already relocated')
    caphelper=bytearray(cap_handler(cap));caprecords=relocate_code(caphelper,0,len(caphelper))
    code=bytearray(handler());records=relocate_code(code,0,len(code))
    reservation=plan(metadata,[dict(name='draw_decimal_1A_dispatch',data=bytes(code),alignment=4),
        dict(name='reveal_decimal_1A_dispatch',data=bytes(caphelper),alignment=4)])
    slot=reservation['patches'][0];helper=slot['rva'];result=bytearray(incoming)
    result[slot['file_offset']:slot['file_offset']+len(code)]=code
    struct.pack_into('<I',result,elf.file_offset(SITE),j(helper))
    # relocate_code defaults to appended LOAD2. This helper resides in LOAD0.
    additions=[(SITE,4)]+[(helper+off,flags&255)for off,flags in struct.iter_unpack('<II',b''.join(records))]
    capslot=reservation['patches'][1];result[capslot['file_offset']:capslot['file_offset']+len(caphelper)]=caphelper
    struct.pack_into('<I',result,elf.file_offset(capsite),j(capslot['rva']))
    additions += [(capsite,4)]+[(capslot['rva']+off,flags&255)for off,flags in struct.iter_unpack('<II',b''.join(caprecords))]
    relph=next(p for p in elf.ph if p[0]==0x700000a0);newrel=(len(result)+15)&-16;result.extend(bytes(newrel-len(result)))
    relbytes=incoming[relph[1]:relph[1]+relph[4]]+b''.join(struct.pack('<II',*r)for r in additions);result.extend(relbytes)
    ss=sections(incoming)
    for s in ss:
        if s[1]==0x700000a0:s[4]=newrel+s[4]-relph[1]
    ss.append([0,0x700000a0,0,0,newrel+relph[4],len(additions)*8,0,1,4,8])
    shoff=(len(result)+3)&-4;result.extend(bytes(shoff-len(result)))
    for s in ss:result.extend(struct.pack('<10I',*s))
    struct.pack_into('<I',result,32,shoff);struct.pack_into('<H',result,48,len(ss))
    phoff=struct.unpack_from('<I',result,28)[0];index=elf.ph.index(relph);p=list(relph);p[1]=newrel;p[4]=len(relbytes);struct.pack_into('<8I',result,phoff+32*index,*p)
    output=bytes(result);out=Elf(output);coverage(output)
    _,_,arg1,native=cap_layout()
    expected_targets=dict(zip([a for a,_ in additions],
        [helper,0xf0e18,0xeff34,0xf0f3c,capslot['rva'],cap+arg1,cap+native]))
    if out.loads!=elf.loads or out.relocs!=elf.relocs+additions:raise ValueError('Inherited LOAD/relocation contract differs')
    if pair_shapes(output)[:-1]!=pair_shapes(incoming):raise ValueError('Inherited HI/LO section semantics differ')
    models=[]
    for base in(0x08804000,0x08900000,0x08fff000):
        memory,visited,skipped,pairs=section_load(output,base)
        for site,target in expected_targets.items():
            word=struct.unpack_from('<I',memory[0],site)[0]
            if ((base+site+4)&0xf0000000)|((word&0x3ffffff)<<2)!=base+target:raise ValueError('Loaded scoped transfer differs')
        models.append(dict(base=base,records=len(visited),skipped_sections=skipped,all_new_R26_passed=True))
    mask=bytearray(incoming)
    for off,size in((slot['file_offset'],len(code)),(capslot['file_offset'],len(caphelper)),(elf.file_offset(capsite),4),
                   (elf.file_offset(SITE),4),(32,4),(48,2),(phoff+32*index,32)):
        mask[off:off+size]=output[off:off+size]
    if output[:len(incoming)]!=mask:raise ValueError('Unselected frozen bytes differ')
    overlays,overlay_samples=overlay_records()
    proof=dict(schema_version=1,status='dry_scoped_decimal_1A_draw_reveal_proposal',input_sha256=SOURCE_SHA,
        output_elf_sha256=sha(output),elf_bytes=len(output),hook_rva=SITE,original_branch_word=elf.word(SITE),
        original_delay_preserved=True,helper_rva=helper,helper_bytes=len(code),helper_sha256=sha(code),
        allocation={k:v for k,v in slot.items()if k!='data'},remaining_tail_bytes=reservation['remaining_bytes'],
        cap_allocation={k:v for k,v in capslot.items()if k!='data'},
        loaded_growth_bytes=0,new_relocations=additions,three_base_actual_SHT_models=models,
        emitted_instruction_cases=cases(),native_consumption_cases=native_consumption_cases(original),
        reveal_cap_cases=cap_cases(cap,capslot['rva'],overlay_samples),overlay_records=overlays,
        unique_overlay_records=7,owned_overlay_occurrences=14,
        cap_hook_rva=capsite,cap_helper_rva=capslot['rva'],cap_helper_bytes=len(caphelper),
        cap_helper_sha256=sha(caphelper),native_argument_width=1,native_argument_callee=0xe9c04,
        native_draw_argument_handler=0xf0e18,native_reveal_already_consumes_1A=True,
        native_ED04C_selector_removed_before_body_count=True,
        accepted_style_values=list(range(10)),unknown_control_nondecimal_NUL_fallback_exact=True,
        all_unselected_native_tail_bytes_exact=True,all_existing_relrecords_exact=True,original_trailer_exact=True,
        runtime_verified=False,source_code_sha256=sha(Path(__file__).read_bytes()),
        limitations=['Decimal styles only; other argument bytes retain current native fallback.','Runtime row-pointer/reveal and exact overlay captures require root QA.'])
    updated=copy.deepcopy(metadata);updated.update(output_elf_sha256=sha(output),output_sha256=sha(output),
        elf_bytes=len(output),input_sha256=SOURCE_SHA,input_version='0.1.21',status='dry_1A_draw_reveal_candidate',runtime_verified=False)
    updated['trailer_recovery']['free_tail_regions']=reservation['free_tail_regions']
    updated['trailer_recovery']['remaining_tail_bytes']=reservation['remaining_bytes']
    for chunk in updated['native_tail_compaction']['chunks']:
        start=chunk['file_offset'];chunk['output_sha256']=sha(output[start:start+chunk['bytes']])
    updated['total_relocations']=len(out.relocs);updated['added_relocations']=len(out.relocs)-71807
    updated['additional_scopes']['tail_reservations'].extend([{k:v for k,v in s.items()if k!='data'}for s in reservation['patches']])
    updated['draw_reveal_1A_proposal']=proof
    proof['updated_core_chunk_hashes']=[dict(name=c['name'],sha256=c['output_sha256'])for c in updated['native_tail_compaction']['chunks']]
    proof['historical_reveal_proof_scope']='Inherited cap bytes are unchanged except one guarded unsupported-control jump; current1A dispatch proof supersedes earlier native-fallback claim for1A.'
    proof['code_input_sha256']={str(p):sha(p.read_bytes())for p in [Path('tools')/(n+'.py')for n in
        ('dialogue_draw_1a','dialogue_wrap','dialogue_vwf_hooks','live_vwf','png_tail_allocate','build_menu_patch',
         'prepare_relocation_019','font_vram_hooks','executable_text_patch','private_latin','dialogue_tokens',
         'rebuild_dialogue','battle_overlay_layout','build_local','save_logo_overlay')]}
    proof['frozen_input_sha256']={str(p):sha(p.read_bytes())for p in (SOURCE,SOURCE.with_name('executable.en.json'),
        Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf'),Path('work/source/ruby_instruction_check.py'),
        Path('work/translation/en/batch_0203.json'),Path('work/translation/en/batch_0204.json'),
        Path('work/output/0.1.19-dialogue-assets/EBOOT.BIN'))}
    from build_local import authoritative_font_metadata
    from save_logo_overlay import validate_native_png_metadata
    proof['authoritative_font_metadata_passed']=True
    proof['authoritative_font_metadata']=authoritative_font_metadata(output,updated)
    proof['native_png_full_metadata_checks']=validate_native_png_metadata(output,updated)
    for s in reservation['patches']:
        if output[s['file_offset']:s['file_offset']+s['bytes']]!=s['data']:raise ValueError('New helper readback differs')
    proof['new_helper_physical_readbacks_passed']=True
    return output,proof,updated

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path)
    p.add_argument('--write',action='store_true');p.add_argument('--output',type=Path);p.add_argument('--approved-plan-sha256');a=p.parse_args()
    data,proof,report=build();canonical=sha(json.dumps(report,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
    print(json.dumps(proof,indent=2));print('DRY PLAN SHA256',canonical)
    if a.report:
        if a.report.exists():raise ValueError('Refuse evidence overwrite')
        a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    if a.write:
        if a.approved_plan_sha256!=canonical:raise ValueError('Exact reviewed dry plan SHA required')
        destination=a.output.resolve()if a.output else None
        if destination is None or destination.exists()or not destination.is_relative_to(Path('work/output').resolve()):raise ValueError('Fresh preparation folder inside work/output required')
        fresh,_,current=build()
        if sha(json.dumps(current,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())!=canonical or fresh!=data:raise ValueError('Fresh generation inputs changed after preview')
        destination.mkdir(parents=True);path=destination/'EBOOT.BIN';path.write_bytes(fresh)
        readback=path.read_bytes()
        from build_local import authoritative_font_metadata
        from save_logo_overlay import validate_native_png_metadata
        if sha(readback)!=report['output_elf_sha256'] or authoritative_font_metadata(readback,report)!=proof['authoritative_font_metadata']:raise ValueError('Executable/font readback differs')
        if validate_native_png_metadata(readback,report)!=proof['native_png_full_metadata_checks']:raise ValueError('PNG metadata readback differs')
        report.update(status='written_1A_draw_reveal_candidate_runtime_unverified',approved_dry_plan_sha256=canonical,
            output=str(path),written_readback_verified=True)
        (destination/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        print('Verified fresh preparation:',path)
    else:print('DRY RUN: no executable/ISO written.')

