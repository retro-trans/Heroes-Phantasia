"""English-only source corner and reported gratitude-shot evidence."""
import struct,json
from pathlib import Path
from prepare_bubble_scenes_036 import read,ORIGINAL,sha
from rebuild_dialogue import parse
from english_bubble_layout_v6 import native_corners
from executable_text_patch import Elf
from bubble_metrics import load_templates

BASE=Path('work/output/0.1.37-title-credit-vwf-4x-candidate/HP.CPK')
NAMES=['phase/bin/p101050.bin','phase/bin/p101051.bin']

def build():
    assets=read(BASE,NAMES);source=read(ORIGINAL,NAMES);records=[]
    elf=Elf(Path('work/output/0.1.32-world-map-assets/EBOOT.BIN').read_bytes())
    widths=struct.unpack_from('<131I',elf.data,elf.file_offset(0x2e4000));templates=load_templates()
    for name,raw in assets.items():
        p=parse(name,raw);op=parse(name,source[name]);b=p['head'][0];h=struct.unpack_from('<16I',raw,b)
        if raw[b:p['start']]!=source[name][op['head'][0]:op['start']]:raise ValueError('Original tracks differ')
        index=3;key,off=p['refs'][index];text=p['spans'][off][0]
        if b'busy schedule'not in text:raise ValueError('Reported English shot differs')
        first=0
        for group,(_,count,_)in enumerate(p['desc']):
            if first<=index<first+count:break
            first+=count
        _,lo,_,_=struct.unpack_from('<4I',raw,b+h[12]+group*16)
        layer=struct.unpack_from('<21I',raw,b+h[14]+lo+key*84);ch=b+h[15]+layer[0]
        shape=struct.unpack_from('<fHH',raw,ch+layer[10]+(layer[9]-1)*8)[1]
        pos=struct.unpack_from('<4fI',raw,ch+layer[14]+(layer[13]-1)*20)[1:3]
        body=text.split(b'\x0e',1)[1];linewidths=[sum(widths[c]for c in line)for line in body.split(b'\x12',1)[0].split(b'\x11')]
        tip=templates[shape]['outline'][(shape-3)%10+1]
        records.append(dict(resource=name,reference_index=index,shape=shape,position=list(pos),body_hex=body.hex(),
            visible_lines=len(linewidths),halfwidth=max(linewidths)/2,native_tail_endpoint=[pos[0]+tip[0],pos[1]+tip[1]],
            original_tracks_exact=True,resource_sha256=sha(raw)))
    corners=native_corners()
    for points in corners:
        cross=[(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])for a,b,c in zip(points,points[1:]+points[:1],points[2:]+points[:2])]
        if min(cross)<=0:raise ValueError('Native common body is not convex')
    reported=corners[(records[0]['shape']-3)//10]
    if reported[1][0]==reported[2][0]or reported[5][0]==reported[6][0]:raise ValueError('Reported native side slope was lost')
    return dict(version='0.1.38',records=records,native_corner_families=corners,all_source_bodies_convex=True,
        reported_long_sides_sloped=True,source_corner_coordinates=True,exact_socket_specific_miters=False)

if __name__=='__main__':print(json.dumps(build(),indent=2))
