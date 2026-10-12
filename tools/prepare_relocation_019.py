"""Minimal guarded .19 SHT relocation repair; dry default, no ISO actions."""
import argparse,copy,json,pathlib,struct
from prepare_complete_018 import canonical
from compact_vwf_patch import loaded
from executable_text_patch import Elf
from build_menu_patch import align
from prepare_native_font_018 import sha

SOURCE=pathlib.Path('work/output/0.1.18-dialogue-assets/EBOOT.BIN')
SOURCE_SHA='2168b241dc63f17090d96bbd38120549fb02ba40c32cb86fb09674c70498e707'
ROOT=pathlib.Path('work/output/0.1.19-dialogue-assets')
REL=0x700000a0
ORIGINAL=pathlib.Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf')
ORIGINAL_SHA='03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1'

def sections(data):
    off=struct.unpack_from('<I',data,32)[0]
    return [list(struct.unpack_from('<10I',data,off+n*40))for n in range(struct.unpack_from('<H',data,48)[0])]

def section_load(data,base,strict=True):
    """Model PPSSPP v1.20.4 SHT gate and per-section raw-op snapshot.

    PSP flags select source/target LOAD segments independently of sh_info;
    the latter only gates whether the section is loaded at all.
    """
    elf=Elf(data);ss=sections(data)
    memory=[bytearray(data[p[1]:p[1]+p[4]])+bytes(p[5]-p[4])for p in elf.ph if p[0]==1]
    visited=[];skipped=[];pairs=0
    for index,s in enumerate(ss):
        if s[1]!=REL or not s[5]:continue
        if not 0<=s[7]<len(ss)or not ss[s[7]][2]&2:
            skipped.append(index)
            if strict:raise ValueError('Loader would skip non-loaded relocation section')
            continue
        if s[5]%8 or s[4]+s[5]>len(data):raise ValueError('Relocation section bounds differ')
        records=list(struct.iter_unpack('<II',data[s[4]:s[4]+s[5]]))
        ops=[]
        for off,f in records:
            source=f>>8&255
            if source>=len(memory)or off+4>len(memory[source]):raise ValueError('Relocation source outside LOAD')
            ops.append(struct.unpack_from('<I',memory[source],off)[0])
        for n,(off,f)in enumerate(records):
            typ=f&15;source=f>>8&255;target=f>>16&255;op=ops[n]
            if target>=len(memory):raise ValueError('Relocation target segment outside LOAD')
            delta=base+elf.ph[target][2]
            if typ==2:op=(op+delta)&0xffffffff
            elif typ==4:op=(op&0xfc000000)|(((op&0x3ffffff)+(delta>>2))&0x3ffffff)
            elif typ==5:
                mate=next((q for q in range(n+1,len(records))if records[q][1]&15 in(1,6)),None)
                if mate is None:raise ValueError('HI lacks per-section LO mate')
                if records[mate][1]>>8!=f>>8:raise ValueError('HI/LO source-target flags mismatch')
                signed=struct.unpack('<h',struct.pack('<H',ops[mate]&65535))[0]
                address=((op&65535)<<16)+signed+delta
                op=(op&0xffff0000)|((address+0x8000)>>16&65535);pairs+=1
            elif typ in(1,6):op=(op&0xffff0000)|((op+delta)&65535)
            elif typ not in(0,7):raise ValueError('Unmodeled native relocation type')
            struct.pack_into('<I',memory[source],off,op);visited.append((off,f))
    return memory,visited,skipped,pairs

def coverage(data):
    elf=Elf(data);ss=sections(data);p=next(x for x in elf.ph if x[0]==REL)
    intervals=[];records=[]
    for index,s in enumerate(ss):
        if s[1]!=REL or not s[5]:continue
        if not 0<=s[7]<len(ss)or not ss[s[7]][2]&2:raise ValueError('SHT binding is not loaded')
        if s[5]%8 or not p[1]<=s[4]or s[4]+s[5]>p[1]+p[4]:raise ValueError('SHT relocation range outside PH3')
        interval=(s[4]-p[1],s[4]-p[1]+s[5]);intervals.append((index,*interval,s[7]))
        records.extend(struct.iter_unpack('<II',data[s[4]:s[4]+s[5]]))
    cursor=0
    for _,start,end,_ in intervals:
        if start!=cursor:raise ValueError('SHT relocation gap, overlap or wrong order')
        cursor=end
    if cursor!=p[4]or records!=elf.relocs:raise ValueError('SHT/PH relocation coverage differs')
    return intervals

def pair_shapes(data,original_only=False):
    """Capture each section-local HI's first following acceptable LO/R16."""
    elf=Elf(data);rp=next(p for p in elf.ph if p[0]==REL);result=[]
    for index,s in enumerate(sections(data)):
        if s[1]!=REL or not s[5]:continue
        if original_only and s[4]-rp[1]>=71807*8:continue
        records=list(struct.iter_unpack('<II',data[s[4]:s[4]+s[5]]));shapes=[]
        for n,record in enumerate(records):
            if record[1]&15!=5:continue
            mate=next((q for q in range(n+1,len(records))if records[q][1]&15 in(1,6)),None)
            if mate is None:raise ValueError('HI crosses relocation section boundary')
            if record[1]>>8!=records[mate][1]>>8:raise ValueError('Section-local HI/LO flag convention differs')
            shapes.append([n,mate,*record,*records[mate]])
        result.append(dict(index=index,relative_offset=s[4]-rp[1],bytes=s[5],sh_info=s[7],records_sha256=sha(data[s[4]:s[4]+s[5]]),pairs=len(shapes),pair_signature_sha256=sha(json.dumps(shapes,separators=(',',':')).encode())))
    return result

def build():
    incoming=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('executable.en.json').read_text(encoding='utf-8'))
    if sha(incoming)!=SOURCE_SHA or before['output_elf_sha256']!=SOURCE_SHA:raise ValueError('Frozen18 executable/report mismatch')
    elf=Elf(incoming);ss=sections(incoming);rp=elf.ph[3]
    if len(ss)!=70 or len(elf.relocs)!=72144:raise ValueError('Exact reviewed18 tables differ')
    if ss[68][4:6]!=[rp[1]+71807*8,311*8]or ss[68][7]!=0 or ss[69][4:6]!=[rp[1]+72138*8,6*8]or ss[69][7]!=0:raise ValueError('Exact18 malformed section guards differ')
    if ss[1][2]!=6 or ss[55][2]!=7 or ss[55][3]!=elf.ph[2][2]or ss[55][5]!=elf.ph[2][4]:raise ValueError('Loaded section1/55 binding differs')
    old_intervals=[(s[4]-rp[1],s[4]-rp[1]+s[5])for s in ss[:68]if s[1]==REL and s[5]]
    if old_intervals[0][0]!=0 or old_intervals[-1][1]!=71807*8 or any(a[1]!=b[0]for a,b in zip(old_intervals,old_intervals[1:])):raise ValueError('Original71807 partition differs')
    ss[68][7]=1
    ss[69][4]=rp[1]+72118*8;ss[69][5]=20*8;ss[69][7]=55
    ss.append([0,REL,0,0,rp[1]+72138*8,6*8,0,1,4,8])
    output=bytearray(incoming);newsh=align(len(output),4);output.extend(bytes(newsh-len(output)))
    for s in ss:output.extend(struct.pack('<10I',*s))
    struct.pack_into('<I',output,32,newsh);struct.pack_into('<H',output,48,len(ss));result=bytes(output)
    masked=bytearray(incoming);masked[32:36]=result[32:36];masked[48:50]=result[48:50]
    if result[:len(incoming)]!=masked:raise ValueError('Repair changed unselected source file bytes')
    intervals=coverage(result);models=[]
    original=ORIGINAL.read_bytes()
    if sha(original)!=ORIGINAL_SHA or Elf(original).relocs!=elf.relocs[:71807]:raise ValueError('Original71807 relocation records differ')
    original_shapes=pair_shapes(original)
    if original_shapes!=pair_shapes(result,original_only=True):raise ValueError('Original per-section pair semantics changed')
    extra_shapes=[p for p in pair_shapes(result)if p['relative_offset']>=71807*8]
    for base in(0x8804000,0x8900000,0x8fff000):
        segment,_,_=loaded(result,base);section,visited,skipped,pairs=section_load(result,base)
        file_backed=[section[n][:elf.ph[n][4]]for n in range(3)]
        if segment!=file_backed or visited!=elf.relocs or skipped:raise ValueError('Actual section-driven relocation model differs from PH model')
        if any(any(section[n][elf.ph[n][4]:])for n in range(3)):raise ValueError('Relocations unexpectedly alter BSS')
        broken,bvisited,bskipped,_=section_load(incoming,base,strict=False)
        if bskipped!=[68,69]or len(bvisited)!=71807:raise ValueError('Observed18 skip reproduction differs')
        rawjump=struct.unpack_from('<I',broken[0],0xe9cc8)[0];fixedjump=struct.unpack_from('<I',section[0],0xe9cc8)[0]
        if rawjump>>26!=2 or (rawjump&0x3ffffff)*4!=0x2e8c90 or (fixedjump&0x3ffffff)*4!=base+0x2e8c90:raise ValueError('Observed cold-boot jump reproduction differs')
        models.append(dict(base=base,section_records=len(visited),HI_LO_pairs=pairs,all_three_loaded_segments_exact_to_PH_model=True,source18_skipped_sections=bskipped,source18_applied_records=len(bvisited),source18_unapplied_records=337,cold_boot_site_rva=0xe9cc8,source18_jump_target=0x2e8c90,repaired_jump_target=base+0x2e8c90))
    report=copy.deepcopy(before);report.update(version='0.1.19',status='dry_section_relocation_repair',output_elf_sha256=sha(result),output_sha256=sha(result),elf_bytes=len(result),runtime_verified=False)
    report['section_relocation_repair']=dict(input_elf_sha256=SOURCE_SHA,input_bytes=len(incoming),output_bytes=len(result),input_report_sha256=sha(SOURCE.with_name('executable.en.json').read_bytes()),
        original_section_count=70,new_section_count=71,original_relocations=71807,total_relocations=72144,missing18_warning_records=20,nonloaded18_extra_records=317,sections=intervals,
        repaired_sections=[dict(index=68,records=311,sh_info=1,source_segments=sorted({f>>8&255 for _,f in elf.relocs[71807:72118]})),dict(index=69,records=20,sh_info=55,source_segments=sorted({f>>8&255 for _,f in elf.relocs[72118:72138]})),dict(index=70,records=6,sh_info=1,source_segments=[0])],
        program_headers_exact=True,all_loaded_file_bytes_exact=True,relocation_program_bytes_exact=True,unloaded_font_trailer_offset_bytes_exact=True,source_prefix_exact_except_ELF_shoff_and_shnum=True,
        original71807_section_partitions_exact=True,all_records_covered_once_in_original_order=True,section_driven_models=models,
        original_source_sha256=ORIGINAL_SHA,original_record_prefix_exact=True,original_section_pair_shapes_exact=original_shapes,extra_section_pair_shapes=extra_shapes,no_HI_crosses_section_boundary=True,
        loader_source='https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/ELF/ElfReader.cpp',loader_source_local_sha256=sha(pathlib.Path('work/source/ppsspp_reference/ElfReader.cpp').read_bytes()),
        loader_gate='sh_info selects SHF_ALLOC gate; each PSP record flags select LOAD source/target. PH3 path runs only with zero section count.',runtime_verified=False)
    report['relocation_repair_code_input_sha256']=sha(pathlib.Path(__file__).read_bytes())
    from build_local import authoritative_font_metadata
    authoritative_font_metadata(result,report)
    return result,report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--expected-report-sha256');p.add_argument('--expected-elf-sha256');a=p.parse_args()
    data,report=build();digest=canonical(report);print(json.dumps(dict(version='0.1.19',elf_sha256=sha(data),canonical_report_sha256=digest,elf_bytes=len(data),repair=report['section_relocation_repair']),indent=2))
    if not a.write:print('DRY ONLY: no executable/ISO written.');return
    if a.expected_report_sha256!=digest or a.expected_elf_sha256!=sha(data):raise ValueError('Writer requires exact reviewed report/ELF hashes')
    if ROOT.exists():raise ValueError('Fresh19 folder required')
    ROOT.mkdir(parents=True);target=ROOT/'EBOOT.BIN';target.write_bytes(data)
    if sha(target.read_bytes())!=sha(data):raise ValueError('Executable readback differs')
    (ROOT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Wrote isolated19 executable/report; runtime verification pending.')

if __name__=='__main__':main()
