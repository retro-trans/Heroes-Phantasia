"""Audit original authored tracks and prepare only the reported name-line reflow."""
import argparse,hashlib,json,struct
from pathlib import Path
from unpack_cpk import inventory,crilayla
from rebuild_dialogue import parse,rebuild
from dialogue_tokens import tokenize_bytes
from bubble_metrics import load_templates
from executable_text_patch import Elf

BASE=Path('work/output/0.1.35-title-credit-vwf-4x-candidate/HP.CPK')
ORIGINAL=Path('work/source/PSP_GAME/USRDIR/HP.CPK')
OUT=Path('work/output/0.1.36-bubble-reflow-assets')
UI=Path('work/ui/dialogue/0.1.36')
NAMES={'phase/bin/p101041.bin':(34,), 'phase/bin/p101050.bin':(2,5,13), 'phase/bin/p101051.bin':(2,5,13)}
OLD=b"I'm from S.I.R.\x11My name is \x010\x011."
NEW=b"I'm from S.I.R.\x11My name is\x11\x010 \x011."
def sha(b):return hashlib.sha256(b).hexdigest()
def read(path,names):
    _,rows=inventory(path);result={}
    with path.open('rb')as f:
        for name in names:
            r=next(r for r in rows if r['path']==name);f.seek(r['offset']);b=f.read(r['stored_size'])
            result[name]=crilayla(b,r['extract_size'])if r['compression']=='CRILAYLA'else b
    return result

def build():
    original=read(ORIGINAL,NAMES);english=read(BASE,NAMES);records=[];assets={};changes=[]
    elf=Elf(Path('work/output/0.1.32-world-map-assets/EBOOT.BIN').read_bytes())
    widths=struct.unpack_from('<131I',elf.data,elf.file_offset(0x2e4000));templates=load_templates()
    if max(widths[32:127])>13:raise ValueError('Native 13px name fallback no longer bounds Latin advances')
    for name,indices in NAMES.items():
        before=parse(name,english[name]);op=parse(name,original[name])
        if original[name][op['head'][0]:op['start']]!=english[name][before['head'][0]:before['start']]:
            raise ValueError('Original animation/layer/channel tracks differ')
        replacements={}
        if name.endswith(('p101050.bin','p101051.bin')):
            raw=before['spans'][before['refs'][2][1]][0]
            if OLD not in raw:raise ValueError('Reported introduction differs')
            replacements[2]=raw.replace(OLD,NEW)
            controls=lambda b:[(t.code,t.argument.hex())for t in tokenize_bytes(b,True)if t.kind=='control'and t.code!=0x11]
            if controls(raw)!=controls(replacements[2]):raise ValueError('Nonline controls changed')
            # Only whitespace is changed; all literal words and substitutions stay.
            if raw.replace(b' ',b'').replace(b'\x11',b'')!=replacements[2].replace(b' ',b'').replace(b'\x11',b''):
                raise ValueError('Dialogue words changed')
            changed,proof=rebuild(name,english[name],replacements);assets[name]=changed
            for n,(_,off)in enumerate(before['refs']):
                if n!=2 and before['spans'][off][0]!=proof['spans'][proof['refs'][n][1]][0]:raise ValueError('Other dialogue changed')
            if english[name][before['end']:]!=changed[proof['end']:]:raise ValueError('Nontext suffix changed')
            changes.append(dict(resource=name,reference_index=2,before=raw.decode('ascii'),after=replacements[2].decode('ascii'),
                native_names_preserved=True,maximum_name_glyphs=26,maximum_name_line_advance_px=28*13,
                output_sha256=sha(changed),other_dialogue_exact=True,nontext_suffix_exact=True))
        installed=assets.get(name,english[name]);p=parse(name,installed);b=p['head'][0];h=struct.unpack_from('<16I',installed,b)
        for index in indices:
            key,off=p['refs'][index];first=0
            for group,(_,count,_)in enumerate(p['desc']):
                if first<=index<first+count:break
                first+=count
            _,layeroff,_,_=struct.unpack_from('<4I',installed,b+h[12]+group*16)
            layer=struct.unpack_from('<21I',installed,b+h[14]+layeroff+key*84)
            if layer[5]!=3:raise ValueError('Selected layer is not a bubble')
            ch=b+h[15]+layer[0]
            shapes=[struct.unpack_from('<fHH',installed,ch+layer[10]+i*8)for i in range(layer[9])]
            positions=[struct.unpack_from('<4fI',installed,ch+layer[14]+i*20)for i in range(layer[13])]
            shape=shapes[-1][1];x,y=positions[-1][1:3];tip=templates[shape]['outline'][(shape-3)%10+1]
            raw=p['spans'][off][0];body=raw.split(b'\x0e',1)[1];tokens=tokenize_bytes(body,True);sizes=[0];dynamic=False
            for t in tokens:
                if t.kind=='latin':sizes[-1]+=widths[t.code]
                elif t.code==1:
                    dynamic=True;sizes[-1]+=13*(9 if t.argument==b'0'else 17)
                elif t.code==0x11:sizes.append(0)
                elif t.code==0x0e:break
            if dynamic:
                # Native measurement uses 13px units for the whole record.
                sizes=[0]
                for t in tokens:
                    if t.kind=='latin':sizes[-1]+=13
                    elif t.code==1:sizes[-1]+=13*(9 if t.argument==b'0'else 17)
                    elif t.code==0x11:sizes.append(0)
                    elif t.code==0x0e:break
            records.append(dict(resource=name,reference_index=index,text_group=group,reference_key=key,
                installed_english=raw.decode('ascii'),body_hex=body.hex(),shape=shape,position=[x,y],
                native_tail_endpoint=[x+tip[0],y+tip[1]],shape_keys=shapes,position_keys=positions,
                native_track_sha256=sha(original[name][op['head'][0]:op['start']]),original_japanese_tracks_exact=True,
                visible_lines=len(sizes),halfwidth=max(sizes)/2,native_name_width=dynamic))
    return assets,dict(version='0.1.36',base_archive_sha256=sha(BASE.read_bytes()),records=records,reflows=changes,
        preserve_original_anchor=True,automatic_mouth_tracking=False,natural_playback_verified=False)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--verify-existing',action='store_true');a=ap.parse_args();assets,p=build()
    print(json.dumps(p,indent=2))
    # Corpus deduplication stores this shared male/female line once.
    from strip_jp import export
    qp=Path('work/translation/en/batch_0014.json');queue=json.loads(qp.read_text(encoding='utf8'))
    row=next(r for r in queue['rows']if r['id']=='687199237ab88afe7406')
    old="I'm from S.I.R.{11}My name is {01}0{01}1."
    new="I'm from S.I.R.{11}My name is{11}{01}0 {01}1."
    if old not in row['target']and new not in row['target']:raise ValueError('Shared logical introduction differs')
    row['target']=row['target'].replace(old,new)
    note=' 0.1.36: three-line introduction; original name selectors preserved, with an English name separator.'
    if note not in row['notes']:row['notes']+=note
    clean=export(queue)
    if a.verify_existing:
        for name,b in assets.items():
            if (OUT/name).read_bytes()!=b:raise ValueError('Prepared resource differs')
        expected=json.loads(json.dumps(p))
        if json.loads((OUT/'reflows.en.json').read_text())!=expected or json.loads((UI/'reported_scenes.en.json').read_text())!=expected:
            raise ValueError('Prepared evidence differs')
        if json.loads(qp.read_text(encoding='utf8'))!=queue or json.loads(qp.with_suffix('.en.json').read_text(encoding='utf8'))!=clean:
            raise ValueError('Shared logical queue/export differs')
        print('Existing preparation and shared logical translation verified.');return
    if not a.write:print('DRY RUN');return
    if OUT.exists()or (UI/'reported_scenes.en.json').exists():raise ValueError('Fresh outputs required')
    OUT.mkdir(parents=True);UI.mkdir(parents=True,exist_ok=True)
    for name,b in assets.items():
        dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
    (OUT/'reflows.en.json').write_text(json.dumps(p,indent=2)+'\n',encoding='utf8')
    (UI/'reported_scenes.en.json').write_text(json.dumps(p,indent=2)+'\n',encoding='utf8')
    qp.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    qp.with_suffix('.en.json').write_text(json.dumps(clean,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
