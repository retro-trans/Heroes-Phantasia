"""Reflow the reported construction-company introduction; preserve its controls."""
import argparse,json,struct
from pathlib import Path
from prepare_bubble_scenes_036 import read,sha
from executable_text_patch import Elf
from rebuild_dialogue import parse,rebuild
from dialogue_tokens import tokenize_bytes
from prepare_bubble_reflow_040 import record
BASE=Path('work/output/0.1.40-title-credit-vwf-4x-candidate/HP.CPK')
OUT=Path('work/output/0.1.41-bubble-scene-assets')
NAMES=['phase/bin/p101050.bin','phase/bin/p101051.bin']

def build():
    elf=Elf(Path('work/output/0.1.32-world-map-assets/EBOOT.BIN').read_bytes())
    widths=struct.unpack_from('<131I',elf.data,elf.file_offset(0x2e4000));assets={};records=[];fixtures=[]
    def advance(b):return sum(widths[t.code]for t in tokenize_bytes(b,True)if t.kind=='latin')
    for name,raw in read(BASE,NAMES).items():
        p=parse(name,raw);old=p['spans'][p['refs'][16][1]][0]
        if not old.startswith(b'\x1cMitch\x0eAn affiliate of the ')or b'Delos Construction,'not in old:raise ValueError('Reported introduction differs')
        speaker,body=old.split(b'\x0e',1);plain,suffix=body.split(b'\x12',1);lines=[b'']
        for word in plain.replace(b'\x11',b' ').split():
            candidate=lines[-1]+(b' 'if lines[-1]else b'')+word
            if advance(candidate)>114 and lines[-1]:lines.append(word)
            else:lines[-1]=candidate
        if len(lines)!=5 or max(advance(line)for line in lines)>114:raise ValueError('Reported line fit differs')
        new=speaker+b'\x0e'+b'\x11'.join(lines)+b'\x12'+suffix
        controls=lambda b:[(t.code,t.argument.hex())for t in tokenize_bytes(b,True)if t.kind=='control'and t.code!=0x11]
        if controls(old)!=controls(new)or old.replace(b' ',b'').replace(b'\x11',b'')!=new.replace(b' ',b'').replace(b'\x11',b''):raise ValueError('Words or nonline controls changed')
        changed,np=rebuild(name,raw,{16:new})
        if raw[p['head'][0]:p['start']]!=changed[np['head'][0]:np['start']]or raw[p['end']:]!=changed[np['end']:]:raise ValueError('Authored tracks or nontext bytes changed')
        for i,(_,off)in enumerate(p['refs']):
            if i!=16 and p['spans'][off][0]!=np['spans'][np['refs'][i][1]][0]:raise ValueError('Unselected dialogue changed')
        assets[name]=changed
        records.append(dict(resource=name,reference_index=16,input_sha256=sha(raw),output_sha256=sha(changed),
            old_english=old.decode('ascii'),new_english=new.decode('ascii'),line_advances=[advance(line)for line in lines],
            words_and_nonline_controls_exact=True,all_authored_tracks_exact=True,other_dialogue_exact=True))
        for ref in (16,17):fixtures.append(record(name,changed,ref,widths))
    return assets,dict(version='0.1.41',records=records,fixtures=fixtures,natural_playback_verified=False)

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
