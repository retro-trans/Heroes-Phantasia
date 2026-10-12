"""Pure first78 native menu candidate from frozen24; no executable writer."""
import argparse, copy, json, struct
from pathlib import Path
from native_menu_install_plan import build as menu_plan, SOURCE, SOURCE_SHA, sha, canonical, cstring
from executable_text_patch import Elf, ORIGINAL, ORIGINAL_SHA
from prepare_relocation_019 import sections, section_load, coverage, pair_shapes
from compact_vwf_patch import loaded
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

PLAN_SHA='4c8a7a4f4f8ee0faecc802403498c163b93d6540c5284b4ad66a999b3bcc1dc3'

def literal_getter_cases(elf):
    """Prove only straight-line constant table/index setup, not dynamic owners."""
    cases=[]
    for site in range(0,2703284,4):
        if elf.word(site)!=0x0c000000|(0x877f4>>2):continue
        values={};sites={}
        # Delay instruction executes before the callee; then inspect preceding
        # writes backwards, stopping at the first intervening control transfer.
        sequence=[site+4]+list(range(site-4,max(-1,site-52),-4))
        for address in sequence:
            word=elf.word(address);op=word>>26;rs=word>>21&31;rt=word>>16&31;rd=word>>11&31
            if op in(1,2,3,4,5,6,7,20,21,22,23)or op==0 and word&63 in(8,9):break
            if op in(28,31):break # Unmodeled SPECIAL2/3 register effects.
            destination=rd if op==0 else rt if op in(8,9,10,11,12,13,14,15,32,33,34,35,36,37,38,48,56)or op in(16,17)and rs in(0,2)else None
            if destination not in(5,6)or destination in values:continue
            value=None
            if op in(9,13)and rs==0:value=word&65535
            elif op==0 and word&63 in(33,37)and rs==rt==0:value=0
            values[destination]=value;sites[destination]=address
        if values.get(5)==0 and isinstance(values.get(6),int):
            cases.append(dict(index=values[6],getter_site=site,constant_setup_sites=sites,
                instruction_words={str(a):elf.word(a)for a in sites.values()},
                scope='Constant table0/index proof only; returned pointer consumer/layout is not inferred.'))
    return cases

def validate(data, report, incoming, before, selected):
    elf=Elf(data);old=Elf(incoming);coverage(data)
    if elf.relocs!=old.relocs or pair_shapes(data)!=pair_shapes(incoming):raise ValueError('Inherited relocation/pair contract differs')
    for e in selected:
        raw=e['target'].encode('ascii')+b'\0'
        if elf.word(e['pointer_slot'])!=e['target_rva']or cstring(elf,e['target_rva'])!=raw:raise ValueError('New menu pointer/complete string differs')
    for e in before['gallery_current_entries']:
        if elf.word(e['pointer_slot'])!=e['target_rva']or cstring(elf,e['target_rva'])!=e['target'].encode('ascii')+b'\0':
            raise ValueError('Inherited25 gallery pointer/string differs')
    trailer=before['font_trailer_offset'];end=before['font_compressed_file_offset']+before['font_compressed_bytes']
    if data[trailer:end]!=incoming[trailer:end]:raise ValueError('Font trailer bytes/offset differ')
    authoritative_font_metadata(data,report);png=validate_native_png_metadata(data,report)
    mask={b for e in selected for b in range(e['pointer_slot'],e['pointer_slot']+4)};models=[]
    for base in(0x08804000,0x08900000,0x08fff000):
        oldmem,_,_,_=section_load(incoming,base);mem,visited,skipped,_=section_load(data,base);ph,_,_=loaded(data,base)
        if ph!=[mem[n][:elf.ph[n][4]]for n in range(3)]or visited!=elf.relocs or skipped:raise ValueError('PH versus actual SHT loader differs')
        if oldmem[1]!=mem[1]or oldmem[2]!=mem[2][:len(oldmem[2])]:raise ValueError('Inherited LOAD1/2 memory differs')
        if any(a!=b and i not in mask for i,(a,b)in enumerate(zip(oldmem[0],mem[0]))):raise ValueError('Unselected LOAD0 memory differs')
        for e in selected:
            if struct.unpack_from('<I',mem[0],e['pointer_slot'])[0]!=base+e['target_rva']:raise ValueError('Actual SHT selected pointer differs')
        models.append(dict(base=base,records=len(visited),selected_pointers=78,PH_SHT_equal=True,unselected_loaded_memory_exact=True))
    return dict(actual_loader_models=models,all25_gallery_pointers_strings_exact=True,font_trailer_bytes_offset_exact=True,
        authoritative_font_metadata_passed=True,native_PNG_full_triples=png)

def build():
    plan=menu_plan()
    if canonical(plan)!=PLAN_SHA:raise ValueError('Root-reviewed menu source/queue/code snapshot changed')
    incoming=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('executable.en.json').read_bytes());elf=Elf(incoming)
    original=ORIGINAL.read_bytes()
    if sha(original)!=ORIGINAL_SHA or sha(incoming)!=SOURCE_SHA:raise ValueError('Original/frozen24 input hash differs')
    oldfont=authoritative_font_metadata(incoming,before);ss=sections(incoming);selected=plan['first78'];payload=bytearray(incoming[elf.ph[2][1]:elf.ph[2][1]+elf.ph[2][4]])
    extent=elf.ph[2][2]+len(payload)
    for e in selected:
        if e['storage']=='append_LOAD2_string':
            raw=e['target'].encode('ascii')+b'\0';off=e['target_rva']-extent
            if off==len(payload)-elf.ph[2][4]:payload.extend(raw)
            elif payload[e['target_rva']-elf.ph[2][2]:e['target_rva']-elf.ph[2][2]+len(raw)]!=raw:
                raise ValueError('Dedup sequential payload plan differs')
    if len(payload)!=4446 or sha(payload[3568:])!=plan['first78_storage']['payload_sha256']:raise ValueError('Exact878B text payload differs')
    ph=[list(p)for p in elf.ph];result=bytearray(incoming);changes=[];allowed=set()
    for e in selected:
        p=elf.file_offset(e['pointer_slot'],4)
        if elf.word(e['pointer_slot'])!=e['expected_word']or elf.relocs[e['relocation_ordinal']]!=(e['pointer_slot'],2):raise ValueError('Expected selected word/R32 differs')
        struct.pack_into('<I',result,p,e['target_rva']);allowed.update(range(p,p+4));changes.append(dict(site=e['pointer_slot'],expected=e['expected_word'],replacement=e['target_rva']))
    alignment=ph[2][7];pf=len(result)+((ph[2][2]-len(result))%alignment)
    result.extend(bytes(pf-len(result)));result.extend(payload)
    ph[2][1]=pf;ph[2][4]=ph[2][5]=len(payload)
    ss[55][4]=pf;ss[55][5]=len(payload)
    newsh=(len(result)+3)&~3;result.extend(bytes(newsh-len(result)))
    for section in ss:result.extend(struct.pack('<10I',*section))
    phoff=struct.unpack_from('<I',incoming,28)[0];struct.pack_into('<8I',result,phoff+64,*ph[2]);allowed.update(range(phoff+64,phoff+96))
    struct.pack_into('<I',result,32,newsh);allowed.update(range(32,36));result=bytes(result)
    if any(a!=b and i not in allowed for i,(a,b)in enumerate(zip(incoming,result))):raise ValueError('Unselected inherited file bytes changed')
    if (pf-ph[2][2])%alignment or Elf(result).ph[:2]!=elf.ph[:2]or Elf(result).ph[3]!=elf.ph[3]:raise ValueError('PH alignment/unselected program headers differ')
    floats=struct.unpack('<131f',incoming[elf.file_offset(before['float_width_lut_rva'],524):elf.file_offset(before['float_width_lut_rva'],524)+524])
    literal_cases=literal_getter_cases(elf)
    for e in selected:
        e.update(estimated_16px_width=sum(floats[ord(c)]for c in e['target']),individual_draw_consumer_verified=False,
            proved_constant_getter_cases=[c for c in literal_cases if c['index']==e['native_index']],
            layout_QA_pending=True,consumer_note='Source table ownership proved; generic descriptor-to87C18 route proved, individual descriptor membership/copy/centering not established.')
    # Concrete descriptor route passes returned table0 pointer directly to generic draw, no text copy here.
    originalelf=Elf(original);a,b=0x77b7c,0x77be4;raw=incoming[elf.file_offset(a):elf.file_offset(b)]
    if raw!=original[originalelf.file_offset(a):originalelf.file_offset(b)]or elf.word(0x77b9c)!=0x0c000000|(0x877f4>>2)or elf.word(0x77bdc)!=0x0c000000|(0x87c18>>2):
        raise ValueError('Native descriptor table0 draw chain changed')
    report=copy.deepcopy(before);report.update(version='0.1.25',status='pure_native_menu_candidate_consumer_layout_pending',input_sha256=SOURCE_SHA,
        input_version='0.1.24',output_elf_sha256=sha(result),output_sha256=sha(result),elf_bytes=len(result),payload_bytes=4446,module_growth_bytes=4480,
        font_native_tail_loaded_extension_bytes=4446,font_native_tail_loaded_extension_sha256=sha(payload),runtime_verified=False)
    report['native_menu_input_history']=dict(source=str(SOURCE),predecessor_status=before.get('status'),predecessor_approved_plan=before.get('approved_dry_plan_sha256'),note='Inherited technical/runtime proofs are historical.78 new menu labels are not display verified.')
    for k in('output','approved_dry_plan_sha256','written_readback_verified'):report.pop(k,None)
    report['memory_forecast']['proposed_module_bytes']=24091392+4480
    report['memory_forecast']['forecast_after_both_requests']-=896
    report['memory_forecast']['first78_menu_increment_conservative64_alignment']=896
    checks=validate(result,report,incoming,before,selected)
    newfont=authoritative_font_metadata(result,report)
    deltas={k:[oldfont.get(k),newfont.get(k)]for k in set(oldfont)|set(newfont)if oldfont.get(k)!=newfont.get(k)}
    if set(deltas)-{'font_native_tail_loaded_extension_bytes','font_native_tail_loaded_extension_sha256'}:raise ValueError('Unexpected authoritative font metadata difference')
    proof=dict(input_plan_sha256=PLAN_SHA,input_sha256=SOURCE_SHA,entries=selected,native_words=changes,payload_bytes=878,loaded_growth_bytes=896,new_relocations=0,
        old_LOAD2_prefix_exact=True,new_LOAD2_file_offset=pf,new_LOAD2_file_bytes=4446,physical_congruence_alignment=alignment,
        PH3_SHT_relocation_bytes_and_pair_semantics_exact=True,all_inherited_file_bytes_exact_except78R32_PH2_shoff=True,
        font_metadata_delta=deltas,checks=checks,
        descriptor_route=dict(start=a,end=b,sha256=sha(raw),getter_site=0x77b9c,draw_site=0x77bdc,table=0,index_source='LHU[descriptor+18]',alignment=0,width=13,local_text_copy=False),
        individual78_consumer_and_layout_QA_pending=True,assets_written=False,runtime_verified=False)
    proof['first78_with_proved_constant_getter_setup']=sum(bool(e['proved_constant_getter_cases'])for e in selected)
    report['native_menu_candidate']=proof
    negative=[]
    cases=[('wrong_selected_R32',elf.file_offset(selected[0]['pointer_slot'],4),selected[0]['target_rva']+1),
        ('invalid_loaded_relocation_gate',newsh+1*40+8,0),('truncated_LOAD2_extent',phoff+64+16,4445)]
    for name,offset,value in cases:
        bad=bytearray(result);struct.pack_into('<I',bad,offset,value)
        try:validate(bytes(bad),report,incoming,before,selected)
        except ValueError as exc:negative.append(dict(case=name,rejected=True,reason=str(exc)))
        else:raise ValueError('Negative model unexpectedly passed:'+name)
    bad=bytearray(result);bad[before['font_compressed_file_offset']]^=1
    try:validate(bytes(bad),report,incoming,before,selected)
    except ValueError as exc:negative.append(dict(case='changed_unloaded_font_packet',rejected=True,reason=str(exc)))
    else:raise ValueError('Changed unloaded font packet passed')
    proof['actual_negative_guards']=negative
    proof['code_input_sha256']={str(p):sha(p.read_bytes())for p in(Path(__file__),Path('tools/native_menu_install_plan.py'),Path('tools/compact_vwf_patch.py'),Path('tools/build_local.py'),Path('tools/prepare_relocation_019.py'))}
    return result,report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path);a=p.parse_args();data,r=build()
    proof=r['native_menu_candidate'];print(json.dumps({k:v for k,v in proof.items()if k not in('entries','native_words')},indent=2));print('SAMPLE',json.dumps(proof['entries'][:5],indent=2));print('ELF SHA256',sha(data));print('CANONICAL PLAN SHA256',canonical(r))
    if a.report:
        if a.report.exists()or not a.report.resolve().is_relative_to(Path('work/source').resolve()):raise ValueError('Fresh ignored report required')
        a.report.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    print('DRY: no executable assets, ISO, encoder, runtime or frozen builder changes.')
