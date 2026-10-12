"""Scoped English reflow for Cougar's field bubble, preserving its source ray."""
import argparse,json,struct
from pathlib import Path
from prepare_bubble_scenes_036 import read,sha
from executable_text_patch import Elf
from rebuild_dialogue import parse,rebuild
from dialogue_tokens import tokenize_bytes
BASE=Path('work/output/0.1.38-title-credit-vwf-4x-candidate/HP.CPK')
OUT=Path('work/output/0.1.39-bubble-field-assets');NAME='fld/talk/f101070.bin'
def build():
    raw=read(BASE,[NAME])[NAME];p=parse(NAME,raw);text=p['spans'][p['refs'][0][1]][0]
    if not text.startswith(b'\x1cCougar\x0eYou know,'):raise ValueError('Reported field record differs')
    e=Elf(Path('work/output/0.1.32-world-map-assets/EBOOT.BIN').read_bytes());ws=struct.unpack_from('<131I',e.data,e.file_offset(0x2e4000))
    speaker,body=text.split(b'\x0e',1);pages=[];sizes=[]
    for page in body.split(b'\x10'):
        plain,suffix=page.split(b'\x12',1);lines=[b'']
        for word in plain.replace(b'\x11',b' ').split():
            c=lines[-1]+(b' 'if lines[-1]else b'')+word
            if sum(ws[v]for v in c)>144 and lines[-1]:lines.append(word)
            else:lines[-1]=c
        pages.append(b'\x11'.join(lines)+b'\x12'+suffix);sizes.append([sum(ws[v]for v in line)for line in lines])
    target=speaker+b'\x0e'+b'\x10'.join(pages)
    controls=lambda b:[(t.code,t.argument.hex())for t in tokenize_bytes(b,True)if t.kind=='control'and t.code!=0x11]
    if controls(text)!=controls(target)or text.replace(b' ',b'').replace(b'\x11',b'')!=target.replace(b' ',b'').replace(b'\x11',b''):raise ValueError('Field wording/control changed')
    changed,np=rebuild(NAME,raw,{0:target})
    if raw[p['head'][0]:p['start']]!=changed[np['head'][0]:np['start']]or raw[p['end']:]!=changed[np['end']:]:raise ValueError('Nontext field bytes changed')
    return changed,dict(version='0.1.39',resource=NAME,reference_index=0,input_sha256=sha(raw),output_sha256=sha(changed),
        old_english=text.decode('ascii'),new_english=target.decode('ascii'),page_line_advances=sizes,words_and_nonline_controls_exact=True,original_tracks_exact=True)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args();raw,p=build();print(json.dumps(p,indent=2))
    if not a.write:print('DRY RUN');return
    if OUT.exists():raise ValueError('Fresh output required')
    dest=OUT/NAME;dest.parent.mkdir(parents=True);dest.write_bytes(raw);(OUT/'reflow.en.json').write_text(json.dumps(p,indent=2)+'\n')
if __name__=='__main__':main()
