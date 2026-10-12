"""Pure three-heading atlas proposal, preserving native sprite slots and all other bytes."""
import argparse,hashlib,json,math,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from inspect_battle_fragment_groups import prepare as inspect_groups,SOURCE,SHA
from inspect_font_assets import texture,unswizzle
from prepare_title_logo_proposal import swizzle,FONT
LABELS={5:('Failed',['FAILED'],20),6:('First Strike Formation',['FIRST STRIKE','FORMATION'],13),8:('Ambush',['AMBUSH'],20)}
def prepare():
 proof,_=inspect_groups();d=SOURCE.read_bytes();offs=struct.unpack_from('<80I',d);t=texture(d,offs[72],offs[73]);w,h=t['width'],t['height'];raw=unswizzle(t['pixels'],w,h);palette=[tuple(t['palette'][i*4:i*4+4]) for i in range(256)];original=Image.frombytes('RGBA',(w,h),b''.join(bytes(palette[k]) for k in raw));pixels=bytearray(raw);entries=[];images=[];rectangles=[];cache={};container=proof['containers'][0]
 for gid,(target,lines,size) in LABELS.items():
  group=container['groups'][gid];assert group['unit_scale_zero_rotation_model'];x0,y0,x1,y1=group['modeled_destination_bounds'];cw,ch=x1-x0,y1-y0;font=ImageFont.truetype(str(FONT),size*4);masks=[]
  for line in lines:
   box=font.getbbox(line);mw=math.ceil((box[2]-box[0])/4);mh=math.ceil((box[3]-box[1])/4);mask=Image.new('L',(mw*4,mh*4));ImageDraw.Draw(mask).text((-box[0],-box[1]),line,font=font,fill=255);mask=mask.resize((mw,mh),Image.Resampling.LANCZOS);assert mw<=cw-2;masks.append((line,mask))
  gap=2 if len(lines)>1 else 0;total=sum(m.height for _,m in masks)+gap*(len(masks)-1);assert total<=ch-2;canvas=Image.new('RGBA',(cw,ch));yy=(ch-total)//2;textboxes=[]
  for line,mask in masks:
   xx=(cw-mask.width)//2;canvas.paste((0,0,0,255),(xx+1,yy+1,xx+1+mask.width,yy+1+mask.height),mask);canvas.paste((255,255,255,255),(xx,yy,xx+mask.width,yy+mask.height),mask);textboxes.append(dict(text=line,box=[xx,yy,mask.width,mask.height]));yy+=mask.height+gap
  for rec in group['records']:
   u0,v0,u1,v1=rec['uv_corners'];dx=rec['position'][0]-rec['pivot'][0]-x0;dy=rec['position'][1]-rec['pivot'][1]-y0;crop=canvas.crop((dx,dy,dx+u1-u0,dy+v1-v0));assert crop.size==(u1-u0,v1-v0);rectangles.append(rec['uv_corners'])
   for py in range(v1-v0):
    for px in range(u1-u0):
     color=crop.getpixel((px,py));idx=cache.setdefault(color,min(range(256),key=lambda i:sum((a-b)**2 for a,b in zip(color,palette[i]))));pixels[(v0+py)*w+u0+px]=idx
  entries.append(dict(group_id=gid,target=target,rendered_lines=lines,native_font_px=size,source_destination_bounds=[x0,y0,x1,y1],text_boxes=textboxes,part_indices=[r['index'] for r in group['records']],native_uv_corners=[r['uv_corners'] for r in group['records']],source_partition_geometry_retained=True,notes='First Strike Formation wraps inside the existing24-pixel heading height; no control, UV, destination or animation metadata changes.'));images.append((gid,canvas))
 allowed={(x,y) for u0,v0,u1,v1 in rectangles for y in range(v0,v1) for x in range(u0,u1)};assert all(a==b for pos,(a,b) in enumerate(zip(raw,pixels)) if (pos%w,pos//w) not in allowed);unrelated=[]
 for group in container['groups']:
  if group['group_id'] in LABELS:continue
  for rec in group['records']:
   u0,v0,u1,v1=rec['uv_corners'];assert not any((x,y) in allowed for y in range(v0,v1) for x in range(u0,u1));unrelated.append(rec['index'])
 proposed=Image.frombytes('RGBA',(w,h),b''.join(bytes(palette[i]) for i in pixels));encoded=swizzle(pixels,w,h);assert unswizzle(encoded,w,h)==pixels;result=bytearray(d);result[t['pixel_offset']:t['pixel_offset']+len(encoded)]=encoded;assert result[:t['pixel_offset']]==d[:t['pixel_offset']] and result[t['pixel_offset']+len(encoded):]==d[t['pixel_offset']+len(encoded):]
 modeled=[]
 for gid,canvas in images:
  group=container['groups'][gid];x0,y0,x1,y1=group['modeled_destination_bounds'];output=Image.new('RGBA',(x1-x0,y1-y0))
  for rec in group['records']:output.alpha_composite(proposed.crop(rec['uv_corners']),(rec['position'][0]-rec['pivot'][0]-x0,rec['position'][1]-rec['pivot'][1]-y0))
  modeled.append((gid,output))
 report=dict(schema_version=1,status='native_slot_english_pixel_proposal_root_review_pending',source=SOURCE.as_posix(),source_sha256=SHA,texture_header_index=72,dimensions=[w,h],format='CI8_RGBA8888_swizzled_16byte_by_8rows',palette_sha256=hashlib.sha256(t['palette']).hexdigest(),proposed_resource_sha256=hashlib.sha256(result).hexdigest(),labels=entries,changed_pixels=sum(a!=b for a,b in zip(raw,pixels)),unrelated_part_indices_preserved=unrelated,all_other_groups_uv_disjoint_from_changed_regions=True,outside_slot_pixels_preserved=True,all_headers_palettes_sprite_records_other_bytes_preserved=True,font_sha256=hashlib.sha256(FONT.read_bytes()).hexdigest(),native_animation_reader_verified=False,runtime_verified=False,assets_written=False)
 return bytes(result),report,original,proposed,modeled
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args();_,r,orig,proposed,models=prepare();print(json.dumps(r,indent=2))
 if a.write:
  dest=Path('work/ui/battle/fragment_english_proposal');assert not dest.exists();dest.mkdir();orig.save(dest/'original.png');proposed.save(dest/'proposed.png');comparison=Image.new('RGBA',(orig.width*2,orig.height));comparison.paste(orig,(0,0));comparison.paste(proposed,(orig.width,0));comparison.save(dest/'comparison.png')
  for gid,im in models:im.save(dest/f'group{gid}_english_model.png')
  (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
