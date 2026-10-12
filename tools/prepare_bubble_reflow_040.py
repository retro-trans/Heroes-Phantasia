"""Fit the reported elevator pages without changing authored motion or words."""
import argparse,json,struct
from pathlib import Path
from prepare_bubble_scenes_036 import read,sha
from executable_text_patch import Elf
from rebuild_dialogue import parse,rebuild
from dialogue_tokens import tokenize_bytes
from bubble_metrics import load_templates
BASE=Path('work/output/0.1.39-title-credit-vwf-4x-candidate/HP.CPK')
OUT=Path('work/output/0.1.40-bubble-scene-assets')
NAMES=['phase/bin/p101040.bin','phase/bin/p101041.bin']

def record(name,raw,index,widths):
    p=parse(name,raw);base=p['head'][0];h=struct.unpack_from('<16I',raw,base);first=0
    for group,(_,count,_)in enumerate(p['desc']):
        if first<=index<first+count:break
        first+=count
    key,off=p['refs'][index];text=p['spans'][off][0]
    _,lo,_,_=struct.unpack_from('<4I',raw,base+h[12]+group*16)
    layer=struct.unpack_from('<21I',raw,base+h[14]+lo+key*84);ch=base+h[15]+layer[0]
    shapes=[struct.unpack_from('<fHH',raw,ch+layer[10]+i*8)for i in range(layer[9])]
    positions=[struct.unpack_from('<4fI',raw,ch+layer[14]+i*20)for i in range(layer[13])]
    shape=shapes[-1][1];t=load_templates()[shape];f=(shape-3)%10;tip=t['outline'][f+1]
    v=[(t['outline'][f][a]+t['outline'][f+2][a])/2-tip[a]for a in (0,1)]
    pages=[]
    for page in text.split(b'\x0e',1)[1].split(b'\x10'):
        advances=[0]
        for token in tokenize_bytes(page,True):
            if token.kind=='latin':advances[-1]+=widths[token.code]
            elif token.code==0x11:advances.append(0)
            elif token.code==0x0e:break
        pages.append(dict(body_hex=page.hex(),line_advances=advances))
    return dict(resource=name,reference_index=index,shape=shape,position=list(positions[-1][1:3]),
        position_keys=positions,shape_keys=shapes,native_reverse_ray=v,
        native_tail_endpoint=[positions[-1][a+1]+tip[a]for a in (0,1)],pages=pages)

def build():
    elf=Elf(Path('work/output/0.1.32-world-map-assets/EBOOT.BIN').read_bytes())
    widths=struct.unpack_from('<131I',elf.data,elf.file_offset(0x2e4000));assets={};records=[];fixtures=[]
    for name,raw in read(BASE,NAMES).items():
        p=parse(name,raw);old=p['spans'][p['refs'][7][1]][0]
        if b'but the elevator is being inspected,'not in old:raise ValueError('Reported elevator text differs')
        speaker,body=old.split(b'\x0e',1);pages=[]
        for page in body.split(b'\x10'):
            plain,suffix=page.split(b'\x12',1);lines=[b'']
            for word in plain.replace(b'\x11',b' ').split():
                candidate=lines[-1]+(b' 'if lines[-1]else b'')+word
                if sum(widths[v]for v in candidate)>176 and lines[-1]:lines.append(word)
                else:lines[-1]=candidate
            pages.append(b'\x11'.join(lines)+b'\x12'+suffix)
        new=speaker+b'\x0e'+b'\x10'.join(pages)
        controls=lambda b:[(t.code,t.argument.hex())for t in tokenize_bytes(b,True)if t.kind=='control'and t.code!=0x11]
        if controls(old)!=controls(new)or old.replace(b' ',b'').replace(b'\x11',b'')!=new.replace(b' ',b'').replace(b'\x11',b''):raise ValueError('Words or nonline controls changed')
        changed,np=rebuild(name,raw,{7:new})
        if raw[p['head'][0]:p['start']]!=changed[np['head'][0]:np['start']]or raw[p['end']:]!=changed[np['end']:]:raise ValueError('Authored tracks or nontext bytes changed')
        assets[name]=changed
        records.append(dict(resource=name,reference_index=7,input_sha256=sha(raw),output_sha256=sha(changed),
            old_english=old.decode('ascii'),new_english=new.decode('ascii'),words_and_nonline_controls_exact=True,all_authored_tracks_exact=True))
        for ref in (6,7,27):
            if ref==27 and name.endswith('040.bin'):continue
            fixtures.append(record(name,changed,ref,widths))
    return assets,dict(version='0.1.40',records=records,fixtures=fixtures,natural_playback_verified=False)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args();assets,p=build()
    print(json.dumps(p,indent=2))
    if not a.write:print('DRY RUN');return
    if OUT.exists():raise ValueError('Fresh output required')
    OUT.mkdir(parents=True)
    for name,raw in assets.items():
        dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    (OUT/'reflow.en.json').write_text(json.dumps(p,indent=2)+'\n')
if __name__=='__main__':main()
