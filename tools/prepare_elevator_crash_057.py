"""Route Latin glyphs before the centered-notice native font search.

The single typed mode-two caller is covered; native glyphs keep their original
renderer. Reuses reviewed zero-filled text storage without loaded growth.
"""
import argparse, copy, json, struct
from pathlib import Path
from executable_text_patch import Elf
from dialogue_vwf_hooks import route
from live_vwf import jal
from build_menu_patch import align
from prepare_english_bubbles_v10 import relocate
from prepare_relocation_019 import sections, coverage, section_load
from prepare_bubble_scenes_036 import sha
from font_vram_hooks import instruction_model
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

BASE=Path('work/output/0.1.56-title-credit-vwf-4x-candidate')
OUT=Path('work/output/0.1.57-elevator-crash-assets')
SITE=0xee300

def build():
    incoming=(BASE/'EBOOT.BIN').read_bytes();e=Elf(incoming)
    before=json.loads((BASE/'manifest.en.json').read_bytes())['setup_patch']
    if sha(incoming)!='cfca3ea96f5328b6c9ae89a14fe1eb3669a75c206cb3dbd4270b49fc6ab93047': raise ValueError('Frozen .56 executable differs')
    callers=[s for s,f in e.relocs if f&15==4 and e.word(s)==jal(0xea718)]
    if callers!=[SITE]: raise ValueError('Native mode-two caller inventory differs')
    code=route(0xea718,131);free=copy.deepcopy(before['menu_labels_052']['remaining_pool_ranges'])
    span=next(v for v in free if v[1]-align(v[0],4)>=len(code));helper=align(span[0],4)
    if any(incoming[e.file_offset(helper):e.file_offset(helper)+len(code)]): raise ValueError('Reviewed pool is occupied')
    if any(f&15==2 and not f>>8&255 and helper<=e.word(s)<helper+len(code) for s,f in e.relocs): raise ValueError('Typed owner enters pool')
    code,additions=relocate(code,helper,0,0);result=bytearray(incoming);allowed=set();mask=set()
    for rva,raw in ((helper,code),(SITE,struct.pack('<I',jal(helper)))):
        at=e.file_offset(rva,len(raw));result[at:at+len(raw)]=raw;allowed.update(range(at,at+len(raw)));mask.update(range(rva,rva+len(raw)))
    rels=e.relocs+additions;ss=sections(incoming);ph=[list(v)for v in e.ph];rp=ph[3];pos=align(len(result),16)
    result.extend(bytes(pos-len(result)));result.extend(b''.join(struct.pack('<II',*v)for v in rels))
    for s in ss:
        if s[1]==0x700000a0:s[4]=pos+s[4]-rp[1]
    ss.append([0,0x700000a0,0,0,pos+len(e.relocs)*8,len(additions)*8,0,1,4,8])
    ph[3][1]=pos;ph[3][4]=len(rels)*8;shoff=align(len(result),4);result.extend(bytes(shoff-len(result)));result.extend(b''.join(struct.pack('<10I',*s)for s in ss))
    po=struct.unpack_from('<I',incoming,28)[0];struct.pack_into('<8I',result,po+96,*ph[3]);allowed.update(range(po+96,po+128))
    struct.pack_into('<I',result,32,shoff);allowed.update(range(32,36));struct.pack_into('<H',result,48,len(ss));allowed.update(range(48,50))
    data=bytes(result);oe=Elf(data);coverage(data)
    if oe.ph[:3]!=e.ph[:3] or oe.relocs[:len(e.relocs)]!=e.relocs or any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,data))):raise ValueError('Unselected bytes or loaded extents differ')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        old,_,_,_=section_load(incoming,base);new,visited,skipped,_=section_load(data,base)
        if skipped or visited!=oe.relocs or old[1:]!=new[1:] or any(a!=b and n not in mask for n,(a,b)in enumerate(zip(old[0],new[0]))):raise ValueError('Unselected loaded bytes differ')
        model=instruction_model();model['execute'].__globals__['B']=base;count=0
        for glyph in (*range(0,256),0x8145,0x82a0,0xf040,0xf041):
            regs=[0]+[0x12340000+n for n in range(1,32)];regs[9]=glyph
            pc,out,_=model['execute'](bytes(new[0][helper:helper+len(code)]),regs,{})
            if pc!=base+(0xea45c if 32<=glyph<131 and glyph!=127 else 0xea718) or any(a!=b for n,(a,b)in enumerate(zip(regs,out))if n!=24):raise ValueError('Route or ABI differs')
            count+=1
        models.append(dict(base=base,route_cases=count,outside_mask_exact=True,loaded_extents_exact=True))
    report=copy.deepcopy(before);report.update(version='0.1.57',input_version='0.1.56',input_sha256=sha(incoming),output_sha256=sha(data),output_elf_sha256=sha(data),elf_bytes=len(data),total_relocations=len(oe.relocs),added_relocations=len(oe.relocs)-before['original_relocations'],runtime_verified=False)
    span[0]=helper+len(code);report['menu_labels_052']['remaining_pool_ranges']=free
    proof=dict(version='0.1.57',helper_rva=helper,helper_bytes=len(code),helper_sha256=sha(code),call_site=SITE,original_renderer=0xea718,latin_renderer=0xea45c,callers=callers,models=models,loaded_growth_bytes=0,native_glyph_path_preserved=True,natural_elevator_playback_verified=False)
    report['elevator_crash_057']=proof;report['additional_scopes']['centered_font_route']=dict(rva=helper,bytes=len(code),sha256=sha(code),loaded_growth_bytes=0)
    for chunk in report['native_tail_compaction']['chunks']:chunk['output_sha256']=sha(data[chunk['file_offset']:chunk['file_offset']+chunk['bytes']])
    authoritative_font_metadata(data,report);validate_native_png_metadata(data,report)
    return data,report

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--write',action='store_true');opts=a.parse_args();data,report=build();print(json.dumps(report['elevator_crash_057']|dict(executable_sha256=sha(data)),indent=2))
    if not opts.write:return
    if OUT.exists():raise ValueError('Fresh destination required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data);(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
