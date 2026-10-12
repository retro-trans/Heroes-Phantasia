"""Read-only installed English dialogue audit; static warnings, not visual proof."""
from pathlib import Path
from unpack_cpk import inventory,crilayla
from rebuild_dialogue import parse
from dialogue_tokens import tokenize_bytes
from prepare_bubble_reflow_040 import record
from executable_text_patch import Elf
import struct,json
import prepare_bubble_reflow_040 as rf
from bubble_metrics import load_templates
cache=load_templates();rf.load_templates=lambda:cache
base=Path('work/output/0.1.41-title-credit-vwf-4x-candidate/HP.CPK')
e=Elf(Path('work/output/0.1.32-world-map-assets/EBOOT.BIN').read_bytes());ws=struct.unpack_from('<131I',e.data,e.file_offset(0x2e4000))
_,rows=inventory(base);names=[];english=[];errors=[];total=0
with base.open('rb')as f:
 for r in rows:
  if not r['path'].startswith(('phase/bin/','fld/talk/','btl/res/','btl/skit/'))or not r['path'].endswith('.bin'):continue
  f.seek(r['offset']);raw=f.read(r['stored_size'])
  if r['compression']=='CRILAYLA':raw=crilayla(raw,r['extract_size'])
  overlay=Path('work/output/0.1.42-bubble-scene-assets')/r['path']
  if overlay.exists():raw=overlay.read_bytes()
  try:p=parse(r['path'],raw)
  except ValueError:continue
  total+=len(p['refs'])
  for n,(_,off)in enumerate(p['refs']):
   text=p['spans'][off][0]
   if b'\x0e'not in text:continue
   body=text.split(b'\x0e',1)[1]
   try:tokens=tokenize_bytes(body,True)
   except ValueError:continue
   if any(t.kind=='native'for t in tokens)or not any(t.kind=='latin'for t in tokens):continue
   item=dict(resource=r['path'],reference_index=n)
   if r['path'].startswith('phase/bin/'):
    try:item.update(record(r['path'],raw,n,ws))
    except (ValueError,IndexError,struct.error)as ex:item['geometry_error']=str(ex)
   english.append(item)

from english_bubble_layout_v10 import native_corners
from english_bubble_layout_v9 import descriptors as olddesc
import math,argparse
corners=native_corners();desc=olddesc()
def clip(lo,hi,p,v,a,b):
 if abs(v)<1e-5:return (lo,hi)if a<=p<=b else (2,1)
 ka,kb=sorted(((a-p)/v,(b-p)/v));return max(lo,ka),min(hi,kb)
def feasible(r,page,modern):
 s=r['shape'];family=(s-3)%10
 if s<3 or family>=8 or cache[s]['count']!=10:return None
 if any(t.kind not in ('latin','control')or t.kind=='control'and t.code not in (0x11,0x12,0x0e,5,0x16,0x17,0x1a)for t in tokenize_bytes(bytes.fromhex(page['body_hex']),True)):return None
 n=len(page['line_advances']);g=(s-3)//10;c=corners[g]
 if n>7:return False
 left=min(x for x,y in c);right=max(x for x,y in c)
 pad=max(right-x if i<4 else x-left for i,(x,y)in enumerate(c))+10
 half=max(page['line_advances'])/2+pad
 if half>230.5:return False
 top,bottom=struct.unpack_from('<bb',desc,s*4+1);height=36+(n-1)*22
 if n<3:height=max(height,(bottom-top)/2)
 x,y=r['position'];tip=cache[s]['outline'][family+1];px,py=x+tip[0],y+tip[1];vx,vy=r['native_reverse_ray']
 clearance=9.5 if modern else 4
 for reach,retry in ((12,1),(3,.25)):
  if abs(vy)<1e-5:continue
  k=max(retry,reach/abs(vy))
  lo,hi=clip(k,1024,py,vy,36 if vy>0 else 36+height,252-height if vy>0 else 252)
  li,ri=(7,0)if vy>0 else (4,3)
  lcut=c[li][0]-left+clearance;rcut=right-c[ri][0]+clearance
  lo,hi=clip(lo,hi,px,vx,9.5+lcut,470.5-rcut)
  if lo<=hi:return True
 if modern:
  topcut=max(c[1][1],c[6][1])-min(y for x,y in c)+9.5
  botcut=max(y for x,y in c)-min(c[2][1],c[5][1])+9.5
  height=max(height,topcut+botcut)
 else:topcut=botcut=20
 for k in (1,.5):
  lo,hi=clip(k,1024,px,vx,9.5 if vx>0 else 9.5+2*half,470.5-2*half if vx>0 else 470.5)
  lo,hi=clip(lo,hi,py,vy,37.5+topcut if modern else 56,250.5-botcut if modern else 232)
  if lo<=hi:return True
 return False
flags=[];counts=dict(english_indexed_references=len(english),phase_references=0,phase_pages=0,standard_pages=0,nonstandard_pages=0,unmodeled_controls_pages=0,ray_feasible_pages=0,potential_fallback_pages=0,new_potential_fallback_pages=0)
for r in english:
 if 'shape'not in r:continue
 counts['phase_references']+=1
 for page_index,page in enumerate(r['pages']):
  counts['phase_pages']+=1
  v=feasible(r,page,True)
  if v is None:
   if (r['shape']-3)%10>=8 or r['shape']<3 or cache[r['shape']]['count']!=10:counts['nonstandard_pages']+=1
   else:counts['unmodeled_controls_pages']+=1
   continue
  counts['standard_pages']+=1
  if v:counts['ray_feasible_pages']+=1
  else:
   counts['potential_fallback_pages']+=1
   previous=feasible(r,page,False)
   counts['new_potential_fallback_pages']+=bool(previous)
   flags.append(dict(resource=r['resource'],reference_index=r['reference_index'],page=page_index,shape=r['shape'],position=r['position'],line_advances=page['line_advances'],previous_static_ray_feasible=previous,geometry_warning='Original ray may not support this English width/height inside the viewport.'))
proof=dict(version='0.1.42',source_version='0.1.41 plus 0.1.42 scoped reflow',source_archive=str(base),total_indexed_references=total,counts=counts,resources_examined=len(set(r['resource']for r in english)),potential_fallbacks=flags,scope='Static English/control and settled phase geometry audit across installed indexed dialogue containers. Field/battle geometry, scale/rotation, interpolation, reveal ordering and natural rendering are not modeled. Warnings are not confirmed screenshot overflows.',full_game_visually_verified=False)
ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
print(json.dumps({k:v for k,v in proof.items()if k!='potential_fallbacks'},indent=2))
if a.write:
 dest=Path('work/ui/dialogue/0.1.42/corpus_audit.en.json')
 if dest.exists():raise ValueError('Fresh audit evidence required')
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(proof,indent=2)+'\n')
else:print('DRY RUN')
