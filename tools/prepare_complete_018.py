"""Pure .18 composition and exact-reviewed-hash writer. No ISO/emulator actions."""
import argparse,copy,json,pathlib,struct
from prepare_native_font_018 import build as native_build,sha
from warning_scope import build as warning_build
from notification_scope import payload as notification_payload,plan as notification_plan
from notification_auxiliary_scope import payload as auxiliary_payload,plan as auxiliary_plan
from cpl_resident_names import build_table,hud_lookup
from png_tail_allocate import plan as tail_plan
from build_menu_patch import align,relocate_code,START
from executable_text_patch import Elf
from compact_vwf_patch import loaded
from live_vwf import j

ROOT=pathlib.Path('work/output/0.1.18-dialogue-assets')

def canonical(report):return sha(json.dumps(report,sort_keys=True,separators=(',',':')).encode())

def build():
    native,native_report=native_build()
    incoming,report=warning_build(native,native_report,lut_rva=native_report['body_integer_lut_rva'])
    elf=Elf(incoming);table,pairs,cpl_proof=build_table();bank,_=notification_payload()
    # Table contains relative offsets. Place helper at a separately aligned
    # address in the same bounded image tail; typed code addresses use LOAD0.
    codeoff=align(len(table),16)
    voices,format_data,_=auxiliary_payload()
    reservations=tail_plan(report,[dict(name='CPL_exact_names_and_HUD_lookup',data=table+bytes(codeoff-len(table))+bytes(len(hud_lookup(0))),alignment=16),dict(name='Gold_numeric_NUL_helper',data=bytes(16),alignment=4),dict(name='34_cast_name_positions',data=voices,alignment=4),dict(name='notification_format8',data=format_data,alignment=4)])
    cpl,gold,cast,format_slot=reservations['patches'];table_rva=cpl['rva'];helper_rva=table_rva+codeoff
    bankoff=align(elf.ph[2][4],16);bank_rva=START+bankoff
    _,_,auxiliary_proof=auxiliary_plan(incoming,report,cast['rva'],format_slot['rva'])
    prefix=bytearray(incoming);payload=bytearray(incoming[elf.ph[2][1]:elf.ph[2][1]+elf.ph[2][4]])
    for reservation in reservations['patches']:
        prefix[reservation['file_offset']:reservation['file_offset']+reservation['bytes']]=reservation['data']
    payload.extend(bytes(bankoff-len(payload)));payload.extend(bank)
    rels=list(elf.relocs);added=[];changes=[]
    def patch(site,expected,value,reason):
        off=elf.file_offset(site,4)
        if struct.unpack_from('<I',prefix,off)[0]!=expected:raise ValueError('Native guard differs: '+hex(site))
        struct.pack_into('<I',prefix,off,value);changes.append(dict(site=site,expected_word=expected,replacement_word=value,reason=reason))
    def code_at(code,rva):
        buf=bytearray(code)
        generated=list(struct.iter_unpack('<II',b''.join(relocate_code(buf,0,len(buf)))))
        for off,f in generated:added.append((rva+off,f&~0xff00))
        off=elf.file_offset(rva,len(buf));prefix[off:off+len(buf)]=buf
        return bytes(buf)
    for row in auxiliary_proof['native_writes']:patch(row['rva'],row['expected_word'],row['replacement_word'],'typed cast name or notification format8')
    shadow=copy.deepcopy(report);shadow['output_elf_sha256']=sha(prefix)
    bank,gold_code,notification_proof=notification_plan(bytes(prefix),shadow,bank_rva,gold['rva'])
    off=elf.file_offset(table_rva,len(table));prefix[off:off+len(table)]=table
    cpl_code=code_at(hud_lookup(table_rva),helper_rva);gold_raw=code_at(gold_code,gold['rva'])
    if incoming[elf.file_offset(0xb06c4,8):elf.file_offset(0xb06c4,8)+8]!=bytes.fromhex('1200043425280002'):raise ValueError('Native HUD lookup replay guard differs')
    patch(0xb06c4,elf.word(0xb06c4),j(helper_rva),'exact CP932-to-English HUD name lookup')
    patch(0xb06c8,elf.word(0xb06c8),0,'HUD lookup jump delay')
    if any(site==0xb06c4 for site,_ in rels):raise ValueError('HUD native entry already relocated')
    added.append((0xb06c4,4))
    for row in notification_proof['native_writes']:patch(row['rva'],row['expected_word'],row['replacement_word'],'typed notification bank or Gold terminator')
    if any(site==0x81074 for site,_ in rels):raise ValueError('Gold native entry already relocated')
    added.append((0x81074,4));rels.extend(added)
    if len(set(rels))!=len(rels):raise ValueError('Duplicate added relocation')
    po,so=struct.unpack_from('<II',incoming,28);ph=[list(x)for x in elf.ph]
    sections=[list(struct.unpack_from('<10I',incoming,so+n*40))for n in range(struct.unpack_from('<H',incoming,48)[0])]
    pf=align(len(prefix),64);prefix.extend(bytes(pf-len(prefix)));prefix.extend(payload)
    rf=align(len(prefix),16);prefix.extend(bytes(rf-len(prefix)));rawrel=b''.join(struct.pack('<II',*x)for x in rels);prefix.extend(rawrel)
    for s in sections:
        if s[1]==0x700000a0:s[4]=rf+s[4]-ph[3][1]
        elif s[3]==START and s[4]==ph[2][1]:s[4]=pf;s[5]=len(payload)
    # The added records follow existing relocation sections, with no change to
    # their order or HI/LO pairing. Describe only the new final suffix here.
    sections.append([0,0x700000a0,0,0,rf+len(elf.relocs)*8,len(added)*8,0,0,4,8])
    newsh=align(len(prefix),4);prefix.extend(bytes(newsh-len(prefix)))
    for s in sections:prefix.extend(struct.pack('<10I',*s))
    ph[2][1]=pf;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=rf;ph[3][4]=len(rawrel)
    for n,p in enumerate(ph):struct.pack_into('<8I',prefix,po+n*32,*p)
    struct.pack_into('<I',prefix,32,newsh);struct.pack_into('<H',prefix,48,len(sections))
    result=bytes(prefix);unselected=bytearray(incoming)
    final=Elf(result)
    def exact_bytes(rva,expected):
        off=final.file_offset(rva,len(expected))
        if result[off:off+len(expected)]!=expected:raise ValueError('Final auxiliary byte range differs')
    exact_bytes(cast['rva'],voices);exact_bytes(format_slot['rva'],format_data);exact_bytes(bank_rva,bank)
    voice_max=0
    for entry in auxiliary_proof['voice_entries']:
        raw=entry['target'].encode('ascii')+b'\0'
        exact_bytes(cast['rva']+entry['payload_offset'],raw);voice_max=max(voice_max,len(raw)-1)
    if voice_max!=auxiliary_proof['voice_max_bytes'] or voice_max!=21:raise ValueError('Final 34-entry cast bound differs')
    for row in changes:
        off=elf.file_offset(row['site'],4);unselected[off:off+4]=result[off:off+4]
    for p in reservations['patches']:unselected[p['file_offset']:p['file_offset']+p['bytes']]=result[p['file_offset']:p['file_offset']+p['bytes']]
    unselected[po:po+128]=result[po:po+128];unselected[32:36]=result[32:36];unselected[48:50]=result[48:50]
    if result[:len(incoming)]!=unselected:raise ValueError('Unselected inherited file bytes differ')
    checks=0
    for base in (0x8804000,0x8900000,0x8fff000):
        before,_,_=loaded(incoming,base);after,_,_=loaded(result,base)
        expected=bytearray(before[0])
        for row in changes:expected[row['site']:row['site']+4]=after[0][row['site']:row['site']+4]
        for p in reservations['patches']:expected[p['rva']:p['rva']+p['bytes']]=after[0][p['rva']:p['rva']+p['bytes']]
        if after[0]!=expected or after[1]!=before[1] or after[2][:len(before[2])]!=before[2]:raise ValueError('Unselected loaded bytes differ')
        for proof in notification_proof['typed_pointer_proofs']:
            hi,lo=proof['sites'];h,l=struct.unpack_from('<I',after[0],hi)[0],struct.unpack_from('<I',after[0],lo)[0]
            resolved=((h&65535)<<16)+struct.unpack('<h',struct.pack('<H',l&65535))[0]
            if resolved!=base+proof['target_rva']:raise ValueError('Notification loaded pointer differs')
            checks+=1
        for entry in auxiliary_proof['voice_entries']:
            value=struct.unpack_from('<I',after[0],entry['site'])[0]
            if value!=base+cast['rva']+entry['payload_offset']:raise ValueError('Loaded cast R32 pointer differs')
            checks+=1
        hi,lo=auxiliary_proof['format_sites'];h,l=struct.unpack_from('<I',after[0],hi)[0],struct.unpack_from('<I',after[0],lo)[0]
        resolved=((h&65535)<<16)+struct.unpack('<h',struct.pack('<H',l&65535))[0]
        if resolved!=base+format_slot['rva']:raise ValueError('Loaded format8 HI/LO pointer differs')
        checks+=1
        for site,f in added:
            typ=f&255;word=struct.unpack_from('<I',after[0],site)[0]
            rawword=struct.unpack_from('<I',result,Elf(result).file_offset(site,4))[0]
            if typ==4 and (word&0x3ffffff)*4!=base+(rawword&0x3ffffff)*4:raise ValueError('New R26 loaded pointer differs')
            if typ==5:
                low=struct.unpack_from('<I',after[0],site+4)[0];rawlow=struct.unpack_from('<I',result,Elf(result).file_offset(site+4,4))[0]
                a=((word&65535)<<16)+struct.unpack('<h',struct.pack('<H',low&65535))[0]
                b=((rawword&65535)<<16)+struct.unpack('<h',struct.pack('<H',rawlow&65535))[0]
                if a!=base+b:raise ValueError('New HI/LO loaded pointer differs')
            checks+=1
    trailer=report['font_trailer_offset'];end=report['font_compressed_file_offset']+report['font_compressed_bytes']
    if result[trailer:end]!=incoming[trailer:end]:raise ValueError('Unloaded font trailer changed')
    report=copy.deepcopy(report);report.update(version='0.1.18',status='dry_complete_native_tail_font_candidate',output_elf_sha256=sha(result),output_sha256=sha(result),elf_bytes=len(result),payload_bytes=len(payload),module_growth_bytes=align(START+len(payload),256)-align(START,256),total_relocations=len(rels),original_relocations=71807,added_relocations=len(rels)-71807,relocation_table_sha256=sha(rawrel),font_native_tail_loaded_extension_bytes=len(payload),font_native_tail_loaded_extension_sha256=sha(payload),runtime_verified=False)
    report['trailer_recovery']['free_tail_regions']=reservations['free_tail_regions'];report['trailer_recovery']['remaining_tail_bytes']=reservations['remaining_bytes']
    report['native_tail_compaction']['proof_scope']='Pure font-only predecessor compaction; current extra tail reservations and LOAD2 growth are additional_scopes. Core chunk addresses/bytes remain exact.'
    report['additional_scopes']=dict(input_elf_sha256=sha(incoming),native_changes=changes,added_relocations=added,loaded_pointer_comparisons=checks,loaded_bases=[0x8804000,0x8900000,0x8fff000],unselected_file_bytes_exact=True,unselected_LOAD0_and_LOAD1_exact=True,inherited_loaded_payload_prefix_exact=True,unloaded_font_trailer_exact=True,tail_reservations=[{k:v for k,v in p.items()if k!='data'}for p in reservations['patches']],CPL=dict(table_rva=table_rva,table_bytes=len(table),table_sha256=sha(table),helper_rva=helper_rva,helper_bytes=len(cpl_code),helper_sha256=sha(cpl_code),original_resources_required=True,proof=cpl_proof),notifications=notification_proof,gold_helper_sha256=sha(gold_raw),runtime_verified=False)
    report['additional_scopes']['cast_and_format8']=auxiliary_proof
    report['additional_scopes']['cast_and_format8'].update(final_voice_blob_exact=True,final_format_blob_exact=True,all34_reconstructed_targets_exact=True,final_voice_max_bytes=voice_max,three_base_pointer_comparisons=105)
    for row in report['additional_scopes']['tail_reservations']:
        row['requested_blob_sha256']=row.pop('sha256')
        row['stored_blob_sha256']=sha(result[row['file_offset']:row['file_offset']+row['bytes']])
    report['memory_forecast'].update(proposed_module_bytes=align(START+len(payload),256),additional_recovery_vs_017=align(START+56740,256)-align(START+len(payload),256),forecast_after_both_requests=23964-report['module_growth_bytes'],all_known_scopes_included=True,actual_contiguous_heap_unmeasured=True)
    report['memory_forecast'].update(actual_warning_loaded_bytes=report['warning_scope']['added_payload_bytes'],actual_notification_loaded_bytes=len(bank),actual_CPL_tail_bytes=cpl['bytes'],actual_Gold_tail_bytes=len(gold_raw),actual_cast_tail_bytes=len(voices),actual_format8_tail_bytes=len(format_data),gold_hook_bytes_unconfirmed=False)
    if report['memory_forecast']['forecast_after_both_requests']<17*1024:raise ValueError('Known-request forecast is below reviewed17KiB floor')
    report['resident_cpl_names']=dict(rows=79,resources=424,original_fallback=True,target_sha256=cpl_proof['target_sha256'],table_rva=table_rva,table_bytes=len(table),table_sha256=sha(table),helper_rva=helper_rva,helper_bytes=len(cpl_code),helper_sha256=sha(cpl_code),hook_site=0xb06c4,hook_bytes=result[elf.file_offset(0xb06c4,8):elf.file_offset(0xb06c4,8)+8].hex(),runtime_verified=False)
    sources=('prepare_complete_018.py','prepare_native_font_018.py','prepare_font_trailer_018.py','font_trailer_hooks.py','font_vram_hooks.py','font_lz4_hc.py','png_lossless_repack.py','png_zopfli_repack.py','png_tail_allocate.py','savedata_tail_proof.py','warning_scope.py','warning_wrap_hooks.py','warning_draw_hooks.py','notification_scope.py','notification_hooks.py','notification_auxiliary_scope.py','cpl_resident_names.py','build_menu_patch.py','compact_vwf_patch.py','build_local.py')
    report['complete_preparation_code_input_sha256']={name:sha((pathlib.Path('tools')/name).read_bytes())for name in sources}
    from build_local import authoritative_font_metadata
    authoritative_font_metadata(result,report)
    return result,report

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');parser.add_argument('--expected-report-sha256');parser.add_argument('--expected-elf-sha256');args=parser.parse_args()
    data,report=build();digest=canonical(report)
    print(json.dumps(dict(version=report['version'],elf_sha256=sha(data),canonical_report_sha256=digest,elf_bytes=len(data),payload_bytes=report['payload_bytes'],memory=report['memory_forecast'],CPL=report['additional_scopes']['CPL'],notifications=report['additional_scopes']['notifications']['slots']),indent=2))
    if not args.write:print('DRY ONLY: no executable/ISO written.');return
    if args.expected_report_sha256!=digest or args.expected_elf_sha256!=sha(data):raise ValueError('Writer requires exact reviewed canonical report and ELF hashes')
    if ROOT.exists():raise ValueError('Fresh output folder required')
    ROOT.mkdir(parents=True);target=ROOT/'EBOOT.BIN';target.write_bytes(data)
    if sha(target.read_bytes())!=report['output_elf_sha256']:raise ValueError('Written executable hash differs')
    (ROOT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Wrote isolated executable and preparation report; runtime verification pending.')

if __name__=='__main__':main()
