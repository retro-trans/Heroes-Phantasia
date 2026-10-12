"""Read original sprite group tables; write review composites only, never atlas bytes."""
import argparse,hashlib,json,struct
from pathlib import Path
from PIL import Image
from inspect_font_assets import texture,unswizzle
SOURCE=Path('work/source/cpk/btl/sys_all.bin');SHA='5eb0b94feb90861f921cc84de6b8421b44c1ffc1f649eaaf042e5b4bd5c197a8'
def prepare():
 d=SOURCE.read_bytes();assert hashlib.sha256(d).hexdigest()==SHA;offs=struct.unpack_from('<80I',d);rows=[];images=[]
 for container,atlas in ((71,72),(73,75),(74,75)):
  base=offs[container];h=struct.unpack_from('<16I',d,base);assert h[4]==128 and h[6]==h[4]+4*(h[3]+1) and h[8]==h[6]+56*h[5];table=struct.unpack_from('<'+str(h[3]+1)+'I',d,base+h[4]);assert table[0]==0 and table[-1]==h[5] and all(a<=b for a,b in zip(table,table[1:]));t=texture(d,offs[atlas],offs[atlas+1]);raw=unswizzle(t['pixels'],t['width'],t['height']);palette=t['palette'];im=Image.frombytes('RGBA',(t['width'],t['height']),b''.join(palette[k*4:k*4+4] for k in raw))
  groups=[]
  for group,(start,end) in enumerate(zip(table,table[1:])):
   records=[]
   for index in range(start,end):
    pos=base+h[6]+index*56;gid,flags=struct.unpack_from('<2H',d,pos);assert gid==group;uv=struct.unpack_from('<4h',d,pos+8);dest=struct.unpack_from('<2h',d,pos+16);pivot=struct.unpack_from('<2h',d,pos+20);norm=struct.unpack_from('<4f',d,pos+24);scale=struct.unpack_from('<2f',d,pos+40);angle=struct.unpack_from('<f',d,pos+48)[0];assert 0<=uv[0]<uv[2]<=t['width'] and 0<=uv[1]<uv[3]<=t['height'];assert flags in (0,3);expected=(uv[2],uv[3],uv[0],uv[1]) if flags==3 else uv;assert all(abs(v-e)<1e-6 for v,e in zip(norm,(expected[0]/t['width'],expected[1]/t['height'],expected[2]/t['width'],expected[3]/t['height'])))
    records.append(dict(index=index,file_offset=pos,group_id=gid,flags=flags,uv_corners=list(uv),position=list(dest),pivot=list(pivot),scale=list(scale),rotation_degrees=angle))
   modelable=bool(records) and all(x['flags']==0 and x['scale']==[1.,1.] and x['rotation_degrees']==0. for x in records)
   g=dict(group_id=group,record_range=[start,end],records=records,static_group_table_consistent=True,unit_scale_zero_rotation_model=modelable,native_group_selection_verified=False,runtime_verified=False)
   if modelable:
    rects=[(x['position'][0]-x['pivot'][0],x['position'][1]-x['pivot'][1],x['uv_corners'][2]-x['uv_corners'][0],x['uv_corners'][3]-x['uv_corners'][1]) for x in records];x0=min(x for x,y,w,h in rects);y0=min(y for x,y,w,h in rects);x1=max(x+w for x,y,w,h in rects);y1=max(y+h for x,y,w,h in rects);canvas=Image.new('RGBA',(x1-x0,y1-y0))
    for rec,(x,y,rw,rh) in zip(records,rects):canvas.alpha_composite(im.crop(rec['uv_corners']),(x-x0,y-y0))
    g.update(modeled_destination_bounds=[x0,y0,x1,y1],modeled_rgba_sha256=hashlib.sha256(canvas.tobytes()).hexdigest());images.append((container,group,canvas))
   groups.append(g)
  rows.append(dict(container_header_index=container,atlas_header_index=atlas,container_offset=base,group_count=h[3],part_count=h[5],index_table_offset=base+h[4],part_table_offset=base+h[6],part_stride=56,group_index_table=list(table),atlas_dimensions=[t['width'],t['height']],atlas_palette_sha256=hashlib.sha256(palette).hexdigest(),atlas_pixel_sha256=hashlib.sha256(t['pixels']).hexdigest(),groups=groups))
 return dict(schema_version=1,status='static_group_model_not_runtime_animation_proof',source=SOURCE.as_posix(),source_sha256=SHA,containers=rows,japanese_heading_group_candidates=[dict(container=71,group=5,source='\u5931\u6557',target_proposed='Failed'),dict(container=71,group=6,source='\u901f\u653b\u614b\u52e2',target_proposed='First Strike Formation'),dict(container=71,group=8,source='\u4e0d\u610f\u8a0e\u3061',target_proposed='Ambush')],atlas75_visual_review='Full original128x128 atlas contains Latin RESULT, LVUP, GAMEOVER, digits, arrows and bars; no Japanese glyph observed. Earlier scope note suggesting Japanese victory lettering is superseded by this visual finding.',limitations=['Group LUT and low-halfword group IDs are exact structural evidence; actual native reader/group selector, flags and animated transforms need separate proof.','Composites use zero-rotation/unit-scale parts only, with native positions minus pivots; they are model illustrations, not ingame screenshots.','No target heading committed, texture bytes or animation IDs changed.'],assets_written=False),images
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args();r,images=prepare();print(json.dumps(dict(source_sha256=SHA,groups=[dict(container=x['container_header_index'],groups=x['group_count'],parts=x['part_count'],table=x['group_index_table']) for x in r['containers']],heading_candidates=r['japanese_heading_group_candidates'],assets_written=False),ensure_ascii=True,indent=2))
 if a.write:
  dest=Path('work/ui/battle/fragment_group_model');assert not dest.exists();dest.mkdir()
  for container,group,im in images:im.save(dest/f'container{container}_group{group}_model.png')
  (dest/'proof.en.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
