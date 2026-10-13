"""Fit English tailless field dialogue, chapter labels and numeric Kogoro names.

Preparation reads the frozen .52 archive. No native font/geometry code changes;
only reviewed tailless styles, their viewport placement and text are changed.
"""
import argparse,copy,json,struct
from pathlib import Path
from executable_text_patch import Elf,ORIGINAL,encoded_text
from native_menu_install_plan import cstring
from prepare_bubble_scenes_036 import read,sha
from unpack_cpk import inventory
from rebuild_dialogue import parse,rebuild
from prepare_ui_dialogue_051 import layer_location
from bubble_metrics import load_templates,centered_interval
from dialogue_tokens import tokenize_bytes
from prepare_relocation_019 import section_load,coverage
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from field_ui_patch import notation
from strip_jp import export

BASE=Path('work/output/0.1.52-title-credit-vwf-4x-candidate')
OUT=Path('work/output/0.1.53-field-dialogue-assets')
UI=Path('work/ui/dialogue/0.1.53')
INPUT_SHA='63802dd66f839be73f86587945ebf43acb85ba93452611103871b5fe5092b76d'
CPK_SHA='aae8379fabd7b47e96fbec03c51a271fae03306d9ce55ebe18d0c120bbc27be6'
NUMERIC='５５６'.encode('cp932')

def rows(text,widths):
    return [[sum(widths[c]for c in line)for line in page.split(b'\x12',1)[0].split(b'\x11')]for page in text.split(b'\x10')]

def interior(shape,pages,templates):
    t=templates[shape];half=max(v for page in pages for v in page)/2
    for page in pages:
        for n,advance in enumerate(page):
            bands=[centered_interval(t['banks'][0],t['text_offset'][1]+n*22+dy)for dy in (.001,8,15.999)]
            if any(q is None or -half<q[0]+1 or -half+advance>q[1]-1 for q in bands):return False
    return True

def reflow(text,widths):
    speaker,body=text.split(b'\x0e',1);pages=[];extra=0
    for page in body.split(b'\x10'):
        if page.count(b'\x12')!=1:raise ValueError('Unexpected field page boundary')
        plain,suffix=page.split(b'\x12')
        if suffix not in (b'',b'\x0e'):raise ValueError('Unexpected field suffix')
        lines=[b'']
        for word in plain.replace(b'\x11',b' ').split():
            if sum(widths[v]for v in word)>200:raise ValueError('Single word exceeds reviewed field width')
            candidate=lines[-1]+(b' 'if lines[-1]else b'')+word
            if sum(widths[v]for v in candidate)>200 and lines[-1]:lines.append(word)
            else:lines[-1]=candidate
        chunk_count=(len(lines)+2)//3
        chunk_size=(len(lines)+chunk_count-1)//chunk_count
        chunks=[lines[n:n+chunk_size]for n in range(0,len(lines),chunk_size)];extra+=len(chunks)-1
        pages.extend(b'\x11'.join(chunk)+b'\x12'+(suffix if n==len(chunks)-1 else b'')for n,chunk in enumerate(chunks))
    return speaker+b'\x0e'+b'\x10'.join(pages),extra

def plain_body(body):
    try:tokens=tokenize_bytes(body,True)
    except ValueError:return False
    return all(t.kind=='latin'or t.kind=='control'and t.code in (0x10,0x11,0x12,0x0e)for t in tokens)

def build():
    incoming=(BASE/'EBOOT.BIN').read_bytes();before=json.loads((BASE/'manifest.en.json').read_bytes())['setup_patch']
    if sha(incoming)!=INPUT_SHA:raise ValueError('Frozen .52 executable differs')
    e=Elf(incoming);o=Elf(ORIGINAL.read_bytes());widths=struct.unpack_from('<131I',incoming,e.file_offset(before['body_integer_lut_rva']));templates=load_templates()
    result=bytearray(incoming);allowed=set();mask=set();free=copy.deepcopy(before['menu_labels_052']['remaining_pool_ranges']);labels=[]
    for n in (210,211,212):
        slot=0x94760+4*n;old=e.word(slot)
        if old!=o.word(slot)or cstring(e,old)!=cstring(o,old):raise ValueError('Chapter source already changed')
        target='Chapter '+str(n-209);raw=target.encode('ascii')+b'\0'
        region=next((r for r in free if r[1]-r[0]>=len(raw)),None)
        if region is None:raise ValueError('Reviewed unused text pool exhausted')
        rva=region[0];region[0]+=len(raw);at=e.file_offset(rva,len(raw))
        if any(incoming[at:at+len(raw)]):raise ValueError('Unused pool is not zero')
        if any(flags&15==2 and not flags>>8&255 and rva<=e.word(site)<rva+len(raw)for site,flags in e.relocs):raise ValueError('Live owner enters unused pool')
        result[at:at+len(raw)]=raw;allowed.update(range(at,at+len(raw)));mask.update(range(rva,rva+len(raw)))
        at=e.file_offset(slot,4);struct.pack_into('<I',result,at,rva);allowed.update(range(at,at+4));mask.update(range(slot,slot+4))
        labels.append(dict(id=f'field_053_chapter_{n-209}',native_index=n,pointer_slot=slot,target_rva=rva,target=target,status='translated'))
    out=bytes(result);oe=Elf(out);coverage(out);models=[]
    if oe.ph!=e.ph or oe.relocs!=e.relocs or any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,out))):raise ValueError('Unselected executable bytes differ')
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);b,_,skipped,_=section_load(out,base)
        if skipped or a[1:]!=b[1:]or any(v!=w and n not in mask for n,(v,w)in enumerate(zip(a[0],b[0]))):raise ValueError('Unselected loaded memory differs')
        for row in labels:
            if struct.unpack_from('<I',b[0],row['pointer_slot'])[0]!=base+row['target_rva']:raise ValueError('Chapter relocation differs')
        models.append(dict(base=base,chapter_pointers_exact=True,outside_mask_exact=True))
    _,archive=inventory(BASE/'HP.CPK');names=[r['path']for r in archive if r['path'].startswith('fld/talk/')and r['path'].endswith('.bin')]
    # Numeric names are only sought in original resources that contain this
    # name, including rows skipped by prose translation because they are silent.
    for prefix in ('phase/bin','btl/res','btl/skit'):
        names.extend(str(p.relative_to('work/source/cpk')).replace('\\','/')for p in Path('work/source/cpk',prefix).glob('*.bin')if NUMERIC in p.read_bytes())
    originals=read(BASE/'HP.CPK',list(dict.fromkeys(names)));assets={};records=[];name_records=[];skipped=[];fit_records=[];queue=[];examined=0;fits=0
    for name,raw in originals.items():
        try:p=parse(name,raw)
        except ValueError:continue
        replacements={};changes=[]
        for n,(_,off)in enumerate(p['refs']):
            text=p['spans'][off][0]
            if b'\x0e'not in text:continue
            speaker,body=text.split(b'\x0e',1)
            if speaker in (b'\x1c'+NUMERIC,b'\x1c556'):
                # Two authored silence lengths: preserve their distinction.
                silence=b'\x81\x63';count=0;rest=body
                while rest.startswith(silence):count+=1;rest=rest[2:]
                if count not in (2,4)or rest!=b'\x12\x0e':raise ValueError('Unreviewed numeric-name body')
                new=b'\x1cKogoro\x0e'+b'.'*(count*3)+rest;replacements[n]=new
                item=dict(resource=name,reference_index=n,old_speaker='556',target='Kogoro',silence_dots=count*3,authored_tracks_exact=True)
                name_records.append(item);queue.append(dict(id=f'field_053_name_{Path(name).stem}_{n}',category='speaker_name',target=notation(new),status='translated'))
            if not name.startswith('fld/talk/'):continue
            ch,layer=layer_location(name,raw,n)
            if layer[5]!=3 or layer[9]!=1:continue
            shape=struct.unpack_from('<H',raw,ch+layer[10]+4)[0]
            if templates[shape]['count']!=8:continue
            examined+=1
            positions=[struct.unpack_from('<4fI',raw,ch+layer[14]+20*k)for k in range(layer[13])]
            if not plain_body(body):skipped.append(dict(resource=name,reference_index=n,reason='Dynamic name or other unmodeled controls/native body; original retained.'));continue
            if any(c<32 or c>128 for c in speaker[1:]):skipped.append(dict(resource=name,reference_index=n,reason='Native speaker label; original retained.'));continue
            oldpages=rows(body,widths)
            if interior(shape,oldpages,templates):fits+=1;continue
            new,extra=reflow(text,widths);newpages=rows(new.split(b'\x0e',1)[1],widths);maxlines=max(map(len,newpages));newshape={1:122,2:132,3:142}[maxlines]
            if not interior(newshape,newpages,templates):raise ValueError('Reflow exceeds authored white interior')
            if text.replace(b' ',b'').replace(b'\x11',b'').replace(b'\x10',b'').replace(b'\x12',b'')!=new.replace(b' ',b'').replace(b'\x11',b'').replace(b'\x10',b'').replace(b'\x12',b''):raise ValueError('Field dialogue words changed')
            signature=lambda b:[(t.code,t.argument)for t in tokenize_bytes(b,True)if t.kind=='control'and t.code!=0x11]
            if extra==0 and signature(text)!=signature(new):raise ValueError('Nonline controls changed')
            replacements[n]=new;changes.append((n,newshape));t=templates[newshape];bounds=[min(x for x,y in t['banks'][1]),min(y for x,y in t['banks'][1]),max(x for x,y in t['banks'][1]),max(y for x,y in t['banks'][1])]
            positioned=[]
            for key in positions:
                if key[1:3]==(0.,0.):raise ValueError('Field box has an unreviewed entrance position')
                x=max(6-bounds[0],min(key[1],474-bounds[2]));y=max(6-bounds[1],min(key[2],252-bounds[3]));positioned.append([x,y])
            rec=dict(resource=name,reference_index=n,input_sha256=sha(raw),old_shape=shape,new_shape=newshape,old_english=notation(text),new_english=notation(new),page_line_advances=newpages,position_keys=positions,new_positions=positioned,extra_pages=extra,words_exact=True,nonline_controls_exact=extra==0,tailless_style=True,white_interior_fit=True,natural_playback_verified=False)
            records.append(rec);queue.append(dict(id=f'field_053_reflow_{Path(name).stem}_{n}',category='field_dialogue',target=notation(new),status='translated',notes='Tailless authored style and word-preserving reflow; '+str(extra)+' additional pages.'))
        if not replacements:continue
        changed,np=rebuild(name,raw,replacements);mut=bytearray(changed);track_mask=set()
        for n,newshape in changes:
            ch,layer=layer_location(name,changed,n);at=ch+layer[10]+4;struct.pack_into('<H',mut,at,newshape);track_mask.update(range(at,at+2))
            rec=next(r for r in records if r['resource']==name and r['reference_index']==n)
            for k,(x,y)in enumerate(rec['new_positions']):
                at=ch+layer[14]+k*20+4;struct.pack_into('<2f',mut,at,x,y);track_mask.update(range(at,at+8))
        changed=bytes(mut)
        if any(a!=b and n not in track_mask for n,(a,b)in enumerate(zip(raw[p['head'][0]:p['start']],changed[np['head'][0]:np['start']]),start=p['head'][0]))or raw[p['end']:]!=changed[np['end']:]:raise ValueError('Unselected native tracks/suffix differ')
        for n,(_,off)in enumerate(p['refs']):
            if n not in replacements and p['spans'][off][0]!=np['spans'][np['refs'][n][1]][0]:raise ValueError('Unselected dialogue changed')
        assets[name]=changed
        for rec in records:
            if rec['resource']==name:rec['output_sha256']=sha(changed)
    for label in labels:queue.append(dict(label,category='quest_chapter_label'))
    expected_names={('phase/bin/p101040.bin',9),('phase/bin/p101041.bin',9),('phase/bin/p208040.bin',29),('phase/bin/p208041.bin',29)}
    if {(r['resource'],r['reference_index'])for r in name_records}!=expected_names or examined!=95:raise ValueError('Reviewed field/name scope differs')
    proof=dict(version='0.1.53',input_version='0.1.52',archive_input_sha256=CPK_SHA,resources_audited=len(originals),tailless_field_records_examined=examined,already_fitting_records=fits,reflow_records=records,numeric_name_records=name_records,unmodeled_records=skipped,labels=labels,loader_models=models,loaded_growth_bytes=0,font_and_geometry_code_exact=True,selected_assets=[dict(resource=n,sha256=sha(b),bytes=len(b))for n,b in assets.items()],full_game_verified=False)
    report=copy.deepcopy(before);report.update(version='0.1.53',input_version='0.1.52',input_sha256=INPUT_SHA,output_elf_sha256=sha(out),output_sha256=sha(out),runtime_verified=False);report['field_dialogue_053']=proof
    authoritative_font_metadata(out,report);validate_native_png_metadata(out,report)
    return out,report,assets,dict(schema_version=1,language='en',rows=queue)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256');a=ap.parse_args();data,report,assets,queue=build();proof=report['field_dialogue_053']
    print(json.dumps(dict(version='0.1.53',executable_sha256=sha(data),resources=len(assets),reflows=len(proof['reflow_records']),numeric_names=len(proof['numeric_name_records']),chapter_labels=3,unmodeled_records=len(proof['unmodeled_records'])),indent=2))
    if not a.write:return
    if a.expected_sha256!=sha(data)or OUT.exists():raise ValueError('Reviewed hash and fresh output required')
    OUT.mkdir(parents=True);UI.mkdir(parents=True,exist_ok=True)
    (OUT/'EBOOT.BIN').write_bytes(data);(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    for name,raw in assets.items():
        dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    (UI/'preparation.en.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    p=Path('work/translation/en/field_dialogue_053.json');p.write_text(json.dumps(queue,indent=2)+'\n',encoding='utf8');p.with_name('field_dialogue_053.en.json').write_text(json.dumps(export(queue),indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
