"""Install field-label fixes using proved retired text storage; dry by default.

The failed .46 candidate grew LOAD2. This composer uses retired original menu
strings and the fully relocated original notification bank, adding no RAM span.
"""
import argparse
import copy
import json
import struct
from pathlib import Path
from executable_text_patch import Elf, ORIGINAL, reference_index, encoded_text
from native_menu_install_plan import cstring
from prepare_field_labels_046 import BASE, SOURCE_SHA, SITE, EVENT, EVENT_SHA, sha, hook, instruction_cases, build as draft
from build_menu_patch import align, relocate_code
from prepare_relocation_019 import sections, section_load, coverage, pair_shapes
from compact_vwf_patch import loaded
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

OUT = Path('work/output/0.1.47-field-label-assets')
QUEUE = Path('work/translation/en/field_labels_047.json')
POOL, SIZE = 0x305dc8, 1280


def build():
    proposed, draft_report, queue = draft()
    planned = draft_report['field_labels_046']; proposed_elf = Elf(proposed)
    incoming = (BASE/'EBOOT.BIN').read_bytes()
    before = json.loads((BASE/'manifest.en.json').read_text(encoding='utf8'))['setup_patch']
    e, o = Elf(incoming), Elf(ORIGINAL.read_bytes())
    refs, _ = reference_index(o)
    selected_slots = {row['pointer_slot'] for row in planned['labels']}
    retire = []
    for slot in [0x94760+n*4 for n in range(234)]+[0x95450+n*4 for n in range(57,63)]:
        source = o.word(slot)
        if e.word(slot) == source and slot not in selected_slots: continue
        raw = cstring(o, source)
        owners = [ref for ref in refs if source <= ref['address'] < source+len(raw)]
        if len(owners) != 1 or owners[0]['kind'] != 'R_MIPS_32' or owners[0]['sites'] != [slot]: continue
        if cstring(e, source) != raw: raise ValueError('Retired menu source already modified')
        if slot not in selected_slots and not all(32 <= c < 127 or c in (0,14,17) for c in cstring(e,e.word(slot))):
            raise ValueError('Retired pointer does not select complete English')
        retire.append(dict(start=source, end=source+len(raw), slot=slot, source_sha256=sha(raw)))
    # This complete bank already lives in LOAD2. Every original native consumer
    # was retargeted in the installed notification patch; check all fourteen
    # typed HI/LO owners and exact source/active bank identities again.
    bank = before['additional_scopes']['notifications']
    old_bank = incoming[e.file_offset(POOL, SIZE):][:SIZE]
    if old_bank != o.data[o.file_offset(POOL, SIZE):][:SIZE]:
        raise ValueError('Retired notification backing differs')
    active = incoming[e.file_offset(bank['pool_rva'], SIZE):][:SIZE]
    if sha(active) != bank['pool_sha256']: raise ValueError('Active notification bank differs')
    owners = [ref for ref in refs if POOL <= ref['address'] < POOL+SIZE]
    if len(owners) != 14: raise ValueError('Notification owner count differs')
    for ref in owners:
        if ref['kind'] != 'R_MIPS_HI16_LO16' or not ref['loader_mate_is_semantic_low'] or ref['shared_high_site']:
            raise ValueError('Unproved retired bank owner')
        hi, lo = ref['sites']; a, b = e.word(hi), e.word(lo)
        value = ((a&65535)<<16)+struct.unpack('<h',struct.pack('<H',b&65535))[0]
        if value != bank['pool_rva']+ref['address']-POOL:
            raise ValueError('Native bank owner was not retargeted')
    retire.sort(key=lambda row: row['start']); free = []
    for row in retire:
        if free and free[-1]['end'] == row['start']: free[-1]['end'] = row['end']
        else: free.append(dict(start=row['start'], end=row['end']))
    free.append(dict(start=POOL,end=POOL+SIZE)); free.sort(key=lambda row:row['end']-row['start'], reverse=True)
    result = bytearray(incoming); allowed = set(); mask = set(); placements = []; additions = []
    def allocate(name, data, alignment=1):
        for region in sorted(free,key=lambda row:row['end']-row['start']):
            start = align(region['start'], alignment)
            if start+len(data) <= region['end']:
                region['start'] = start+len(data)
                file = e.file_offset(start, len(data)); result[file:file+len(data)] = data
                allowed.update(range(file,file+len(data))); mask.update(range(start,start+len(data)))
                placements.append(dict(name=name,rva=start,bytes=len(data),sha256=sha(data)))
                return start
        raise ValueError('No reviewed retired region fits '+name)
    # Reserve the largest block first so that fragmented label spans cannot
    # starve the complete helper; the provisional bytes are replaced below.
    old_helper = before['field_ui_patch']['episode_inline_banner']['helper_rva']
    helper_bytes = len(hook(planned['notices'], old_helper))
    helper = allocate('field_notice_helper',bytes(helper_bytes),16)
    labels = copy.deepcopy(planned['labels']); notices = copy.deepcopy(planned['notices'])
    for row in notices: row['id']=row['id'].replace('_046_','_047_')
    for row in queue['rows']: row['id']=row['id'].replace('_046_','_047_')
    requests=[]; sources=[]
    for row in labels:
        requests.append((f'label_{row["native_index"]}',encoded_text(row['target'],'ascii')+b'\0'))
    for row in notices:
        raw=cstring(proposed_elf,row['source_payload_rva']);sources.append(raw)
        requests.append((row['id']+'_key',raw))
        requests.append((row['id']+'_target',encoded_text(row['target'],'ascii')+b'\0'))
    pointers={name:allocate(name,data)for name,data in sorted(requests,key=lambda item:len(item[1]),reverse=True)}
    for row in labels:
        row['target_rva'] = pointers[f'label_{row["native_index"]}']
        f = e.file_offset(row['pointer_slot'],4); struct.pack_into('<I',result,f,row['target_rva'])
        allowed.update(range(f,f+4)); mask.update(range(row['pointer_slot'],row['pointer_slot']+4))
    for row in notices:
        row['source_payload_rva'] = pointers[row['id']+'_key']
        row['target_payload_rva'] = pointers[row['id']+'_target']
    code = bytearray(hook(notices,old_helper)); records = relocate_code(code,0,len(code))
    for record in records:
        offset, flags = struct.unpack('<II',record)
        additions.append(struct.pack('<II',helper+offset,flags&255))
    hf=e.file_offset(helper,len(code)); result[hf:hf+len(code)]=code
    placements[0]['sha256']=sha(code)
    f=e.file_offset(SITE,8); struct.pack_into('<II',result,f,j_helper(helper),0)
    allowed.update(range(f,f+8)); mask.update(range(SITE,SITE+8))
    # Grow only the file relocation/SHT tail. Loaded program extents and the
    # unloaded compressed-font trailer keep their exact original coordinates.
    ss=sections(incoming); ph=[list(p)for p in e.ph]; rp=ph[3]; relend=rp[1]+rp[4]
    shold=struct.unpack_from('<I',incoming,32)[0]
    if shold!=relend or shold+len(ss)*40!=len(incoming): raise ValueError('Expected relocation/SHT file tail differs')
    result.extend(bytes(len(additions)*8+40))
    extra=b''.join(additions); result[relend:relend+len(extra)]=extra
    allowed.update(range(shold,len(incoming)))
    ss.append([0,0x700000a0,0,0,relend,len(extra),0,1,4,8])
    shoff=relend+len(extra)
    for n,section in enumerate(ss): struct.pack_into('<10I',result,shoff+n*40,*section)
    rp[4]+=len(extra); phoff=struct.unpack_from('<I',incoming,28)[0]
    struct.pack_into('<8I',result,phoff+96,*rp); allowed.update(range(phoff+96,phoff+128))
    struct.pack_into('<I',result,32,shoff);allowed.update(range(32,36))
    struct.pack_into('<H',result,48,len(ss));allowed.update(range(48,50))
    result=bytes(result); out=Elf(result)
    if out.ph[:3]!=e.ph[:3] or out.relocs[:len(e.relocs)]!=e.relocs:
        raise ValueError('Inherited LOAD spans/relocations changed')
    if pair_shapes(result)[:len(pair_shapes(incoming))]!=pair_shapes(incoming): raise ValueError('Inherited HI/LO semantics changed')
    if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,result))): raise ValueError('Unselected file bytes changed')
    coverage(result); models=[]
    episode=cstring(e,before['field_ui_patch']['episode_inline_banner']['source_payload_rva'])
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);b,visited,skipped,_=section_load(result,base)
        independent,_,_=loaded(result,base)
        if skipped or visited!=out.relocs or independent!=[b[n][:out.ph[n][4]]for n in range(3)]: raise ValueError('Independent loaders differ')
        if a[1:]!=b[1:] or any(x!=y and n not in mask for n,(x,y)in enumerate(zip(a[0],b[0]))): raise ValueError('Unselected loaded memory changed')
        mapped=[dict(row,source_payload_rva=base+row['source_payload_rva'],target_payload_rva=base+row['target_payload_rva'])for row in notices]
        cases=instruction_cases(bytes(b[0][helper:helper+len(code)]),base+helper,mapped,sources,base+old_helper,episode)
        for row in labels:
            if struct.unpack_from('<I',b[0],row['pointer_slot'])[0]!=base+row['target_rva'] or cstring(out,row['target_rva'])!=encoded_text(row['target'],'ascii')+b'\0': raise ValueError('Installed label differs')
        models.append(dict(base=base,labels=28,unselected_memory_exact=True,instruction_checks=cases))
    report=copy.deepcopy(before)
    for key in ('output','approved_dry_plan_sha256','written_readback_verified'):report.pop(key,None)
    report.update(version='0.1.47',input_version='0.1.45',input_sha256=SOURCE_SHA,
        output_elf_sha256=sha(result),output_sha256=sha(result),elf_bytes=len(result),
        total_relocations=len(out.relocs),added_relocations=len(out.relocs)-before['original_relocations'],
        relocation_table_sha256=sha(result[rp[1]:rp[1]+rp[4]]),runtime_verified=False,
        status='field_labels_and_notices_zero_loaded_growth_candidate')
    report['field_labels_047']=dict(labels=labels,notices=notices,event=EVENT,event_sha256=EVENT_SHA,event_occurrences=15,
        hook_site=SITE,helper_rva=helper,helper_bytes=len(code),helper_sha256=sha(code),episode_hook_continuation_rva=old_helper,
        loaded_growth_bytes=0,new_relocations=len(additions),loader_models=models,
        retired_menu_regions=retire,retired_notification_bank=dict(rva=POOL,bytes=SIZE,original_sha256=sha(old_bank),typed_owners_retargeted=14),
        placements=placements,remaining_retired_bytes=sum(x['end']-x['start']for x in free),
        file_growth_bytes=len(result)-len(incoming),event_bytecode_exact=True,natural_gameplay_verified=False,
        inherited_bubble_and_font_code_exact=True,archive_resources_unchanged=True)
    authoritative_font_metadata(result,report);validate_native_png_metadata(result,report)
    return result,report,queue


def j_helper(rva):
    from live_vwf import j
    return j(rva)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256')
    args=ap.parse_args();data,report,queue=build();p=report['field_labels_047']
    print(json.dumps(dict(version=report['version'],sha256=sha(data),labels=len(p['labels']),notices=len(p['notices']),
        loaded_growth_bytes=0,file_growth_bytes=p['file_growth_bytes'],new_relocations=p['new_relocations'],
        remaining_retired_bytes=p['remaining_retired_bytes'],loader_models=p['loader_models']),indent=2))
    if not args.write:print('DRY RUN: no executable or translation files written.');return
    if args.expected_sha256!=sha(data) or OUT.exists() or QUEUE.exists():raise ValueError('Reviewed hash and fresh destinations required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data)
    if (OUT/'EBOOT.BIN').read_bytes()!=data:raise ValueError('Executable readback differs')
    report['written_readback_verified']=True
    (OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
