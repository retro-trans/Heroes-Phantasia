"""Memory-neutral custom English bubble installer; dry-run then guarded write."""
import argparse,copy,json,struct
from pathlib import Path
from executable_text_patch import Elf, reference_index
from english_bubble_layout import primary, secondary, descriptors
from bubble_metrics import catalog,load_templates
from build_menu_patch import relocate_code,align
from prepare_relocation_019 import sections,coverage,section_load
from compact_vwf_patch import loaded
from field_ui_patch import sha
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

SOURCE=Path('work/output/0.1.32-world-map-assets/EBOOT.BIN')
SOURCE_SHA='9164b9c90dd0b5fb5bab36484ff231707c7539eda924ffdf33346366ce617b43'
OUT=Path('work/output/0.1.33-english-bubble-assets')
CORE=0x16fad20;CORE_BYTES=1732;REGION=0x2e43c0;REGION_BYTES=3648

def relocate(raw,rva,segment,segment_rva):
    blob=bytearray(raw);records=relocate_code(blob,0,len(blob))
    output=[(rva-segment_rva+off,(flags&255)|(segment<<8)) for off,flags in struct.iter_unpack('<II',b''.join(records))]
    return bytes(blob),output

def build():
    incoming=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('executable.en.json').read_text())
    if sha(incoming)!=SOURCE_SHA or before['output_elf_sha256']!=SOURCE_SHA:raise ValueError('Frozen source differs')
    e=Elf(incoming);ss=sections(incoming);ph=[list(p)for p in e.ph]
    oldcore=incoming[e.file_offset(CORE):e.file_offset(CORE)+CORE_BYTES]
    if sha(oldcore)!=before['serish_tail_patch']['helper_sha256']:raise ValueError('Current active geometry differs')
    _,packed=catalog(load_templates(),compact_catalog=True)
    if len(packed)!=REGION_BYTES or incoming[e.file_offset(REGION):e.file_offset(REGION)+REGION_BYTES]!=packed:
        raise ValueError('Reusable old catalog differs')
    # Only the soon-to-be-replaced primary geometry may refer into this catalog.
    refs,_=reference_index(e)
    for ref in refs:
        if REGION<=ref['address']<REGION+REGION_BYTES:
            if any(not CORE<=site<CORE+CORE_BYTES for site in ref['sites']):raise ValueError('Catalog has another owner')
    probe_return=CORE+1600
    size=len(secondary(REGION+2000,probe_return))
    epilogue_rva=REGION+align(size,16)
    # Its bounded ABI suffix precedes the immutable descriptor/contour data.
    desc=epilogue_rva+align(220,16)
    core,ret,epi=primary(REGION,desc,CORE,epilogue_rva)
    helper=secondary(desc,ret)
    if len(helper)!=size or len(epi)!=220 or len(core)>CORE_BYTES:raise ValueError('Reviewed code extents differ')
    helper,hrecords=relocate(helper,REGION,0,0)
    epi,erecords=relocate(epi,epilogue_rva,0,0)
    core,crecords=relocate(core,CORE,2,ph[2][2])
    block=bytearray(REGION_BYTES);block[:len(helper)]=helper
    block[epilogue_rva-REGION:epilogue_rva-REGION+len(epi)]=epi
    meta=descriptors();pos=desc-REGION
    if pos+len(meta)>REGION_BYTES:raise ValueError('Custom code/data exceeds reclaimed catalog')
    block[pos:pos+len(meta)]=meta
    core=core+bytes(CORE_BYTES-len(core))
    result=bytearray(incoming);allowed=set();masks=[set(),set(),set()]
    for rva,raw in ((REGION,bytes(block)),(CORE,core)):
        f=e.file_offset(rva,len(raw));result[f:f+len(raw)]=raw;allowed.update(range(f,f+len(raw)))
        segment=0 if rva==REGION else 2;masks[segment].update(range(rva-ph[segment][2],rva-ph[segment][2]+len(raw)))
    removed={n for n,(off,flags)in enumerate(e.relocs)if (flags>>8&255)==2 and CORE<=ph[2][2]+off<CORE+CORE_BYTES}
    if len(removed)!=7 or min(removed)<before['original_relocations']:raise ValueError('Old geometry relocation scope differs')
    rp=e.ph[3];kept=[r for n,r in enumerate(e.relocs)if n not in removed]
    newrecords=kept+hrecords+erecords+crecords
    relfile=align(len(result),16);result.extend(bytes(relfile-len(result)))
    result.extend(b''.join(struct.pack('<II',*r)for r in newrecords))
    for s in ss:
        if s[1]==0x700000a0:
            first=(s[4]-rp[1])//8;count=s[5]//8
            s[4]=relfile+(first-sum(n<first for n in removed))*8
            s[5]-=sum(n in removed for n in range(first,first+count))*8
    first=relfile+len(kept)*8
    ss.append([0,0x700000a0,0,0,first,(len(hrecords)+len(erecords))*8,0,1,4,8])
    ss.append([0,0x700000a0,0,0,first+(len(hrecords)+len(erecords))*8,len(crecords)*8,0,55,4,8])
    ph[3][1]=relfile;ph[3][4]=len(newrecords)*8
    shoff=align(len(result),4);result.extend(bytes(shoff-len(result)))
    for s in ss:result.extend(struct.pack('<10I',*s))
    phoff=struct.unpack_from('<I',incoming,28)[0]
    struct.pack_into('<8I',result,phoff+96,*ph[3]);allowed.update(range(phoff+96,phoff+128))
    struct.pack_into('<I',result,32,shoff);allowed.update(range(32,36))
    struct.pack_into('<H',result,48,len(ss));allowed.update(range(48,50));result=bytes(result)
    if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,result))):raise ValueError('Unselected file bytes differ')
    out=Elf(result);coverage(result)
    if out.relocs[:before['original_relocations']]!=e.relocs[:before['original_relocations']]:raise ValueError('Original relocation records differ')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        old,_,_,_=section_load(incoming,base);new,visited,skipped,_=section_load(result,base);program,_,_=loaded(result,base)
        if skipped or visited!=out.relocs or program!=[new[n][:out.ph[n][4]]for n in range(3)]:raise ValueError('PH/SHT loader coverage differs')
        for segment in range(3):
            if len(old[segment])!=len(new[segment]) or any(a!=b and n not in masks[segment]for n,(a,b)in enumerate(zip(old[segment],new[segment]))):
                raise ValueError('Unselected loaded memory differs')
        models.append(dict(base=base,relocations=len(visited),unselected_memory_exact=True,loaded_growth_bytes=0))
    report=copy.deepcopy(before)
    for k in ('output','approved_dry_plan_sha256','written_readback_verified'):report.pop(k,None)
    report.update(version='0.1.33',input_version='0.1.32',input_sha256=SOURCE_SHA,output_elf_sha256=sha(result),
        output_sha256=sha(result),elf_bytes=len(result),total_relocations=len(out.relocs),added_relocations=len(out.relocs)-before['original_relocations'],
        relocation_table_sha256=sha(b''.join(struct.pack('<II',*r)for r in newrecords)),runtime_verified=False,status='custom_english_bubble_candidate')
    payload=result[ph[2][1]:ph[2][1]+ph[2][4]];report['font_native_tail_loaded_extension_sha256']=sha(payload)
    for chunk in report['native_tail_compaction']['chunks']:
        f=chunk['file_offset'];n=chunk['bytes']
        if result[f:f+n]!=incoming[f:f+n]:
            if any(f+k not in allowed for k,(a,b)in enumerate(zip(incoming[f:f+n],result[f:f+n]))if a!=b):raise ValueError('Unselected compacted chunk changed')
            chunk['output_sha256']=sha(result[f:f+n]);chunk['current_proof_scope']='Custom English body code in reclaimed catalog; remaining bytes preserved.'
    report['english_bubble_layout']=dict(primary_rva=CORE,primary_bytes=CORE_BYTES,primary_sha256=sha(core),
        body_helper_rva=REGION,body_helper_bytes=len(helper),body_helper_sha256=sha(helper),
        epilogue_rva=epilogue_rva,epilogue_bytes=len(epi),epilogue_sha256=sha(epi),
        descriptor_rva=desc,descriptor_bytes=len(meta),reclaimed_catalog_bytes=REGION_BYTES,
        native_tail_endpoints_preserved=True,reviewed_serish_tail_leaf_preserved=True,
        loaded_growth_bytes=0,new_relocations=len(hrecords)+len(erecords)+len(crecords),removed_old_relocations=len(removed),
        three_base_models=models,standard_templates=120,other_templates_native_fallback=32,
        maximum_visible_lines=4,body_padding_px=10,bevel_px=8,border_halfwidth_px=1.5,
        viewport_body_bounds=[8,36,472,252],growth_policy='Grow upward from the authored bottom; extend downward if the upper safe bound is reached.',
        accepted_controls=['05:3 decimal','16:2 decimal','17:1 decimal','1A:1 decimal','exact Hideo reading','private Latin pairs'],
        scope='Stationary unit-scale unrotated supported Latin, centered standard speech bubbles. Word wrapping is a separate offline preparation step.',
        native_instruction_verified=False,natural_story_scene_verified=False)
    report['serish_tail_patch']['current_common_geometry_replaced']=True
    report['serish_tail_patch']['current_common_geometry_proof']='english_bubble_layout'
    authoritative_font_metadata(result,report)
    if validate_native_png_metadata(result,report)!=validate_native_png_metadata(incoming,before):raise ValueError('Native font/image contract differs')
    return result,report

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256');a=ap.parse_args()
    data,report=build();print(json.dumps(dict(sha256=sha(data),**report['english_bubble_layout']),indent=2))
    if not a.write:print('DRY RUN');return
    if a.expected_sha256!=sha(data)or OUT.exists():raise ValueError('Reviewed hash and fresh output required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data)
    if (OUT/'EBOOT.BIN').read_bytes()!=data:raise ValueError('Written executable differs')
    report['written_readback_verified']=True;(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
