"""Fresh .16 font+typed UI preparation; dry default, exact-hash guarded writer."""
import argparse,copy,hashlib,json,struct
from pathlib import Path
from prepare_font_016 import build as font_build
from font_ram_plan import SHA
from build_menu_patch import START,align
from compact_vwf_patch import loaded
from build_local import authoritative_font_metadata

TEMPLATE=Path('work/source/executable_relocation_dry.en.json')
OUTPUT=Path('work/output/0.1.16-dialogue-assets')


def sha(b):return hashlib.sha256(b).hexdigest()


def build():
    base,report=font_build();planner_bytes=TEMPLATE.read_bytes();planner=json.loads(planner_bytes)
    t=planner['scoped_integration_template']
    from executable_text_patch import plan,scoped_template,ORIGINAL
    fresh=scoped_template(plan(ORIGINAL,Path(planner['base_manifest']),Path('work/translation/en')))
    if fresh!=t:raise ValueError('Frozen UI template differs from fresh current targets/source/reference plan')
    if t['base_sha256']!=SHA or t['original_sha256']!='03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1':raise ValueError('UI template source/base changed')
    if t['selected_records']!=451 or t['typed_pointer_writes']!=452 or t['payload_bytes']!=7239:raise ValueError('Reviewed UI template counts changed')
    po,so=struct.unpack_from('<II',base,28);ph=[list(struct.unpack_from('<8I',base,po+n*32))for n in range(4)]
    sections=[list(struct.unpack_from('<10I',base,so+n*40))for n in range(struct.unpack_from('<H',base,48)[0])]
    payload=bytearray(base[ph[2][1]:ph[2][1]+ph[2][4]]);oldpayload=bytes(payload)
    records=list(struct.iter_unpack('<II',base[ph[3][1]:ph[3][1]+ph[3][4]]));where={r:n for n,r in enumerate(records)}
    prefix=bytearray(base[:0x508880]);changes=[];strings=[];slots=set()
    payload.extend(bytes((-len(payload))%16))
    for row in t['entries']:
        raw=bytes.fromhex(row['payload_hex'])
        if sha(raw)!=row['payload_sha256']or len(raw)!=row['payload_bytes']or not raw.endswith(b'\0')or b'\0'in raw[:-1]:raise ValueError('Typed UI payload changed')
        if row['encoding']=='utf-8':
            if len(raw)>128:raise ValueError('Savedata caption exceeds native128-byte capacity')
            raw[:-1].decode('utf-8')
        elif row['encoding']!='engine-private-latin':raise ValueError('Unproved UI codec')
        offset=len(payload);rva=START+offset;payload.extend(raw)
        for write in row['pointer_writes']:
            slot=int(write['pointer_rva'],0)if isinstance(write['pointer_rva'],str)else write['pointer_rva']
            expected=int(write['expected_word'],0)if isinstance(write['expected_word'],str)else write['expected_word']
            if slot in slots or struct.unpack_from('<I',prefix,slot+192)[0]!=expected:raise ValueError('Typed UI pointer expected bytes differ')
            slots.add(slot)
            matches=[n for n,(off,flags)in enumerate(records)if off==slot and flags>>8&255==0 and flags&255==2]
            if len(matches)!=1:raise ValueError('Typed UI pointer requires exactly one native R32')
            n=matches[0];oldflag=records[n][1]
            # Explicit target2 uses segment-relative offset, not full RVA.
            records[n]=(slot,0x20002);struct.pack_into('<I',prefix,slot+192,offset)
            changes.append(dict(id=row['id'],slot_rva=slot,expected_word=expected,stored_offset=offset,resolved_rva=rva,
                                old_relocation_flags=oldflag,new_relocation_flags=0x20002,unchanged_other_consumers=True))
        strings.append(dict(id=row['id'],target=row['target'],encoding=row['encoding'],payload_rva=rva,payload_bytes=len(raw),payload_sha256=sha(raw),runtime_verified=False))
    if len(slots)!=452 or len(payload)-align(len(oldpayload),16)!=7239:raise ValueError('Typed UI totals differ')
    rel=b''.join(struct.pack('<II',*x)for x in records)
    pf=align(len(prefix),64);prefix.extend(bytes(pf-len(prefix)));prefix.extend(payload)
    rf=align(len(prefix),16);prefix.extend(bytes(rf-len(prefix)));prefix.extend(rel)
    for s in sections:
        if s[1]==0x700000a0:s[4]=rf+s[4]-ph[3][1]
        elif s[3]==START and s[4]==ph[2][1]:s[4]=pf;s[5]=len(payload)
    newsh=align(len(prefix),4);prefix.extend(bytes(newsh-len(prefix)))
    for s in sections:prefix.extend(struct.pack('<10I',*s))
    ph[2][1]=pf;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=rf;ph[3][4]=len(rel)
    for n,p in enumerate(ph):struct.pack_into('<8I',prefix,po+n*32,*p)
    struct.pack_into('<I',prefix,32,newsh);struct.pack_into('<H',prefix,48,len(sections))
    checks=0
    for loadbase in (0x8804000,0x8900000,0x8fff000):
        segs,_,_=loaded(prefix,loadbase);oldsegs,_,_=loaded(base,loadbase)
        if segs[1]!=oldsegs[1]or segs[2][:len(oldpayload)]!=oldsegs[2]:raise ValueError('Inherited font/setup state changed')
        for item in changes:
            if struct.unpack_from('<I',segs[0],item['slot_rva'])[0]!=loadbase+item['resolved_rva']:raise ValueError('Typed UI target2 loaded pointer differs')
            checks+=1
        oldnative=bytearray(oldsegs[0])
        for item in changes:oldnative[item['slot_rva']:item['slot_rva']+4]=segs[0][item['slot_rva']:item['slot_rva']+4]
        if oldnative!=segs[0]:raise ValueError('Unselected native consumer changed')
    result=bytes(prefix);previous=report['output_elf_sha256']
    report.update(status='dry_font_and_typed_ui_candidate',output_elf_sha256=sha(result),output_sha256=sha(result),elf_bytes=len(result),payload_bytes=len(payload),
                  module_growth_bytes=len(payload),payload_growth=len(payload)-217152,relocation_table_sha256=sha(rel),runtime_verified=False)
    report['scoped_executable_ui']=dict(font_input_candidate_sha256=previous,template_sha256=sha(planner_bytes),selected_records=len(strings),
        typed_pointer_writes=len(changes),payload_bytes=7239,payload_alignment_bytes=align(len(oldpayload),16)-len(oldpayload),
        target_segment=2,stored_pointer_policy='Offset relative to LOAD2; resolved pointer=modulebase+START+offset',
        strings=strings,pointer_changes=changes,inherited_font_payload_prefix_exact=True,inherited_LOAD1_exact=True,
        loaded_pointer_comparisons=checks,loaded_bases=[0x8804000,0x8900000,0x8fff000],
        unselected_native_consumers_exact=True,unselected_templates_not_integrated=True,runtime_verified=False)
    report['scoped_executable_ui']['fresh_current_queue_plan_matches_frozen_template']=True
    report['memory_forecast'].update(recovered_bytes=217152-len(payload),margin_before_new_ui=217152-len(payload)-133376,
                                   typed_ui_bytes_included=7239,other_ui_not_integrated=True)
    from tutorial_scope_016 import build as tutorial_build
    result,report=tutorial_build(result,report)
    authoritative_font_metadata(result,report)
    return result,report


def report_hash(report):return sha(json.dumps(report,sort_keys=True,separators=(',',':')).encode('utf-8'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--approved-elf-sha');p.add_argument('--approved-report-sha');a=p.parse_args()
    data,report=build();reviewsha=report_hash(report);print(json.dumps(report,indent=2));print('Canonical dry report SHA256:',reviewsha)
    if not a.write:print('DRY RUN: no executable, assets or reports written.')
    else:
        if a.approved_elf_sha!=sha(data)or a.approved_report_sha!=reviewsha:raise ValueError('Writer requires exact reviewed executable and dry-report hashes')
        if OUTPUT.exists():raise ValueError('Fresh output folder required; never overwrite a candidate')
        OUTPUT.mkdir();(OUTPUT/'EBOOT.BIN').write_bytes(data)
        if sha((OUTPUT/'EBOOT.BIN').read_bytes())!=sha(data):raise ValueError('Executable readback differs')
        report['status']='written_font_and_typed_ui_candidate_runtime_unverified'
        report['approved_dry_report_sha256']=reviewsha
        (OUTPUT/'setup_patch.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print('Fresh technical candidate written; no archive or ISO mutation.')
