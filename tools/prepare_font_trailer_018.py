"""Pure .18 trailer/bootstrap and PNG-tail placement proposal; no writer."""
import copy,hashlib,json,struct,zlib
from pathlib import Path
from build_menu_patch import START,align
from compact_vwf_patch import loaded
from font_vram_hooks import initialize as previous_initializer
from font_trailer_hooks import initialize,checksum,MAGIC,IO
from png_lossless_repack import repack
from font_ram_plan import decode

SOURCE=Path('work/output/0.1.17-dialogue-assets/EBOOT.BIN')
SHA='321d1e5918ddb9ea7258163acc9185fe6a0e54c04d38d50e2cc8ee6fb14c1235'
def sha(data):return hashlib.sha256(data).hexdigest()

def build(png_repacker=repack,include_pic1=False):
    original=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('setup_patch.en.json').read_text())
    if sha(original)!=SHA or before['output_elf_sha256']!=SHA:raise ValueError('Frozen .17 source guard differs')
    po,so=struct.unpack_from('<II',original,28);ph=[list(struct.unpack_from('<8I',original,po+n*32))for n in range(4)]
    sections=[list(struct.unpack_from('<10I',original,so+n*40))for n in range(struct.unpack_from('<H',original,48)[0])]
    old=original[ph[2][1]:ph[2][1]+ph[2][4]];records=list(struct.iter_unpack('<II',original[ph[3][1]:ph[3][1]+ph[3][4]]))
    oldinit=before['font_hooks']['initializer'];expected,expected_rel=previous_initializer(START+0x500,before['font_runtime_state_rva'],before['high_bank'],20268,193024,before['font_hooks']['decompressor'])
    if old[oldinit-START:oldinit-START+len(expected)]!=expected:raise ValueError('Old initializer fingerprint differs')
    packed=old[before['high_bank']-START:before['high_bank']-START+20268]
    if sha(packed)!=before['font_compressed_sha256']or sha(decode(packed,193024))!=before['high_bank_sha256']:raise ValueError('Exact decoded font guard differs')
    hi,lo=struct.unpack_from('<2I',old,0x52c);table=((hi&65535)<<16)+struct.unpack('<h',struct.pack('<H',lo&65535))[0]
    if hi>>26!=15 or lo>>26!=9:raise ValueError('Resident table pointer ABI differs')
    tablebytes=old[table-START:table-START+328*12];entries=list(struct.iter_unpack('<Iff',tablebytes))
    if len(entries)!=328 or [v[0]for v in entries]!=sorted(v[0]for v in entries):raise ValueError('Active328 descriptor differs')
    prefix=bytearray(original[:0x508880]);icons=json.loads(Path('work/source/save_ui_015_rgb_candidate.en.json').read_text())['save_ui_patch']['icons'];tails=[];pngproof=[];native_changes=[]
    if include_pic1:
        off=0x2aece0;n=239279
        icons.append(dict(name='shared_pic1',original_file_offset=hex(off),replacement_bytes=n,original_bytes=n,output_sha256=sha(original[off:off+n]),pointer_file_offset='0x470a70',additional_pointer_file_offsets=['0x470a94']))
    for icon in icons:
        off=int(icon['original_file_offset'],16);n=icon['replacement_bytes'];data=original[off:off+n]
        if sha(data)!=icon['output_sha256']:raise ValueError('Current savedata PNG source hash differs')
        result,proof=png_repacker(data);prefix[off:off+len(result)]=result
        slots=[int(x,16)for x in [icon['pointer_file_offset']]+icon.get('additional_pointer_file_offsets',[])]
        for slot in slots:
            if struct.unpack_from('<3I',original,slot)!=(off-192,n,n):raise ValueError('PNG native pointer/size triple differs')
            struct.pack_into('<II',prefix,slot+4,len(result),len(result));native_changes.append((slot+4,slot+12))
        native_changes.append((off,off+len(result)));slot=slots[0]
        start=align(off-192+len(result),4);end=off-192+icon['original_bytes'];tails.append(dict(name=icon['name'],start=start,end=end,cursor=start))
        pngproof.append(dict(name=icon['name'],file_offset=off,pointer_slot_rva=slot-192,pointer_slot_rvas=[v-192 for v in slots],original_pointer_rva=off-192,current_bytes=n,proposed_bytes=len(result),allocated_original_capacity=icon['original_bytes'],tail_start_rva=start,tail_end_rva=end,rgba_pixels_identical=True,input_sha256=sha(data),output_sha256=sha(result),filter_proof=proof))
    # Every typed active address is checked against new tail destinations before
    # placement. Declared PNG stream sizes exclude these exact original bytes.
    def read(off,f):return struct.unpack_from('<I',original,ph[f>>8&255][1]+off)[0]
    def absolute(n):
        off,f=records[n];typ=f&255;w=read(off,f)
        if typ==2:value=w
        elif typ==4:value=(w&0x3ffffff)*4
        elif typ==5:
            q=next(k for k in range(n+1,len(records))if records[k][1]&255==6);o,g=records[q];value=((w&65535)<<16)+struct.unpack('<h',struct.pack('<H',read(o,g)&65535))[0]
        else:return None
        return value+ph[f>>16&255][2]
    for n in range(len(records)):
        address=absolute(n)
        if address is not None and any(t['start']<=address<t['end']for t in tails):raise ValueError('Active preexisting relocation references PNG tail')
    placements=[]
    def place(name,address,data):
        if old[address-START:address-START+len(data)]!=data:raise ValueError('Moved source bytes differ')
        for tail in tails:
            start=align(tail['cursor'],4)
            if start+len(data)<=tail['end']:
                prefix[start+192:start+192+len(data)]=data;native_changes.append((start+192,start+192+len(data)));tail['cursor']=start+len(data)
                placements.append(dict(name=name,old_start=address,old_end=address+len(data),new_start=start,bytes=len(data),sha256=sha(data),tail=tail['name']));return
        raise ValueError('Exact PNG tails cannot hold all selected data')
    place('resident_328_descriptor',table,tablebytes)
    groups=[]
    for key in ('scoped_executable_ui','scoped_tutorial_quest_ui'):
        strings=before[key]['strings'];start=min(x['payload_rva']for x in strings);end=max(x['payload_rva']+x['payload_bytes']for x in strings)
        groups.append((key,start,align(end,16)))
        unique={}
        for row in strings:
            address=row['payload_rva'];data=old[address-START:address-START+row['payload_bytes']]
            if not data.endswith(b'\0')or b'\0'in data[:-1]:raise ValueError('Moved player string has embedded NUL')
            if row.get('payload_sha256')and row['payload_sha256']!=sha(data):raise ValueError('Scoped target byte hash differs')
            unique.setdefault(address,(row['id'],data))
        for address,(name,data)in sorted(unique.items(),key=lambda x:(-len(x[1][1]),x[0])):place(name,address,data)
    ranges=[dict(name='loaded_compressed_font',start=before['high_bank']-START,end=before['high_bank']-START+20272),dict(name='obsolete_loaded_font_initializer',start=oldinit-START,end=oldinit-START+align(len(expected),16)),dict(name='resident_descriptor_to_png_tail',start=table-START,end=table-START+align(len(tablebytes),16))]
    ranges.extend(dict(name=key+'_to_png_tails',start=start-START,end=end-START)for key,start,end in groups);ranges.sort(key=lambda x:x['start'])
    if any(a['end']>b['start']for a,b in zip(ranges,ranges[1:])):raise ValueError('Reclamation ranges overlap')
    def member(off):return next((x for x in ranges if x['start']<=off<x['end']),None)
    recovery=sum(x['end']-x['start']for x in ranges)
    def mapped(address):
        item=next((x for x in placements if x['old_start']<=address<x['old_end']),None)
        if item:return item['new_start']+address-item['old_start']
        if not START<=address<START+len(old):return address
        off=address-START
        if member(off):raise ValueError('Surviving pointer into removed range '+hex(address))
        return address-sum(x['end']-x['start']for x in ranges if x['end']<=off)
    def site(off,f):
        if f>>8&255!=2:return off
        if member(off):raise ValueError('Relocation site inside reclaimed data')
        return mapped(START+off)-START
    payload=bytearray();last=0
    for item in ranges:payload.extend(old[last:item['start']]);last=item['end']
    payload.extend(old[last:])
    # Appended code addresses are assigned only after final compaction layout.
    initaddr=START+align(len(payload),16);crcaddr=initaddr+align(924,16);pathaddr=crcaddr+align(len(checksum()),16)
    core_placeholder=6000000
    newinit,initrel,scalar_sites=initialize(START+0x500,mapped(before['font_runtime_state_rva']),pathaddr,core_placeholder,20268,193024,mapped(before['font_hooks']['decompressor']),crcaddr,zlib.crc32(packed))
    if len(newinit)!=924:raise ValueError('Reviewed bootstrap size changed')
    payload.extend(bytes(initaddr-START-len(payload)));payload.extend(newinit);payload.extend(bytes(crcaddr-START-len(payload)));payload.extend(checksum());payload.extend(bytes(pathaddr-START-len(payload)));payload.extend(b'disc0:/PSP_GAME/SYSDIR/EBOOT.BIN\0');payload.extend(bytes((-len(payload))%16))
    kept=[];removed=[];changes=[];skip=set();paired=set();lo_newflags={};native_hook=(0x4c0ec,4)
    if native_hook not in records or absolute(records.index(native_hook))!=oldinit:raise ValueError('Actual resident-init dispatch guard differs')
    def put(off,f,value):
        segment=f>>8&255
        struct.pack_into('<I',payload if segment==2 else prefix,site(off,f)if segment==2 else ph[segment][1]+off,value&0xffffffff)
    for n,(off,f)in enumerate(records):
        segment=f>>8&255;typ=f&255;target=f>>16&255
        if segment==2 and member(off):removed.append((off,f));continue
        if n in skip:kept.append((site(off,f),lo_newflags.get(n,f)));continue
        w=read(off,f);a=absolute(n)
        if typ==6:kept.append((site(off,f),f));continue
        new=initaddr if (off,f)==native_hook else mapped(a);newtarget=0 if new<START and target==2 else target;nf=(f&~0xff0000)|(newtarget<<16);stored=new-ph[newtarget][2]
        kept.append((site(off,f),nf))
        if typ==2:put(off,f,stored)
        elif typ==4:put(off,f,(w&0xfc000000)|(stored>>2))
        elif typ==5:
            q=next(k for k in range(n+1,len(records))if records[k][1]&255==6);oo,ff=records[q];low=read(oo,ff);paired.add(q)
            if member(oo)and ff>>8&255==2:raise ValueError('Live HI with removed LO')
            if new!=a and (q!=n+1 or ff>>16&255!=target):raise ValueError('Changed HI/LO must be adjacent/same target')
            put(off,f,(w&0xffff0000)|((stored+0x8000)>>16&65535));put(oo,ff,(low&0xffff0000)|(stored&65535));skip.add(q);lo_newflags[q]=(ff&~0xff0000)|(newtarget<<16)
        if new!=a or nf!=f:changes.append(dict(segment=segment,old_site=off,new_site=site(off,f),type=typ,old_resolved_rva=a,new_resolved_rva=new,old_flags=f,new_flags=nf))
    for n,(off,f)in enumerate(records):
        if f&255!=5:continue
        q=next(k for k in range(n+1,len(records))if records[k][1]&255==6)
        if ((off,f)in removed)!=(records[q]in removed):raise ValueError('Removed HI/LO halves differ')
    kept.extend((initaddr-START+off,0x200|typ)for off,typ in initrel)
    if len(kept)!=len(records)-len(removed)+len(initrel)or len(set(kept))!=len(kept):raise ValueError('Unexpected duplicated/lost relocation records')
    # All retained bytes outside typed relocation words must remain exact.
    relocation_bytes={b for off,f in records if f>>8&255==2 for b in range(off,off+4)}
    identity_checks=0
    for off,value in enumerate(old):
        if member(off)or off in relocation_bytes:continue
        if payload[mapped(START+off)-START]!=value:raise ValueError('Retained nonrelocation payload byte differs')
        identity_checks+=1
    native_masked=bytearray(original[:0x508880])
    for start,end in native_changes:native_masked[start:end]=prefix[start:end]
    for off,f in records:
        if f>>8&255==0:
            start=ph[0][1]+off;native_masked[start:start+4]=prefix[start:start+4]
    if native_masked!=prefix:raise ValueError('Unreported native-prefix change')
    # Walk surviving injected instructions from all actual native J/JAL entries.
    # An unrelocated conditional/fallthrough cannot enter removed storage.
    roots=[absolute(n)-START for n,(off,f)in enumerate(records)if f>>8&255==0 and f&255==4 and START<=absolute(n)<START+len(old) and(off,f)!=native_hook]
    todo=list(roots);visited=set();branch_edges=0
    def enqueue(off):
        if not 0<=off<len(old):return
        if off%4:raise ValueError('Unaligned injected code entry')
        if member(off):raise ValueError('Active flow enters removed data/code')
        if off not in visited:todo.append(off)
    while todo:
        off=todo.pop()
        if off in visited:continue
        enqueue(off);visited.add(off)
        word=struct.unpack_from('<I',old,off)[0];op=word>>26;sv=struct.unpack('<h',struct.pack('<H',word&65535))[0]
        currentoff=mapped(START+off)-START;current=struct.unpack_from('<I',payload,currentoff)[0]
        def edge(nextoff):
            enqueue(nextoff)
            if 0<=nextoff<len(old)and mapped(START+nextoff)-START!=currentoff+(nextoff-off):raise ValueError('Compaction alters an active relative/fallthrough edge')
        special=op in(1,2,3,4,5,6,7,20,21,22,23)or(op==17 and word>>21&31==8)or(op==0 and word&63 in(8,9))
        if special:
            edge(off+4);visited.add(off+4)
            if op in(2,3):
                target=(word&0x3ffffff)*4
                enqueue(target-START)
                if (current&0x3ffffff)*4!=mapped(target):raise ValueError('Injected call/jump target differs')
                if op==3:edge(off+8)
            elif op==0:
                if word>>21&31!=31:raise ValueError('Indirect injected entry needs proof')
            else:edge(off+4+sv*4);edge(off+8);branch_edges+=1
        else:edge(off+4)
    # Existing user IO stubs are bound to exact offline NIDs/module, not guessed
    # syscall numbers. Runtime PPSSPP rewrites these same imported stubs.
    expected_io={'open':0x109f50bc,'read':0x6a638d83,'seek64':0x27eb27b8,'close':0x810c4bc3};io_guards=[]
    native=original[ph[0][1]:ph[0][1]+ph[0][4]]
    for offset in range(0x2946c8,0x294894,20):
        name,version,attr,length,varcount,count,nids,stub=struct.unpack_from('<IHHBBHII',native,offset)
        module=native[name:native.index(0,name)].decode('ascii')
        for index in range(count):
            nid=struct.unpack_from('<I',native,nids+4*index)[0]
            for label,value in expected_io.items():
                if nid==value:
                    rva=stub+8*index
                    if module!='IoFileMgrForUser'or length!=5 or varcount or rva!=IO[label]or struct.unpack_from('<I',native,rva)[0]!=0x03e00008:raise ValueError('Native IO binding differs')
                    io_guards.append(dict(name=label,module=module,nid=nid,rva=rva,exact_stub_hex=native[rva:rva+8].hex()))
    if len(io_guards)!=4:raise ValueError('Missing/duplicate native IO imports')
    allocator_guards=[]
    for label,rva,expected_hex in [('allocate',0xc70,'f0ffbd273f008424823104002801043ce8a58424803106000000bfafef00000c400005340000bf8f0800e0031000bd27'),('free',0xca0,'f0ffbd27252880002801043c0000bfaf7701000ce8a584240000bf8f0800e0031000bd27')]:
        expected_bytes=bytes.fromhex(expected_hex)
        if native[rva:rva+len(expected_bytes)]!=expected_bytes:raise ValueError('Native VRAM callee instructions differ')
        allocator_guards.append(dict(name=label,rva=rva,exact_code_hex=expected_hex,code_sha256=sha(expected_bytes)))
    rel=b''.join(struct.pack('<II',*x)for x in kept);pf=align(len(prefix),64);prefix.extend(bytes(pf-len(prefix)));prefix.extend(payload);rf=align(len(prefix),16);prefix.extend(bytes(rf-len(prefix)));prefix.extend(rel)
    cursor=0;payloadsection=next(n for n,s in enumerate(sections)if s[3]==START and s[4]==ph[2][1])
    for s in sections:
        if s[1]==0x700000a0:
            if cursor<71807*8:s[4]=rf+cursor;cursor+=s[5]
            else:s[4]=rf+71807*8;s[5]=0
        elif s[3]==START and s[4]==ph[2][1]:s[4]=pf;s[5]=len(payload)
    if cursor!=71807*8:raise ValueError('Original relocation sections differ')
    sections.append([0,0x700000a0,0,0,rf+cursor,len(rel)-cursor,0,payloadsection,4,8]);newsh=align(len(prefix),4);prefix.extend(bytes(newsh-len(prefix)))
    for s in sections:prefix.extend(struct.pack('<10I',*s))
    ph[2][1]=pf;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=rf;ph[3][4]=len(rel)
    for n,p in enumerate(ph):struct.pack_into('<8I',prefix,po+n*32,*p)
    struct.pack_into('<I',prefix,32,newsh);struct.pack_into('<H',prefix,48,len(sections))
    trailer_offset=align(len(prefix),16);prefix.extend(bytes(trailer_offset-len(prefix)))
    finalized,finalrel,finalscalar=initialize(START+0x500,mapped(before['font_runtime_state_rva']),pathaddr,trailer_offset,20268,193024,mapped(before['font_hooks']['decompressor']),crcaddr,zlib.crc32(packed))
    if len(finalized)!=len(newinit)or finalrel!=initrel:raise ValueError('File-offset scalar changed code layout')
    prefix[pf+initaddr-START:pf+initaddr-START+len(finalized)]=finalized
    prefix.extend(MAGIC+struct.pack('<II',20268,193024)+packed)
    # The trailer is outside every load/REL/section span and has no relocations.
    if any(p[1]+p[4]>trailer_offset for p in ph)or any(s[1]!=8 and s[4]+s[5]>trailer_offset for s in sections):raise ValueError('Trailer overlaps declared ELF storage')
    comparisons=0
    for base in (0x8804000,0x8900000,0x8fff000):
        oldsegments,_,nextlo=loaded(original,base);newsegments,_,_=loaded(prefix,base)
        if newsegments[1]!=oldsegments[1]:raise ValueError('Native LOAD1 changed')
        for n,(off,f)in enumerate(records):
            if (off,f)in removed:continue
            segment=f>>8&255;typ=f&255;ow=struct.unpack_from('<I',oldsegments[segment],off)[0];nw=struct.unpack_from('<I',newsegments[segment],site(off,f))[0]
            if typ==2:x,y=ow,nw
            elif typ==4:x,y=(ow&0x3ffffff)*4,(nw&0x3ffffff)*4
            elif typ==5:
                oo,ff=records[nextlo[n]];ls=ff>>8&255;ol=struct.unpack_from('<I',oldsegments[ls],oo)[0];nl=struct.unpack_from('<I',newsegments[ls],site(oo,ff))[0]
                x=((ow&65535)<<16)+struct.unpack('<h',struct.pack('<H',ol&65535))[0];y=((nw&65535)<<16)+struct.unpack('<h',struct.pack('<H',nl&65535))[0]
            else:
                if n not in paired and ow!=nw:raise ValueError('Standalone LO changed')
                continue
            expected=base+initaddr if(off,f)==native_hook else base+mapped(x-base)
            if y!=expected:raise ValueError('Loaded pointer differs '+hex(off))
            comparisons+=1
    def metadata(value,key=''):
        if isinstance(value,dict):return {k:metadata(v,k)for k,v in value.items()}
        if isinstance(value,list):return [metadata(v,key)for v in value]
        if type(value)==int:return mapped(START+value)if key=='stored_offset'else mapped(value)
        if isinstance(value,str)and value.startswith('0x'):
            try:number=int(value,16)
            except ValueError:return value
            return hex(mapped(number))
        return value
    current=copy.deepcopy(before);current.pop('input_build_history',None);current.pop('payload_recovery',None);current.pop('memory_forecast',None);current.pop('approved_dry_report_sha256',None)
    current['high_bank']=None;current['font_hooks']['initializer']=initaddr
    # New initializer is not an old address and must not be remapped twice.
    hooks=current.pop('font_hooks');hooks={k:(initaddr if k=='initializer'else mapped(v))for k,v in hooks.items()}
    report=metadata(current);report['font_hooks']=hooks
    for key in ('scoped_executable_ui','scoped_tutorial_quest_ui'):
        report[key]['target_segment']=0;report[key]['stored_pointer_policy']='LOAD0-relative RVA in typed R32 slots; current targets reside in excluded PNG tails.'
        report[key]['inherited_payload_prefix_exact']=False;report[key]['preservation_proof']='trailer_recovery loaded pointer models and exact moved text bytes'
    for row in report['scoped_executable_ui']['pointer_changes']:row['new_relocation_flags']=2
    report.update(version='0.1.18',input_version='0.1.17',input_sha256=SHA,status='dry_unloaded_trailer_font_candidate',runtime_verified=False,output_elf_sha256=sha(prefix),output_sha256=sha(prefix),elf_bytes=len(prefix),payload_bytes=len(payload),module_growth_bytes=len(payload),total_relocations=len(kept),original_relocations=71807,added_relocations=len(kept)-71807,relocation_table_sha256=sha(rel),font_runtime_storage='owned_vram_lz4_trailer_v1',high_bank_address_kind='unloaded_elf_file_offset',font_trailer_offset=trailer_offset,font_compressed_file_offset=trailer_offset+16,font_scratch_bytes=20272,font_compressed_crc32=zlib.crc32(packed),font_descriptor_rva=mapped(table),font_hooks_extra=dict(checksum=crcaddr),input_build_history=dict(scope='Frozen .17 historical report only',report=before),trailer_recovery=dict(recovered_loaded_bytes=len(old)-len(payload),removed_loaded_ranges=ranges,moved_data=placements,pngs=pngproof,remaining_tail_bytes=sum(t['end']-t['cursor']for t in tails),removed_relocations=removed,address_changes=changes,loaded_pointer_comparisons=comparisons,loaded_bases=[0x8804000,0x8900000,0x8fff000],native_LOAD1_exact=True,trailer_outside_all_declared_spans=True,source_bank_sha256=sha(packed),decoded_bank_sha256=before['high_bank_sha256'],bootstrap_bytes=len(finalized),checksum_bytes=len(checksum()),bootstrap_relocations=initrel,scalar_sites=finalscalar,io_imports=IO,original_initializer_order_preserved=True,no_assets_written=True),limitations=['IO into VRAM is supported by PPSSPP source; native PSP firmware behavior remains unverified.','Movie/battle peak allocations and all font routes require fresh runtime QA.','No kernel-only decompressor imports or pixel/text reductions.'])
    report['runtime_font_bank_pointer_source']['state_rva']=report['font_runtime_state_rva']
    proof=report['trailer_recovery']
    from savedata_tail_proof import prove
    proof['savedata_native_tail_lifetime']=prove(bytes(prefix))
    proof.update(surviving_nonrelocation_byte_comparisons=identity_checks,native_LOAD0_only_reported_changes=True,native_change_file_ranges=native_changes,
        injected_control_flow_roots=len(roots),reachable_instruction_words=len(visited),conditional_branch_edges=branch_edges,all_active_relative_and_fallthrough_edges_preserved=True,
        original_relocation_tail_references_rejected=True,png_tails_excluded_by_exact_declared_sizes=True,
        native_io_guards=io_guards,native_vram_callee_guards=allocator_guards,
        free_tail_regions=[dict(name=t['name'],start_rva=t['cursor'],end_rva=t['end'],next_aligned4_rva=align(t['cursor'],4),bytes=t['end']-t['cursor'])for t in tails],
        tail_lifetime_limitations=['Exact typed PNG references, sole table consumer and all4 native row-constructor JALs guarded. Arbitrary untyped/dynamic fabricated pointers and native firmware decode remain outside static proof.'])
    report['memory_forecast']=dict(allocator_granularity=256,allocator_source='PPSSPPv1.20.4 Core/HLE/sceKernelMemory.cpp userMemory(256); Core/Util/BlockAllocator.cpp Alloc/AllocAt',
        original_module_bytes=align(0x16f9acc,256),source_017_module_bytes=align(START+len(old),256),proposed_018_module_bytes=align(START+len(payload),256),
        raw_module_end_017=START+len(old),raw_module_end_018=START+len(payload),module_allocation_recovery_bytes=align(START+len(old),256)-align(START+len(payload),256),
        retained_vram_bank_bytes=193024,retained_vram_bank_allocation_bytes=193088,temporary_vram_scratch_bytes=20272,temporary_vram_scratch_allocation_bytes=20336,
        scratch_released_before_movie=True,observed_movie_prx_request_bytes=10752,observed_movie_request_bytes=49152,
        source_017_margin_before_movie=before['memory_forecast']['margin_before_movie'],
        forecast_margin_before_prx=before['memory_forecast']['margin_before_movie']+align(START+len(old),256)-align(START+len(payload),256),
        forecast_margin_before_request=before['memory_forecast']['margin_after_one_observed_movie_request']+align(START+len(old),256)-align(START+len(payload),256),
        forecast_margin_after_request=before['memory_forecast']['margin_after_one_observed_movie_request']+align(START+len(old),256)-align(START+len(payload),256)-49152,
        known_requests_forecast_passed=False,
        actual_contiguous_heap_unmeasured=True,transition_failure_unresolved=True)
    return bytes(prefix),report

if __name__=='__main__':
    data,report=build();print(json.dumps(report,indent=2));print('Canonical dry report SHA256:',sha(json.dumps(report,sort_keys=True,separators=(',',':')).encode()));print('DRY ONLY: no ELF/ISO writer.')
