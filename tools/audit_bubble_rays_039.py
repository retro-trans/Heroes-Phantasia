"""Read original Japanese anchors and directions for the reported airport shot."""
import struct
from pathlib import Path
from prepare_bubble_scenes_036 import read,sha
from rebuild_dialogue import parse
from bubble_metrics import load_templates
BASE=Path('work/output/0.1.38-title-credit-vwf-4x-candidate/HP.CPK')
def build():
    records=[];names=['phase/bin/p101060.bin','phase/bin/p101061.bin'];original=read(Path('work/source/PSP_GAME/USRDIR/HP.CPK'),names)
    templates=load_templates()
    for name,raw in read(BASE,names).items():
        p=parse(name,raw);op=parse(name,original[name]);b=p['head'][0];h=struct.unpack_from('<16I',raw,b)
        if raw[b:p['start']]!=original[name][op['head'][0]:op['start']]:raise ValueError('Airport source tracks changed')
        key,off=p['refs'][0];text=p['spans'][off][0]
        if not text.startswith(b'\x1cCougar\x0eIf you like,'):raise ValueError('Reported airport record differs')
        _,lo,_,_=struct.unpack_from('<4I',raw,b+h[12]);l=struct.unpack_from('<21I',raw,b+h[14]+lo+84*key);ch=b+h[15]+l[0]
        shapes=[struct.unpack_from('<fHH',raw,ch+l[10]+i*8)for i in range(l[9])]
        positions=[struct.unpack_from('<4fI',raw,ch+l[14]+i*20)for i in range(l[13])]
        shape=shapes[-1][1];x,y=positions[-1][1:3];t=templates[shape];f=(shape-3)%10;pnt=t['outline'][f+1]
        v=[(t['outline'][f][axis]+t['outline'][f+2][axis])/2-pnt[axis]for axis in range(2)]
        records.append(dict(resource=name,reference_index=0,shape=shape,position=[x,y],original_tracks_exact=True,
            body_hex=text.split(b'\x0e',1)[1].hex(),native_tail_endpoint=[x+pnt[0],y+pnt[1]],native_reverse_ray=v,
            shape_keys=shapes,position_keys=positions,source_track_sha256=sha(raw[b:p['start']])))
    return records
