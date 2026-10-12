"""Pure near-original-RAM font composition using bounded native PNG tails."""
import copy,json,struct,hashlib
from prepare_font_trailer_018 import build as trailer_build,sha
from png_zopfli_repack import optimize
from png_tail_allocate import plan
from compact_vwf_patch import loaded
from build_menu_patch import START,align,relocate_code
from dialogue_vwf_hooks import decoder

def build():
    incoming,before=trailer_build(png_repacker=optimize,include_pic1=True)
    po,so=struct.unpack_from('<II',incoming,28);ph=[list(struct.unpack_from('<8I',incoming,po+n*32))for n in range(4)]
    sections=[list(struct.unpack_from('<10I',incoming,so+n*40))for n in range(struct.unpack_from('<H',incoming,48)[0])]
    old=incoming[ph[2][1]:ph[2][1]+ph[2][4]];records=list(struct.iter_unpack('<II',incoming[ph[3][1]:ph[3][1]+ph[3][4]]))
    # First decoder is exactly obsolete; all other removed bytes are literal
    # zero slot padding, excluding every active function/delay/lookup byte.
    dead=bytearray(decoder(True));relocate_code(dead,0,len(dead))
    for off in range(0,len(dead),4):
        typ=next((f&255 for site,f in records if site==off and f>>8&255==2),None)
        mask=0xfc000000 if typ==4 else 0xffff0000 if typ in(5,6)else 0xffffffff
        if struct.unpack_from('<I',old,off)[0]&mask!=struct.unpack_from('<I',dead,off)[0]&mask:raise ValueError('Obsolete first decoder fingerprint differs')
    ranges=[(0,0x100),(0x150,0x200),(0x2a0,0x300),(0x320,0x400),(0x450,0x500),(0x560,0x600),(0x710,0x800)]
    if old[len(dead):0x100]!=bytes(0x100-len(dead)):raise ValueError('Dead decoder slot padding differs')
    for start,end in ranges[1:]:
        if old[start:end]!=bytes(end-start):raise ValueError('Native slot padding is not zero')
    def removed(off):return any(start<=off<end for start,end in ranges)
    prefix_chunk=bytearray();last=0
    for start,end in ranges:prefix_chunk.extend(old[last:start]);last=end
    prefix_chunk.extend(old[last:0xa40])
    if len(prefix_chunk)!=1296 or len(old)-0xa40!=21216:raise ValueError('Reviewed two-chunk sizes differ')
    # Use caption tails for the small first chunk, PIC1 only for the large one.
    tailreport=copy.deepcopy(before);tailreport['trailer_recovery']['free_tail_regions']=[x for x in before['trailer_recovery']['free_tail_regions']if x['name']!='shared_pic1']
    small=plan(tailreport,[dict(name='resident_hooks_float_lookup_labels',data=bytes(prefix_chunk),alignment=16)])
    tailreport['trailer_recovery']['free_tail_regions']=[x for x in before['trailer_recovery']['free_tail_regions']if x['name']=='shared_pic1']
    large=plan(tailreport,[dict(name='remaining_font_dialogue_setup_hooks_and_tables',data=old[0xa40:],alignment=16)])
    first=small['patches'][0]['rva'];second=large['patches'][0]['rva'];free=small['free_tail_regions']+large['free_tail_regions']
    def mapped(address):
        if not START<=address<START+len(old):return address
        off=address-START
        if removed(off):raise ValueError('Surviving pointer into obsolete decoder/padding')
        if off<0xa40:return first+off-sum(end-start for start,end in ranges if end<=off)
        return second+off-0xa40
    output=bytearray(incoming);placements=small['patches']+large['patches']
    for row in placements:output[row['file_offset']:row['file_offset']+row['bytes']]=row['data']
    def word(off,f):return struct.unpack_from('<I',incoming,ph[f>>8&255][1]+off)[0]
    def site(off,f):return mapped(START+off)if f>>8&255==2 else off
    def storage(f):return 0 if f>>8&255==2 else f>>8&255
    def put(off,f,value):struct.pack_into('<I',output,ph[storage(f)][1]+site(off,f),value&0xffffffff)
    def absolute(n):
        off,f=records[n];typ=f&255;w=word(off,f)
        if typ==2:a=w
        elif typ==4:a=(w&0x3ffffff)*4
        elif typ==5:
            q=next(k for k in range(n+1,len(records))if records[k][1]&255==6);oo,ff=records[q]
            a=((w&65535)<<16)+struct.unpack('<h',struct.pack('<H',word(oo,ff)&65535))[0]
        else:return None
        return a+ph[f>>16&255][2]
    kept=[];dropped=[];skip=set();low_flags={};paired=set();changes=[]
    for n,(off,f)in enumerate(records):
        if f>>8&255==2 and removed(off):dropped.append((off,f));continue
        sf=(f&~0xff00)|(storage(f)<<8)
        if n in skip:kept.append((site(off,f),low_flags[n]));continue
        typ=f&255
        if typ==6:kept.append((site(off,f),sf));continue
        old_address=absolute(n);new_address=mapped(old_address);target=f>>16&255;newtarget=0 if target==2 else target;nf=(sf&~0xff0000)|(newtarget<<16)
        stored=new_address-ph[newtarget][2];w=word(off,f);kept.append((site(off,f),nf))
        if typ==2:put(off,f,stored)
        elif typ==4:put(off,f,(w&0xfc000000)|(stored>>2))
        elif typ==5:
            q=next(k for k in range(n+1,len(records))if records[k][1]&255==6);oo,ff=records[q]
            if ff>>8&255==2 and removed(oo):raise ValueError('Live HI with dead LO')
            if new_address!=old_address and(q!=n+1 or ff>>16&255!=target):raise ValueError('Changed shared/nonadjacent HI-LO requires separate model')
            put(off,f,(w&0xffff0000)|((stored+0x8000)>>16&65535));put(oo,ff,(word(oo,ff)&0xffff0000)|(stored&65535));skip.add(q);paired.add(q)
            low_flags[q]=(ff&~0xffff00)|(storage(ff)<<8)|(newtarget<<16)
        else:raise ValueError('Unexpected relocation type')
        if new_address!=old_address or nf!=f:changes.append(dict(old_site=off,new_site=site(off,f),old_flags=f,new_flags=nf,old_resolved_rva=old_address,new_resolved_rva=new_address))
    for n,(off,f)in enumerate(records):
        if f&255==5:
            q=next(k for k in range(n+1,len(records))if records[k][1]&255==6)
            if ((off,f)in dropped)!=(records[q]in dropped):raise ValueError('Removed HI/LO halves inconsistent')
    if len(kept)!=len(records)-len(dropped)or len(set(kept))!=len(kept)or any(f>>8&255==2 or f>>16&255==2 for _,f in kept):raise ValueError('Relocation duplication or retained empty segment reference')
    # Preserve incoming trailer and its file-offset constants; append only new
    # relocation/section tables after EOF, never implicitly move its font data.
    rf=align(len(output),16);output.extend(bytes(rf-len(output)));rel=b''.join(struct.pack('<II',*x)for x in kept);output.extend(rel)
    ph[2][4]=ph[2][5]=0;ph[3][1]=rf;ph[3][4]=len(rel);cursor=0
    for section in sections:
        if section[1]==0x700000a0:
            if cursor<71807*8:section[4]=rf+cursor;cursor+=section[5]
            else:section[4]=rf+71807*8;section[5]=0
        elif section[3]==START and section[4]==ph[2][1]:section[5]=0
    if cursor!=71807*8:raise ValueError('Original relocation partition changed')
    sections.append([0,0x700000a0,0,0,rf+cursor,len(rel)-cursor,0,0,4,8]);newsh=align(len(output),4);output.extend(bytes(newsh-len(output)))
    for section in sections:output.extend(struct.pack('<10I',*section))
    for n,p in enumerate(ph):struct.pack_into('<8I',output,po+n*32,*p)
    struct.pack_into('<I',output,32,newsh);struct.pack_into('<H',output,48,len(sections))
    # All source byte reads outside removed bytes have exact identity, masking
    # only relocated words already checked by three loaded-pointer simulations.
    rbytes={b for off,f in records if f>>8&255==2 for b in range(off,off+4)};identities=0
    for off,value in enumerate(old):
        if removed(off)or off in rbytes:continue
        if output[mapped(START+off)+192]!=value:raise ValueError('Moved nonrelocation byte differs')
        identities+=1
    roots=[absolute(n)-START for n,(off,f)in enumerate(records)if f>>8&255==0 and f&255==4 and START<=absolute(n)<START+len(old)];todo=list(roots);seen=set();branches=0
    def enqueue(off):
        if not 0<=off<len(old):return
        if off%4 or removed(off):raise ValueError('Active CFG enters removed/unaligned storage')
        if off not in seen:todo.append(off)
    while todo:
        off=todo.pop()
        if off in seen:continue
        enqueue(off);seen.add(off);w=struct.unpack_from('<I',old,off)[0];op=w>>26;sv=struct.unpack('<h',struct.pack('<H',w&65535))[0]
        def edge(target):
            enqueue(target)
            if 0<=target<len(old)and mapped(START+target)-mapped(START+off)!=target-off:raise ValueError('Native-tail chunk splits an active relative/fallthrough edge')
        special=op in(1,2,3,4,5,6,7,20,21,22,23)or(op==17 and w>>21&31==8)or(op==0 and w&63 in(8,9))
        if special:
            edge(off+4);seen.add(off+4)
            if op in(2,3):
                target=(w&0x3ffffff)*4;enqueue(target-START)
                nw=struct.unpack_from('<I',output,mapped(START+off)+192)[0]
                if (nw&0x3ffffff)*4!=mapped(target):raise ValueError('Moved code target differs')
                if op==3:edge(off+8)
            elif op==0:
                if w>>21&31!=31:raise ValueError('Injected indirect jump requires target proof')
            else:edge(off+4+sv*4);edge(off+8);branches+=1
        else:edge(off+4)
    checks=0;standalone=0
    for base in(0x8804000,0x8900000,0x8fff000):
        a,_,mates=loaded(incoming,base);b,_,_=loaded(output,base)
        if a[1]!=b[1]:raise ValueError('Native LOAD1 differs')
        for n,(off,f)in enumerate(records):
            if(off,f)in dropped:continue
            s=f>>8&255;typ=f&255;ow=struct.unpack_from('<I',a[s],off)[0];nw=struct.unpack_from('<I',b[storage(f)],site(off,f))[0]
            if typ==2:x,y=ow,nw
            elif typ==4:x,y=(ow&0x3ffffff)*4,(nw&0x3ffffff)*4
            elif typ==5:
                oo,ff=records[mates[n]];ol=struct.unpack_from('<I',a[ff>>8&255],oo)[0];nl=struct.unpack_from('<I',b[storage(ff)],site(oo,ff))[0]
                x=((ow&65535)<<16)+struct.unpack('<h',struct.pack('<H',ol&65535))[0];y=((nw&65535)<<16)+struct.unpack('<h',struct.pack('<H',nl&65535))[0]
            else:
                if n not in paired:
                    if ow!=nw:raise ValueError('Standalone LO changed')
                    standalone+=1
                continue
            if y!=base+mapped(x-base):raise ValueError('Loaded native-tail pointer mismatch')
            checks+=1
    def remap(value,key=''):
        if isinstance(value,dict):return {k:remap(v,k)for k,v in value.items()}
        if isinstance(value,list):return [remap(v,key)for v in value]
        if type(value)==int:return mapped(value)
        if isinstance(value,str)and value.startswith('0x'):
            try:return hex(mapped(int(value,16)))
            except ValueError:raise ValueError('Active hex metadata refers to removed range: '+key)
        return value
    current=copy.deepcopy(before);history=current.pop('input_build_history');current.pop('trailer_recovery');current.pop('memory_forecast')
    report=remap(current);report.update(status='dry_native_png_tail_font_candidate',output_elf_sha256=sha(output),output_sha256=sha(output),elf_bytes=len(output),payload_bytes=0,module_growth_bytes=0,total_relocations=len(kept),added_relocations=len(kept)-71807,relocation_table_sha256=sha(rel),font_legacy_initializer_rva=mapped(START+0x500),input_build_history=history)
    report['runtime_font_bank_pointer_source']['state_rva']=report['font_runtime_state_rva']
    body_hash='72506aefb9b2d208812e15132fc3a3bca8d4ced8c58468b9364a8f1b52200a43'
    body_matches=[off for off in range(0,len(old)-523,4)if sha(old[off:off+524])==body_hash]
    if len(body_matches)!=1:raise ValueError('Unique reviewed body integer LUT not found')
    report['body_integer_lut_rva']=mapped(START+body_matches[0])
    report['body_integer_lut_sha256']=body_hash
    report['float_width_lut_rva']=mapped(START+0x800)
    trailer=before['font_trailer_offset'];end=before['font_compressed_file_offset']+20268
    if output[trailer:end]!=incoming[trailer:end]:raise ValueError('Unloaded trailer moved/changed')
    report['trailer_recovery']=copy.deepcopy(before['trailer_recovery']);report['trailer_recovery']['free_tail_regions']=free
    report['trailer_recovery']['remaining_tail_bytes']=sum(x['end_rva']-x['start_rva']for x in free)
    report['trailer_recovery']['proof_scope']='Predecessor pure trailer/PNG stage native transfer, IO, initial relocation and moved-string proofs; current code/address relocation is native_tail_compaction. No predecessor prefix-identity claim applies to relocated chunks.'
    native_changed={b for off,f in records if f>>8&255==0 for b in range(off,off+4)}
    native_chunks={b for row in placements for b in range(row['file_offset'],row['file_offset']+row['bytes'])}
    native_identical=0
    for off in range(ph[0][1],ph[0][1]+ph[0][4]):
        if off in native_chunks or off-ph[0][1] in native_changed:continue
        if output[off]!=incoming[off]:raise ValueError('Unselected native LOAD0 byte differs')
        native_identical+=1
    for row in placements:
        row['source_sha256']=sha(row['data'])
        row['output_sha256']=sha(output[row['file_offset']:row['file_offset']+row['bytes']])
    report['native_tail_compaction']=dict(input_pure_elf_sha256=sha(incoming),input_loaded_payload_bytes=len(old),removed_dead_and_zero_ranges=ranges,removed_bytes=sum(b-a for a,b in ranges),
        chunks=[{k:v for k,v in x.items()if k!='data'}for x in placements],remaining_tail_bytes=sum(x['end_rva']-x['start_rva']for x in free),free_tail_regions=free,
        removed_relocations=dropped,address_changes=changes,surviving_nonrelocation_byte_comparisons=identities,loaded_pointer_comparisons=checks,standalone_lo_comparisons=standalone,loaded_bases=[0x8804000,0x8900000,0x8fff000],
        control_flow_roots=len(roots),reachable_instruction_words=len(seen),conditional_branch_edges=branches,all_active_relative_edges_preserved=True,original_LOAD1_exact=True,trailer_offset_and_bytes_preserved=True,empty_LOAD2_runtime_loader_acceptance_unverified=True)
    report['native_tail_compaction']['native_LOAD0_masked_byte_comparisons']=native_identical
    report['native_tail_compaction']['native_LOAD0_exceptions']='Two exact relocated chunks and typed relocation words only; PNG recompression is separately proven in input pure stage.'
    report['memory_forecast']=dict(original_module_bytes=align(0x16f9acc,256),proposed_module_bytes=align(START,256),additional_recovery_vs_017=align(START+56740,256)-align(START,256),
        source_017_margin_before_movie=27036,known_prx_request=10752,known_movie_request=49152,forecast_after_both_requests=27036+align(START+56740,256)-align(START,256)-10752-49152,
        planned_warning_bytes=2292,planned_notification_bytes=1280,planned_gold_data_bytes=16,planned_CPL_helper_and_map_bytes=2784,gold_hook_bytes_unconfirmed=True,actual_contiguous_heap_unmeasured=True,transition_failure_unresolved=True)
    return bytes(output),report

if __name__=='__main__':
    data,report=build();print(json.dumps(dict(elf_sha256=sha(data),report_sha256=sha(json.dumps(report,sort_keys=True,separators=(',',':')).encode()),memory=report['memory_forecast'],proof=report['native_tail_compaction']),indent=2));print('DRY ONLY: no ELF/ISO writer.')
