"""Read-only234-slot menu audit and bounded first78 storage proposal; no ELF writer."""
import argparse, json, struct, re
from pathlib import Path
from executable_text_patch import Elf, reference_index, ORIGINAL
from gallery_label_patch import sha, canonical
from dialogue_vwf_hooks import decoder
from build_menu_patch import relocate_code
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from prepare_relocation_019 import coverage, sections

SOURCE=Path('work/output/0.1.24-gallery-assets/EBOOT.BIN')
SOURCE_SHA='17cdb7435ed0a2abdf04fcc453140e6e6cda06b2021e74a4ca527ee869763ccb'
QUEUES=[Path('work/translation/en/executable_native_menu_0001.json'),Path('work/translation/en/executable_native_menu_0002.json')]

def cstring(elf,rva):
    p=elf.file_offset(rva);load=next(x for x in elf.loads if x[2]<=rva<x[2]+x[4]);end=load[1]+load[4]
    n=elf.data.find(b'\0',p,min(p+1024,end))
    if n<0:raise ValueError('Unterminated bounded native menu string')
    return elf.data[p:n+1]

def build():
    data=SOURCE.read_bytes();rawmeta=SOURCE.with_name('executable.en.json').read_bytes();report=json.loads(rawmeta)
    if sha(data)!=SOURCE_SHA or report['output_elf_sha256']!=SOURCE_SHA:raise ValueError('Frozen24 input differs')
    elf=Elf(data);original=Elf(ORIGINAL.read_bytes());refs,_=reference_index(original)
    authoritative_font_metadata(data,report);png=validate_native_png_metadata(data,report);coverage(data)
    code=bytearray(decoder(True,(0xf0cf0,0xf0d98,0xec644,0x881e8),private_pairs=True));relocate_code(code,0,len(code))
    gateway=report['font_hooks']['decoder'];p=elf.file_offset(gateway,len(code))
    if elf.word(0xe9cc8)!=0x08000000|(gateway>>2)or data[p:p+len(code)]!=code:
        raise ValueError('Full existing ASCII/private decoder gateway differs')
    q=[];hashes={}
    for path in QUEUES:
        raw=path.read_bytes();hashes[str(path)]=sha(raw);q.append(json.loads(raw)['rows'])
    if len(q[0])!=80 or len(q[1])!=76:raise ValueError('Expected80/76 working rows')
    indexed={r['native_index']:r for group in q for r in group}
    if len(indexed)!=156:raise ValueError('Queue native indices overlap')
    supplemental={}
    for path in sorted(Path('work/translation/en').glob('executable*.json')):
        if path.name.endswith('.en.json')or path in QUEUES:continue
        rows=json.loads(path.read_bytes()).get('rows',[])
        for row in rows:
            if isinstance(row.get('offset'),int)and row.get('target')and row.get('source'):
                supplemental.setdefault((row['offset'],row['source']),[]).append(dict(queue=str(path),id=row['id'],target=row['target']))
    entries=[];reusable={}
    for index in range(234):
        slot=0x94760+index*4;source=original.word(slot);raw=cstring(original,source);text=raw[:-1].decode('cp932')
        ref=[r for r in refs if r['kind']=='R_MIPS_32'and r['sites']==[slot]and r['address']==source]
        if len(ref)!=1 or len(ref[0]['relocation_ordinals'])!=1:raise ValueError('Table slot lacks unique original typed R32')
        ordinal=ref[0]['relocation_ordinals'][0]
        if elf.relocs[ordinal]!=(slot,2):raise ValueError('Current typed menu R32 differs')
        current=elf.word(slot);currentraw=cstring(elf,current)
        islatin=all(32<=c<=126 for c in currentraw[:-1])
        if islatin:reusable.setdefault(currentraw,current)
        row=indexed.get(index)
        if row:
            if row['pointer_slot_rva']!=slot or row['source_rva']!=source or row['relocation_ordinal']!=ordinal or row['source']!=text or row['source_sha256_with_NUL']!=sha(raw)or row['offset']!=original.file_offset(source):
                raise ValueError('Working queue source/table/hash differs')
            status='held'if not row['target']else('installed_exact'if currentraw==row['target'].encode('ascii')+b'\0'else'approved_uninstalled')
        else:status='outside_first_two_queues'
        entries.append(dict(native_index=index,pointer_slot=slot,source_rva=source,source_sha256=sha(raw),relocation_ordinal=ordinal,
            current_pointer_rva=current,pointer_retargeted=current!=source,current_string_sha256=sha(currentraw),
            current_plain_Latin=islatin,source_contains_Japanese=bool(re.search('[\u3040-\u30ff\u3400-\u9fff]',text)),
            queue_status=status,approved_target=row['target']if row else None,
            other_working_drafts=supplemental.get((original.file_offset(source),text),[]),
            visibility='Typed source slot only; individual caller, buffer and layout remain unverified outside observed Gallery scopes.'))
    first=[e for e in entries if e['native_index']in {r['native_index']for r in q[0]}and e['queue_status']!='held']
    if len(first)!=78:raise ValueError('Expected78 approved first-queue labels')
    payload=bytearray();dedup={};planned=[]
    for e in first:
        raw=e['approved_target'].encode('ascii')+b'\0'
        if any(c<32 or c>126 for c in raw[:-1]):raise ValueError('Approved menu label not printable ASCII')
        if raw in reusable:
            target=reusable[raw];kind='reuse_guarded_current_menu_string'
        else:
            if raw not in dedup:dedup[raw]=len(payload);payload.extend(raw)
            target=elf.ph[2][2]+elf.ph[2][4]+dedup[raw];kind='append_LOAD2_string'
        planned.append(dict(native_index=e['native_index'],pointer_slot=e['pointer_slot'],expected_word=e['current_pointer_rva'],
            relocation_ordinal=e['relocation_ordinal'],target=e['approved_target'],target_rva=target,storage=kind,encoded_bytes=len(raw)))
    section55=sections(data)[55]
    if section55[3:6]!=[elf.ph[2][2],elf.ph[2][1],elf.ph[2][4]]:raise ValueError('Current loaded section55 mismatch')
    counts={}
    for e in entries:counts[e['queue_status']]=counts.get(e['queue_status'],0)+1
    return dict(schema_version=1,status='pure_native_menu_storage_proposal_not_ready_for_writer',input_version='0.1.24',input_elf_sha256=SOURCE_SHA,
        input_metadata_sha256=sha(rawmeta),queues_sha256=hashes,table_slots=234,counts=counts,
        current_pointer_retargeted_slots=sum(e['pointer_retargeted']for e in entries),
        source_Japanese_still_original_slots=sum(e['source_contains_Japanese']and not e['pointer_retargeted']for e in entries),
        other_drafted_source_slots=sum(bool(e['other_working_drafts'])for e in entries if e['queue_status']=='outside_first_two_queues'),
        first_queue_approved=78,held_indices=[e['native_index']for e in entries if e['queue_status']=='held'],entries=entries,first78=planned,
        first78_storage=dict(raw_total_bytes=sum(e['encoded_bytes']for e in planned),new_unique_strings=len(dedup),append_bytes=len(payload),
            payload_sha256=sha(payload),reused_current_strings=sum(e['storage'].startswith('reuse')for e in planned),
            free_PNG_tail_bytes=report['trailer_recovery']['remaining_tail_bytes'],preserve_free_PNG_tails=True,
            old_LOAD2_bytes=elf.ph[2][4],proposed_LOAD2_bytes=elf.ph[2][4]+len(payload),
            old_module_growth_bytes=report['module_growth_bytes'],proposed_module_growth_bytes=((elf.ph[2][4]+len(payload)+63)//64)*64,
            required_new_relocations=0,
            relocation_policy='Existing source0/target0 R32 records retain flags2 and store full resulting RVA. Actual per-section three-base load must prove each pointer before any writer.',
            file_policy='Preserve all old EOF bytes including unloaded font trailer; append copied LOAD2 plus new strings after EOF. Repoint PH2 and SHT55 physical extent only; existing PH3/SHT relocation tables remain at exact offsets. Old LOAD2 copy becomes unloaded file data.',
            preserve='All prior LOAD0/1 except selected78 typed words; LOAD2 inherited3568-byte prefix;25 Gallery labels;5 PNG triples/pixels;decoder/font/code;relocations/HI-LO pairs.'),
        renderer=dict(full_decoder_bytes=len(code),decoder_sha256=sha(code),gateway_rva=0xe9cc8,active_rva=gateway,
            complete_generator_equal=True,scope='87D38 generic draw decoder return route is Latin/private capable; each new menu consumer/formatting buffer/centering still requires bounded caller audit before install readiness.'),
        native_PNG_checks=png,assets_written=False,runtime_verified=False,
        remaining_work=['Audit first78 typed getter consumers for copies/fixed buffers and centered EAD20 counting; no claim every table0 getter uses87C18.',
            'Pure ELF construction must prove exact PH2/SHT55 geometry, unchanged font trailer seek/pixels and all actual SHT loaded bytes at three bases.',
            'Current memory forecast is historical; incremental load estimate must be reviewed against19+ runtime heap evidence.'],
        code_input_sha256={str(p):sha(p.read_bytes())for p in(Path(__file__),Path('tools/executable_text_patch.py'),Path('tools/dialogue_vwf_hooks.py'),Path('tools/build_menu_patch.py'),Path('tools/build_local.py'),Path('tools/save_logo_overlay.py'),Path('tools/prepare_relocation_019.py'))})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path);a=p.parse_args();r=build()
    print(json.dumps({k:v for k,v in r.items()if k not in('entries','first78')},indent=2));print('FIRST78 SAMPLE',json.dumps(r['first78'][:8],indent=2));print('CANONICAL PLAN SHA256',canonical(r))
    if a.report:
        if a.report.exists()or not a.report.resolve().is_relative_to(Path('work/source').resolve()):raise ValueError('Fresh ignored proposal path required')
        a.report.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    print('DRY: no ELF assets, source data or emulator changes.')
