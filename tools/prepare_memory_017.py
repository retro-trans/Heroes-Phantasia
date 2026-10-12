"""Pure .17 payload reclamation from frozen .16; no executable or ISO writer."""
import copy,hashlib,json,struct
from pathlib import Path
from build_menu_patch import START,align,relocate_code
from compact_vwf_patch import loaded
from font_ram_plan import decode
from font_lz4_hc import encode
from font_vram_hooks import initialize,instruction_model,decompress
from dialogue_vwf_hooks import decoder,measure as early_measure
from dialogue_measure import measure
from dialogue_ruby_hooks import ruby_center,name_glyph_units
from dialogue_wrap import literal_reveal_cap

SOURCE=Path('work/output/0.1.16-dialogue-assets/EBOOT.BIN')
SHA='21d483664a13ee179ebb711fb6c594978516c002dbe8b9a5e54038f379acee24'
def sha(data):return hashlib.sha256(data).hexdigest()


def build():
    original=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('setup_patch.en.json').read_text())
    if sha(original)!=SHA or before['output_elf_sha256']!=SHA:raise ValueError('Frozen .16 guard changed')
    po,so=struct.unpack_from('<II',original,28);ph=[list(struct.unpack_from('<8I',original,po+n*32))for n in range(4)]
    sections=[list(struct.unpack_from('<10I',original,so+n*40))for n in range(struct.unpack_from('<H',original,48)[0])]
    old=original[ph[2][1]:ph[2][1]+ph[2][4]];records=list(struct.iter_unpack('<II',original[ph[3][1]:ph[3][1]+ph[3][4]]))
    relo={off:flags&255 for off,flags in records if flags>>8&255==2}
    def fingerprint(code,off):
        code=bytearray(code);relocate_code(code,0,len(code))
        for n,(a,b)in enumerate(zip(struct.iter_unpack('<I',code),struct.iter_unpack('<I',old[off:off+len(code)]))):
            a=a[0];b=b[0];typ=relo.get(off+n*4)
            if a>>26==11 and a&65535==129 and b&65535==131:a=(a&0xffff0000)|131
            mask=0xfc000000 if typ==4 else 0xffff0000 if typ in(5,6)else 0xffffffff
            if a&mask!=b&mask:raise ValueError('Dead-function signature differs at '+hex(off+n*4))
        size=align(len(code),16)
        # A save-caption string starts immediately after one660B old cap.
        # Keep its final4B dead instruction and all adjoining text; never treat
        # nonzero bytes beyond a matched function as alignment padding.
        if old[off+len(code):off+size]!=bytes(size-len(code)):size=len(code)//16*16
        return size
    functions=[('obsolete_first_measure',0x7dd0,early_measure(0x1760000)),('obsolete_control_measure',0xaf90,measure(0x1760000)),
        ('obsolete_ruby_decoder',0xbe80,decoder(True,(0xf0cf0,0xf0d98))),('obsolete_ruby_center',0xc020,ruby_center(0x1760000)),
        ('obsolete_name_count',0xc140,name_glyph_units()),('obsolete_literal_cap',0xc210,literal_reveal_cap()),
        ('obsolete_battle_decoder',0xc620,decoder(True,(0xf0cf0,0xf0d98,0xec644))),('obsolete_paired_cap',0xc830,literal_reveal_cap(True)),
        ('obsolete_terminal_cap',0xcc80,literal_reveal_cap(True,True)),('obsolete_private_decoder',0xe1a0,decoder(True,(0xf0cf0,0xf0d98,0xec644),True))]
    ranges=[dict(name=name,start=off,end=off+fingerprint(code,off),replacement=b'',alias=None)for name,off,code in functions]
    # Exact old sorted326 descriptor is a strict subset of active328 records.
    table=old[0xa40:0xa40+326*12];active=old[0xcf20:0xcf20+328*12]
    oldentries=list(struct.iter_unpack('<Iff',table));newentries=list(struct.iter_unpack('<Iff',active))
    if len(oldentries)!=326 or any(x not in newentries for x in oldentries)or old[0xa40+326*12:0x1990]!=bytes(8):raise ValueError('Superseded resident table differs')
    ranges.append(dict(name='obsolete_326_descriptor',start=0xa40,end=0x1990,replacement=b'',alias=None))
    # Original .13 ledger used only by the superseded center above. All incoming
    # references from surviving instructions are rejected by the graph below.
    ranges.append(dict(name='obsolete_ruby_ledger',start=0xb4d0,end=0xbe80,replacement=b'',alias=None))
    canonical=0x7ae0;pattern=old[canonical:canonical+524]
    for off in (0x9780,0xa920,0xad80,0xc410):
        if old[off:off+524]!=pattern or old[off+524:off+528]!=bytes(4):raise ValueError('Integer LUT not identical/padded')
        ranges.append(dict(name='duplicate_body_integer_lut',start=off,end=off+528,replacement=b'',alias=canonical))
    bankstart=before['high_bank']-START;packed=old[bankstart:bankstart+before['font_compressed_bytes']]
    bank=decode(packed,before['high_bank_bytes']);newpacked=encode(bank)
    if len(newpacked)!=20268 or sha(newpacked)!='808b5e9dd52d9822fd2fca9212003378b7f344a848c81cc12913a0feb9e80086' or decode(newpacked,len(bank))!=bank:raise ValueError('Exact lossless HC font model differs')
    ranges.append(dict(name='lossless_lz4_higher_match_search',start=bankstart,end=bankstart+24800,replacement=newpacked+bytes((-len(newpacked))%16),alias=bankstart))
    # Execute the unchanged persisted MIPS decoder on the complete new stream.
    scope=instruction_model();regs=[0]*32;regs[4]=0x200000;regs[5]=len(newpacked);regs[6]=0x300000;regs[7]=len(bank);regs[31]=0xdeadbeec
    memory={0x200000+n:b for n,b in enumerate(newpacked)}
    pc,out,reads=scope['execute'](decompress(),regs,memory)
    if pc!=0xdeadbeec or out[2]!=1 or bytes(memory[0x300000+n]for n in range(len(bank)))!=bank:raise ValueError('Persisted decoder failed complete HC bank')
    if any(not(0x200000<=x<0x200000+len(newpacked)or 0x300000<=x<0x300000+len(bank))for x in reads):raise ValueError('HC decoder read outside exact buffers')
    decoder_proof=dict(actual_emitted_instructions_executed=True,compressed_bytes=len(newpacked),decoded_bytes=len(bank),all_reads_within_exact_buffers=True,decoded_sha256=sha(bank),passed=True)
    ranges.sort(key=lambda x:x['start'])
    if any(a['end']>b['start']for a,b in zip(ranges,ranges[1:])):raise ValueError('Overlapping reclamation ranges')
    def member(off):return next((x for x in ranges if x['start']<=off<x['end']),None)
    def mapped(address):
        if not START<=address<START+len(old):return address
        off=address-START;item=member(off)
        if item:
            if item['alias'] is None:raise ValueError('Surviving reference into obsolete range '+item['name']+' '+hex(address))
            delta=off-item['start']
            if item['name']=='duplicate_body_integer_lut'and delta>=524:raise ValueError('Reference into duplicate LUT alignment padding')
            if item['replacement'] and delta>=len(item['replacement']):raise ValueError('Reference into replaced font tail')
            return mapped(START+item['alias'])+delta if item['alias']!=item['start'] else START+off+sum(len(x['replacement'])-(x['end']-x['start'])for x in ranges if x['end']<=off)
        return address+sum(len(x['replacement'])-(x['end']-x['start'])for x in ranges if x['end']<=off)
    def mapped_site(off,flags):return mapped(START+off)-START if flags>>8&255==2 else off
    # Walk actual injected control flow from every native R26 entry. Direct
    # calls/jumps and local conditional branches include delay-slot reads.
    # This rules out unrelocated branch/fallthrough entry into deleted blocks.
    roots=[]
    for off,f in records:
        if f>>8&255==0 and f&255==4:
            word=struct.unpack_from('<I',original,ph[0][1]+off)[0];target=(word&0x3ffffff)*4+ph[f>>16&255][2]
            if START<=target<START+len(old):roots.append(target-START)
    todo=list(roots);visited=set();branch_edges=0
    def enqueue(off):
        if not 0<=off<len(old):return
        if off%4:raise ValueError('Unaligned injected control flow')
        item=member(off)
        if item and item['name']!='lossless_lz4_higher_match_search':raise ValueError('Active control flow enters reclaimed range '+item['name'])
        if item:raise ValueError('Active code enters compressed font data')
        if off not in visited:todo.append(off)
    while todo:
        off=todo.pop()
        if off in visited:continue
        enqueue(off);visited.add(off)
        word=struct.unpack_from('<I',old,off)[0];op=word>>26;sv=struct.unpack('<h',struct.pack('<H',word&65535))[0]
        special=op in (1,2,3,4,5,6,7,20,21,22,23)or(op==17 and word>>21&31==8)or(op==0 and word&63 in(8,9))
        if special:
            enqueue(off+4);visited.add(off+4)
            if op in (2,3):
                enqueue((word&0x3ffffff)*4-START)
                if op==3:enqueue(off+8)
            elif op==0:
                if word>>21&31!=31:raise ValueError('Injected indirect jump requires target proof')
            else:enqueue(off+4+sv*4);enqueue(off+8);branch_edges+=1
        else:enqueue(off+4)
    alias_tests=0
    for item in ranges:
        if item['name']=='duplicate_body_integer_lut':
            for delta in (0,4,520):
                if mapped(START+item['start']+delta)!=mapped(START+canonical)+delta:raise ValueError('LUT alias offset differs')
                alias_tests+=1
            for delta in (524,527):
                try:mapped(START+item['start']+delta)
                except ValueError:alias_tests+=1
                else:raise ValueError('Duplicate LUT padding accepted')
    payload=bytearray();last=0
    for item in ranges:payload.extend(old[last:item['start']]);payload.extend(item['replacement']);last=item['end']
    payload.extend(old[last:]);prefix=bytearray(original[:0x508880]);kept=[];removed=[];changes=[];skip=set()
    def read(off,f):return struct.unpack_from('<I',original,ph[f>>8&255][1]+off)[0]
    def put(off,f,value):
        s=f>>8&255;target=payload if s==2 else prefix;where=mapped_site(off,f)if s==2 else ph[s][1]+off
        struct.pack_into('<I',target,where,value)
    for n,(off,f)in enumerate(records):
        s=f>>8&255;t=f>>16&255;typ=f&255
        if s==2 and member(off):removed.append((off,f));continue
        kept.append((mapped_site(off,f),f))
        if n in skip:continue
        w=read(off,f)
        if typ==2:a=w
        elif typ==4:a=(w&0x3ffffff)*4
        elif typ==5:
            q=next(k for k in range(n+1,len(records))if records[k][1]&255==6);oo,ff=records[q];lo=read(oo,ff)
            a=((w&65535)<<16)+struct.unpack('<h',struct.pack('<H',lo&65535))[0]
        elif typ==6:continue
        else:raise ValueError('Unknown relocation')
        targetbase=ph[t][2];absolute=a+targetbase;new=mapped(absolute)-targetbase
        if new!=a:
            if typ==2:put(off,f,new)
            elif typ==4:put(off,f,(w&0xfc000000)|(new>>2))
            else:
                if q!=n+1 or ff>>16&255!=t:raise ValueError('Changed nonadjacent/different-target HI/LO')
                put(off,f,(w&0xffff0000)|((new+0x8000)>>16&65535));put(oo,ff,(lo&0xffff0000)|(new&65535));skip.add(q)
            changes.append(dict(segment=s,old_site=off,new_site=mapped_site(off,f),type=typ,old_resolved_rva=absolute,new_resolved_rva=mapped(absolute),target_segment=t))
            if typ==5:changes[-1].update(lo_site=oo,lo_segment=ff>>8&255)
    # Loader pairs each HI with the next LO in relocation order. Removing only
    # half a pair could corrupt a surviving address even if its HI was dead.
    paired_lows=set();pair_checks=0
    for n,(off,f)in enumerate(records):
        if f&255!=5:continue
        q=next(k for k in range(n+1,len(records))if records[k][1]&255==6)
        if ((off,f)in removed)!=(records[q]in removed):raise ValueError('Removed HI/live LO or live HI/removed LO')
        paired_lows.add(q);pair_checks+=1
    unpaired_lows=[n for n,(_,f)in enumerate(records)if f&255==6 and n not in paired_lows]
    # Native standalone LO records never came from the generated payload.
    # Keep their original sites/target/raw words and compare loaded words below.
    for n in unpaired_lows:
        off,f=records[n]
        if f>>8&255==2 or (off,f)in removed or mapped_site(off,f)!=off or read(off,f)!=struct.unpack_from('<I',prefix,ph[f>>8&255][1]+off)[0]:raise ValueError('Changed standalone LO requires independent address proof')
    # The one intentional scalar code difference is compressed input length.
    h=before['font_hooks'];expected,_=initialize(START+0x500,before['font_runtime_state_rva'],before['high_bank'],24790,193024,h['decompressor'])
    if old[h['initializer']-START:h['initializer']-START+len(expected)]!=expected:raise ValueError('Frozen initializer code differs')
    newinit,initrel=initialize(START+0x500,mapped(before['font_runtime_state_rva']),mapped(before['high_bank']),len(newpacked),193024,mapped(h['decompressor']))
    initoff=mapped(h['initializer'])-START;scalar_changes=[]
    transformed=bytes(payload[initoff:initoff+len(newinit)])
    for n,(a,b)in enumerate(zip(struct.iter_unpack('<I',transformed),struct.iter_unpack('<I',newinit))):
        if a!=b:scalar_changes.append(dict(old_site=h['initializer']-START+n*4,new_site=initoff+n*4,expected_word=a[0],replacement_word=b[0]))
    if len(scalar_changes)!=1 or scalar_changes[0]['expected_word']&65535!=24790 or scalar_changes[0]['replacement_word']&65535!=20268 or scalar_changes[0]['expected_word']>>16!=scalar_changes[0]['replacement_word']>>16:raise ValueError('Unexpected initializer scalar/code difference')
    payload[initoff:initoff+len(newinit)]=newinit
    # Identity of all retained, non-relocated bytes proves this is a compaction,
    # not an unreported native or active-function rewrite.
    relocation_bytes=set()
    for off,f in records:
        if (off,f)not in removed and f>>8&255==2:relocation_bytes.update(range(off,off+4))
    scalar_bytes={x for item in scalar_changes for x in range(item['old_site'],item['old_site']+4)}
    identity_checks=0
    for off,value in enumerate(old):
        if member(off)or off in relocation_bytes or off in scalar_bytes:continue
        if payload[mapped(START+off)-START]!=value:raise ValueError('Retained non-relocation payload byte changed')
        identity_checks+=1
    native_masked=bytearray(original[:0x508880])
    for x in changes:
        if x['segment']==0:
            off=ph[0][1]+x['old_site'];native_masked[off:off+4]=prefix[off:off+4]
        if x['type']==5 and x['lo_segment']==0:
            off=ph[0][1]+x['lo_site'];native_masked[off:off+4]=prefix[off:off+4]
    if native_masked!=prefix:raise ValueError('Unreported original LOAD0/file-prefix byte change')
    rel=b''.join(struct.pack('<II',*x)for x in kept)
    pf=align(len(prefix),64);prefix.extend(bytes(pf-len(prefix)));prefix.extend(payload);rf=align(len(prefix),16);prefix.extend(bytes(rf-len(prefix)));prefix.extend(rel)
    native_bytes=71807*8;cursor=0;payloadsection=next(n for n,s in enumerate(sections)if s[3]==START and s[4]==ph[2][1])
    for s in sections:
        if s[1]==0x700000a0:
            if cursor<native_bytes:s[4]=rf+cursor;cursor+=s[5]
            else:s[4]=rf+native_bytes;s[5]=0
        elif s[3]==START and s[4]==ph[2][1]:s[4]=pf;s[5]=len(payload)
    if cursor!=native_bytes:raise ValueError('Original relocation partition changed')
    sections.append([0,0x700000a0,0,0,rf+native_bytes,len(rel)-native_bytes,0,payloadsection,4,8])
    newsh=align(len(prefix),4);prefix.extend(bytes(newsh-len(prefix)))
    for s in sections:prefix.extend(struct.pack('<10I',*s))
    ph[2][1]=pf;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=rf;ph[3][4]=len(rel)
    for n,p in enumerate(ph):struct.pack_into('<8I',prefix,po+n*32,*p)
    struct.pack_into('<I',prefix,32,newsh);struct.pack_into('<H',prefix,48,len(sections))
    checks=0
    for base in (0x8804000,0x8900000,0x8fff000):
        olds,_,lows=loaded(original,base);news,_,_=loaded(prefix,base)
        if news[1]!=olds[1]:raise ValueError('Native LOAD1 changed')
        for n,(off,f)in enumerate(records):
            if (off,f)in removed:continue
            s=f>>8&255;typ=f&255;ow=struct.unpack_from('<I',olds[s],off)[0];nw=struct.unpack_from('<I',news[s],mapped_site(off,f))[0]
            if typ==2:x,y=ow,nw
            elif typ==4:x,y=(ow&0x3ffffff)*4,(nw&0x3ffffff)*4
            elif typ==5:
                oo,ff=records[lows[n]];ss=ff>>8&255
                ol=struct.unpack_from('<I',olds[ss],oo)[0];nl=struct.unpack_from('<I',news[ss],mapped_site(oo,ff))[0]
                x=((ow&65535)<<16)+struct.unpack('<h',struct.pack('<H',ol&65535))[0];y=((nw&65535)<<16)+struct.unpack('<h',struct.pack('<H',nl&65535))[0]
            elif typ==6:
                if n not in unpaired_lows:continue
                if ow!=nw:raise ValueError('Inherited standalone LO loaded word changed')
                checks+=1;continue
            else:continue
            if y!=base+mapped(x-base):raise ValueError('Loaded active pointer mismatch '+hex(off))
            checks+=1
    def metadata(v,key=''):
        if isinstance(v,dict):return {k:metadata(x,k)for k,x in v.items()}
        if isinstance(v,list):return [metadata(x,key)for x in v]
        if type(v)==int:
            if key=='stored_offset':return mapped(START+v)-START
            return mapped(v)
        if isinstance(v,str)and v.startswith('0x'):
            try:a=int(v,16)
            except ValueError:return v
            return hex(mapped(a))
        return v
    current_keys=['high_bank','high_bank_bytes','high_glyph_count','high_codes','high_glyph_offsets','high_lookup_entry_bytes','high_lookup_unit','font_input_sha256','font_asset_sha256','high_bank_sha256','high_lookup_rva','font_runtime_storage','high_bank_address_kind','font_compressed_bytes','font_compressed_sha256','font_runtime_state_rva','font_codec_model','font_raster_sha256','font_hooks','font_descriptor','default_name_storage','setup_fields','setup_conversion','osk','strings','scoped_executable_ui','scoped_tutorial_quest_ui','ruby_current_snapshot']
    report=metadata({k:copy.deepcopy(before[k])for k in current_keys})
    report.update(version='0.1.17',input_version='0.1.16',input_sha256=SHA,status='dry_dead_payload_recovery_candidate',runtime_verified=False,
        output_elf_sha256=sha(prefix),output_sha256=sha(prefix),elf_bytes=len(prefix),payload_bytes=len(payload),module_growth_bytes=len(payload),
        total_relocations=len(kept),original_relocations=71807,added_relocations=len(kept)-71807,relocation_table_sha256=sha(rel),font_compressed_bytes=len(newpacked),font_compressed_sha256=sha(newpacked),
        font_compression_variant='lz4_hc1024_v1',
        input_build_history=dict(scope='Frozen .16 historical reports only; old addresses/proofs are not current active metadata.',report=before),
        payload_recovery=dict(bytes=len(old)-len(payload),ranges=[dict(name=x['name'],old_range=[START+x['start'],START+x['end']],old_bytes=x['end']-x['start'],new_bytes=len(x['replacement']),alias_old_rva=None if x['alias']is None else START+x['alias'],old_sha256=sha(old[x['start']:x['end']]))for x in ranges],
            removed_relocations=removed,address_changes=changes,loaded_pointer_comparisons=checks,loaded_bases=[0x8804000,0x8900000,0x8fff000],original_LOAD1_exact=True,
            hi_lo_pair_checks=pair_checks,removed_pair_halves_consistent=True,inherited_standalone_lo_records=len(unpaired_lows),standalone_lo_loaded_comparisons=len(unpaired_lows)*3,native_LOAD0_only_reported_pointer_changes=True,
            surviving_nonrelocation_byte_comparisons=identity_checks,initializer_scalar_changes=scalar_changes,duplicate_lut_semantic_bytes=524,duplicate_lut_padding_references_rejected=True,alias_semantic_and_padding_tests=alias_tests,
            injected_control_flow_roots=len(roots),reachable_instruction_words=len(visited),conditional_branch_edges=branch_edges,no_active_relative_branch_or_fallthrough_into_removed_ranges=True,
            scalar_initializer_change='Only compressed input length24790 ->20268; original initializer ABI/control flow preserved.',decoded_bank_sha256=sha(bank),decoded_bank_unchanged=True,decoder_proof=decoder_proof),
        memory_forecast=dict(additional_recovery_bytes=len(old)-len(payload),total_recovery_vs_015=217152-len(payload),observed_fpl_deficit=133376,margin_before_movie=217152-len(payload)-133376,
            observed_movie_prx_request=10752,margin_after_one_observed_movie_request=217152-len(payload)-133376-10752,other_movie_allocations_unverified=True),
        limitations=['Movie/battle total heap requirements unverified; recovered margin is a forecast.','Only exact generated dead functions, obsolete table/ledger and identical LUTs removed; all surviving pointer references reject removed storage.'])
    report['scoped_executable_ui']['inherited_font_payload_prefix_exact']=False
    report['scoped_tutorial_quest_ui']['inherited_payload_prefix_exact']=False
    report['scoped_executable_ui']['preservation_proof']='payload_recovery loaded address semantics and surviving non-relocated byte identity'
    report['scoped_tutorial_quest_ui']['preservation_proof']='payload_recovery loaded address semantics and surviving non-relocated byte identity'
    report['runtime_font_bank_pointer_source']=dict(state_rva=report['font_runtime_state_rva'],pointer_word_offset=0,status_word_offset=4,ready_status=3,decoded_bytes=193024,static_texture_rva=None,runtime_verified=False)
    # Their old byte-replacement annotations are historical .16 proof, whereas
    # the current pointer records/RVAs above are remapped active metadata.
    report['scoped_tutorial_quest_ui'].pop('native_instruction_changes',None)
    report['scoped_tutorial_quest_ui']['current_instruction_sites']=[dict(site=x['site'],current_hex=bytes(prefix[x['site']+192:x['site']+192+len(bytes.fromhex(x['replacement_hex']))]).hex())for x in before['scoped_tutorial_quest_ui']['native_instruction_changes']]
    report['scoped_executable_ui']['font_input_candidate_sha256']=SHA
    from build_local import authoritative_font_metadata
    authoritative_font_metadata(bytes(prefix),report)
    return bytes(prefix),report


if __name__=='__main__':
    data,report=build();print(json.dumps(report,indent=2));print('Canonical dry report SHA256:',sha(json.dumps(report,sort_keys=True,separators=(',',':')).encode()));print('DRY ONLY: no executable/ISO writer exists in this tool.')

