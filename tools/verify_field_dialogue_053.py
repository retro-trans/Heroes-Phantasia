"""Verify nested .53 assets, all changed field fits and native width execution."""
import json,struct
from pathlib import Path
from prepare_field_dialogue_053 import BASE,OUT,UI,build,interior,rows
from prepare_bubble_scenes_036 import sha,read
from executable_text_patch import Elf,encoded_text
from rebuild_dialogue import parse
from prepare_ui_dialogue_051 import layer_location,ruby_digits
from prepare_dialogue_commands_048 import capture
from dialogue_measure_1a import measure_1a,instruction_cases
import dialogue_measure as dm
from bubble_metrics import load_templates
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from title_stamp import prepare as title_prepare,RESOURCE
from build_local import sha as file_sha

ROOT=Path('work/output/0.1.53-title-credit-vwf-4x-candidate')

def main():
    manifest=json.loads((ROOT/'manifest.en.json').read_bytes());data=(ROOT/'EBOOT.BIN').read_bytes();expected,report,assets,_=build();prep=report['field_dialogue_053']
    if manifest['version']!='0.1.53'or data!=expected or sha(data)!=manifest['output_elf_sha256']:raise ValueError('Build executable differs')
    e=Elf(data);widths=struct.unpack_from('<131I',data,e.file_offset(report['body_integer_lut_rva']));templates=load_templates();fits=[];samples=[]
    for rec in prep['reflow_records']:
        name,n=rec['resource'],rec['reference_index'];raw=assets[name];p=parse(name,raw);text=p['spans'][p['refs'][n][1]][0];ch,layer=layer_location(name,raw,n);shape=struct.unpack_from('<H',raw,ch+layer[10]+4)[0];pages=rows(text.split(b'\x0e',1)[1],widths)
        if shape!=rec['new_shape']or not interior(shape,pages,templates):raise ValueError('Installed white-interior fit differs')
        t=templates[shape];bounds=[]
        for k in range(layer[13]):
            pos=struct.unpack_from('<4fI',raw,ch+layer[14]+20*k);poly=t['banks'][1];b=[pos[1]+min(x for x,y in poly),pos[2]+min(y for x,y in poly),pos[1]+max(x for x,y in poly),pos[2]+max(y for x,y in poly)]
            if not(6<=b[0]<b[2]<=474 and 6<=b[1]<b[3]<=252):raise ValueError('Installed field box leaves viewport')
            bounds.append(b)
        samples.extend(([line+b'\x12'for line in page.split(b'\x12',1)[0].split(b'\x11')],True)for page in text.split(b'\x0e',1)[1].split(b'\x10'))
        fits.append(dict(resource=name,reference_index=n,shape=shape,page_line_advances=pages,all_position_bounds=bounds,white_interior_and_viewport_fit=True))
    for row in prep['numeric_name_records']:
        p=parse(row['resource'],assets[row['resource']]);text=p['spans'][p['refs'][row['reference_index']][1]][0]
        if text!=b'\x1cKogoro\x0e'+b'.'*row['silence_dots']+b'\x12\x0e':raise ValueError('Complete speaker/silence differs')
    # Run the existing measurement instructions against every new visible row.
    code,labels=capture(lambda:measure_1a(report['body_integer_lut_rva'],True),dm)
    offset,chunk=ruby_digits(labels,'endline','char',11,25,13,15);code=bytearray(code);code[offset:offset+len(chunk)]=chunk
    installed=data[e.file_offset(report['font_hooks']['measurement']):][:len(code)]
    # The compact installed hook uses the typed ADDIU low half; the historical
    # generator uses ORI. Its positive LUT low half gives the same address.
    at=25*4;generated=struct.unpack_from('<I',code,at)[0];actual=struct.unpack_from('<I',installed,at)[0]
    if generated!=0x35ce4000 or actual!=0x25ce4000:raise ValueError('Native LUT address construction differs')
    struct.pack_into('<I',code,at,actual)
    if installed!=code:raise ValueError('Installed native measurement differs')
    test=bytearray(installed)
    if struct.unpack_from('<I',test,24*4)[0]!=0x3c0e002e:raise ValueError('Native LUT high half differs')
    struct.pack_into('<II',test,24*4,0x3c0e0024,0x25ce0000)
    native=instruction_cases(widths,bytes(test),samples)
    for r in prep['labels']:
        if e.word(r['pointer_slot'])!=r['target_rva']or data[e.file_offset(r['target_rva']):][:len(r['target'])+1]!=encoded_text(r['target'],'ascii')+b'\0':raise ValueError('Chapter pointer/string differs')
    _,old=inventory(BASE/'HP.CPK');_,new=inventory(ROOT/'HP.CPK');changed=[a['path']for a,b in zip(old,new)if a!=b]
    if len(old)!=len(new)or set(changed)!=set(assets)|{RESOURCE}:raise ValueError('Unselected archive entry differs')
    title,*_=title_prepare(manifest['config']);assets[RESOURCE]=title
    if read(ROOT/'HP.CPK',list(assets))!=assets:raise ValueError('Packaged selected assets differ')
    iso=Path(manifest['iso_path']);entries=iso_inventory(iso);exe=next(r for r in entries if r['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');cpk=next(r for r in entries if r['path']=='PSP_GAME/USRDIR/HP.CPK')
    with iso.open('rb')as stream:
        stream.seek(exe['offset'])
        if stream.read(exe['size'])!=data:raise ValueError('Nested executable differs')
        for name,raw in assets.items():
            r=next(r for r in new if r['path']==name);stream.seek(cpk['offset']+r['offset'])
            if r['compression']!='none'or stream.read(len(raw))!=raw:raise ValueError('Nested asset differs')
    if file_sha(iso)!=manifest['iso_sha256']:raise ValueError('ISO digest differs')
    proof=dict(version='0.1.53',iso_sha256=manifest['iso_sha256'],executable_sha256=sha(data),archive_sha256=manifest['dialogue_cpk_sha256'],changed_archive_rows=len(changed),unselected_archive_rows_exact=len(new)-len(changed),field_fit_records=len(fits),native_measurement_pages=len(native),native_measurement_rows=sum(len(r['line_halfwidths'])for r in native),numeric_speaker_labels=4,chapter_labels=3,all_nested_assets_exact=True,loaded_growth_bytes=0,natural_scene_playback_verified=False)
    UI.mkdir(parents=True,exist_ok=True);(UI/'field_fit.en.json').write_text(json.dumps(dict(version='0.1.53',records=fits,native_measurement=native),indent=2)+'\n',encoding='utf8');(UI/'validation.en.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps(proof,indent=2))

if __name__=='__main__':main()
