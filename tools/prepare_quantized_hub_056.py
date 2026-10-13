"""Install the integer-tail fan-origin correction in reclaimed geometry space."""
import argparse,copy,json,struct
from pathlib import Path
from executable_text_patch import Elf
from prepare_relocation_019 import sections,coverage,section_load
from prepare_english_bubbles_v10 import relocate,CORE,CORE_BYTES
from build_menu_patch import align
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from quantized_bubble_hub import generate
from prepare_bubble_scenes_036 import sha
from prepare_dialogue_commands_048 import capture
import english_bubble_layout_v10 as old

BASE=Path('work/output/0.1.55-title-credit-vwf-4x-candidate')
OUT=Path('work/output/0.1.56-dialogue-guard-assets')
UI=Path('work/ui/dialogue/0.1.56')

def build():
    incoming=(BASE/'EBOOT.BIN').read_bytes();m=json.loads((BASE/'manifest.en.json').read_text(encoding='utf8'));before=m['setup_patch'];e=Elf(incoming)
    if sha(incoming)!='20e295dd2932aa74d42fc2ae2d457b0771408b82a8267c774a79fae48e89ac0b':raise ValueError('Frozen .55 executable differs')
    b=before['english_bubble_layout'];hub=b['socket_hub_rva'];capacity=0x2e5200-hub
    # The existing menu pool has 338 bytes recorded by .52; .53 uses its
    # first 30 bytes for chapter labels. Select aligned, still-zero space
    # after those typed owners, without growing any loaded segment.
    free=copy.deepcopy(before['menu_labels_052']['remaining_pool_ranges'])
    region=next(v for v in free if v[1]-v[0]>=128)
    used_end=max(v['target_rva']+len(v['target'])+1 for v in before['field_dialogue_053']['labels'])
    spare=align(max(region[0],used_end),4)
    if spare+128>region[1]:raise ValueError('Reviewed unused pool exhausted')
    original,labels=capture(lambda:old.secondary(b['descriptor_rva'],0,b['tail_fit_rva'],CORE+16,b['contour_rva'],hub),old)
    # secondary returns code plus continuation RVAs; only the third result
    # selects the existing hub continuation. No primary/body code is changed.
    continuation=original[2]
    previous=old.socket_hub(continuation)
    previous,_=relocate(previous,hub,0,0)
    at=e.file_offset(hub,capacity)
    if incoming[at:at+len(previous)]!=previous or any(incoming[at+len(previous):at+capacity]):raise ValueError('Hub source or reclaimed tail bytes differ')
    at_spare=e.file_offset(spare,128)
    if any(incoming[at_spare:at_spare+128]):raise ValueError('Reviewed text pool is not zero')
    if any(flags&15==2 and not flags>>8&255 and spare<=e.word(site)<spare+128 for site,flags in e.relocs):raise ValueError('A typed owner enters the spare pool')
    main,extension,proof=generate(continuation,hub,spare,capacity)
    main,mrels=relocate(main,hub,0,0);extension,srels=relocate(extension,spare,0,0)
    result=bytearray(incoming);allowed=set();masks=[set(),set(),set()]
    for rva,raw,segment in ((hub,main,0),(spare,extension,0)):
        at=e.file_offset(rva,len(raw));result[at:at+len(raw)]=raw;allowed.update(range(at,at+len(raw)));masks[segment].update(range(rva-e.ph[segment][2],rva-e.ph[segment][2]+len(raw)))
    removed={n for n,(site,flags)in enumerate(e.relocs)if flags>>8&255==0 and hub<=site<hub+capacity}
    if any(n<before['original_relocations'] for n in removed):raise ValueError('Original relocation selected')
    kept=[r for n,r in enumerate(e.relocs)if n not in removed];newrels=kept+mrels+srels;rp=e.ph[3];ss=sections(incoming);relfile=align(len(result),16);result.extend(bytes(relfile-len(result)));result.extend(b''.join(struct.pack('<II',*r)for r in newrels))
    for s in ss:
        if s[1]!=0x700000a0:continue
        first=(s[4]-rp[1])//8;count=s[5]//8;s[4]=relfile+(first-sum(n<first for n in removed))*8;s[5]-=sum(n in removed for n in range(first,first+count))*8
    first=relfile+len(kept)*8
    ss.append([0,0x700000a0,0,0,first,(len(mrels)+len(srels))*8,0,1,4,8])
    ph=[list(p)for p in e.ph];ph[3][1]=relfile;ph[3][4]=len(newrels)*8;shoff=align(len(result),4);result.extend(bytes(shoff-len(result)));result.extend(b''.join(struct.pack('<10I',*s)for s in ss))
    phoff=struct.unpack_from('<I',incoming,28)[0];struct.pack_into('<8I',result,phoff+96,*ph[3]);allowed.update(range(phoff+96,phoff+128));struct.pack_into('<I',result,32,shoff);allowed.update(range(32,36));struct.pack_into('<H',result,48,len(ss));allowed.update(range(48,50));out=bytes(result);oe=Elf(out);coverage(out)
    if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,out))):raise ValueError('Unselected executable bytes differ')
    if oe.ph[:3]!=e.ph[:3] or oe.relocs[:before['original_relocations']]!=e.relocs[:before['original_relocations']]:raise ValueError('Loaded extent or original relocations differ')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);z,visited,skipped,_=section_load(out,base)
        if skipped or visited!=oe.relocs:raise ValueError('Relocation loader coverage differs')
        for s in range(3):
            if len(a[s])!=len(z[s]) or any(x!=y and n not in masks[s]for n,(x,y)in enumerate(zip(a[s],z[s]))):raise ValueError('Unselected loaded memory differs')
        models.append(dict(base=base,loaded_extents_exact=True,outside_mask_exact=True))
    report=copy.deepcopy(before);report.update(version='0.1.56',input_version='0.1.55',input_sha256=sha(incoming),output_sha256=sha(out),output_elf_sha256=sha(out),elf_bytes=len(out),total_relocations=len(oe.relocs),added_relocations=len(newrels)-len(e.relocs),runtime_verified=False)
    proof.update(version='0.1.56',source_version='0.1.55',hub_rva=hub,spare_rva=spare,main_sha256=sha(main),spare_sha256=sha(extension),continuation_rva=continuation,loaded_growth_bytes=0,models=models,native_instruction_verified=False,natural_story_playback_verified=False)
    report['quantized_hub_056']=proof;report['english_bubble_layout']['socket_hub_bytes']=len(main);report['english_bubble_layout']['primary_sha256']=sha(out[oe.file_offset(CORE):oe.file_offset(CORE)+CORE_BYTES]);report['english_bubble_layout']['quantized_socket_cone']=True
    report['font_native_tail_loaded_extension_sha256']=sha(out[oe.ph[2][1]:oe.ph[2][1]+oe.ph[2][4]])
    report['additional_scopes']['quantized_fan_origin']=dict(rva=spare,bytes=len(extension),sha256=sha(extension),loaded_growth_bytes=0)
    region[0]=spare+len(extension);report['menu_labels_052']['remaining_pool_ranges']=free
    for chunk in report['native_tail_compaction']['chunks']:
        chunk['output_sha256']=sha(out[chunk['file_offset']:chunk['file_offset']+chunk['bytes']])
    authoritative_font_metadata(out,report);validate_native_png_metadata(out,report)
    return out,report

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--write',action='store_true');opts=a.parse_args();data,report=build();print(json.dumps(report['quantized_hub_056']|dict(executable_sha256=sha(data)),indent=2))
    if not opts.write:return
    if OUT.exists():raise ValueError('Fresh output required')
    OUT.mkdir(parents=True);UI.mkdir(parents=True,exist_ok=True);(OUT/'EBOOT.BIN').write_bytes(data);(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');(UI/'preparation.en.json').write_text(json.dumps(report['quantized_hub_056'],indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
