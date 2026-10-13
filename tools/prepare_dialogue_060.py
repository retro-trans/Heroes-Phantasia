"""Remove duplicate English ruby and preserve minimum native corner height."""
import argparse, copy, json, struct
from pathlib import Path
import dialogue_layout_guard as g
from dialogue_tokens import tokenize_bytes
from executable_text_patch import Elf, reference_index
from dialogue_vwf_hooks import Block, r, address
from live_vwf import i,j
from english_bubble_layout_v10 import fp, fconstant
from prepare_relocation_019 import sections, coverage, section_load
from prepare_english_bubbles_v10 import relocate
from build_menu_patch import align
from rebuild_dialogue import parse,rebuild
from field_ui_patch import notation
from strip_jp import export
from append_cpk import main as append_main
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from prepare_dialogue_commands_048 import capture
import english_bubble_layout_v10 as original_geometry

BASE=Path('work/output/0.1.59-title-credit-vwf-4x-candidate')
OUT=Path('work/output/0.1.60-dialogue-assets-final')
UI=Path('work/ui/dialogue/0.1.60')
MIN_HEIGHT_RVA=616940

def remove_duplicate_ruby(text):
    ts=tokenize_bytes(text,True);ranges=[]
    for k,t in enumerate(ts):
        if t.kind!='ruby_open':continue
        end=next(v.offset for v in ts[k+1:] if v.kind=='ruby_close')
        reading=text[t.offset+2:end]
        # A literal suffix match removes only a duplicated Latin reading.
        # Transliterations of a different base word remain for later review.
        if reading and all(32<=v<=126 for v in reading) and text[:t.offset].lower().endswith(reading.lower()):
            ranges.append((t.offset,end+1,reading.decode('ascii')))
    out=text
    for a,b,_ in reversed(ranges):out=out[:a]+out[b:]
    if any(t.kind=='ruby_open' for t in tokenize_bytes(out,True)) and not ranges:return text,[]
    return out,ranges

def minimum_height(return_rva,displaced):
    h=Block();h.emit(i(57,29,2,100));address(h,7,0x2e7460+894)
    h.emit(i(35,29,24,92),r(7,24,7),i(36,7,24,0),0x44800000|(24<<16)|(6<<11),0x46800020|(6<<11)|(6<<6))
    fconstant(h,0,0x3f000000);fp(h,2,6,6,0)
    fp(h,0x3c,0,2,6);h.branch(17,8,0,'return');h.emit(i(57,29,6,100))
    h.label('return');h.emit(j(return_rva),displaced)
    return h.finish()

def executable():
    incoming=(BASE/'EBOOT.BIN').read_bytes();m=json.loads((BASE/'manifest.en.json').read_bytes());before=m['setup_patch'];e=Elf(incoming)
    if g.sha(incoming)!='5e1af24667f807e2d22653ecfb99a86aeade342047dad0ad95c8837820e7eee4':raise ValueError('Frozen .59 executable differs')
    fit=before['english_bubble_layout']['tail_fit_rva'];size=before['english_bubble_layout']['tail_fit_bytes'];at=e.file_offset(fit,size)
    b=before['english_bubble_layout']
    secondary,_=capture(lambda:original_geometry.secondary(b['descriptor_rva'],0,fit,0x16fad20+16,b['contour_rva'],b['socket_hub_rva']),original_geometry)
    raw=bytearray(original_geometry.tail_fit(secondary[1]));old,_=relocate(bytes(raw),fit,0,0)
    if old!=incoming[at:at+size]:raise ValueError('Reviewed generated tail fitter differs')
    words=struct.unpack_from('<II',raw,28)
    if words!=(i(57,29,2,100),i(13,0,25,0x3f80)):raise ValueError('Reviewed height store and displaced instruction differ')
    helper=minimum_height(fit+36,words[1]);pool=next(v for v in before['menu_labels_052']['remaining_pool_ranges'] if v[0]==MIN_HEIGHT_RVA)
    if len(helper)>pool[1]-pool[0]:raise ValueError('Minimum-height helper exceeds the unused pool')
    spare_at=e.file_offset(MIN_HEIGHT_RVA,len(helper))
    if any(incoming[spare_at:spare_at+len(helper)]):raise ValueError('Minimum-height pool is not zero')
    refs,_=reference_index(e)
    if any(MIN_HEIGHT_RVA<=v['address']<MIN_HEIGHT_RVA+len(helper) for v in refs):raise ValueError('Typed owner enters helper pool')
    struct.pack_into('<II',raw,28,j(MIN_HEIGHT_RVA),0)
    patched,rels=relocate(bytes(raw),fit,0,0);helper,hrels=relocate(helper,MIN_HEIGHT_RVA,0,0)
    result=bytearray(incoming);allowed=set();masks=[set(),set(),set()]
    _,desc=g.geometry()
    minima=bytes(max(desc[608+n*16+3]+desc[608+n*16+5],desc[608+n*16+13]+desc[608+n*16+11])+8 for n in range(15))
    desc_rva=b['descriptor_rva']+894
    if any(incoming[e.file_offset(desc_rva):][:len(minima)]):raise ValueError('Minimum corner-height table padding differs')
    for rva,b in ((fit,patched),(MIN_HEIGHT_RVA,helper),(desc_rva,minima)):
        off=e.file_offset(rva,len(b));result[off:off+len(b)]=b;allowed.update(range(off,off+len(b)));masks[0].update(range(rva,rva+len(b)))
    removed={n for n,(site,flags) in enumerate(e.relocs) if flags>>8&255==0 and fit<=site<fit+size}
    if any(n<before['original_relocations'] for n in removed):raise ValueError('Original relocation selected')
    kept=[v for n,v in enumerate(e.relocs) if n not in removed];newrels=kept+rels+hrels
    rp=e.ph[3];ss=sections(incoming);relfile=align(len(result),16);result.extend(bytes(relfile-len(result)));result.extend(b''.join(struct.pack('<II',*v) for v in newrels))
    for s in ss:
        if s[1]!=0x700000a0:continue
        first=(s[4]-rp[1])//8;count=s[5]//8;s[4]=relfile+(first-sum(n<first for n in removed))*8;s[5]-=sum(n in removed for n in range(first,first+count))*8
    ss.append([0,0x700000a0,0,0,relfile+len(kept)*8,(len(rels)+len(hrels))*8,0,1,4,8])
    ph=[list(v) for v in e.ph];ph[3][1]=relfile;ph[3][4]=len(newrels)*8;shoff=align(len(result),4);result.extend(bytes(shoff-len(result)));result.extend(b''.join(struct.pack('<10I',*s) for s in ss))
    phoff=struct.unpack_from('<I',incoming,28)[0];struct.pack_into('<8I',result,phoff+96,*ph[3]);allowed.update(range(phoff+96,phoff+128));struct.pack_into('<I',result,32,shoff);allowed.update(range(32,36));struct.pack_into('<H',result,48,len(ss));allowed.update(range(48,50))
    out=bytes(result);oe=Elf(out);coverage(out)
    if any(a!=b and n not in allowed for n,(a,b) in enumerate(zip(incoming,out))):raise ValueError('Unselected executable bytes changed')
    if oe.ph[:3]!=e.ph[:3] or oe.relocs[:before['original_relocations']]!=e.relocs[:before['original_relocations']]:raise ValueError('Original loaded extent/relocations changed')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);z,visited,skipped,_=section_load(out,base)
        if skipped or visited!=oe.relocs:raise ValueError('Relocation loader coverage differs')
        for s in range(3):
            if len(a[s])!=len(z[s]) or any(x!=y and n+e.ph[s][2] not in masks[s] for n,(x,y) in enumerate(zip(a[s],z[s]))):raise ValueError('Unselected loaded memory changed')
        models.append(dict(base=base,loaded_extents_exact=True,outside_mask_exact=True))
    report=copy.deepcopy(before);report.update(version='0.1.60',input_version='0.1.59',input_sha256=g.sha(incoming),output_sha256=g.sha(out),output_elf_sha256=g.sha(out),elf_bytes=len(out),total_relocations=len(oe.relocs),added_relocations=len(newrels)-len(e.relocs),runtime_verified=False)
    proof=dict(version='0.1.60',helper_rva=MIN_HEIGHT_RVA,helper_bytes=len(helper),helper_sha256=g.sha(helper),tail_fit_rva=fit,tail_fit_bytes=size,tail_fit_sha256=g.sha(patched),minimum_height='maximum of paired right/left corner cuts + 4px; applied before either tail-fit route',minimum_corner_heights=[v/2 for v in minima],table_rva=desc_rva,authored_corner_coefficients_and_speaker_endpoints_unchanged=True,loaded_growth_bytes=0,models=models,native_instruction_verified=False,natural_story_playback_verified=False)
    report['minimum_corner_height_060']=proof;report['english_bubble_layout']['tail_fit_sha256']=g.sha(patched)
    report['additional_scopes']['minimum_corner_height']=dict(rva=MIN_HEIGHT_RVA,bytes=len(helper),sha256=g.sha(helper),loaded_growth_bytes=0)
    report['menu_labels_052']['remaining_pool_ranges']=copy.deepcopy(before['menu_labels_052']['remaining_pool_ranges'])
    next(v for v in report['menu_labels_052']['remaining_pool_ranges'] if v[0]==MIN_HEIGHT_RVA)[0]+=len(helper)
    for chunk in report['native_tail_compaction']['chunks']:chunk['output_sha256']=g.sha(out[chunk['file_offset']:chunk['file_offset']+chunk['bytes']])
    authoritative_font_metadata(out,report);validate_native_png_metadata(out,report)
    return out,report

def build_assets():
    assets={};records=[];queue=[];unchanged_readings=0
    for name,raw in g.resources(BASE/'HP.CPK'):
        try:p=parse(name,raw)
        except ValueError:continue
        changes={}
        for n,(_,off) in enumerate(p['refs']):
            text=p['spans'][off][0]
            try:new,spans=remove_duplicate_ruby(text)
            except ValueError:continue
            if not spans:continue
            changes[n]=new;records.append(dict(resource=name,reference_index=n,removed_readings=[v[2] for v in spans],old_sha256=g.sha(text),new_sha256=g.sha(new),literal_body_and_nonruby_controls_exact=True,authored_tracks_exact=True))
            queue.append(dict(id=f'ruby_060_{Path(name).stem}_{n}',file=name,category='duplicate_english_pronunciation',target=notation(new),status='translated',notes='Removed only ASCII readings identical to their preceding literal suffix; base text and other controls preserved.'))
        if not changes:continue
        changed,np=rebuild(name,raw,changes)
        if raw[p['head'][0]:p['start']]!=changed[np['head'][0]:np['start']] or raw[p['end']:]!=changed[np['end']:]:raise ValueError('Ruby cleanup changed authored tracks/suffix')
        assets[name]=changed
    return assets,records,dict(schema_version=1,language='en',rows=queue)

def corner_reflows(assets,exe_path):
    import prepare_dialogue_guard_055 as plain
    from prepare_name_dialogue_059 import reflow as names_reflow
    prior=json.loads(Path('work/ui/dialogue/0.1.59/layout_exceptions.en.json').read_bytes())
    retained={(r['resource'],r['reference_index']) for r in prior['retained_maximum_name_risks']}
    audit=g.audit(BASE/'HP.CPK',exe_path,assets);widths=g.widths_from(exe_path);selected={};records=[]
    for r in audit['records']:
        if r['status']=='overflow' and (r['resource'],r['reference_index']) not in retained:selected.setdefault(r['resource'],[]).append(r)
    from prepare_bubble_scenes_036 import read
    originals=read(BASE/'HP.CPK',list(selected))
    for name,rows in selected.items():
        raw=assets.get(name,originals[name]);p=parse(name,raw);changes={};offsets={}
        for r in rows:
            n=r['reference_index'];off=p['refs'][n][1];text=p['spans'][off][0]
            fn=names_reflow if r['measurement_policy']=='native_13px_with_bounded_names' else plain.reflow
            new,detail=fn(text,r,widths)
            if off in offsets and offsets[off]!=new:raise ValueError('Incompatible shared corner reflow')
            offsets[off]=new;records.append(dict(resource=name,reference_index=n,shape=r['shape'],old_sha256=g.sha(text),new_sha256=g.sha(new),new_english=notation(new),**detail,authored_tracks_exact=True))
        for n,(_,off) in enumerate(p['refs']):
            if off in offsets:changes[n]=offsets[off]
        new,np=rebuild(name,raw,changes)
        if raw[p['head'][0]:p['start']]!=new[np['head'][0]:np['start']] or raw[p['end']:]!=new[np['end']:]:raise ValueError('Corner reflow changed tracks/suffix')
        assets[name]=new
    return records

def write_layout_ledger():
    from prepare_bubble_scenes_036 import read
    old=json.loads(Path('work/ui/dialogue/0.1.59/layout_exceptions.en.json').read_bytes())
    audit=g.audit(OUT/'HP.CPK',OUT/'EBOOT.BIN')
    names=list(dict.fromkeys(v['resource'] for v in old['records']+old['retained_maximum_name_risks']))
    rs=read(BASE/'HP.CPK',names);parsed={n:parse(n,b) for n,b in rs.items()}
    prior={(v['resource'],v['reference_index']):v for v in old['records']+old['retained_maximum_name_risks']}
    unknown=[];risks=[];updated=0
    for r in audit['records']:
        if r['status']=='fit':continue
        key=r['resource'],r['reference_index']
        if key not in prior:raise ValueError('New layout exception '+str(key))
        prev=prior[key];p=parsed[r['resource']];text=p['spans'][p['refs'][r['reference_index']][1]][0];new,spans=remove_duplicate_ruby(text)
        if r['text_sha256']!=g.sha(new) or r.get('geometry_sha256')!=prev.get('geometry_sha256'):raise ValueError('Unreviewed exception mutation')
        if spans:updated+=1
        if r['status']=='unverified':
            if r['reason']!=prev.get('reason'):raise ValueError('Exception category changed')
            unknown.append({k:r.get(k) for k in ('resource','reference_index','text_sha256','geometry_sha256','reason')})
        else:
            if r['parent_maximum_width']!=prev.get('parent_maximum_width'):raise ValueError('Risk width changed')
            risks.append({k:r.get(k) for k in ('resource','reference_index','text_sha256','geometry_sha256','parent_maximum_width','measurement_policy')})
    ledger=dict(version='0.1.60',name_selector_limits={k.decode():v for k,v in g.NAME_LIMITS.items()},runtime_contract=g.runtime_contract(OUT/'EBOOT.BIN'),scope='Inherited unsupported/maximum-name risks only. Text changes in this ledger are exact duplicate ASCII ruby removal; no base text, names or geometry changes. Maximum-name risks remain explicitly unsafe at some permitted lengths.',records=unknown,retained_maximum_name_risks=risks,duplicate_only_exception_updates=updated)
    (UI/'layout_exceptions.en.json').write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf8')
    proof=g.enforce(OUT/'HP.CPK',OUT/'EBOOT.BIN')
    (UI/'corpus_audit.en.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')

def main():
    a=argparse.ArgumentParser();a.add_argument('--write',action='store_true');opts=a.parse_args();exe,report=executable();assets,records,queue=build_assets()
    print(json.dumps(dict(version='0.1.60',resources=len(assets),references=len(records),removed_readings=sum(len(r['removed_readings']) for r in records),minimum_corner_height=report['minimum_corner_height_060']),indent=2))
    if not opts.write:return
    if OUT.exists():raise ValueError('Fresh output required')
    OUT.mkdir(parents=True);UI.mkdir(parents=True,exist_ok=True);(OUT/'EBOOT.BIN').write_bytes(exe)
    corner_records=corner_reflows(assets,OUT/'EBOOT.BIN')
    queue['rows'].extend(dict(id=f"corner_060_{Path(r['resource']).stem}_{r['reference_index']}",file=r['resource'],category='minimum_corner_height_reflow',target=r['new_english'],status='translated',notes='Word-preserving reflow for the bounded native bevel height; authored tracks and speaker endpoints preserved.') for r in corner_records)
    for n,b in assets.items():p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    proof=dict(version='0.1.60',source_version='0.1.59',records=records,selected_assets=[dict(resource=n,sha256=g.sha(b),bytes=len(b)) for n,b in assets.items()],removed_readings=sum(len(r['removed_readings']) for r in records),natural_playback_verified=False)
    report['duplicate_ruby_060']=proof;(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');(UI/'preparation.en.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    report['corner_reflows_060']=dict(version='0.1.60',records=corner_records)
    (OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    (UI/'corner_reflows.en.json').write_text(json.dumps(report['corner_reflows_060'],indent=2)+'\n',encoding='utf8')
    p=Path('work/translation/en/duplicate_ruby_060.json');p.write_text(json.dumps(queue,indent=2)+'\n',encoding='utf8');p.with_suffix('.en.json').write_text(json.dumps(export(queue),indent=2)+'\n',encoding='utf8')
    import sys
    m=json.loads((BASE/'manifest.en.json').read_bytes());sys.argv=['append','--archive',str(BASE/'HP.CPK'),'--expected-sha256',m['dialogue_cpk_sha256'],'--version','0.1.60','--output',str(OUT/'HP.CPK'),'--write']
    for n in assets:sys.argv+=['--replace',n+'='+str(OUT/n)]
    append_main()
    write_layout_ledger()

if __name__=='__main__':main()
