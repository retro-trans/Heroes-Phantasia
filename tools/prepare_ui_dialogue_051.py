"""Repair reported profile/battle layouts and party/result UI from frozen .50."""
import argparse, copy, json, struct
from pathlib import Path
from executable_text_patch import Elf, ORIGINAL, reference_index, encoded_text
from native_menu_install_plan import cstring
from prepare_relocation_019 import section_load, coverage
from prepare_bubble_scenes_036 import read, sha
from rebuild_dialogue import parse, rebuild
from prepare_dialogue_commands_048 import capture, ruby_chunk, scanner_cases
from dialogue_measure_1a import measure_1a, instruction_cases
import dialogue_measure as dm
import english_bubble_layout_v10 as eb
from dialogue_vwf_hooks import Block
from live_vwf import i
from build_menu_patch import relocate_code
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from strip_jp import export
from field_ui_patch import notation

BASE=Path('work/output/0.1.50-title-credit-vwf-4x-candidate')
OUT=Path('work/output/0.1.51-ui-dialogue-assets')
INPUT_SHA='f6385e2d24484ce775dedc9935b573753f2a8f7e8da4fb5d6a5d9dfbdd8941d6'
LABELS={0:'Cheer',1:'Items',2:'Brave',4:'Members',48:'Actions',176:'Switch Menu'}
HELP={51:'Cheer on allies{11}to restore lost HP.{0E}',
      52:'Allocate Brave Points{11}to strengthen characters.{0E}',
      53:'Configure attack actions.{0E}',54:'Equip accessories.{0E}',
      55:'Arrange battle members.{0E}',56:'Choose amulets.{0E}',
      70:'{1A}2{17}2Overcharge type selection unlocked.{11}{17}2Change it on the Actions screen.{0E}',
      71:"{1A}5{17}2Gourry's smithing skill improved.{0E}",
      72:"'s{11}{17}2new Chain Action has been unlocked.{0E}",
      73:' obtained!{0E}',74:'{1A}5{17}2Photo set as the background.{0E}'}

def menu_bitmap(data):
    from inspect_font_assets import texture,unswizzle
    from title_stamp import swizzle
    from prepare_battle_labels_045 import lettering
    from PIL import Image
    if sha(data)!='b17aaf43ecfed61cafe8d632c3355879fe34e3f7d2016f8690693c4bfbd2f1c0':raise ValueError('Frozen resident atlas differs')
    t=texture(data,0x4ddf0);w,h=t['width'],t['height'];palette=[tuple(t['palette'][i:i+4])for i in range(0,1024,4)]
    before=unswizzle(t['pixels'],w,h);pixels=bytearray(before)
    rect=(0,160,40,16);canvas,size,boxes=lettering(['Menu'],40,16,13,shadow=True)
    # Quantize only the reviewed word crop into the existing immutable palette.
    colors={c:min(range(256),key=lambda k:sum((a-b)**2 for a,b in zip(c,palette[k])))for c in set(canvas.getdata())}
    allowed=set()
    for y in range(16):
        for x in range(40):
            at=(160+y)*w+x;allowed.add(at);pixels[at]=colors[canvas.getpixel((x,y))]
    if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(before,pixels))):raise ValueError('Unselected atlas pixels differ')
    result=bytearray(data);start=t['pixel_offset'];result[start:start+len(pixels)]=swizzle(pixels,w,h)
    after=texture(result,0x4ddf0)
    if after['palette']!=t['palette']or result[:start]!=data[:start]or result[start+len(pixels):]!=data[start+len(pixels):]:raise ValueError('Atlas metadata or other assets differ')
    preview=Image.frombytes('RGBA',(w,h),b''.join(bytes(palette[v])for v in pixels))
    return bytes(result),dict(resource='resident/ALLResidentNML.bin',texture_offset=0x4ddf0,rectangle=list(rect),target='Menu',font_native_pixels=size,text_boxes=boxes,input_sha256=sha(data),output_sha256=sha(result),outside_rectangle_pixel_exact=True,palette_uv_and_dimensions_exact=True,natural_display_verified=False),preview

def ruby_digits(labels,end_label,resume,pointer,counter,char,tmp):
    # Reuse the complete bounded .48 scanner; replace its exact digit2 check
    # with a nonzero decimal span check in the same original 140-byte extent.
    offset,old=ruby_chunk(labels,end_label,resume,pointer,counter,char,tmp)
    start=labels['hideo_reading'];h=Block()
    h.labels.update({k:labels[k]-start for k in ('return',resume)})
    h.emit(i(11,counter,tmp,1022));h.branch(4,tmp,0,'return')
    h.emit(i(36,pointer,char,1),i(9,char,tmp,-49),i(11,tmp,tmp,9));h.branch(4,tmp,0,'return')
    h.emit(i(36,pointer,char,2),i(9,char,tmp,-32),i(11,tmp,tmp,95));h.branch(4,tmp,0,'return')
    h.emit(i(9,pointer,pointer,2),i(9,counter,counter,2))
    h.label('reading');h.emit(i(11,counter,tmp,1024));h.branch(4,tmp,0,'return')
    h.emit(i(36,pointer,char,0),i(9,pointer,pointer,1),i(9,counter,counter,1),i(13,0,tmp,15))
    h.branch(4,char,tmp,resume)
    h.emit(i(9,char,tmp,-32),i(11,tmp,tmp,95));h.branch(4,tmp,0,'return')
    h.branch(4,0,0,'reading');code=h.finish()
    if len(code)>len(old):raise ValueError('Ruby block grew')
    return offset,code+bytes(len(old)-len(code))

def scanner_digits_cases(code,labels):
    from font_vram_hooks import instruction_model
    from live_vwf import j
    model=instruction_model();b=model['B'];patched=bytearray(code)
    struct.pack_into('<II',patched,0,j(b+labels['byte']*4),0)
    for label,dest in [('return',0xeadbe00),('validated',0xeadbe20)]:struct.pack_into('<II',patched,labels[label]*4,j(dest),0)
    samples=[(b'A\x0f'+str(n).encode()+b'A\x0f\x12\x0e',True)for n in range(1,10)]
    samples +=[(b'Kogoro\x0f3Kogoro\x0f!!\x12\x0e',True),(b'A'*1016+b'\x0f3hero\x0f\0',True),(b'A'*1017+b'\x0f3hero\x0f\0',False)]
    samples +=[(s,False)for s in (b'A\x0f0A\x0f\0',b'A\x0f:A\x0f\0',b'A\x0f3\x0f\0',b'A\x0f3A\x11B\x0f\0',b'A\x0f3A\0')]
    results=[]
    for raw,supported in samples:
        regs=[0]*32;regs[5]=0x220000;regs[10]=1;regs[29]=0x250000
        mem={0x220000+n:v for n,v in enumerate(raw)};mem.update({0x250000+n:0 for n in range(128)})
        mem.update({0x250000+76+n:v for n,v in enumerate(struct.pack('<I',1))})
        pc,_,reads=model['execute'](bytes(patched),regs,mem)
        probes=[a for a in reads if 0x220000<=a<0x221000]
        if pc!=(0xeadbe20 if supported else 0xeadbe00)or max(probes,default=0)>0x220000+min(len(raw)-1,1023):raise ValueError('Digit scanner result/bound differs')
        results.append(dict(bytes=len(raw),supported=supported,passed=True))
    return results

def layer_location(name,raw,index):
    p=parse(name,raw);base=p['head'][0];h=struct.unpack_from('<16I',raw,base);first=0
    for group,(_,count,_)in enumerate(p['desc']):
        if first<=index<first+count:break
        first+=count
    key=p['refs'][index][0]
    _,lo,_,_=struct.unpack_from('<4I',raw,base+h[12]+group*16)
    layer=struct.unpack_from('<21I',raw,base+h[14]+lo+key*84)
    return base+h[15]+layer[0],layer

def build():
    incoming=(BASE/'EBOOT.BIN').read_bytes();before=json.loads((BASE/'manifest.en.json').read_bytes())['setup_patch']
    if sha(incoming)!=INPUT_SHA:raise ValueError('Frozen .50 executable differs')
    e=Elf(incoming);o=Elf(ORIGINAL.read_bytes());refs,_=reference_index(e)
    result=bytearray(incoming);allowed=set();masks=[set(),set(),set()];changes=[];queue=[]
    def install(rva,data,name):
        off=e.file_offset(rva,len(data));result[off:off+len(data)]=data
        allowed.update(range(off,off+len(data)))
        segment=next(n for n,p in enumerate(e.ph[:3])if p[2]<=rva and rva+len(data)<=p[2]+p[4])
        masks[segment].update(range(rva-e.ph[segment][2],rva-e.ph[segment][2]+len(data)))
        changes.append(dict(name=name,rva=rva,bytes=len(data),before_sha256=sha(incoming[off:off+len(data)]),after_sha256=sha(data)))
    for table,base,targets in ((0,0x94760,LABELS),(1,0x95450,HELP)):
        for index,target in targets.items():
            slot=base+index*4;rva=e.word(slot);old=cstring(e,rva);original=cstring(o,o.word(slot))
            if rva!=o.word(slot)or old!=original:raise ValueError('Selected UI already changed: '+str((table,index)))
            owners=[r for r in refs if rva<=r['address']<rva+len(old)]
            if len(owners)!=1 or owners[0]['kind']!='R_MIPS_32' or owners[0]['sites']!=[slot]:raise ValueError('UI has another owner')
            new=encoded_text(target,'ascii')+b'\0'
            if len(new)>len(old):raise ValueError('UI capacity exceeded: '+str((table,index,len(new),len(old))))
            install(rva,new,'ui_'+str(table)+'_'+str(index))
            queue.append(dict(id='ui_051_'+str(table)+'_'+str(index),category='battle_result_ui'if table==1 and index>=70 else'party_menu_ui',native_index=index,native_table=table,target=target,status='installed_static_verified',source_sha256=sha(old)))
    layout=before['english_bubble_layout'];measured,ml=capture(lambda:measure_1a(before['body_integer_lut_rva'],True),dm)
    primary,pl=capture(lambda:eb.primary(layout['body_helper_rva'],layout['descriptor_rva'],layout['main_rva'],layout['epilogue_rva']),eb)
    new_codes=[]
    for name,code,labels,rva,end,resume,regs in (
        ('measurement',measured,ml,before['font_hooks']['measurement'],'endline','char',(11,25,13,15)),
        ('geometry_scanner',primary[0],pl,layout['main_rva'],'row_end','byte',(5,6,7,24))):
        offset,old=ruby_chunk(labels,end,resume,*regs)
        if incoming[e.file_offset(rva+offset):][:len(old)]!=old:raise ValueError('Inherited ruby differs')
        _,chunk=ruby_digits(labels,end,resume,*regs)
        install(rva+offset,chunk,name);new=bytearray(code);new[offset:offset+len(chunk)]=chunk;new_codes.append(bytes(new))
    widths=struct.unpack_from('<131I',incoming,e.file_offset(before['body_integer_lut_rva']))
    test=bytearray(measure_1a(0x240000,True));offset,chunk=ruby_digits(ml,'endline','char',11,25,13,15);test[offset:offset+len(chunk)]=chunk
    samples=[([b'Kogoro\x0f3Kogoro\x0f!!\x12'],True),([b'Michie\x0f2Michie\x0f Sawada\x0f3Sawada\x0f\x12'],True)]
    samples += [([b'A\x0f'+str(n).encode()+b'A\x0f\x12'],True) for n in range(1,10)]
    samples += [([raw],False)for raw in (b'A\x0f0A\x0f\x12',b'A\x0fXA\x0f\x12',b'A\x0f3\x0f\x12',b'A\x0f3A\x11B\x0f\x12',b'A\x0f3A\0',b'A\x0f3\x83\x41\x0f\x12')]
    samples += [([b'\x1a5As the combo count rises, damage increases.\x12'],True),
        ([b'\x1a6Use the directional buttons.\x11',b'Front-row characters\x11',b'cannot perform Offense Actions.\x12'],True),
        ([b'\x1a0A\x12'],True),([b'\x1a9A\x12'],True),([b'\x1aXA\x12'],False),([b'\x1a\0'],False),
        ([b'\x1a5\x010A\x12'],False),([b'\x1a5A\x0f1A\x0f\x12'],True),
        ([b'\x1a5\xf0\x40\xf0\x41\x12'],True),([b'A'*1022+b'\x1a5\x12'],True),([b'A'*1023+b'\x1a5\x12'],False)]
    measurement=instruction_cases(widths,bytes(test),samples)
    scanners=scanner_cases(new_codes[1],pl)+scanner_digits_cases(new_codes[1],pl)
    out=bytes(result);oe=Elf(out);coverage(out)
    if oe.ph!=e.ph or oe.relocs!=e.relocs or any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,out))):raise ValueError('Unselected ELF bytes changed')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);b,_,skipped,_=section_load(out,base)
        if skipped or any(len(x)!=len(y)or any(v!=w and n not in masks[s]for n,(v,w)in enumerate(zip(x,y)))for s,(x,y)in enumerate(zip(a,b))):raise ValueError('Unselected loaded bytes changed')
        models.append(dict(base=base,unselected_memory_exact=True))
    report=copy.deepcopy(before);report.update(version='0.1.51',input_version='0.1.50',input_sha256=INPUT_SHA,output_elf_sha256=sha(out),output_sha256=sha(out),elf_bytes=len(out),runtime_verified=False)
    for c in report['native_tail_compaction']['chunks']:
        f,n=c['file_offset'],c['bytes']
        if out[f:f+n]!=incoming[f:f+n]:c['output_sha256']=sha(out[f:f+n])
    report['english_bubble_layout']['main_sha256']=sha(out[e.file_offset(layout['main_rva']):][:layout['main_bytes']])
    report['font_native_tail_loaded_extension_sha256']=sha(out[e.ph[2][1]:e.ph[2][1]+e.ph[2][4]])
    report['english_bubble_layout']['accepted_controls']=[s.replace('span digit2','span digits1 through9') for s in layout['accepted_controls']]
    report['ui_dialogue_051']=dict(changes=changes,labels=queue,measurement_cases=measurement,scanner_cases=scanners,loader_models=models,loaded_growth_bytes=0,natural_gameplay_verified=False)
    authoritative_font_metadata(out,report);validate_native_png_metadata(out,report)
    # Profile cards use authored tailless styles; choose the existing widest
    # three-line style and add readable pages rather than inventing a tail.
    replacements={7:b'\x010\x11\x011\x11Age 24\x12\x0e',
        8:b'This young\x11agent works\x11for \x05131\x1603S.I.R.\x1601,\x12\x10a private\x11investigation\x11agency.\x12\x10Also known as\x11\x012.\x12\x0e',
        10:b'Michie\x0f2Michie\x0f Sawada\x0f3Sawada\x0f\x11Age 17\x12\x0e',
        11:b'This provisional\x11S.I.R. member\x11serves as\x12\x10\x011\x27s\x11assistant.\x12\x10Nickname: Mitch.\x12\x0e',
        21:b'\x1cKogoro\x0eCorrect!\x11I am the\x11space detective,\x11Kogoro\x0f3Kogoro\x0f!!\x12\x0e'}
    assets={};records=[]
    names=['phase/bin/p101020.bin','phase/bin/p101021.bin','btl/res/r05002.bin','resident/ALLResidentNML.bin']
    for name,raw in read(BASE/'HP.CPK',names).items():
        if name.startswith('resident/'):
            assets[name],report['ui_dialogue_051']['menu_heading_bitmap'],_=menu_bitmap(raw)
            continue
        p=parse(name,raw);selected=replacements if name.startswith('phase')else{7:b'\x1cGourry\x0eWith the Sword of Light,\x11I\x27m as strong as\x11a hundred men!\x12\x0e'}
        changed,np=rebuild(name,raw,selected);mut=bytearray(changed);track_allowed=set()
        for index,new in selected.items():
            edits=[]
            old=p['spans'][p['refs'][index][1]][0]
            ch,layer=layer_location(name,changed,index)
            if name.startswith('phase')and index in (7,8,10,11):
                if layer[9]!=1:raise ValueError('Profile has multiple shapes')
                newshape={7:112,8:112,10:132,11:142}[index]
                pos=ch+layer[10]+4;oldshape=struct.unpack_from('<H',mut,pos)[0];struct.pack_into('<H',mut,pos,newshape)
                edits.append(dict(offset=pos,old_shape=oldshape,new_shape=newshape))
                track_allowed.update(range(pos,pos+2))
            if name.startswith('btl'):
                pos=ch+layer[10]+4;struct.pack_into('<H',mut,pos,141);edits.append(dict(offset=pos,old_shape=121,new_shape=141))
                track_allowed.update(range(pos,pos+2))
                for k in range(layer[13]):
                    pos=ch+layer[14]+k*20;v=list(struct.unpack_from('<4fI',mut,pos));v[1]+=20;v[2]-=37;struct.pack_into('<4fI',mut,pos,*v)
                    edits.append(dict(offset=pos+4,position_delta=[20,-37]))
                    track_allowed.update(range(pos+4,pos+12))
            records.append(dict(resource=name,reference_index=index,old_english=old.decode('ascii'),new_english=new.decode('ascii'),original_tail_anchor_preserved=index==21,profile_has_no_tail=index in(7,8,10,11),layout_edits=edits.copy(),natural_playback_verified=False))
        for index,(_,off)in enumerate(p['refs']):
            if index not in selected and p['spans'][off][0]!=np['spans'][np['refs'][index][1]][0]:raise ValueError('Other dialogue changed')
        if raw[p['end']:]!=changed[np['end']:]:raise ValueError('Nontext suffix changed')
        if any(a!=b and n not in track_allowed for n,(a,b)in enumerate(zip(changed,mut))):raise ValueError('Unselected scene track changed')
        assets[name]=bytes(mut)
    report['ui_dialogue_051']['records']=records
    return out,report,assets,dict(schema_version=1,language='en',rows=queue)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256');a=ap.parse_args()
    data,report,assets,queue=build();p=report['ui_dialogue_051']
    print(json.dumps(dict(version='0.1.51',sha256=sha(data),labels=len(p['labels']),resources=list(assets),measurement_cases=len(p['measurement_cases']),records=p['records']),indent=2))
    if not a.write:print('DRY RUN');return
    if OUT.exists()or a.expected_sha256!=sha(data):raise ValueError('Fresh output and reviewed hash required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data);(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for name,b in assets.items():
        path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
    # Keep the editable source queues and their publishable English copies in sync.
    for batch in ('batch_0013','batch_0199'):
        path=Path('work/translation/en')/(batch+'.json');working=json.loads(path.read_text(encoding='utf-8'))
        for row in working['rows']:
            matches=[r for r in p['records']if r['resource']+':'+str(r['reference_index']).zfill(4)in row.get('occurrences',[])]
            if matches:
                values={notation(r['new_english'].encode('ascii'))for r in matches}
                if len(values)!=1:raise ValueError('Logical row variants disagree')
                row['target']=values.pop();row['notes']='0.1.51 scoped profile/dialogue reflow; stored player names and original Kogoro speaker anchor retained. Natural playback pending.'
        path.write_text(json.dumps(working,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        path.with_suffix('.en.json').write_text(json.dumps(export(working),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    q=Path('work/translation/en/ui_dialogue_051.json');q.write_text(json.dumps(queue,indent=2)+'\n',encoding='utf-8');q.with_suffix('.en.json').write_text(json.dumps(export(queue),indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
