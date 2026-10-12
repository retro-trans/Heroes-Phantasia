"""Fresh save UI + terminal-safe reveal cap; dry by default, guarded writer."""
import argparse, ast, hashlib, json, struct
from pathlib import Path
from build_menu_patch import START, align, relocate_code
from live_vwf import words, j
from dialogue_wrap import literal_reveal_cap
from compact_vwf_patch import loaded

SOURCE=Path('work/source/save_ui_015_rgb_EBOOT.BIN')
REPORT=Path('work/source/save_ui_015_rgb_candidate.en.json')
SHA='de7492a481b3aadff1e5faf3876dd969bc34a7616932a4022411de92f62da1e5'
OUTPUT=Path('work/output/0.1.15-dialogue-assets')
APPROVED_SHA='378649b06adc9427f6208bed57be92a6f791eddc04de40019bf1f2087e6630b2'


def digest(data):return hashlib.sha256(data).hexdigest()


def cases(code):
    # Reuse the persisted instruction interpreter's definitions only: importing
    # its top-level historical tests would depend on today's translation ledger.
    source=Path('work/source/ruby_instruction_check.py').read_text()
    tree=ast.parse(source)
    defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('execute','put')]
    scope=dict(struct=struct,B=0x1750000)
    exec(compile(ast.Module(body=defs,type_ignores=[]),'<persisted instruction interpreter>','exec'),scope)
    execute,put=scope['execute'],scope['put']
    samples=[('short_question',b'???\x12',3,45),('exact45',b'A'*45+b'\x12',45,46),
             ('long62',b'A'*62+b'\x11',62,63),('long80',b'A'*80+b'\x0e',80,81),
             ('short_ruby',b'Hideo\x0f2Hideo\x0f\x12',5,45),
             ('long_ruby',b'A'*60+b'\x0f2English\x0f\x12',60,61),
             ('neutral',b'A'*46+b'\x172100\x05003\x1602\x12',49,50),
             ('runtime01',b'A\x010B\x12',3,45),('runtime02',b'A\x020000B\x12',3,45),
             ('native',bytes.fromhex('82a082a2')+b'\x12',2,45),
             ('empty',b'\x12',0,45),('controls_only',b'\x05003\x172\x12',0,45),
             ('count_mismatch',b'A'*60+b'\x12',59,45),
             ('bound1024',b'A'*1024+b'\x12',1024,1025),
             ('truncated_ruby',b'A\x0f2English',1,45),('DEL',b'A\x7f\x12',2,45)]
    results=[]
    for name,raw,count,expected in samples:
        regs=[0]*32;regs[6]=0x200000;regs[7]=count;regs[17]=0x210000;regs[29]=0x220000;regs[30]=0xffffffff
        for reg in range(8,16):regs[reg]=0x12340000+reg
        before=regs[:];mem={};put(mem,regs[6],raw+b'\0')
        pc,out,reads=execute(code,regs,mem)
        assert pc==0xee98c and out[6]==expected
        assert out[29]==before[29] and all(out[r]==before[r]for r in range(8,16))
        assert int.from_bytes(bytes(mem[0x210008+n]for n in range(4)),'little')==0xffffffff
        assert max(x for x in reads if 0x200000<=x<0x210000)<=0x200000+min(len(raw),1024)
        results.append(dict(name=name,count=count,cap=expected,passed=True))
    # Execute the original terminal handlers, rather than assigning expected
    # state in a parallel implementation. They return99 to EE710's break gate.
    native=Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf').read_bytes()
    exits=[]
    for control,entry,state in [(0x12,0xefc58,5),(0x11,0xefc10,6),(0x0e,0xefc40,8),(0,0xeed90,8)]:
        regs=[0]*32;regs[16]=0x210000;mem={};put(mem,0x210000,bytes(160))
        scope['B']=entry
        pc,out,reads=execute(native[entry+192:entry+192+80],regs,mem)
        actual=int.from_bytes(bytes(mem[0x210048+n]for n in range(4)),'little')
        assert pc==0xefec0 and out[17]==99 and actual==state
        exits.append(dict(control=hex(control),handler=hex(entry),object_state=actual,return_marker=out[17],passed=True))
    # In EE644/EE648, index < reveal admits the terminating control after N
    # visible glyphs iff cap>N. Dispatcher return99 immediately breaks EE710.
    assert struct.unpack_from('<I',native,0xee644+192)[0]==0x0212282a
    terminal_cases=[]
    for name,raw,count,cap in samples[:7]:
        regs=[0]*32;regs[4]=99;regs[16]=count+1;regs[17]=0x210000;regs[18]=cap;regs[19]=99
        mem={};put(mem,0x210000,bytes(160));scope['B']=0xee710
        pc,out,reads=execute(native[0xee710+192:0xee72c+192],regs,mem)
        assert pc==0xee72c and out[16]==count
        assert set(reads)==set(range(0x210058,0x21005c))
        terminal_cases.append(dict(name=name,terminal_admitted=cap>count,
                                   native_break_pc=hex(pc),nonvisible_terminal_excluded_from_glyph_index=True,
                                   reads_past_terminal=False))
    assert all(x['terminal_admitted']for x in terminal_cases)
    return dict(instruction_cases=results,native_terminal_handlers=exits,terminal_room_cases=terminal_cases,
                interpreter_sha256=digest(source.encode()),unsupported_retains_native45=True)


def build():
    original=SOURCE.read_bytes();report=json.loads(REPORT.read_text())
    if digest(original)!=SHA or report['output_elf_sha256']!=SHA:raise ValueError('Reviewed save input changed')
    phoff,shoff=struct.unpack_from('<II',original,28);phnum=struct.unpack_from('<H',original,44)[0];shnum=struct.unpack_from('<H',original,48)[0]
    ph=[list(struct.unpack_from('<8I',original,phoff+32*n))for n in range(phnum)]
    sections=[list(struct.unpack_from('<10I',original,shoff+40*n))for n in range(shnum)]
    if phnum!=4 or ph[2][2]!=START:raise ValueError('Unexpected segment layout')
    prefix=original[ph[2][1]:ph[2][1]+ph[2][4]];rel=original[ph[3][1]:ph[3][1]+ph[3][4]]
    code=literal_reveal_cap(True,terminal_room=True);proof=cases(code)
    payload=bytearray(prefix);payload.extend(bytes((-len(payload))%16));off=len(payload);payload.extend(code)
    additions=b''.join(relocate_code(payload,off,len(code)));addr=START+off
    oldjump=struct.unpack_from('<I',original,0xee984+192)[0]
    oldaddr=(oldjump&0x3ffffff)*4
    if oldjump>>26!=2 or original[0xee988+192:0xee98c+192]!=bytes(4) or (0xee984,4)not in set(struct.iter_unpack('<II',rel)):
        raise ValueError('Existing reveal hook signature/relocation changed')
    oldcode=literal_reveal_cap(True)
    if prefix[oldaddr-START:oldaddr-START+len(oldcode)]!=oldcode:raise ValueError('Expected reviewed paired cap block')
    patch=bytearray(original);patch[0xee984+192:0xee988+192]=words([j(addr)])
    newpayload=align(len(patch),64);patch.extend(bytes(newpayload-len(patch)));patch.extend(payload)
    newrel=align(len(patch),16);patch.extend(bytes(newrel-len(patch)));patch.extend(rel+additions)
    for s in sections:
        if s[1]==0x700000a0:s[4]=newrel+(s[4]-ph[3][1])
        elif s[3]==START and s[4]==ph[2][1]:s[4]=newpayload;s[5]=len(payload)
    payload_section=next(n for n,s in enumerate(sections)if s[3]==START and s[4]==newpayload)
    sections.append([0,0x700000a0,0,0,newrel+len(rel),len(additions),0,payload_section,4,8])
    newsh=align(len(patch),4);patch.extend(bytes(newsh-len(patch)))
    for s in sections:patch.extend(struct.pack('<10I',*s))
    ph[2][1]=newpayload;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=newrel;ph[3][4]=len(rel)+len(additions)
    for n,p in enumerate(ph):struct.pack_into('<8I',patch,phoff+32*n,*p)
    struct.pack_into('<I',patch,32,newsh);struct.pack_into('<H',patch,48,len(sections))
    checks=[]
    for base in (0x8804000,0x8900000,0x8fff000):
        before,records,_=loaded(original,base);after,allrecords,_=loaded(bytes(patch),base)
        for site,flags in records:
            seg=flags>>8&255
            if seg==0 and site==0xee984:continue
            assert before[seg][site:site+4]==after[seg][site:site+4]
        jump=struct.unpack_from('<I',after[0],0xee984)[0]
        assert (jump&0x3ffffff)*4==base+addr
        assert after[2][:len(prefix)]==before[2]
        checks.append(dict(base=hex(base),inherited_unchanged_words=len(records)-1,passed=True))
    assert payload[:len(prefix)]==prefix and patch[newrel:newrel+len(rel)]==rel
    allowed=set(range(28,36))|set(range(48,50))|set(range(phoff+64,phoff+128))|set(range(0xee984+192,0xee988+192))
    assert all(a==b or n in allowed for n,(a,b)in enumerate(zip(original,patch)))
    report.update(status='dry_terminal_reveal_candidate_runtime_unverified',runtime_verified=False,
                  input_sha256=SHA,output_sha256=digest(patch),output_elf_sha256=digest(patch),elf_bytes=len(patch),
                  payload_bytes=len(payload),payload_growth=len(payload)-len(prefix),module_growth_bytes=len(payload),
                  added_relocations=len(additions)//8,total_relocations=(len(rel)+len(additions))//8,
                  inherited_payload_sha256=digest(prefix),inherited_payload_preserved=True,
                  inherited_relocation_table_sha256=digest(rel),relocation_prefix_unchanged=True,
                  relocation_table_sha256=digest(rel+additions))
    report['hooks']['terminal_safe_reveal_cap']=hex(addr)
    report['reveal_terminal_patch']=dict(site='0xee984',old_hook=hex(oldaddr),new_hook=hex(addr),
                                        expected_hex=words([oldjump]).hex(),replacement_hex=words([j(addr)]).hex(),
                                        code_bytes=len(code),minimum_cap=45,validated_long_cap='visible glyph count + 1',
                                        ruby_supported=True,maximum_probe_bytes=1024,terminal_probe_bytes=1,
                                        native_fallback=45,proof=proof,loaded_relocations=checks,
                                        runtime_verified=False,total_growth_vs_014=len(payload)-216036)
    return bytes(patch),report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path);p.add_argument('--write',action='store_true');a=p.parse_args()
    data,report=build();print(json.dumps({k:report[k]for k in ('version','input_sha256','output_elf_sha256','elf_bytes','payload_bytes','added_relocations','reveal_terminal_patch')},indent=2))
    if a.report:
        if a.report.parent!=Path('work/source') or not a.report.name.startswith('save_ui_015_')or a.report.exists():raise ValueError('Expected fresh ignored proposal report')
        a.report.write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf8')
    if a.write:
        if digest(data)!=APPROVED_SHA:raise ValueError('Candidate differs from independently reviewed dry hash')
        if any((OUTPUT/n).exists()for n in ('EBOOT.BIN','setup_patch.en.json')):raise ValueError('Refusing to overwrite fresh candidate')
        OUTPUT.mkdir(parents=True,exist_ok=True);(OUTPUT/'EBOOT.BIN').write_bytes(data)
        report['status']='written_terminal_reveal_candidate_runtime_unverified'
        (OUTPUT/'setup_patch.en.json').write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n')
        assert digest((OUTPUT/'EBOOT.BIN').read_bytes())==report['output_elf_sha256']
    else:print('DRY RUN: no executable assets written.')


if __name__=='__main__':main()
