"""Read the three reported .35 records and native phase tracks; dry first."""
import argparse,json,struct
from pathlib import Path
from rebuild_dialogue import parse
from unpack_cpk import inventory

BASE=Path('work/output/0.1.34-title-credit-vwf-4x-candidate')
OUT=Path('work/ui/dialogue/0.1.35/reported_scenes.en.json')
def build():
    _,rows=inventory(BASE/'HP.CPK');records=[]
    with (BASE/'HP.CPK').open('rb')as f:
        for name in ('phase/bin/p101040.bin','phase/bin/p101041.bin'):
            row=next(r for r in rows if r['path']==name)
            if row['compression']!='none':raise ValueError('Unexpected compressed phase')
            f.seek(row['offset']);raw=f.read(row['stored_size']);p=parse(name,raw)
            base=p['head'][0];h=struct.unpack_from('<16I',raw,base)
            for ref in (0,1,4):
                text=p['spans'][p['refs'][ref][1]][0];group=0;first=0
                for group,(_,count,_)in enumerate(p['desc']):
                    if first<=ref<first+count:break
                    first+=count
                count,off,_,_=struct.unpack_from('<4I',raw,base+h[12]+group*16)
                key=p['refs'][ref][0]
                if key>=count:raise ValueError('Reference layer key outside animation')
                layer=struct.unpack_from('<21I',raw,base+h[14]+off+key*84)
                if layer[5]!=3:raise ValueError('Reported layer is not a bubble')
                channel=base+h[15]+layer[0]
                shapes=[struct.unpack_from('<fHH',raw,channel+layer[10]+i*8)for i in range(layer[9])]
                positions=[struct.unpack_from('<4fI',raw,channel+layer[14]+i*20)for i in range(layer[13])]
                records.append(dict(resource=name,reference_index=ref,text_group=group,reference_key=key,
                    installed_english=text.decode('ascii'),shape=shapes[-1][1],position=list(positions[-1][1:3]),
                    portrait_association=layer[6],shape_keys=shapes,position_keys=positions))
    return dict(version='0.1.35',source_version='0.1.34',records=records,natural_playback_verified=False)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args();p=build()
    print(json.dumps(p,indent=2))
    if not a.write:return
    if OUT.exists():raise ValueError('Fresh evidence required')
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(p,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
