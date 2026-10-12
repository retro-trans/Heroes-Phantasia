"""Prepare the reviewed Serish lip-anchor correction; dry first, fresh assets."""
import argparse,copy,json,struct
from pathlib import Path
from executable_text_patch import Elf
from build_menu_patch import align,relocate_code
from bubble_layout_hooks import geometry
from bubble_metrics import load_templates
from prepare_relocation_019 import sections,coverage,section_load,pair_shapes
from compact_vwf_patch import loaded
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from field_ui_patch import sha
from live_vwf import j

SOURCE=Path('work/output/0.1.29-save-tutorial-assets/EBOOT.BIN')
SHA='6c4f596036c0bc310cef44dbb326d9aa1511ebd0d3f388cf0d23b3ca3c2f5de7'
OUT=Path('work/output/0.1.30-serish-tail-assets')

def build():
    incoming=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('executable.en.json').read_text())
    if sha(incoming)!=SHA or before['output_elf_sha256']!=SHA:raise ValueError('Frozen .29 identity differs')
    e=Elf(incoming);ss=sections(incoming);ph=[list(p)for p in e.ph];p=ph[2];rp=ph[3]
    oldtarget=next(x['new_target']for x in before['hideo_bubble_fix']['entry_changes']if x['site_rva']==0xe4e0c)
    oldcode=bytearray(geometry(0x2e43c0,True,True,True,131));relocate_code(oldcode,0,len(oldcode))
    if incoming[e.file_offset(oldtarget,len(oldcode)):e.file_offset(oldtarget,len(oldcode))+len(oldcode)]!=oldcode:raise ValueError('Inherited geometry generator differs')
    t=load_templates()[8]
    if t['count']!=10 or t['banks'][0][6]!=(-59.,4.)or t['banks'][1][6]!=(-66.,6.):raise ValueError('Reviewed shape8 tip differs')
    oldpayload=incoming[p[1]:p[1]+p[4]];payload=bytearray(oldpayload)
    payload.extend(bytes(align(len(payload),16)-len(payload)));offset=len(payload);target=p[2]+offset
    code=geometry(0x2e43c0,True,True,True,131,serish_mouth=True);payload.extend(code);additions=relocate_code(payload,offset,len(code))
    result=bytearray(incoming);entry=e.file_offset(0xe4e0c,8)
    if incoming[entry:entry+8]!=struct.pack('<II',j(oldtarget),0)or(0xe4e0c,4)not in e.relocs:raise ValueError('Entry branch/typed relocation differs')
    result[entry:entry+8]=struct.pack('<II',j(target),0)
    file=len(result)+((p[2]-len(result))%p[7]);result.extend(bytes(file-len(result)));result.extend(payload)
    binding=None
    for n,s in enumerate(ss):
        if s[3]==p[2]and s[4]==p[1]:s[4]=file;s[5]=len(payload);binding=n
    if binding is None:raise ValueError('No loaded payload section')
    relfile=align(len(result),16);result.extend(bytes(relfile-len(result)));oldrel=incoming[rp[1]:rp[1]+rp[4]];result.extend(oldrel+b''.join(additions))
    for s in ss:
        if s[1]==0x700000a0:s[4]=relfile+s[4]-rp[1]
    ss.append([0,0x700000a0,0,0,relfile+len(oldrel),len(additions)*8,0,binding,4,8])
    shoff=align(len(result),4);result.extend(bytes(shoff-len(result)))
    for s in ss:result.extend(struct.pack('<10I',*s))
    ph[2][1]=file;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=relfile;ph[3][4]=len(oldrel)+len(additions)*8
    phoff=struct.unpack_from('<I',incoming,28)[0]
    for n in (2,3):struct.pack_into('<8I',result,phoff+32*n,*ph[n])
    struct.pack_into('<I',result,32,shoff);struct.pack_into('<H',result,48,len(ss));result=bytes(result);out=Elf(result);coverage(result)
    allowed=set(range(entry,entry+8))|set(range(32,36))|set(range(48,50))|set(range(phoff+64,phoff+128))
    if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,result))):raise ValueError('Unselected file bytes changed')
    if out.relocs[:len(e.relocs)]!=e.relocs or pair_shapes(result)[:len(pair_shapes(incoming))]!=pair_shapes(incoming):raise ValueError('Inherited relocations differ')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        old,_,_,_=section_load(incoming,base);new,visited,skipped,_=section_load(result,base);program,_,_=loaded(result,base)
        expected=bytearray(old[0]);struct.pack_into('<I',expected,0xe4e0c,j(base+target))
        if new[0]!=expected or new[1]!=old[1]or new[2][:len(oldpayload)]!=old[2]or skipped or program!=[new[n][:out.ph[n][4]]for n in range(3)]:raise ValueError('Unselected memory or PH/SHT model differs')
        models.append(dict(base=base,relocations=len(visited),unchanged_memory_except_entry_branch=True))
    report=copy.deepcopy(before)
    for k in ('output','approved_dry_plan_sha256','written_readback_verified'):report.pop(k,None)
    report.update(version='0.1.30',input_version='0.1.29',input_sha256=SHA,output_elf_sha256=sha(result),output_sha256=sha(result),elf_bytes=len(result),
      payload_bytes=len(payload),module_growth_bytes=len(payload),font_native_tail_loaded_extension_bytes=len(payload),font_native_tail_loaded_extension_sha256=sha(payload),
      total_relocations=len(out.relocs),added_relocations=len(out.relocs)-before['original_relocations'],relocation_table_sha256=sha(oldrel+b''.join(additions)),runtime_verified=False,status='serish_tail_candidate')
    report['serish_tail_patch']=dict(site_rva=0xe4e0c,old_target=oldtarget,helper_rva=target,helper_bytes=len(code),helper_sha256=sha(payload[offset:offset+len(code)]),
      loaded_growth_bytes=len(payload)-len(oldpayload),new_relocations=len(additions),three_base_models=models,
      template=8,tip_index=6,native_center=[369,99],portrait_center=[222,148],portrait_lip_reference=[21,-14],screen_lip_reference=[243,134],
      text='Who will accompany you?{12}{0E}',source_record='96a6bd56348c7203229c',resources=['phase/bin/p101010.bin','phase/bin/p101011.bin'],
      only_tip_changes=True,all_other_records_and_geometry_inherited=True,animated_states_inherited=True,source_controls_unchanged=True,
      landmark_kind='Visually reviewed source-portrait landmark, not automatic mouth tracking',native_instruction_verified=False,natural_scene_verified=False)
    report['memory_forecast']['proposed_module_bytes']=p[2]+align(len(payload),64)
    report['memory_forecast']['forecast_after_both_requests']-=align(len(payload),64)-align(len(oldpayload),64)
    authoritative_font_metadata(result,report)
    if validate_native_png_metadata(result,report)!=validate_native_png_metadata(incoming,before):raise ValueError('PNG metadata differs')
    return result,report

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256');a=ap.parse_args()
    data,report=build();print(json.dumps({k:report[k]for k in ('version','output_elf_sha256','elf_bytes','serish_tail_patch')},indent=2))
    if not a.write:print('DRY RUN');return
    if a.expected_sha256!=sha(data)or OUT.exists():raise ValueError('Reviewed digest and fresh folder required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data);(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n')
    if (OUT/'EBOOT.BIN').read_bytes()!=data:raise ValueError('Readback differs')
if __name__=='__main__':main()
