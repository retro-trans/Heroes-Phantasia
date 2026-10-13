"""Cover both native font sizes used by the corrected notice dispatcher."""
import argparse,copy,json,struct
from pathlib import Path
from executable_text_patch import Elf
from dialogue_vwf_hooks import Block,r
from dialogue_ruby_hooks import small_latin_font
from live_vwf import i,j
from prepare_english_bubbles_v10 import relocate
from prepare_relocation_019 import sections,coverage,section_load
from prepare_bubble_scenes_036 import sha
from build_menu_patch import align
from font_vram_hooks import instruction_model
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

BASE=Path('work/output/0.1.57-title-credit-vwf-4x-candidate')
OUT=Path('work/output/0.1.58-elevator-crash-assets')
HELPER=0x2e6ed0
CAPACITY=128

def generate():
    h=Block();h.emit(r(8,0,20));h.branch(5,7,9,'large')
    h.emit(i(11,4,24,32));h.branch(5,24,0,'small')
    h.emit(i(11,4,24,131));h.branch(4,24,0,'small')
    h.emit(i(13,0,24,127));h.branch(4,4,24,'small')
    h.emit(i(35,29,24,0x20),i(15,0,25,14),i(13,25,25,0xe430));h.branch(4,24,25,'large')
    # One typed HI/LO pair, then relative deltas, retains all three reviewed
    # resident callers and adds the notice caller inside the original slot.
    previous=0xee430
    for caller in (0xee404,0xee2b0,0xee308):
        h.emit(i(9,25,25,caller-previous));h.branch(4,24,25,'large');previous=caller
    h.label('small');h.emit(j(0xea4b4),0);h.label('large');h.emit(j(0xea550),0)
    code=h.finish()
    if len(code)>CAPACITY:raise ValueError('Small font helper exceeds reviewed slot')
    return code+bytes(CAPACITY-len(code))

def build():
    incoming=(BASE/'EBOOT.BIN').read_bytes();e=Elf(incoming);before=json.loads((BASE/'manifest.en.json').read_bytes())['setup_patch']
    if sha(incoming)!='c6c3185042b9fbb776115cdf34110ba7f342b7e87a24618e11831e27d031e3f7':raise ValueError('Frozen .57 executable differs')
    previous=small_latin_font(131);previous,_=relocate(previous,HELPER,0,0);at=e.file_offset(HELPER,CAPACITY)
    if incoming[at:at+len(previous)]!=previous or any(incoming[at+len(previous):at+CAPACITY]):raise ValueError('Reviewed font helper or padding differs')
    code,additions=relocate(generate(),HELPER,0,0);result=bytearray(incoming);result[at:at+CAPACITY]=code;allowed=set(range(at,at+CAPACITY))
    removed={n for n,(site,f)in enumerate(e.relocs)if not f>>8&255 and HELPER<=site<HELPER+CAPACITY}
    if any(n<before['original_relocations']for n in removed):raise ValueError('Original relocation selected')
    kept=[v for n,v in enumerate(e.relocs)if n not in removed];rels=kept+additions;ss=sections(incoming);ph=[list(v)for v in e.ph];rp=ph[3];pos=align(len(result),16)
    result.extend(bytes(pos-len(result)));result.extend(b''.join(struct.pack('<II',*v)for v in rels))
    for s in ss:
        if s[1]!=0x700000a0:continue
        first=(s[4]-rp[1])//8;count=s[5]//8;s[4]=pos+(first-sum(n<first for n in removed))*8;s[5]-=sum(n in removed for n in range(first,first+count))*8
    ss.append([0,0x700000a0,0,0,pos+len(kept)*8,len(additions)*8,0,1,4,8]);ph[3][1]=pos;ph[3][4]=len(rels)*8;shoff=align(len(result),4);result.extend(bytes(shoff-len(result)));result.extend(b''.join(struct.pack('<10I',*s)for s in ss))
    po=struct.unpack_from('<I',incoming,28)[0];struct.pack_into('<8I',result,po+96,*ph[3]);allowed.update(range(po+96,po+128));struct.pack_into('<I',result,32,shoff);allowed.update(range(32,36));struct.pack_into('<H',result,48,len(ss));allowed.update(range(48,50))
    data=bytes(result);oe=Elf(data);coverage(data)
    if oe.ph[:3]!=e.ph[:3] or oe.relocs[:before['original_relocations']]!=e.relocs[:before['original_relocations']] or any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,data))):raise ValueError('Original/unselected bytes differ')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);b,visited,skipped,_=section_load(data,base)
        if skipped or visited!=oe.relocs or a[1:]!=b[1:] or any(x!=y and not HELPER<=n<HELPER+CAPACITY for n,(x,y)in enumerate(zip(a[0],b[0]))):raise ValueError('Unselected loaded bytes differ')
        model=instruction_model();model['execute'].__globals__['B']=base;count=0
        for size in (4,8):
            for caller in (0xee430,0xee404,0xee2b0,0xee308,0xee2dc):
                for glyph in (*range(256),0x8145,0x82a0,0xf040,0xf041):
                    regs=[0]+[0x12340000+n for n in range(1,32)];regs[4]=glyph;regs[7]=size;regs[9]=8;regs[29]=0x230000;mem={0x230020+n:v for n,v in enumerate(struct.pack('<I',base+caller))}
                    pc,out,_=model['execute'](bytes(b[0][HELPER:HELPER+CAPACITY]),regs,mem)
                    large=size!=8 or (32<=glyph<131 and glyph!=127 and caller!=0xee2dc)
                    if pc!=base+(0xea550 if large else 0xea4b4) or out[20]!=regs[8] or any(x!=y for n,(x,y)in enumerate(zip(regs,out))if n not in (20,24,25)):raise ValueError('Small font route/ABI differs')
                    count+=1
        models.append(dict(base=base,cases=count,all_original_callers_preserved=True,outside_mask_exact=True,loaded_extents_exact=True))
    report=copy.deepcopy(before);report.update(version='0.1.58',input_version='0.1.57',input_sha256=sha(incoming),output_sha256=sha(data),output_elf_sha256=sha(data),elf_bytes=len(data),total_relocations=len(oe.relocs),added_relocations=len(oe.relocs)-before['original_relocations'],runtime_verified=False)
    proof=dict(version='0.1.58',helper_rva=HELPER,helper_bytes=CAPACITY,helper_sha256=sha(code),new_return_gate=0xee308,original_return_gates=[0xee430,0xee404,0xee2b0],destination_size_and_native_glyph_path_preserved=True,models=models,loaded_growth_bytes=0,natural_elevator_playback_verified=False)
    report['elevator_small_font_058']=proof;report['additional_scopes']['centered_small_font_route']=dict(rva=HELPER,bytes=CAPACITY,sha256=sha(code),loaded_growth_bytes=0)
    for chunk in report['native_tail_compaction']['chunks']:chunk['output_sha256']=sha(data[chunk['file_offset']:chunk['file_offset']+chunk['bytes']])
    authoritative_font_metadata(data,report);validate_native_png_metadata(data,report)
    return data,report

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--write',action='store_true');opts=a.parse_args();data,report=build();print(json.dumps(report['elevator_small_font_058']|dict(executable_sha256=sha(data)),indent=2))
    if not opts.write:return
    if OUT.exists():raise ValueError('Fresh destination required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data);(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
