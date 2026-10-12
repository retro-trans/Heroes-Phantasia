"""Reorder the reported two bubbles, preserving their original authored tracks.

Only group0 of p101040/041 is selected. Whole bubble layer records move,
with corresponding text reference keys. Channels and portrait associations
stay with their bubbles, so reveal times, motion and native anchors are exact.
"""
import argparse,json,struct
from pathlib import Path
from prepare_bubble_scenes_036 import read,sha
from rebuild_dialogue import parse,rebuild
from executable_text_patch import Elf
from dialogue_tokens import tokenize_bytes
from bubble_metrics import load_templates

BASE=Path('work/output/0.1.38-title-credit-vwf-4x-candidate/HP.CPK')
OUT=Path('work/output/0.1.39-bubble-scene-assets')
NAMES=['phase/bin/p101040.bin','phase/bin/p101041.bin']
def build():
    assets={};records=[];templates=load_templates();elf=Elf(Path('work/output/0.1.32-world-map-assets/EBOOT.BIN').read_bytes())
    widths=struct.unpack_from('<131I',elf.data,elf.file_offset(0x2e4000))
    for name,raw in read(BASE,NAMES).items():
        p=parse(name,raw);input_sha=sha(raw);old_text=p['spans'][p['refs'][17][1]][0]
        speaker,body=old_text.split(b'\x0e',1);words=body.split(b'\x12',1)[0].replace(b'\x11',b' ').split();lines=[b'']
        for word in words:
            candidate=lines[-1]+(b' 'if lines[-1]else b'')+word
            if sum(widths[v]for v in candidate)>120 and lines[-1]:lines.append(word)
            else:lines[-1]=candidate
        new_text=speaker+b'\x0e'+b'\x11'.join(lines)+b'\x12'+body.split(b'\x12',1)[1]
        if len(lines)!=6 or b'To people like you'not in new_text:raise ValueError('Reported mainland reflow differs')
        controls=lambda b:[(t.code,t.argument.hex())for t in tokenize_bytes(b,True)if t.kind=='control'and t.code!=0x11]
        if controls(old_text)!=controls(new_text)or old_text.replace(b' ',b'').replace(b'\x11',b'')!=new_text.replace(b' ',b'').replace(b'\x11',b''):raise ValueError('Mainland words or nonline controls changed')
        raw,proof=rebuild(name,raw,{17:new_text});p=parse(name,raw);base=p['head'][0];h=struct.unpack_from('<16I',raw,base)
        count,offset,duration,unused=struct.unpack_from('<4I',raw,base+h[12])
        if count!=4 or offset!=0:raise ValueError('Reported first group differs')
        layerbase=base+h[14]+offset
        before=[raw[layerbase+n*84:layerbase+(n+1)*84]for n in range(count)]
        if [struct.unpack_from('<I',v,20)[0]for v in before] != [0,1,3,3]:raise ValueError('Layer kinds differ')
        texts=[p['spans'][off][0]for key,off in p['refs'][:2]]
        if b'Straight Cougar.'not in texts[0]or b"You're a member of HOLY?"not in texts[1]or [r[0]for r in p['refs'][:2]]!=[2,3]:raise ValueError('Reported speakers differ')
        result=bytearray(raw);result[layerbase+168:layerbase+336]=before[3]+before[2]
        struct.pack_into('<I',result,p['refs_start'],3);struct.pack_into('<I',result,p['refs_start']+8,2)
        allowed=set(range(layerbase+168,layerbase+336))|set(range(p['refs_start'],p['refs_start']+4))|set(range(p['refs_start']+8,p['refs_start']+12))
        if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(raw,result))):raise ValueError('Unselected resource bytes differ')
        pp=parse(name,result)
        if pp['spans']!=p['spans']or pp['desc']!=p['desc']or pp['head']!=p['head']:raise ValueError('Dialogue/structure changed')
        details=[]
        for ref in (0,1):
            oldkey=p['refs'][ref][0];newkey=pp['refs'][ref][0]
            original=before[oldkey];changed=bytes(result[layerbase+newkey*84:layerbase+(newkey+1)*84])
            if changed!=original:raise ValueError('Bubble identity/tracks changed')
            l=struct.unpack('<21I',original);ch=base+h[15]+l[0]
            positions=[struct.unpack_from('<4fI',raw,ch+l[14]+i*20)for i in range(l[13])]
            shapes=[struct.unpack_from('<fHH',raw,ch+l[10]+i*8)for i in range(l[9])]
            shape=shapes[-1][1];x,y=positions[-1][1:3];t=templates[shape];tip=t['outline'][(shape-3)%10+1]
            details.append(dict(reference_index=ref,old_layer=oldkey,new_layer=newkey,layer_identity_exact=True,
                shape=shape,position=[x,y],native_tip=[x+tip[0],y+tip[1]],position_keys=positions,shape_keys=shapes,
                portrait_association=l[6],reveal_start_frame=21 if ref==0 else 10))
        assets[name]=bytes(result);records.append(dict(resource=name,input_sha256=input_sha,output_sha256=sha(result),
            bubble_order_back_to_front=['Mitch','Cougar'],text_reference_remap={'2':3,'3':2},bubbles=details,
            all_channel_bytes_exact=True,other_dialogue_bytes_exact=True,other_group_tracks_exact=True,
            reflow=dict(reference_index=17,old_english=old_text.decode('ascii'),new_english=new_text.decode('ascii'),visible_lines=6,
                maximum_line_px=max(sum(widths[v]for v in line)for line in lines),words_and_nonline_controls_exact=True)))
    return assets,dict(version='0.1.39',base_archive_sha256=sha(BASE.read_bytes()),records=records,
        scope='Reported first two-bubble group, both protagonist branches.',natural_playback_verified=False)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args();assets,p=build();print(json.dumps(p,indent=2))
    if not a.write:print('DRY RUN');return
    if OUT.exists():raise ValueError('Fresh output required')
    OUT.mkdir(parents=True)
    for name,raw in assets.items():
        dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    (OUT/'order.en.json').write_text(json.dumps(p,indent=2)+'\n')
if __name__=='__main__':main()
