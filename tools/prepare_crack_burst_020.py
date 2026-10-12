"""Pure frozen19 Crack Burst/isolated name decoder candidate; no ELF writer."""
import argparse,copy,hashlib,json,struct,inspect
from pathlib import Path
from executable_text_patch import Elf,address_pair
from remaining_label_audit import build as audit,CURRENT,CURRENT_SHA,ORIGINAL
from dialogue_vwf_hooks import Block,route
from live_vwf import i,jal
from png_tail_allocate import plan
from prepare_relocation_019 import sections,coverage,section_load,pair_shapes
from font_vram_hooks import instruction_model

def sha(data):return hashlib.sha256(data).hexdigest()

def wrapper():
    h=Block();h.emit(i(9,29,29,-16),i(43,29,31,0),i(43,29,24,4),i(43,29,25,8),jal(0xe9c64),0)
    h.emit(i(37,6,24,0),i(11,24,25,32));h.branch(5,25,0,'done')
    h.emit(i(11,24,25,127));h.branch(5,25,0,'visible')
    h.emit(i(11,24,25,131));h.branch(4,25,0,'done')
    h.emit(i(13,0,25,127));h.branch(4,24,25,'done')
    h.emit(i(35,5,25,0),i(9,25,25,-2));h.branch(5,25,0,'done')
    h.label('visible');h.emit(i(13,0,2,1));h.label('done')
    h.emit(i(35,29,31,0),i(35,29,24,4),i(35,29,25,8),0x03e00008,i(9,29,29,16))
    return h.finish()

def instruction_cases(current,metadata):
    # Extend the existing emitted-instruction interpreter with native SLTI.
    # No native bytes are substituted or rewritten for this instruction test.
    import font_vram_hooks
    definition=inspect.getsource(instruction_model)
    definition=definition.replace('    scope = dict(struct=struct,B=0x1750000)',
        "    source = source.replace('elif op==13:', 'elif op==10:regs[t]=int((regs[s] if regs[s]<0x80000000 else regs[s]-0x100000000)<sv)\\n        elif op==13:')\n"
        "    source = source.replace('elif op in (4,5):', 'elif op in (4,5,20,21):').replace('if (regs[s]==regs[t])==(op==4):nextjump=pc+4+sv*4', 'if (regs[s]==regs[t])==(op in (4,20)):nextjump=pc+4+sv*4\\n            elif op in (20,21):pc+=4')\n"
        "    scope = dict(struct=struct,B=0x1750000)")
    environment=font_vram_hooks.__dict__.copy();exec(definition,environment)
    model=environment['instruction_model']();execute=model['execute'];base=model['B'];code=wrapper()
    native=ORIGINAL.read_bytes()[0xe9c64+192:0xe9cd0+192]
    # Original leaf plus the actual frozen global return hook, whose private
    # mapping runs but whose visible gate does not match this scoped wrapper.
    decoder_rva=metadata['font_hooks']['decoder']
    decoder=current.data[current.file_offset(decoder_rva):current.file_offset(decoder_rva)+288]
    results=[]
    samples=[b'\0',b'\x01',b'\x11',b'\x1f',b' ',b'A',b'~',b'\x7f',b'\x80',b'\xa1',b'\xdf',b'\x82\xa0',b'\xf0\x40',b'\xf0\x41',b'\xf0\x42']
    for raw in samples:
        regs=[0]+[0x54320000+n for n in range(1,32)];regs[4:7]=[0x200000,0x210000,0x220000];regs[29]=0x230000;regs[31]=0xdeadbeec
        mem={0x200000+n:x for n,x in enumerate(raw+b'\0')};before=regs[:]
        execute.__globals__['B']=base
        pc,regs,_=execute(code,regs,mem)
        if pc!=0xe9c64:raise ValueError('Wrapper native call mismatch')
        resume=regs[31];native_in=regs[:]
        execute.__globals__['B']=0xe9c64
        pc,regs,_=execute(native,regs,mem)
        if pc!=resume:raise ValueError('Native leaf return mismatch')
        execute.__globals__['B']=decoder_rva
        pc,regs,_=execute(decoder,regs,mem)
        if pc!=resume:raise ValueError('Frozen global decoder return mismatch')
        expected=regs[:];glyph=int.from_bytes(bytes(mem[0x220000+n]for n in range(2)),'little')
        # Independent pinned input cases, not a copy of wrapper predicates.
        if raw in (b' ',b'A',b'~',b'\xf0\x40',b'\xf0\x41'):expected[2]=1
        if raw in (b'\0',b'\x01',b'\x11',b'\x1f',b'\x7f',b'\x80',b'\xa1',b'\xdf'):expected[2]=0
        if raw in (b'\x82\xa0',b'\xf0\x42'):expected[2]=1
        expected[24:26]=before[24:26];expected[29]=before[29];expected[31]=before[31]
        execute.__globals__['B']=base
        pc,out,_=execute(code,regs,mem,resume)
        if pc!=before[31]or out!=expected:raise ValueError('Wrapper ABI/model mismatch')
        results.append(dict(input_hex=raw.hex(),glyph=glyph,classification=out[2],consumed_bytes=int.from_bytes(bytes(mem[0x210000+n]for n in range(4)),'little'),all_registers_except_native_outputs_and_classification_preserved=True))
    return results

def build():
    checks=audit();incoming=CURRENT.read_bytes();elf=Elf(incoming)
    report_raw=CURRENT.with_name('executable.en.json').read_bytes()
    if sha(report_raw)!='c3b5b1998b7d8734422f6e50a75fd09d8752254386053c0ee3971f2a22a98f17':raise ValueError('Frozen19 report differs')
    before=json.loads(report_raw)
    code=wrapper();reservations=plan(before,[dict(name='Crack_Burst_Latin',data=b'Crack Burst\0',alignment=4),dict(name='scoped_EBE2C_decoder',data=code,alignment=4)])
    text_rva,helper_rva=[p['rva']for p in reservations['patches']]
    route_rva=(elf.word(0xee330)&0x3ffffff)<<2
    expected_route=route(0xe9918,131)
    actual_route=incoming[elf.file_offset(route_rva):elf.file_offset(route_rva)+len(expected_route)]
    if actual_route!=expected_route:raise ValueError('Inherited Latin/JP route generator differs')
    result=bytearray(incoming);changes=[]
    for p in reservations['patches']:
        offset=elf.file_offset(p['rva'],p['bytes'])
        if offset!=p['file_offset']:raise ValueError('PNG-tail file mapping differs')
        if any(p['rva']<a['rva']+a['bytes']and a['rva']<p['rva']+p['bytes'] for a in before['additional_scopes']['tail_reservations']):raise ValueError('Tail overlaps active additional allocation')
        changes.append(dict(kind='proved_free_tail',rva=p['rva'],bytes=p['bytes'],before_sha256=sha(incoming[offset:offset+p['bytes']]),after_sha256=sha(p['data'])))
        result[offset:offset+p['bytes']]=p['data']
    for entry in checks['crack_burst']['entries']:
        hi,lo=entry['pointer_sites'];hw,lw=elf.word(hi),elf.word(lo)
        if address_pair(hw,lw)!=entry['source_rva']:raise ValueError('Source semantic pair changed')
        for site,word in ((hi,(hw&0xffff0000)|((text_rva+0x8000)>>16)),(lo,(lw&0xffff0000)|(text_rva&65535))):
            struct.pack_into('<I',result,elf.file_offset(site),word);changes.append(dict(kind='existing_HI_LO',rva=site,before_word=elf.word(site),after_word=word))
    for site,target in ((0xebe2c,helper_rva),(0xebeac,route_rva)):
        if sum(off==site and f==4 for off,f in elf.relocs)!=1:raise ValueError('Existing native JAL R26 missing')
        struct.pack_into('<I',result,elf.file_offset(site),jal(target));changes.append(dict(kind='existing_JAL_R26',rva=site,before_word=elf.word(site),after_word=jal(target)))
    if elf.word(0xebe30)!=0x02402025 or elf.word(0xebeb0)!=0x44056000:raise ValueError('Caller delay slots changed')
    # Append new contiguous REL copy and SHT, retaining every inherited record
    # and section-local pairing. Unloaded font trailer remains at exact offset.
    oldrel=next(p for p in elf.ph if p[0]==0x700000a0);new_record=(helper_rva+16,4)
    newoff=(len(result)+15)&-16;result.extend(bytes(newoff-len(result)))
    relbytes=incoming[oldrel[1]:oldrel[1]+oldrel[4]]+struct.pack('<II',*new_record);result.extend(relbytes)
    ss=sections(incoming)
    for s in ss:
        if s[1]==0x700000a0:s[4]=newoff+s[4]-oldrel[1]
    ss.append([0,0x700000a0,0,0,newoff+oldrel[4],8,0,1,4,8])
    shoff=(len(result)+3)&-4;result.extend(bytes(shoff-len(result)))
    for s in ss:result.extend(struct.pack('<10I',*s))
    struct.pack_into('<I',result,32,shoff);struct.pack_into('<H',result,48,len(ss))
    phoff=struct.unpack_from('<I',result,28)[0];relindex=elf.ph.index(oldrel);newph=list(oldrel);newph[1]=newoff;newph[4]=len(relbytes)
    struct.pack_into('<8I',result,phoff+32*relindex,*newph);output=bytes(result);out=Elf(output)
    if out.loads!=elf.loads or out.relocs!=elf.relocs+[new_record]:raise ValueError('LOAD or inherited relocation changed')
    coverage(output)
    if pair_shapes(output)[:-1]!=pair_shapes(incoming):raise ValueError('Inherited section HI/LO pairing changed')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        mem,records,skipped,pairs=section_load(output,base)
        for entry in checks['crack_burst']['entries']:
            hi,lo=entry['pointer_sites'];hw,lw=[struct.unpack_from('<I',mem[0],s)[0]for s in (hi,lo)]
            if address_pair(hw,lw)!=base+text_rva:raise ValueError('Actual SHT loaded text pointer differs')
        for site,target in ((0xebe2c,helper_rva),(0xebeac,route_rva),(helper_rva+16,0xe9c64)):
            w=struct.unpack_from('<I',mem[0],site)[0]
            if ((base+site+4)&0xf0000000)|((w&0x3ffffff)<<2)!=base+target:raise ValueError('Actual SHT loaded JAL differs')
        models.append(dict(base=base,total_records=len(records),HI_LO_pairs=pairs,skipped_sections=skipped,selected_pointers_and_calls_passed=True))
    # Only the reviewed native words/free gaps and ELF metadata may differ.
    masked=bytearray(incoming)
    for c in changes:
        size=c.get('bytes',4);off=elf.file_offset(c['rva'],size);masked[off:off+size]=output[off:off+size]
    for off,size in ((32,4),(48,2),(phoff+32*relindex,32)):masked[off:off+size]=output[off:off+size]
    if output[:len(incoming)]!=masked:raise ValueError('Unselected incoming file bytes changed')
    native_disassembly=Path('work/source/crack_burst_020_native_disassembly.en.txt')
    native_spans=[]
    original=Elf(ORIGINAL.read_bytes())
    for start,end in ((0xebc08,0xebec4),(0xde100,0xde240)):
        old=original.data[original.file_offset(start):original.file_offset(end)]
        now=incoming[elf.file_offset(start):elf.file_offset(end)]
        if old!=now:raise ValueError('Original caller context changed in frozen19')
        native_spans.append(dict(start_rva=start,end_rva=end,sha256=sha(old),frozen19_exact_original=True))
    proof=dict(version='0.1.20',status='pure_Crack_Burst_scope_no_writer',input_elf_sha256=CURRENT_SHA,
        input_report_sha256=sha(report_raw),output_elf_sha256=sha(output),elf_bytes=len(output),loaded_growth_bytes=0,
        native_disassembly_file=str(native_disassembly),native_disassembly_sha256=sha(native_disassembly.read_bytes()),native_contexts=native_spans,
        allocation=[{k:v for k,v in p.items()if k!='data'}for p in reservations['patches']],remaining_tail_bytes=reservations['remaining_bytes'],
        changes=changes,wrapper_bytes=len(code),wrapper_sha256=sha(code),route_rva=route_rva,route_generator_byte_exact=True,
        original_delays_preserved=['EBE30 move A0,S2','EBEB0 mfc1 A1,F12'],
        register_contract='Original E9C64 call runs once; only V0 gains printable/private classification. RA/SP/T8/T9 restored; all other outputs match native decoder/global private mapping. Caller delay slots and13px slots unchanged.',
        new_relocations=[new_record],new_section_sh_info=1,section_coverage=coverage(output),inherited_section_pair_shapes_exact=True,
        three_base_section_loader=models,native_instruction_cases=instruction_cases(elf,before),
        selected_cache_count_indices_untouched=True,unselected_file_prefix_exact=True,all_LOAD_headers_exact=True,
        original_unloaded_trailer_bytes_offset_preserved=True,install_ready=False,runtime_verified=False,
        code_input_sha256={name:sha(Path('tools',name).read_bytes())for name in ('prepare_crack_burst_020.py','remaining_label_audit.py','dialogue_vwf_hooks.py','png_tail_allocate.py','prepare_relocation_019.py','font_vram_hooks.py')},
        limitations=['Review candidate before any writer. Actual animation label clipping/centering and all instances remain unverified.','67 sys_tbl labels remain blocked on live-owner/selector proof.'])
    return output,proof

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path);a=p.parse_args()
    data,report=build();raw=json.dumps(report,indent=2)+'\n';print(raw)
    if a.report:
        if a.report.exists():raise ValueError('Refuse report overwrite')
        a.report.write_text(raw,encoding='utf8')
    print('DRY ONLY: no ELF/ISO writer.')

if __name__=='__main__':main()
