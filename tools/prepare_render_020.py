"""Pure composition of reviewed Crack Burst and 1A measurement; no ELF writer."""
import argparse,copy,json,struct,hashlib
from pathlib import Path
import prepare_crack_burst_020 as crack
import dialogue_measure_1a as measure
from executable_text_patch import Elf,address_pair
from prepare_relocation_019 import sections,coverage,section_load,pair_shapes
from png_tail_allocate import plan

def sha(data):return hashlib.sha256(data).hexdigest()

def build():
    original=crack.CURRENT.read_bytes();old=Elf(original)
    report=copy.deepcopy(json.loads(crack.CURRENT.with_name('executable.en.json').read_text(encoding='utf8')))
    cracked,cp=crack.build();measured,mp=measure.build();out=bytearray(cracked)
    start=mp['code_rva'];size=mp['new_code_bytes'];offset=old.file_offset(start,size)
    out[offset:offset+size]=measured[offset:offset+size]
    # Keep even the retained historical PHREL copy coherent. Locate complete
    # frozen19 streams, rather than blindly replacing matching 8B words.
    ph=next(p for p in old.ph if p[0]==0x700000a0)
    stream=original[ph[1]:ph[1]+ph[4]];copies=[];pos=0
    while True:
        pos=cracked.find(stream,pos)
        if pos<0:break
        copies.append(pos);pos+=len(stream)
    active=next(p for p in Elf(cracked).ph if p[0]==0x700000a0)
    if ph[1]not in copies or active[1]not in copies:raise ValueError('Inherited/current relocation copy missing')
    for change in mp['moved_existing_relocations']:
        before=struct.pack('<II',*change['old']);after=struct.pack('<II',*change['new'])
        for where in copies:
            slot=where+change['ordinal']*8
            if out[slot:slot+8]!=before:raise ValueError('Relocation copy ordinal differs')
            out[slot:slot+8]=after
    # Root-reviewed meaning correction in an already relocated 41B allocation.
    # No extra pointer, allocation or text shortening is introduced here.
    queue=Path('work/translation/en/executable_0007.json');queue_raw=queue.read_bytes()
    row=next(r for r in json.loads(queue_raw)['rows']if r['id']=='exe_002ed438_cp932')
    target='First Strike Formation / Ambush';oldtext=b'Rapid-Attack Formation / Surprise Attack\0'
    rva=2768244;slot=3306144;extent=41;oldoff=old.file_offset(rva,extent)
    if row['target']!=target or row['offset']!=3068984 or row['encoding']!='cp932':raise ValueError('Approved heading queue snapshot differs')
    record=next(r for r in report['scoped_tutorial_quest_ui']['strings']if r['id']==row['id'])
    if record['payload_rva']!=rva or record['payload_bytes']!=extent or record['target']!=oldtext[:-1].decode():raise ValueError('Frozen heading allocation differs')
    if old.word(slot)!=rva or out[oldoff:oldoff+extent]!=oldtext:raise ValueError('Heading byte/pointer guard differs')
    if sum(p==slot and f==2 for p,f in old.relocs)!=1:raise ValueError('Heading existing typed R32 differs')
    replacement=target.encode('ascii')+b'\0';replacement+=bytes(extent-len(replacement))
    out[oldoff:oldoff+extent]=replacement
    heading=dict(id=row['id'],rva=rva,pointer_slot=slot,allocated_bytes=extent,encoded_bytes=32,
        target=target,queue_path=queue.as_posix(),queue_sha256=sha(queue_raw),
        target_sha256=sha(target.encode()),before_hex=oldtext.hex(),after_hex=replacement.hex(),
        before_sha256=sha(oldtext),after_sha256=sha(replacement),runtime_verified=False)
    record['target']=target;record['encoded_bytes']=32;record['current_allocation_sha256']=sha(replacement)
    moved=next(p for p in report['trailer_recovery']['moved_data']if p['name']==row['id'])
    if moved['new_start']!=rva or moved['bytes']!=extent or moved['sha256']!=sha(oldtext):raise ValueError('Moved heading proof differs')
    moved['historical_sha256']=moved['sha256'];moved['sha256']=sha(replacement)
    moved['current_proof_scope']='Approved meaning correction render_scope_020.heading_meaning_fix; original lifetime and allocation remain inherited.'
    result=bytes(out);elf=Elf(result);cov=coverage(result)
    expected=list(old.relocs)
    for change in mp['moved_existing_relocations']:expected[change['ordinal']]=tuple(change['new'])
    expected.extend(tuple(x)for x in cp['new_relocations'])
    if elf.relocs!=expected or elf.loads!=old.loads:raise ValueError('Combined relocation/LOAD contract differs')
    shape=lambda data:[{k:v for k,v in p.items()if k!='records_sha256'}for p in pair_shapes(data)]
    if shape(result)[:-1]!=shape(original):raise ValueError('Inherited HI/LO semantics differ')
    helper=next(a['rva']for a in cp['allocation']if a['name']=='scoped_EBE2C_decoder')
    text=next(a['rva']for a in cp['allocation']if a['name']=='Crack_Burst_Latin')
    models=[]
    for base in(0x08804000,0x08900000,0x08fff000):
        memory,visited,skipped,pairs=section_load(result,base)
        for hi,lo in((0x842a4,0x842b0),(0x84324,0x84330)):
            words=[struct.unpack_from('<I',memory[0],p)[0]for p in(hi,lo)]
            if address_pair(*words)!=base+text:raise ValueError('Combined text pointer differs')
        if struct.unpack_from('<I',memory[0],slot)[0]!=base+rva:raise ValueError('Loaded heading R32 differs')
        calls=((0xebe2c,helper),(0xebeac,cp['route_rva']),(helper+16,0xe9c64),
               (mp['moved_existing_relocations'][0]['new'][0],0xed164))
        for site,target in calls:
            word=struct.unpack_from('<I',memory[0],site)[0]
            resolved=((base+site+4)&0xf0000000)|((word&0x3ffffff)<<2)
            if resolved!=base+target:raise ValueError('Combined loaded call differs')
        models.append(dict(base=base,total_records=len(visited),skipped_sections=skipped,
            HI_LO_pairs=pairs,two_text_pointers_and_four_control_transfers_passed=True,heading_R32_passed=True))
    # Composition introduces only the already reviewed code/pad and relocation
    # ordinal edits relative to the independently checked Crack Burst image.
    mask=bytearray(cracked);mask[offset:offset+size]=result[offset:offset+size]
    mask[oldoff:oldoff+extent]=replacement
    for where in copies:
        for c in mp['moved_existing_relocations']:
            p=where+c['ordinal']*8;mask[p:p+8]=result[p:p+8]
    if result!=mask:raise ValueError('Unexpected composition difference')
    reservations=plan(report,[dict(name='Crack_Burst_Latin',data=b'Crack Burst\0',alignment=4),
        dict(name='scoped_EBE2C_decoder',data=crack.wrapper(),alignment=4)])
    report.update(version='0.1.20',input_version='0.1.19',input_sha256=sha(original),
        status='pure_combined_render_proposal_no_writer',runtime_verified=False,
        output_elf_sha256=sha(result),output_sha256=sha(result),elf_bytes=len(result),
        total_relocations=len(elf.relocs),added_relocations=len(elf.relocs)-report['original_relocations'],
        relocation_table_sha256=sha(result[active[1]:active[1]+active[4]]))
    report['trailer_recovery']['free_tail_regions']=reservations['free_tail_regions']
    report['trailer_recovery']['historical_remaining_tail_bytes']=report['trailer_recovery']['remaining_tail_bytes']
    report['trailer_recovery']['remaining_tail_bytes']=reservations['remaining_bytes']
    report['additional_scopes']['tail_reservations'].extend(cp['allocation'])
    for source,hi,lo in((0x2eb2be,0x842a4,0x842b0),(0x2eb310,0x84324,0x84330)):
        report['strings'].append(dict(original_file_offset=hex(source+192),target='Crack Burst',
            payload_rva=hex(text),pointer_rvas=[],address_pairs=[[hex(hi),hex(lo)]],
            integration_scope='render_scope_020',runtime_verified=False))
    report['section_relocation_repair']['proof_scope']='Historical .19 section repair only. Current .20 coverage, one moved R26 and one appended R26 are render_scope_020.'
    report['render_input_history']=dict(version='0.1.19',output_elf_sha256=sha(original),
        evidence_scope='Historical predecessor only; current selected deltas are render_scope_020.')
    report['render_scope_020']=dict(crack_burst=cp,measurement_1A=mp,heading_meaning_fix=heading,
        section_coverage=cov,three_base_SHT_loader=models,relocation_copies_updated=copies,
        all_LOAD_headers_exact=True,loaded_growth_bytes=0,remaining_tail_bytes=reservations['remaining_bytes'],
        original_unloaded_font_trailer_exact=True,inherited_pair_semantics_exact=True,
        inherited_proofs_scope='Historical predecessor proofs remain linked; selected native words, measurement code and return relocation now governed by this scope.',
        runtime_verified=False)
    code_names=('prepare_render_020.py','prepare_crack_burst_020.py','dialogue_measure_1a.py',
        'dialogue_measure.py','prepare_relocation_019.py','png_tail_allocate.py')
    report['render_preparation_code_input_sha256']={n:sha(Path('tools',n).read_bytes())for n in code_names}
    # Report current bytes explicitly: no inherited historical prefix claim.
    report['render_scope_020']['current_measurement_sha256']=sha(result[offset:offset+size])
    report['render_scope_020']['current_wrapper_sha256']=sha(result[elf.file_offset(helper):elf.file_offset(helper)+cp['wrapper_bytes']])
    refreshed=[]
    for chunk in report['native_tail_compaction']['chunks']:
        first=chunk['file_offset'];last=first+chunk['bytes']
        if sha(original[first:last])!=chunk['output_sha256']:
            raise ValueError('Inherited active native-tail chunk differs')
        current_hash=sha(result[first:last])
        if current_hash!=chunk['output_sha256']:
            if not first<=offset<offset+size<=last:
                raise ValueError('Changed active chunk is outside reviewed measurement')
            masked=bytearray(original[first:last]);masked[offset-first:offset-first+size]=result[offset:offset+size]
            if bytes(masked)!=result[first:last]:raise ValueError('Unexpected active chunk changes')
            chunk['historical_output_sha256']=chunk['output_sha256'];chunk['output_sha256']=current_hash
            chunk['current_proof_scope']='render_scope_020.measurement_1A'
            refreshed.append(dict(name=chunk['name'],sha256=current_hash))
    if len(refreshed)!=1:raise ValueError('Expected exactly one active measurement chunk refresh')
    report['render_scope_020']['refreshed_current_native_tail_chunks']=refreshed
    return result,report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path)
    p.add_argument('--output',type=Path);p.add_argument('--approved-plan-sha256');p.add_argument('--write',action='store_true');a=p.parse_args()
    data,report=build();raw=json.dumps(report,indent=2,ensure_ascii=True)+'\n'
    checksum=sha(json.dumps(report,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
    print(json.dumps({k:report[k]for k in('version','output_elf_sha256','elf_bytes','payload_bytes','total_relocations','render_scope_020','render_preparation_code_input_sha256')},indent=2))
    if a.report:
        if a.report.exists():raise ValueError('Refuse evidence overwrite')
        a.report.write_text(raw,encoding='utf8')
    print('DRY PLAN SHA256',checksum)
    if a.write:
        if a.approved_plan_sha256!=checksum:raise ValueError('Exact dry proposal approval required')
        root=a.output.resolve() if a.output else None
        if root is None or root.exists() or not root.is_relative_to(Path('work/output').resolve()):
            raise ValueError('Fresh output folder inside work/output required')
        root.mkdir(parents=True);path=root/'EBOOT.BIN';path.write_bytes(data)
        if sha(path.read_bytes())!=report['output_elf_sha256']:raise ValueError('Written ELF readback differs')
        report.update(status='written_combined_render_candidate_runtime_unverified',
            approved_dry_plan_sha256=checksum,output=str(path),written_readback_verified=True)
        (root/'executable.en.json').write_text(json.dumps(report,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
        print('Verified fresh ELF and preparation metadata:',path)
    else:print('DRY RUN: no ELF/ISO written.')
if __name__=='__main__':main()
