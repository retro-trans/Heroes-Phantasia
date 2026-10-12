"""Memory-neutral Serish correction reusing the obsolete pre-.27 geometry slot."""
import argparse,copy,json,struct
from pathlib import Path
from prepare_serish_tail import SOURCE,SHA
from executable_text_patch import Elf
from bubble_layout_hooks import geometry,constant,fconstant,fp
from dialogue_vwf_hooks import Block
from live_vwf import i,j
from field_ui_patch import sha
from build_menu_patch import relocate_code
from prepare_relocation_019 import sections,coverage,section_load
from compact_vwf_patch import loaded
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

OUT=Path('work/output/0.1.31-serish-tail-assets');SLOT=0x2e5200

def leaf(size):
    h=Block();h.emit(i(9,29,29,-64))
    for n,reg in enumerate((8,9,24,25)):h.emit(i(43,29,reg,n*4))
    h.emit(0x4448f800,i(43,29,8,16))
    for n in range(6):h.emit(i(57,29,n,24+4*n))
    h.emit(i(35,29,24,196),i(13,0,25,1));h.branch(5,24,25,'return')
    h.emit(i(37,4,24,0x318),i(13,0,25,8));h.branch(5,24,25,'return')
    for base,off,bits in ((29,208,0x43b88000),(4,0x2d4,0x42c60000)):
        h.emit(i(35,base,24,off));constant(h,25,bits);h.branch(5,24,25,'return')
    h.emit(i(35,29,9,220))
    for n,value in enumerate(b'Who will accompany you?\x12\x0e'):
        h.emit(i(36,9,24,n),i(13,0,25,value));h.branch(5,24,25,'return')
    fconstant(h,0,0x43730000);h.emit(i(49,4,1,0x2d0));fp(h,1,0,0,1)
    fconstant(h,1,0x43060000);h.emit(i(49,4,2,0x2d4));fp(h,1,1,1,2)
    h.emit(i(57,4,0,48),i(57,4,1,52));fconstant(h,2,0x40600000);fconstant(h,3,0x3f800000)
    fp(h,0,4,0,2);fp(h,1,5,1,3);h.emit(i(57,4,4,0x120),i(57,4,5,0x124))
    fp(h,1,4,0,2);fp(h,0,5,1,3);h.emit(i(57,4,4,0x210),i(57,4,5,0x214))
    h.label('return')
    for n in range(6):h.emit(i(49,29,n,24+4*n))
    h.emit(i(35,29,8,16),0x44c8f800)
    for n,reg in enumerate((8,9,24,25)):h.emit(i(35,29,reg,n*4))
    h.emit(i(9,29,29,64));h.branch(4,0,0,'footer')
    if len(h.code)*4>size-8:raise ValueError('Leaf exceeds reviewed dormant slot')
    h.emit(*([0]*((size-8)//4-len(h.code))));h.label('footer');h.emit(j(0xe4e14),0)
    return h.finish()

def build():
    incoming=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('executable.en.json').read_text())
    if sha(incoming)!=SHA:raise ValueError('Frozen source differs')
    e=Elf(incoming);ss=sections(incoming);ph=[list(p)for p in e.ph]
    active=next(x['new_target']for x in before['hideo_bubble_fix']['entry_changes']if x['site_rva']==0xe4e0c)
    legacy=bytearray(geometry(0x2e43c0,True,True,glyph_limit=131));relocate_code(legacy,0,len(legacy))
    core=bytearray(geometry(0x2e43c0,True,True,True,131));relocate_code(core,0,len(core))
    for rva,code in ((SLOT,legacy),(active,core)):
        f=e.file_offset(rva,len(code))
        if incoming[f:f+len(code)]!=code:raise ValueError('Reviewed hook differs')
    # Verify no current entry points to the obsolete slot: this remains the
    # active .27 hook. Its native final jump will call the new leaf instead.
    if e.word(0xe4e0c)!=j(active):raise ValueError('Active entry differs')
    words=list(struct.unpack('<'+'I'*(len(core)//4),core));changes=[]
    def replace(index,expected,new):
        if words[index]!=expected:raise ValueError('Capture site differs')
        words[index]=new;changes.append(dict(site=active+index*4,old_word=expected,new_word=new))
    shape=words.index(i(37,8,10,0x318));replace(shape+3,0,i(35,8,7,0x2d0))
    fzero=words.index(i(13,0,25,0x3f80));replace(fzero+2,i(13,25,25,0),i(43,29,7,80))
    source=words.index(i(35,11,5,0x14));replace(source+12,0,i(43,29,5,92))
    replace(len(words)-2,j(0xe4e14),j(SLOT));core=struct.pack('<'+'I'*len(words),*words)
    code=leaf(len(legacy));result=bytearray(incoming);allowed=set();mask=set()
    for rva,blob in ((SLOT,code),(active,core)):
        f=e.file_offset(rva,len(blob));result[f:f+len(blob)]=blob;allowed.update(range(f,f+len(blob)));mask.update(range(rva,rva+len(blob)))
    # Drop only six obsolete HI/LO records. Keep its footer R26 at exactly the
    # same site/target. Rebuild each relocation section independently.
    oldrel=incoming[ph[3][1]:ph[3][1]+ph[3][4]];drop={n for n,(off,flags)in enumerate(e.relocs)if flags>>8&255==0 and SLOT<=off<SLOT+len(legacy)and flags&255 in (5,6)}
    if len(drop)!=6 or min(drop)<before['original_relocations']:raise ValueError('Obsolete appended relocation scope differs')
    records=[oldrel[n*8:n*8+8]for n in range(len(e.relocs))];newrel=b''.join(r for n,r in enumerate(records)if n not in drop)
    relfile=(len(result)+15)//16*16;result.extend(bytes(relfile-len(result)));result.extend(newrel)
    for s in ss:
        if s[1]==0x700000a0:
            first=(s[4]-ph[3][1])//8;count=s[5]//8;removed=sum(n in drop for n in range(first,first+count))
            s[4]=relfile+(first-sum(n<first for n in drop))*8;s[5]-=removed*8
    ph[3][1]=relfile;ph[3][4]=len(newrel);shoff=(len(result)+3)//4*4;result.extend(bytes(shoff-len(result)))
    for s in ss:result.extend(struct.pack('<10I',*s))
    phoff=struct.unpack_from('<I',incoming,28)[0];struct.pack_into('<8I',result,phoff+96,*ph[3]);allowed.update(range(phoff+96,phoff+128));struct.pack_into('<I',result,32,shoff);allowed.update(range(32,36));result=bytes(result)
    if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,result))):raise ValueError('Unselected file bytes differ')
    out=Elf(result);coverage(result)
    if out.relocs!=[r for n,r in enumerate(e.relocs)if n not in drop]:raise ValueError('Unexpected relocation change')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);b,visited,skipped,_=section_load(result,base);prog,_,_=loaded(result,base)
        expected2=bytearray(a[2])
        for c in changes:struct.pack_into('<I',expected2,c['site']-ph[2][2],j(base+SLOT)if c['site']==active+len(core)-8 else c['new_word'])
        if a[1]!=b[1]or expected2!=b[2]or skipped or prog!=[b[n][:out.ph[n][4]]for n in range(3)]or any(x!=y and n not in mask for n,(x,y)in enumerate(zip(a[0],b[0]))):raise ValueError('Unselected loaded memory differs')
        if struct.unpack_from('<I',b[2],active-ph[2][2]+len(core)-8)[0]!=j(base+SLOT):raise ValueError('New repair jump differs')
        models.append(dict(base=base,relocations=len(visited),unselected_memory_exact=True,loaded_growth_bytes=0))
    q=copy.deepcopy(before)
    for k in ('output','approved_dry_plan_sha256','written_readback_verified'):q.pop(k,None)
    payload=result[ph[2][1]:ph[2][1]+ph[2][4]]
    q.update(version='0.1.31',input_version='0.1.29',input_sha256=SHA,output_elf_sha256=sha(result),output_sha256=sha(result),elf_bytes=len(result),
      total_relocations=len(out.relocs),added_relocations=len(out.relocs)-before['original_relocations'],relocation_table_sha256=sha(newrel),runtime_verified=False,status='memory_neutral_serish_tail_candidate',font_native_tail_loaded_extension_sha256=sha(payload))
    q['serish_tail_patch']=dict(site_rva=0xe4e0c,old_target=active,helper_rva=active,helper_bytes=len(core),helper_sha256=sha(core),repair_rva=SLOT,repair_bytes=len(code),repair_sha256=sha(code),
      loaded_growth_bytes=0,new_relocations=0,removed_obsolete_relocations=6,three_base_models=models,core_capture_changes=changes,template=8,tip_index=6,
      native_center=[369,99],portrait_center=[222,148],portrait_lip_reference=[21,-14],screen_lip_reference=[243,134],text='Who will accompany you?{12}{0E}',source_record='96a6bd56348c7203229c',
      resources=['phase/bin/p101010.bin','phase/bin/p101011.bin'],only_tip_changes=True,all_other_records_and_geometry_inherited=True,animated_states_inherited=True,source_controls_unchanged=True,
      native_instruction_verified=False,natural_scene_verified=False,landmark_kind='Reviewed source portrait landmark, not automatic mouth tracking')
    updated=[]
    for chunk in q['native_tail_compaction']['chunks']:
        f=chunk['file_offset'];size=chunk['bytes'];raw=result[f:f+size]
        if raw!=incoming[f:f+size]:
            scope=set(range(e.file_offset(SLOT),e.file_offset(SLOT)+len(legacy)))
            if any(f+n not in scope for n,(a,b)in enumerate(zip(incoming[f:f+size],raw))if a!=b):raise ValueError('Unexpected native font chunk change')
            chunk['output_sha256']=sha(raw);chunk['current_proof_scope']='Memory-neutral Serish leaf; all other bytes in this chunk preserved';updated.append(chunk['output_sha256'])
    if len(updated)!=1:raise ValueError('Dormant chunk identity not updated')
    authoritative_font_metadata(result,q)
    if validate_native_png_metadata(result,q)!=validate_native_png_metadata(incoming,before):raise ValueError('Font/image metadata differs')
    return result,q

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256');a=ap.parse_args();data,q=build()
    print(json.dumps({k:q[k]for k in ('version','output_elf_sha256','serish_tail_patch')},indent=2))
    if not a.write:print('DRY RUN');return
    if a.expected_sha256!=sha(data)or OUT.exists():raise ValueError('Reviewed digest and fresh folder required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data);(OUT/'executable.en.json').write_text(json.dumps(q,indent=2)+'\n')
    if (OUT/'EBOOT.BIN').read_bytes()!=data:raise ValueError('Readback differs')
if __name__=='__main__':main()
