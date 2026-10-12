"""Pure title phonetic-line proposal. --write saves review PNG/JSON only, never assets."""
import argparse,hashlib,json,math,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from inspect_font_assets import texture,unswizzle
SOURCE=Path('work/source/cpk/menu/TitleMenu_Data.bin')
SOURCE_SHA='5bff5e0e0c105664281b39d2bc5ef2fe231bf6acbb748fbfffb96cfd14e083ce'
FONT=Path('work/source/ppsspp/assets/Roboto_Condensed-Regular.ttf')
def swizzle(linear,width,height):
 if len(linear)!=width*height or width%16 or height%8:raise ValueError('Invalid CI8 dimensions')
 return b''.join(linear[y*width+x:y*width+x+16] for by in range(0,height,8) for x in range(0,width,16) for y in range(by,by+8))
REGIONS=((1,(139,107,238,117),7),(3,(67,88,119,95),4))
def prepare():
 data=SOURCE.read_bytes();assert hashlib.sha256(data).hexdigest()==SOURCE_SHA;offsets=struct.unpack_from('<9I',data);result=bytearray(data);previews=[];entries=[]
 for section,box,size in REGIONS:
  t=texture(data,offsets[section],offsets[section+1]);w,h=t['width'],t['height'];raw=unswizzle(t['pixels'],w,h);assert swizzle(raw,w,h)==t['pixels'];pal=[tuple(t['palette'][i*4:i*4+4]) for i in range(256)];im=Image.frombytes('RGBA',(w,h),b''.join(bytes(pal[i]) for i in raw));text='HEROES PHANTASIA';font=ImageFont.truetype(str(FONT),size*4);bb=font.getbbox(text);mw=math.ceil((bb[2]-bb[0])/4);mh=math.ceil((bb[3]-bb[1])/4);mask=Image.new('L',(mw*4,mh*4));ImageDraw.Draw(mask).text((-bb[0],-bb[1]),text,font=font,fill=255);mask=mask.resize((mw,mh),Image.Resampling.LANCZOS);assert mw<=box[2]-box[0]-2 and mh<=box[3]-box[1]-2
  x=box[0]+((box[2]-box[0])-mw)//2;y=box[1]+((box[3]-box[1])-mh)//2;proposal=im.copy();proposal.paste((33,29,27,255),box);proposal.paste((245,241,232,255),(x,y,x+mw,y+mh),mask)
  pixels=bytearray(raw);cache={};rgba=proposal.tobytes();changes=[]
  for yy in range(box[1],box[3]):
   for xx in range(box[0],box[2]):
    pos=yy*w+xx;color=tuple(rgba[pos*4:pos*4+4]);idx=cache.setdefault(color,min(range(256),key=lambda i:sum((a-b)**2 for a,b in zip(color,pal[i]))));pixels[pos]=idx
    if idx!=raw[pos]:changes.append((xx,yy))
  assert all(old==new for pos,(old,new) in enumerate(zip(raw,pixels)) if not(box[0]<=pos%w<box[2] and box[1]<=pos//w<box[3]));encoded=swizzle(pixels,w,h);assert unswizzle(encoded,w,h)==pixels;result[t['pixel_offset']:t['pixel_offset']+len(encoded)]=encoded;preview=Image.frombytes('RGBA',(w,h),b''.join(bytes(pal[i]) for i in pixels));previews.append((section,im,preview));entries.append(dict(section_index=section,offset=t['offset'],dimensions=[w,h],palette_sha256=hashlib.sha256(t['palette']).hexdigest(),original_pixel_sha256=hashlib.sha256(t['pixels']).hexdigest(),original_rgba_sha256=hashlib.sha256(im.tobytes()).hexdigest(),proposed_rgba_sha256=hashlib.sha256(preview.tobytes()).hexdigest(),source_label='Phonetic Japanese game title',target=text,replacement_box=list(box),font_native_pixels=size,raster_scale=4,text_box=[x,y,mw,mh],changed_pixels=len(changes),all_outside_box_pixels_preserved=True,all_palette_bytes_preserved=True,swizzle_roundtrip=True,notes='Rectangle is a proposed cover plate around visually inspected phonetic lettering, not a proof of every pixel being a glyph. Tiny mini-logo legibility and native sprite UV ownership need review.'))
 affected=set()
 for section,box,size in REGIONS:
  t=texture(data,offsets[section],offsets[section+1]);affected.update(range(t['pixel_offset'],t['pixel_offset']+len(t['pixels'])))
 assert all(a==b for i,(a,b) in enumerate(zip(data,result)) if i not in affected)
 return bytes(result),dict(schema_version=1,status='pure_proposal_no_game_assets_written',resource=SOURCE.as_posix(),original_sha256=SOURCE_SHA,proposed_resource_sha256=hashlib.sha256(result).hexdigest(),source_font=FONT.as_posix(),source_font_sha256=hashlib.sha256(FONT.read_bytes()).hexdigest(),labels=entries,unique_source_text_units=1,physical_occurrences=2,all_headers_offsets_palettes_other_sections_preserved=True,title_stamp_code_unchanged=True,runtime_verified=False,uv_ownership_verified=False,game_assets_written=False),previews
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args();resource,r,ims=prepare();print(json.dumps(r,indent=2))
 if a.write:
  dest=Path('work/ui/title_logo_proposal');assert not dest.exists();dest.mkdir()
  for section,orig,proposed in ims:
   orig.save(dest/f'section{section}_original.png');proposed.save(dest/f'section{section}_proposed.png');pair=Image.new('RGBA',(orig.width*2,orig.height),(32,29,27,255));pair.paste(orig,(0,0));pair.paste(proposed,(orig.width,0));pair.save(dest/f'section{section}_comparison.png')
  (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
