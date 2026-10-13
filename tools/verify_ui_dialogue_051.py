"""Verify .51 nested assets, selected tracks and default-name native style fit."""
import json,struct
from pathlib import Path
from executable_text_patch import Elf
from prepare_ui_dialogue_051 import BASE,OUT,layer_location
from prepare_bubble_scenes_036 import read,sha
from rebuild_dialogue import parse
from bubble_metrics import load_templates,centered_interval
from dialogue_tokens import tokenize_bytes
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from title_stamp import prepare,RESOURCE

ROOT=Path('work/output/0.1.51-title-credit-vwf-4x-candidate')
UI=Path('work/ui/dialogue/0.1.51')

def fit(assets=None):
    data=(OUT/'EBOOT.BIN').read_bytes();e=Elf(data);p=json.loads((OUT/'executable.en.json').read_text());widths=struct.unpack_from('<131I',data,e.file_offset(p['body_integer_lut_rva']));templates=load_templates();results=[]
    for name in ('phase/bin/p101020.bin','phase/bin/p101021.bin','btl/res/r05002.bin'):
        raw=assets[name]if assets is not None else(OUT/name).read_bytes();parsed=parse(name,raw)
        for index in ((7,8,10,11)if name.startswith('phase')else(7,)):
            ch,layer=layer_location(name,raw,index);shape=struct.unpack_from('<H',raw,ch+layer[10]+4)[0];t=templates[shape]
            position=struct.unpack_from('<4fI',raw,ch+layer[14]+(layer[13]-1)*20)
            polygon=t['banks'][1];bounds=[position[1]+min(x for x,y in polygon),position[2]+min(y for x,y in polygon),position[1]+max(x for x,y in polygon),position[2]+max(y for x,y in polygon)]
            if not(0<=bounds[0]<bounds[2]<=480 and 30<=bounds[1]<bounds[3]<=258):raise ValueError('Authored style exceeds viewport')
            text=parsed['spans'][parsed['refs'][index][1]][0]
            if text.startswith(b'\x1c'):text=text.split(b'\x0e',1)[1]
            fallback=b'\x01'in text;pages=[]
            for page in text.split(b'\x10'):
                lines=[bytearray()]
                for token in tokenize_bytes(page,True):
                    if token.ruby or token.kind in ('ruby_open','ruby_close'):continue
                    if token.kind=='latin':lines[-1].extend(token.data)
                    elif token.code==0x01:lines[-1].extend({b'0':b'Watari',b'1':b'Shinobu',b'2':b'S.I.R. Ace'}[token.argument])
                    elif token.code==0x11:lines.append(bytearray())
                advances=[len(line)*13 if fallback else sum(widths[c]for c in line)for line in lines]
                for n,advance in enumerate(advances):
                    top=t['text_offset'][1]+n*22;bands=[centered_interval(t['banks'][0],top+dy)for dy in (.001,8.,15.999)]
                    if any(q is None or -advance/2<q[0]+1 or advance/2>q[1]-1 for q in bands):raise ValueError('Text exceeds authored white interior')
                pages.append(dict(lines=[line.decode('ascii')for line in lines],advances=advances,mode='native13px conservative fallback'if fallback else'VWF',white_interior_fit=True))
            parent_half=max(advance for page in pages for advance in page['advances'])/2
            for page in pages:
                for n,advance in enumerate(page['advances']):
                    top=t['text_offset'][1]+n*22;bands=[centered_interval(t['banks'][0],top+dy)for dy in (.001,8.,15.999)]
                    if any(-parent_half<q[0]+1 or -parent_half+advance>q[1]-1 for q in bands):raise ValueError('Left-aligned parent width exceeds authored white interior')
            results.append(dict(resource=name,reference_index=index,shape=shape,pages=pages,settled_outline_bounds=bounds,outline_in_viewport=True,left_aligned_parent_width_fit=True))
    return dict(version='0.1.51',records=results,custom_names_preserved=True,max_length_custom_names_layout_verified=False,natural_gameplay_verified=False)

def main():
    manifest=json.loads((ROOT/'manifest.en.json').read_text());data=(ROOT/'EBOOT.BIN').read_bytes()
    if manifest['version']!='0.1.51'or data!=(OUT/'EBOOT.BIN').read_bytes()or sha(data)!=manifest['output_elf_sha256']:raise ValueError('Build identity differs')
    _,old=inventory(BASE/'HP.CPK');_,new=inventory(ROOT/'HP.CPK')
    selected=['phase/bin/p101020.bin','phase/bin/p101021.bin','btl/res/r05002.bin','resident/ALLResidentNML.bin'];changed=[a['path']for a,b in zip(old,new)if a!=b]
    if len(old)!=len(new)or set(changed)!=set(selected+[RESOURCE]):raise ValueError('Unselected archive row changed')
    title,*_=prepare(manifest['config']);expected={name:(OUT/name).read_bytes()for name in selected};expected[RESOURCE]=title
    if read(ROOT/'HP.CPK',list(expected))!=expected:raise ValueError('Installed archive asset differs')
    iso=Path(manifest['iso_path']);rows=iso_inventory(iso);exe=next(r for r in rows if r['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');cpk=next(r for r in rows if r['path']=='PSP_GAME/USRDIR/HP.CPK')
    with iso.open('rb')as f:
        f.seek(exe['offset'])
        if f.read(exe['size'])!=data:raise ValueError('Nested executable differs')
        for name,b in expected.items():
            r=next(r for r in new if r['path']==name);f.seek(cpk['offset']+r['offset'])
            if r['compression']!='none'or f.read(len(b))!=b:raise ValueError('Nested selected resource differs')
    UI.mkdir(parents=True,exist_ok=True);(UI/'native_style_fit.en.json').write_text(json.dumps(fit(),indent=2)+'\n')
    proof=dict(version='0.1.51',iso_sha256=manifest['iso_sha256'],executable_sha256=sha(data),archive_sha256=manifest['dialogue_cpk_sha256'],changed_archive_rows=changed,unselected_archive_rows_exact=len(new)-len(changed),nested_selected_assets_exact=True,default_name_style_fit_records=9,loaded_growth_bytes=0,natural_gameplay_verified=False,full_game_verified=False)
    (UI/'validation.en.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))

if __name__=='__main__':main()
