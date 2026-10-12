"""Prepare guarded 0.1.29 save/menu and Field Tutorial corrections; dry first."""
import argparse,copy,json,struct
from pathlib import Path
from field_ui_patch import sha,notation
from executable_text_patch import Elf,ORIGINAL,ORIGINAL_SHA,reference_index,encoded_text
from native_menu_install_plan import cstring
from prepare_relocation_019 import sections,section_load,coverage,pair_shapes
from compact_vwf_patch import loaded
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from dialogue_tokens import validate_controls
from build_menu_patch import align,relocate_code,reloc
from live_vwf import j,i
from field_tutorial_width import hook,cases,SITE,EXPECTED,CONTINUATION

SOURCE=Path('work/output/0.1.28-field-ui-assets/EBOOT.BIN')
SOURCE_SHA='c7435d60f2599991d279adba6147aa4f387f1839089692e0bf1d60533d305f17'
OUT=Path('work/output/0.1.29-save-tutorial-assets')
QUEUE=Path('work/translation/en/executable_save_ui_0001.json')
TARGETS=((0,0x94760,126,'Save'),(0,0x94760,127,'Delete Data'),(0,0x94760,16,'Cancel'),
 (1,0x95450,44,'Next, system save data will be updated.{11}System data includes Gallery unlocks.{11}If you do not save, newly unlocked Gallery{11}content will not be saved.{0E}'))

def build():
    incoming=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('executable.en.json').read_text());original=ORIGINAL.read_bytes()
    if sha(incoming)!=SOURCE_SHA or before['output_elf_sha256']!=SOURCE_SHA or sha(original)!=ORIGINAL_SHA:raise ValueError('Frozen source differs')
    e=Elf(incoming);o=Elf(original);refs,_=reference_index(o);ss=sections(incoming);ph=[list(p)for p in e.ph]
    old=incoming[ph[2][1]:ph[2][1]+ph[2][4]];payload=bytearray(old);result=bytearray(incoming);allowed=set();mask=set();entries=[];rows=[]
    floats=struct.unpack('<131f',incoming[e.file_offset(before['float_width_lut_rva'],524):e.file_offset(before['float_width_lut_rva'],524)+524])
    widths=list(struct.unpack('<131I',incoming[e.file_offset(before['body_integer_lut_rva'],524):e.file_offset(before['body_integer_lut_rva'],524)+524]))
    for table,base,index,target in TARGETS:
        slot=base+index*4;source=o.word(slot);raw=cstring(o,source);text=notation(raw[:-1]);validate_controls(text,target)
        matched=[r for r in refs if r['kind']=='R_MIPS_32' and r['sites']==[slot] and r['address']==source]
        if len(matched)!=1 or len(matched[0]['relocation_ordinals'])!=1:raise ValueError('Typed pointer not unique')
        ordinal=matched[0]['relocation_ordinals'][0]
        if e.relocs[ordinal]!=(slot,2)or e.word(slot)!=source or cstring(e,source)!=raw:raise ValueError('Selected source differs')
        new=encoded_text(target,'ascii')+b'\0';rva=ph[2][2]+len(payload);payload.extend(new)
        f=e.file_offset(slot,4);struct.pack_into('<I',result,f,rva);allowed.update(range(f,f+4));mask.update(range(slot,slot+4))
        line_widths=[sum(floats[c]for c in line if 32<=c<=126)for line in new[:-1].split(b'\x11')];limit=440 if table==1 else 104
        if max(line_widths)>limit:raise ValueError('Text exceeds screenshot field')
        entries.append(dict(table=table,native_index=index,pointer_slot=slot,expected_word=source,target_rva=rva,target=target,
            source_sha256=sha(raw),relocation_ordinal=ordinal,encoded_bytes=len(new),line_widths_px=line_widths,available_width_px=limit))
        rows.append(dict(id=f'save_table{table}_{index:03}',file='PSP_GAME/SYSDIR/EBOOT.decrypted.elf',offset=o.file_offset(source),
            byte_length=len(raw)-1,encoding='cp932',category='ui',source=text,target=target,status='translated',
            context='Player-reported save-point menu/system notice.',decisions='Complete meaning and original control order retained; typed pointer relocated.'))
    payload.extend(bytes(align(len(payload),16)-len(payload)));hoff=len(payload);helper=ph[2][2]+hoff;code=hook(before['body_integer_lut_rva']);payload.extend(code)
    additions=relocate_code(payload,hoff,len(code))
    f=e.file_offset(SITE,16)
    if incoming[f:f+16]!=EXPECTED or any(SITE<=off<SITE+16 and flags>>8&255==0 for off,flags in e.relocs):raise ValueError('Constructor site differs')
    result[f:f+8]=struct.pack('<II',j(helper),0);allowed.update(range(f,f+8));mask.update(range(SITE,SITE+8));additions.insert(0,reloc(SITE,4,0))
    # This branch composes the two already translated table strings. Match the
    # current unscaled renderer widths; both constants are exactly LUI floats.
    field=cstring(e,e.word(0x94918))[:-1];tutorial=cstring(e,e.word(0x94834))[:-1]
    if field!=b'Field' or tutorial!=b'Tutorial':raise ValueError('Composed heading differs')
    gap=sum(floats[c]for c in field)+floats[32];left=int((480-gap-sum(floats[c]for c in tutorial))/2)
    changes=[]
    for site,expected,value in ((0x940c8,0x3c04431c,left),(0x94128,0x3c044282,gap)):
        bits=struct.unpack('<I',struct.pack('<f',value))[0]
        if bits&65535:raise ValueError('Heading constant needs a different instruction form')
        if e.word(site)!=expected:raise ValueError('Heading placement site differs')
        f=e.file_offset(site,4);word=i(15,0,4,bits>>16);struct.pack_into('<I',result,f,word);allowed.update(range(f,f+4));mask.update(range(site,site+4))
        changes.append(dict(site=site,expected_word=expected,replacement_word=word,value_px=value))
    pf=len(result)+((ph[2][2]-len(result))%ph[2][7]);result.extend(bytes(pf-len(result)));result.extend(payload)
    ph[2][1]=pf;ph[2][4]=ph[2][5]=len(payload);ss[55][4]=pf;ss[55][5]=len(payload)
    rp=e.ph[3];relfile=align(len(result),16);result.extend(bytes(relfile-len(result)));oldrel=incoming[rp[1]:rp[1]+rp[4]];result.extend(oldrel+b''.join(additions))
    for s in ss:
        if s[1]==0x700000a0:s[4]=relfile+s[4]-rp[1]
    ss.append([0,0x700000a0,0,0,relfile+len(oldrel),len(additions)*8,0,55,4,8]);ph[3][1]=relfile;ph[3][4]=len(oldrel)+len(additions)*8
    shoff=align(len(result),4);result.extend(bytes(shoff-len(result)))
    for s in ss:result.extend(struct.pack('<10I',*s))
    phoff=struct.unpack_from('<I',incoming,28)[0]
    for n in (2,3):struct.pack_into('<8I',result,phoff+n*32,*ph[n]);allowed.update(range(phoff+n*32,phoff+n*32+32))
    struct.pack_into('<I',result,32,shoff);allowed.update(range(32,36));struct.pack_into('<H',result,48,len(ss));allowed.update(range(48,50));result=bytes(result)
    if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,result))):raise ValueError('Unselected file bytes changed')
    report=copy.deepcopy(before)
    for k in ('output','approved_dry_plan_sha256','written_readback_verified'):report.pop(k,None)
    report.update(version='0.1.29',input_version='0.1.28',input_sha256=SOURCE_SHA,output_elf_sha256=sha(result),output_sha256=sha(result),
        elf_bytes=len(result),payload_bytes=len(payload),module_growth_bytes=len(payload),font_native_tail_loaded_extension_bytes=len(payload),
        font_native_tail_loaded_extension_sha256=sha(payload),total_relocations=len(Elf(result).relocs),
        added_relocations=len(Elf(result).relocs)-before['original_relocations'],relocation_table_sha256=sha(oldrel+b''.join(additions)),runtime_verified=False,status='save_tutorial_candidate')
    report['save_tutorial_patch']=dict(entries=entries,rows=len(rows),loaded_growth_bytes=len(payload)-len(old),new_relocations=len(additions),
        source_controls_preserved=True,old_LOAD2_prefix_exact=True,constructor_site=SITE,helper_rva=helper,helper_bytes=len(code),
        helper_sha256=sha(payload[hoff:hoff+len(code)]),continuation=CONTINUATION,heading_placement=changes,
        header_already_English_in_input=True,header_left_px=left,header_separator_px=gap,native_verified=False)
    report['memory_forecast']['proposed_module_bytes']=ph[2][2]+align(len(payload),64)
    report['memory_forecast']['forecast_after_both_requests']-=align(len(payload),64)-align(len(old),64)
    validate(result,report,incoming,mask,widths);return result,report,dict(schema_version=1,language='en',rows=rows)

def validate(data,report,incoming,mask,widths):
    e=Elf(data);old=Elf(incoming);coverage(data);p=report['save_tutorial_patch']
    if e.relocs[:len(old.relocs)]!=old.relocs or pair_shapes(data)[:len(pair_shapes(incoming))]!=pair_shapes(incoming):raise ValueError('Inherited relocations changed')
    for r in p['entries']:
        if e.word(r['pointer_slot'])!=r['target_rva']or cstring(e,r['target_rva'])!=encoded_text(r['target'],'ascii')+b'\0':raise ValueError('Installed target differs')
    authoritative_font_metadata(data,report);validate_native_png_metadata(data,report);models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);b,visited,skipped,_=section_load(data,base);program,_,_=loaded(data,base)
        if program!=[b[n][:e.ph[n][4]]for n in range(3)]or visited!=e.relocs or skipped:raise ValueError('PH/SHT load differs')
        if a[1]!=b[1]or a[2]!=b[2][:len(a[2])]:raise ValueError('Inherited LOAD1/2 differs')
        if any(x!=y and n not in mask for n,(x,y)in enumerate(zip(a[0],b[0]))):raise ValueError('Unselected LOAD0 differs')
        for r in p['entries']:
            if struct.unpack_from('<I',b[0],r['pointer_slot'])[0]!=base+r['target_rva']:raise ValueError('Loaded pointer differs')
        if struct.unpack_from('<II',b[0],SITE)!=(j(base+p['helper_rva']),0):raise ValueError('Loaded constructor hook differs')
        off=p['helper_rva']-e.ph[2][2];code=bytes(b[2][off:off+p['helper_bytes']])
        tests=cases(widths,code,base+p['helper_rva'],base+CONTINUATION,base+report['body_integer_lut_rva'])
        models.append(dict(base=base,records=len(visited),selected_pointers=4,unselected_memory_exact=True,instruction_cases=tests))
    p['loader_models']=models

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256');a=ap.parse_args()
    data,report,queue=build();p=report['save_tutorial_patch'];print(json.dumps(dict(version=report['version'],sha256=sha(data),growth=p['loaded_growth_bytes'],relocations=p['new_relocations'],entries=p['entries'],heading=p['heading_placement'],cases=p['loader_models'][0]['instruction_cases']),indent=2))
    if not a.write:print('DRY RUN');return
    if a.expected_sha256!=sha(data)or OUT.exists()or QUEUE.exists():raise ValueError('Reviewed hash and fresh destinations required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data);(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n')
    QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if (OUT/'EBOOT.BIN').read_bytes()!=data:raise ValueError('Written executable differs')
    print('Fresh assets and working targets written; readback passed.')

if __name__=='__main__':main()
