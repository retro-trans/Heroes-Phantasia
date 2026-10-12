"""Relocate the screenshot-reported field UI from frozen 0.1.27; dry by default."""
import argparse, copy, hashlib, json, re, struct
from pathlib import Path
from executable_text_patch import Elf, ORIGINAL, ORIGINAL_SHA, reference_index, encoded_text
from native_menu_install_plan import cstring
from prepare_relocation_019 import sections, section_load, coverage, pair_shapes
from compact_vwf_patch import loaded
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from dialogue_tokens import validate_controls
from build_menu_patch import align,relocate_code,reloc
from live_vwf import j
from episode_banner_hook import SITE,EXPECTED,TARGET,source_payload,hook,cases

SOURCE=Path('work/output/0.1.27-bubble-assets/EBOOT.BIN')
SOURCE_SHA='192b142327aef79f58bdec65ead3fdec33c30034a76793978e336b54f435bc25'
OUT=Path('work/output/0.1.28-field-ui-assets')
QUEUE=Path('work/translation/en/executable_field_ui_0001.json')
# Complete drafts are retained in the historical native-menu queues. Compact
# camera choices retain the meaning of the camera's focus selection.
LABELS={3:'Status',5:'Gallery',11:'ON',12:'OFF',20:'Amulets',49:'Accessories',
 50:'Quests',51:'Catalog',52:'Options',53:'Tutorial',66:'BGM Volume',
 67:'SFX/Voice Volume',68:'Custom Soundtrack',69:'Battle BGM Settings',
 70:'Default Battle Camera',71:'Default Defense Turn',72:'Show Route Conductor',
 73:'Data Install',74:'MIN',75:'MAX',76:'Default',77:'Allies',78:'Enemies',
 79:'Distant',80:'Manual',81:'Auto',109:'Battle',110:'Field',111:'Menu',
 125:'Spirit',166:'Volume',194:'Wait',228:'Active'}
HELP={57:'View character stats.{0E}',58:'Check quest progress.{0E}',
 59:'Browse acquired items.{0E}',
 60:"Browse Heroes Phantasia's{11}collection of game information.{0E}",
 61:'Review controls and game rules.{0E}',62:'Adjust options.{0E}'}
ACTIONS={0:'Jump',1:'Inspect',2:'Talk',3:'Push',4:'Warp'}

def sha(data):return hashlib.sha256(data).hexdigest()
def notation(raw):return ''.join('{%02X}'%ord(c) if ord(c)<32 else c for c in raw.decode('cp932'))

def build():
    incoming=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('executable.en.json').read_text())
    original=ORIGINAL.read_bytes()
    if sha(incoming)!=SOURCE_SHA or before['output_elf_sha256']!=SOURCE_SHA or sha(original)!=ORIGINAL_SHA:
        raise ValueError('Frozen source identity differs')
    e=Elf(incoming);o=Elf(original);refs,_=reference_index(o);ss=sections(incoming);ph=[list(p)for p in e.ph]
    old= incoming[ph[2][1]:ph[2][1]+ph[2][4]];payload=bytearray(old);result=bytearray(incoming)
    floats=struct.unpack('<131f',incoming[e.file_offset(before['float_width_lut_rva'],524):e.file_offset(before['float_width_lut_rva'],524)+524])
    entries=[];rows=[];allowed=set();dedup={}
    for table,base,targets in ((0,0x94760,LABELS),(1,0x95450,HELP),(6,0x96ce0,ACTIONS)):
        if o.word(0x306580+table*4)!=base or e.word(0x306580+table*4)!=base:raise ValueError('Native table binding differs')
        for index,target in targets.items():
            slot=base+index*4;source=o.word(slot);raw=cstring(o,source);text=notation(raw[:-1])
            match=[r for r in refs if r['kind']=='R_MIPS_32' and r['sites']==[slot] and r['address']==source]
            if len(match)!=1 or len(match[0]['relocation_ordinals'])!=1:raise ValueError('Typed pointer is not unique')
            ordinal=match[0]['relocation_ordinals'][0]
            if e.relocs[ordinal]!=(slot,2) or e.word(slot)!=source or cstring(e,source)!=raw:raise ValueError('Source slot already differs')
            validate_controls(text,target);new=encoded_text(target,'ascii')+b'\0'
            if new not in dedup:dedup[new]=ph[2][2]+len(payload);payload.extend(new)
            rva=dedup[new];f=e.file_offset(slot,4);struct.pack_into('<I',result,f,rva);allowed.update(range(f,f+4))
            widths=[sum(floats[c]for c in line if 32<=c<=126)for line in new[:-1].split(b'\x11')]
            # Source controls in these six help records have no printed arguments.
            limit=440 if table==1 else 72 if index in (76,77,78,79,194,228) else 200
            if max(widths)>limit:raise ValueError('Screenshot field width exceeded: '+target)
            entry=dict(table=table,native_index=index,pointer_slot=slot,expected_word=source,source_sha256=sha(raw),
              relocation_ordinal=ordinal,target=target,target_rva=rva,encoded_bytes=len(new),line_widths_px=widths,
              conservative_available_width_px=limit,individual_native_layout_verified=False)
            entries.append(entry)
            rows.append(dict(id=f'field_table{table}_{index:03}',file='PSP_GAME/SYSDIR/EBOOT.decrypted.elf',offset=o.file_offset(source),
              byte_length=len(raw)-1,encoding='cp932',category='ui',source=text,target=target,status='translated',
              context='Field UI reported in player screenshots; typed source table and generic Latin renderer.',
              decisions='Relocate complete text; retain source control bytes. Compact option choices fit their individual fields.'))
    # The descriptor route returns table0 text directly to the Latin-capable
    # generic renderer; it does not copy text into a source-size local buffer.
    if incoming[e.file_offset(0x77b7c,104):e.file_offset(0x77b7c,104)+104]!=original[o.file_offset(0x77b7c,104):o.file_offset(0x77b7c,104)+104]:
        raise ValueError('Inherited descriptor rendering route differs')
    banner_source=source_payload();banner_target=encoded_text(TARGET,'ascii')+b'\0'
    validate_controls(notation(banner_source[:-1]),TARGET)
    key=ph[2][2]+len(payload);payload.extend(banner_source)
    target=ph[2][2]+len(payload);payload.extend(banner_target)
    payload.extend(bytes(align(len(payload),16)-len(payload)));hoff=len(payload);helper=ph[2][2]+hoff
    code=hook(key,target,len(banner_source));payload.extend(code);additions=relocate_code(payload,hoff,len(code))
    f=e.file_offset(SITE,8)
    if incoming[f:f+8]!=EXPECTED or any(off in (SITE,SITE+4) and flags>>8&255==0 for off,flags in e.relocs):
        raise ValueError('Styled parser entry/relocation differs')
    result[f:f+8]=struct.pack('<II',j(helper),0);allowed.update(range(f,f+8))
    additions.insert(0,reloc(SITE,4,0))
    rows.append(dict(id='field_episode_1_banner',file='fld/event/d01.evt',offset=0x10949,byte_length=35,encoding='cp932',category='ui',
      source=notation(banner_source[:-1]),target=TARGET,status='translated',
      context='Episode 1 modal banner reported in player screenshot.',
      decisions='Exact NUL-terminated payload replacement at the common styled-text parser; event bytecode remains byte-identical.'))
    pf=len(result)+((ph[2][2]-len(result))%ph[2][7]);result.extend(bytes(pf-len(result)));result.extend(payload)
    ph[2][1]=pf;ph[2][4]=ph[2][5]=len(payload);ss[55][4]=pf;ss[55][5]=len(payload)
    rp=e.ph[3];relfile=align(len(result),16);result.extend(bytes(relfile-len(result)))
    oldrel=incoming[rp[1]:rp[1]+rp[4]];result.extend(oldrel+b''.join(additions))
    for s in ss:
        if s[1]==0x700000a0:s[4]=relfile+s[4]-rp[1]
    ss.append([0,0x700000a0,0,0,relfile+len(oldrel),len(additions)*8,0,55,4,8])
    ph[3][1]=relfile;ph[3][4]=len(oldrel)+len(additions)*8
    shoff=(len(result)+3)&~3;result.extend(bytes(shoff-len(result)))
    for s in ss:result.extend(struct.pack('<10I',*s))
    phoff=struct.unpack_from('<I',incoming,28)[0];struct.pack_into('<8I',result,phoff+64,*ph[2]);allowed.update(range(phoff+64,phoff+96))
    struct.pack_into('<8I',result,phoff+96,*ph[3]);allowed.update(range(phoff+96,phoff+128))
    struct.pack_into('<I',result,32,shoff);allowed.update(range(32,36))
    struct.pack_into('<H',result,48,len(ss));allowed.update(range(48,50));result=bytes(result)
    if any(a!=b and i not in allowed for i,(a,b)in enumerate(zip(incoming,result))):raise ValueError('Unselected inherited file bytes changed')
    report=copy.deepcopy(before)
    for k in ('output','approved_dry_plan_sha256','written_readback_verified'):report.pop(k,None)
    report.update(version='0.1.28',input_version='0.1.27',input_sha256=SOURCE_SHA,output_elf_sha256=sha(result),
      output_sha256=sha(result),elf_bytes=len(result),payload_bytes=len(payload),module_growth_bytes=len(payload),
      font_native_tail_loaded_extension_bytes=len(payload),font_native_tail_loaded_extension_sha256=sha(payload),
      runtime_verified=False,status='field_ui_candidate')
    report.update(total_relocations=len(Elf(result).relocs),added_relocations=len(Elf(result).relocs)-report['original_relocations'],
      relocation_table_sha256=sha(oldrel+b''.join(additions)))
    report['field_ui_patch']=dict(entries=entries,rows=len(rows),menu_rows=len(entries),loaded_growth_bytes=len(payload)-len(old),new_relocations=len(additions),
      source_controls_preserved=True,old_LOAD2_prefix_exact=True,individual_native_layout_verified=False,
      episode_inline_banner=dict(site=SITE,helper_rva=helper,helper_bytes=len(code),helper_sha256=sha(payload[hoff:hoff+len(code)]),
        source_payload_rva=key,target_payload_rva=target,source_payload_bytes=len(banner_source),target_payload_bytes=len(banner_target),
        source_payload_sha256=sha(banner_source),target_payload_sha256=sha(banner_target),target=TARGET,
        event_bytecode_unchanged=True,common_styled_parser_redirect_installed=True,natural_scene_interception_verified=False,
        native_cursor_reset_and_destructor_audited=True))
    report['memory_forecast']['proposed_module_bytes']=ph[2][2]+((len(payload)+63)//64)*64
    report['memory_forecast']['forecast_after_both_requests']-=((len(payload)-len(old)+63)//64)*64
    validate(result,report,incoming,before)
    return result,report,dict(schema_version=1,language='en',rows=rows)

def validate(data,report,incoming,before):
    e=Elf(data);old=Elf(incoming);coverage(data)
    if e.relocs[:len(old.relocs)]!=old.relocs or pair_shapes(data)[:len(pair_shapes(incoming))]!=pair_shapes(incoming):raise ValueError('Inherited relocation semantics differ')
    entries=report['field_ui_patch']['entries'];mask={i for r in entries for i in range(r['pointer_slot'],r['pointer_slot']+4)}
    banner=report['field_ui_patch']['episode_inline_banner'];mask.update(range(SITE,SITE+8))
    for r in entries:
        if e.word(r['pointer_slot'])!=r['target_rva'] or cstring(e,r['target_rva'])!=encoded_text(r['target'],'ascii')+b'\0':
            raise ValueError('Complete installed English text differs')
    start=before['font_trailer_offset'];end=before['font_compressed_file_offset']+before['font_compressed_bytes']
    if data[start:end]!=incoming[start:end]:raise ValueError('Font trailer changed')
    authoritative_font_metadata(data,report);validate_native_png_metadata(data,report)
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);b,visited,skipped,_=section_load(data,base);p,_,_=loaded(data,base)
        if p!=[b[n][:e.ph[n][4]]for n in range(3)] or visited!=e.relocs or skipped:raise ValueError('PH/SHT load differs')
        if a[1]!=b[1] or a[2]!=b[2][:len(a[2])]:raise ValueError('Inherited LOAD1/2 changed')
        if any(x!=y and i not in mask for i,(x,y)in enumerate(zip(a[0],b[0]))):raise ValueError('Unselected LOAD0 changed')
        for r in entries:
            if struct.unpack_from('<I',b[0],r['pointer_slot'])[0]!=base+r['target_rva']:raise ValueError('Loaded pointer differs')
        if struct.unpack_from('<II',b[0],SITE)!=(j(base+banner['helper_rva']),0):raise ValueError('Loaded parser redirect differs')
        off=banner['helper_rva']-e.ph[2][2];code=bytes(b[2][off:off+banner['helper_bytes']])
        tests=cases(code,base+banner['helper_rva'],base+banner['source_payload_rva'],base+banner['target_payload_rva'],source_payload(),base+SITE+8)
        models.append(dict(base=base,records=len(visited),selected_pointers=len(entries),unselected_memory_exact=True,banner_instruction_cases=len(tests)))
    report['field_ui_patch']['loader_models']=models

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256');a=ap.parse_args()
    data,report,queue=build();p=report['field_ui_patch']
    print(json.dumps(dict(version=report['version'],sha256=sha(data),rows=p['rows'],growth=p['loaded_growth_bytes'],
      loader_models=p['loader_models'],sample=p['entries'][:3],options=[r for r in p['entries']if r['native_index'] in (67,71,77,78,79)]),indent=2))
    if not a.write:print('DRY RUN');return
    if a.expected_sha256!=sha(data) or OUT.exists() or QUEUE.exists():raise ValueError('Reviewed hash and fresh destinations required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data);(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n')
    QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    validate((OUT/'EBOOT.BIN').read_bytes(),report,SOURCE.read_bytes(),json.loads(SOURCE.with_name('executable.en.json').read_text()))
    print('Fresh assets and translation queue written; readback passed.')

if __name__=='__main__':main()
