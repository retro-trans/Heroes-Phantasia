"""Pure PSP PNG lettering previews; --write creates review images, never source assets."""
import argparse,hashlib,json,math,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
FONT=Path('work/source/ppsspp/assets/Roboto_Condensed-Regular.ttf')
CASES=(('PSP_GAME_PIC0.PNG','2a60ebcaa673e4a4231732477d5cefce17015c78eee054317a8e6b90c2523303',[(114,95,200,105,'HEROES PHANTASIA',8)]),('PSP_GAME_ICON0.PNG','d237f8b332740f281961acae98766f73b5cad4e5d0ee88fa9cd2fc2cfb9964d4',[(55,44,95,50,'HEROES PHANTASIA',4)]),('PSP_GAME_INSDIR_ICON0.PNG','a97e043a352e5e623ccf83196cd6f9a53e6a88d20ab890621b7428131257143c',[(55,37,95,44,'HEROES PHANTASIA',4),(12,64,134,80,'INSTALL DATA',12)]))
def prepare():
 entries=[];images=[]
 for name,sha,regions in CASES:
  path=Path('work/source/media_audit')/name;d=path.read_bytes();assert hashlib.sha256(d).hexdigest()==sha;native=Image.open(path);mode=native.mode;im=native.convert('RGBA');out=im.copy();w,h=im.size;fields=struct.unpack_from('>IIBBBBB',d,16);records=[]
  for x0,y0,x1,y1,text,size in regions:
   if text=='INSTALL DATA':
    # Review-only interpolation of clean adjacent rows, not a proven original background.
    for x in range(x0,x1):
     top=im.getpixel((x,y0-1));bottom=im.getpixel((x,y1-1))
     for y in range(y0,y1):
      ratio=(y-y0+1)/(y1-y0);out.putpixel((x,y),tuple(round(a+(b-a)*ratio) for a,b in zip(top,bottom)))
   else:out.paste((33,29,27,255),(x0,y0,x1,y1))
   font=ImageFont.truetype(str(FONT),size*4);bb=font.getbbox(text);mw=math.ceil((bb[2]-bb[0])/4);mh=math.ceil((bb[3]-bb[1])/4);mask=Image.new('L',(mw*4,mh*4));ImageDraw.Draw(mask).text((-bb[0],-bb[1]),text,font=font,fill=255);mask=mask.resize((mw,mh),Image.Resampling.LANCZOS);assert mw<=x1-x0-2 and mh<=y1-y0-2;x=x0+(x1-x0-mw)//2;y=y0+(y1-y0-mh)//2
   if text=='INSTALL DATA':out.paste((54,24,54,255),(x+1,y+1,x+1+mw,y+1+mh),mask)
   out.paste((245,241,232,255),(x,y,x+mw,y+mh),mask);records.append(dict(source_region=[x0,y0,x1,y1],target=text,text_box=[x,y,mw,mh],font_native_px=size,background_policy='review_only_adjacent_row_interpolation' if text=='INSTALL DATA' else 'bounded_dark_cover_plate'))
  outside=all(im.getpixel((x,y))==out.getpixel((x,y)) for y in range(h) for x in range(w) if not any(x0<=x<x1 and y0<=y<y1 for x0,y0,x1,y1,_,_ in regions));assert outside
  if mode=='RGB':assert all(a==255 for a in out.getchannel('A').getdata())
  entries.append(dict(source_path=path.as_posix(),source_sha256=sha,dimensions=[w,h],native_mode=mode,ihdr_bit_depth=fields[2],ihdr_color_type=fields[3],native_palette=False,original_rgba_sha256=hashlib.sha256(im.tobytes()).hexdigest(),proposed_rgba_sha256=hashlib.sha256(out.tobytes()).hexdigest(),outside_regions_pixel_exact=outside,regions=records,encoded_png_prepared=False,notes='No PNG replacement container encoded. Future integration must preserve source IHDR mode and ancillary chunk semantics, verify palette is absent, and coordinate any PNG-tail memory ownership.'));images.append((name,im,out))
 return dict(schema_version=1,status='pure_native_pixel_proposal_root_review_pending',font=FONT.as_posix(),font_sha256=hashlib.sha256(FONT.read_bytes()).hexdigest(),entries=entries,unique_semantic_units=2,physical_label_occurrences=4,assets_written=False,runtime_verified=False),images
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args();r,images=prepare();print(json.dumps(r,indent=2))
 if a.write:
  dest=Path('work/ui/psp_bitmap_proposal');assert not dest.exists();dest.mkdir()
  for name,orig,out in images:
   orig.save(dest/(name+'_original.png'));out.save(dest/(name+'_proposed.png'));pair=Image.new('RGBA',(orig.width*2,orig.height));pair.paste(orig,(0,0));pair.paste(out,(orig.width,0));pair.save(dest/(name+'_comparison.png'))
  (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
