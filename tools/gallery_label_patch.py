"""Pure frozen22 gallery pointer proposal; never writes executable assets."""
import argparse, copy, hashlib, json, struct
from pathlib import Path
from executable_text_patch import Elf, reference_index
from png_tail_allocate import plan
from prepare_relocation_019 import coverage, section_load, pair_shapes
from dialogue_vwf_hooks import decoder
from build_menu_patch import relocate_code
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

SOURCE = Path('work/output/0.1.22-render-verified-assets/EBOOT.BIN')
SOURCE_SHA = 'faae14c915f628eed10ad310eebf9415b4b7e1c8a5d241582a2d81a91f48e1e2'
QUEUE = Path('work/translation/en/executable_gallery_0001.json')
QUEUE_SHA = '20aeb57d1795d1086c5f01027dcf1e11e7c4a4f77df8abb86e702b62cac230a8'
ORIGINAL = Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(report):
    return sha(json.dumps(report,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())

def build():
    incoming=SOURCE.read_bytes(); metadata_raw=SOURCE.with_name('executable.en.json').read_bytes()
    before=json.loads(metadata_raw); elf=Elf(incoming); original=Elf(ORIGINAL.read_bytes())
    queue_raw=QUEUE.read_bytes(); rows=json.loads(queue_raw)['rows']
    if sha(incoming)!=SOURCE_SHA or before['output_elf_sha256']!=SOURCE_SHA:
        raise ValueError('Frozen22 executable or metadata differs')
    if sha(queue_raw)!=QUEUE_SHA or len(rows)!=19:
        raise ValueError('Reviewed nineteen-target snapshot differs')
    font=authoritative_font_metadata(incoming,before); validate_native_png_metadata(incoming,before)
    references,_=reference_index(original)
    # Actual decoder return gateway is outside its first96-byte native entry.
    code=bytearray(decoder(True,(0xf0cf0,0xf0d98,0xec644,0x881e8),private_pairs=True))
    relocate_code(code,0,len(code)); gateway=before['font_hooks']['decoder']
    if elf.word(0xe9cc8)!=0x08000000|(gateway>>2):
        raise ValueError('Shared native decoder return gateway differs')
    if incoming[elf.file_offset(gateway):elf.file_offset(gateway)+len(code)]!=code:
        raise ValueError('Active Latin/private decoder differs from complete generator')
    callers=[]
    for start,end,getter,draw in ((0x68c50,0x68cd8,0x68c60,0x68cd0),(0x1f08c,0x1f0e0,0x1f09c,0x1f0d8)):
        raw=incoming[elf.file_offset(start):elf.file_offset(end)]
        if raw!=original.data[original.file_offset(start):original.file_offset(end)]:
            raise ValueError('Observed gallery caller continuation changed')
        if elf.word(getter)!=0x0c000000|(0x877f4>>2) or elf.word(draw)!=0x0c000000|(0x87c18>>2):
            raise ValueError('Gallery getter-to-draw chain differs')
        callers.append(dict(start=start,end=end,getter_site=getter,draw_site=draw,
            sha256=sha(raw),native_exact=True,height=16,
            alignment='Tabs set T1=0; observed footer getter S2=0 is replayed to T1.',
            width='Tabs LH[descriptorS3+16]; footer saved callerT1 (observed13).'))
    payload=bytearray(); entries=[]
    floats=struct.unpack('<131f',incoming[elf.file_offset(before['float_width_lut_rva'],524):elf.file_offset(before['float_width_lut_rva'],524)+524])
    for row in rows:
        source=row['expected_source_rva']; slot=row['typed_R_MIPS_32_pointer_slot_rva']
        raw=row['source'].encode('cp932')+b'\0'; actual=original.data[original.file_offset(source):original.file_offset(source)+len(raw)]
        if raw!=actual or sha(raw)!=row['source_sha256_with_NUL'] or row['offset']!=original.file_offset(source):
            raise ValueError('Original source bytes/offset/hash differ')
        refs=[r for r in references if r['kind']=='R_MIPS_32' and r['sites']==[slot] and r['address']==source]
        if len(refs)!=1 or refs[0]['relocation_ordinals']!=[row['relocation_ordinal']]:
            raise ValueError('Typed source reference differs')
        ordinal=row['relocation_ordinal']
        if elf.relocs[ordinal]!=(slot,2) or elf.word(slot)!=source:
            raise ValueError('Current typed R32 pointer/ordinal differs')
        target=row['target'].encode('ascii')+b'\0'
        if any(c<32 or c>126 for c in target[:-1]):raise ValueError('Target not plain printable Latin')
        entries.append(dict(id=row['id'],pointer_slot=slot,source_rva=source,source_sha256=sha(raw),
            relocation_ordinal=ordinal,relative_offset=len(payload),target=row['target'],encoded_bytes=len(target),
            estimated_16px_VWF_width=sum(floats[c] for c in target[:-1]),
            runtime_layout_verified=False))
        payload.extend(target)
    reservation=plan(before,[dict(name='gallery_nineteen_Latin_labels',data=bytes(payload),alignment=4)])
    placement=reservation['patches'][0]; result=bytearray(incoming); allowed=set()
    start=elf.file_offset(placement['rva'],len(payload))
    if start!=placement['file_offset']:
        raise ValueError('Proof-backed free tail is not file-backed')
    for active in before['additional_scopes']['tail_reservations']+before['native_tail_compaction']['chunks']:
        if placement['rva']<active['rva']+active['bytes'] and active['rva']<placement['rva']+len(payload):
            raise ValueError('Text overlaps active font/code/data allocation')
    result[start:start+len(payload)]=payload; allowed.update(range(start,start+len(payload)))
    for entry in entries:
        entry['target_rva']=placement['rva']+entry['relative_offset']; p=elf.file_offset(entry['pointer_slot'],4)
        struct.pack_into('<I',result,p,entry['target_rva']);allowed.update(range(p,p+4))
    output=bytes(result); out=Elf(output)
    if len(output)!=len(incoming) or out.ph!=elf.ph or out.relocs!=elf.relocs or pair_shapes(output)!=pair_shapes(incoming):
        raise ValueError('Inherited ELF/load/relocation/pair contracts changed')
    if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(incoming,output))):
        raise ValueError('Unselected file bytes changed')
    coverage(output); models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        old,_,_,_=section_load(incoming,base); new,visited,skipped,_=section_load(output,base)
        loaded_allowed=set(range(placement['rva'],placement['rva']+len(payload)))
        for entry in entries:
            slot=entry['pointer_slot'];loaded_allowed.update(range(slot,slot+4))
            if struct.unpack_from('<I',new[0],slot)[0]!=base+entry['target_rva']:
                raise ValueError('Actual section-loaded target pointer differs')
        if old[1:]!=new[1:] or any(a!=b and i not in loaded_allowed for i,(a,b)in enumerate(zip(old[0],new[0]))):
            raise ValueError('Unselected loaded memory changed')
        models.append(dict(base=base,relocations=len(visited),skipped_sections=skipped,
            exact_selected_R32_pointers=19,unselected_loaded_memory_exact=True))
    updated=copy.deepcopy(before); updated.update(version='0.1.23',input_version='0.1.22',input_sha256=SOURCE_SHA,
        status='pure_gallery_pointer_candidate_runtime_unverified',output_elf_sha256=sha(output),output_sha256=sha(output),
        elf_bytes=len(output),runtime_verified=False)
    updated['gallery_input_history']=dict(source=str(SOURCE),source_sha256=SOURCE_SHA,
        historical_predecessor_status=before.get('status'),
        historical_predecessor_approved_plan=before.get('approved_dry_plan_sha256'),
        preservation_scope='Predecessor font/render/save proofs remain historical; this pure candidate has no written asset or runtime verification.')
    for key in ('output','approved_dry_plan_sha256','written_readback_verified'):
        updated.pop(key,None)
    updated['trailer_recovery']['free_tail_regions']=reservation['free_tail_regions']
    updated['trailer_recovery']['remaining_tail_bytes']=reservation['remaining_bytes']
    allocation={k:v for k,v in placement.items()if k!='data'}
    updated['additional_scopes']['tail_reservations'].append(allocation)
    proof=dict(input_metadata_sha256=sha(metadata_raw),queue_sha256=QUEUE_SHA,entries=entries,
        payload_bytes=len(payload),allocation=allocation,remaining_tail_bytes=reservation['remaining_bytes'],
        replaced_excluded_tail_bytes_sha256=sha(incoming[start:start+len(payload)]),
        loaded_growth_bytes=0,new_relocations=0,all_PH_SHT_relocations_pairs_exact=True,
        decoder_return_gateway_rva=0xe9cc8,active_decoder_rva=gateway,active_decoder_bytes=len(code),
        active_decoder_sha256=sha(code),active_decoder_complete_generator_equal=True,
        actual_getter_to_draw_callers=callers,three_base_actual_SHT_models=models,
        all_unselected_file_and_loaded_bytes_exact=True,all_active_font_code_and_PNG_bytes_exact=True,
        runtime_verified=False,limitations=['Only getter callers observed live; draw callsite coordinates still pending.',
            'Twelve franchise pointers are typed static evidence, not individually observed getter calls.',
            'Long franchise titles need actual destination width/layout QA; full text retained.'])
    updated['gallery_label_proposal']=proof
    newfont=authoritative_font_metadata(output,updated)
    if {k:v for k,v in newfont.items()if k!='additional_scopes'}!={k:v for k,v in font.items()if k!='additional_scopes'}:
        raise ValueError('Authoritative font contract changed')
    if updated['additional_scopes']['tail_reservations'][:-1]!=before['additional_scopes']['tail_reservations']:
        raise ValueError('Inherited additional allocation changed')
    proof['authoritative_font_metadata_exact_predecessor']=True
    proof['font_metadata_delta']='Only additional_scopes.tail_reservations appends the new gallery text allocation; all font values and bytes exact.'
    proof['native_png_full_metadata_checks']=validate_native_png_metadata(output,updated)
    proof['code_input_sha256']={str(p):sha(p.read_bytes())for p in [Path('tools')/(n+'.py')for n in
        ('gallery_label_patch','executable_text_patch','png_tail_allocate','prepare_relocation_019',
         'dialogue_vwf_hooks','build_menu_patch','build_local','save_logo_overlay')]}
    return output,updated

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path);a=p.parse_args()
    data,report=build();print(json.dumps(report['gallery_label_proposal'],indent=2));print('DRY PLAN SHA256',canonical(report))
    if a.report:
        if a.report.exists()or not a.report.resolve().is_relative_to(Path('work/source').resolve()):
            raise ValueError('Fresh ignored dry report required')
        a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('DRY: no executable assets, ISO or emulator changes.')
