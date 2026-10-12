"""Prepare readable compact battle-stat badges; default dry-run."""
import argparse,hashlib,json,math,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from unpack_cpk import inventory,crilayla
from inspect_font_assets import texture,unswizzle
from title_stamp import swizzle

VERSION='0.1.44'
BASE=Path('work/output/0.1.43-title-credit-vwf-4x-candidate/HP.CPK')
RESOURCE='btl/sys_all.bin'
BASE_RESOURCE_SHA='9a8abe108472aba62e9e52f7e0866b86c72ad346e7567e1297f58b411a2e1dad'
FONT=Path('work/source/ppsspp/assets/Roboto_Condensed-Bold.ttf')
QUEUE=Path('work/translation/en/bitmap_battle_0001.json')
UI=Path('work/ui/battle/0.1.44')
OUT=Path('work/output/0.1.44-battle-badge-assets')
TARGETS=[('Attack','ATK'),('Defense','DEF'),('Charm','CHA'),('Teamwork','TEAM'),
         ('Power','PWR'),('Accuracy','ACC'),('Hits','HITS'),('Critical','CRIT')]

def digest(b):return hashlib.sha256(b).hexdigest()

def extract(path,row):
    with path.open('rb')as f:f.seek(row['offset']);b=f.read(row['stored_size'])
    return crilayla(b,row['extract_size'])if row['compression']=='CRILAYLA'else b

def prepare():
    _,rows=inventory(BASE);data=extract(BASE,next(r for r in rows if r['path']==RESOURCE))
    if digest(data)!=BASE_RESOURCE_SHA:raise ValueError('Reviewed English battle atlas changed')
    queue=json.loads(QUEUE.read_text(encoding='utf-8'))['rows']
    oldreport=json.loads(Path('work/ui/battle/combined_bitmap_proposal_v2/proposal.en.json').read_text(encoding='utf-8'))
    offsets=struct.unpack_from('<80I',data);t=texture(data,offsets[3],offsets[4])
    if(t['offset'],t['width'],t['height'])!=(0x28d0,256,352):raise ValueError('Atlas geometry differs')
    palette=[tuple(t['palette'][i:i+4])for i in range(0,1024,4)]
    white=next(i for i,c in enumerate(palette)if c==(255,255,255,255))
    transparent=next(i for i,c in enumerate(palette)if c[3]==0)
    old=unswizzle(t['pixels'],256,352);new=bytearray(old);allowed=set();entries=[]
    for index,(semantic,display)in enumerate(TARGETS):
        row=queue[index];x,y,w,h=row['proposed_crop_rect']
        if row['target']!=semantic or (x,y,w,h)!=(32*index,34,32,14):raise ValueError('Stat label ownership differs')
        for size in range(16,10,-1):
            font=ImageFont.truetype(str(FONT),size*4);bb=font.getbbox(display)
            mw,mh=math.ceil((bb[2]-bb[0])/4),math.ceil((bb[3]-bb[1])/4)
            if mw<=28 and mh<=12:break
        else:raise ValueError('Readable full abbreviation does not fit')
        mask4=Image.new('L',(mw*4,mh*4));ImageDraw.Draw(mask4).text((-bb[0],-bb[1]),display,font=font,fill=255)
        mask=mask4.resize((mw,mh),Image.Resampling.LANCZOS).point(lambda a:255 if a>=112 else 0)
        tx,ty=x+(w-mw)//2,y+(h-mh)//2
        for yy in range(y,y+h):
            for xx in range(x,x+w):new[yy*256+xx]=transparent;allowed.add(yy*256+xx)
        for yy in range(mh):
            for xx in range(mw):
                if mask.getpixel((xx,yy)):new[(ty+yy)*256+tx+xx]=white
        ink=mask.getbbox()
        if ink is None:raise ValueError('Empty abbreviation')
        entries.append(dict(id=row['id'],target=semantic,displayed_text=display,displayed_abbreviation=display,
            texture_rect=[x,y,w,h],text_box=[tx,ty,mw,mh],ink_height=ink[3]-ink[1],font_native_pixels=size,
            previous_font_native_pixels=oldreport['whole_labels'][index]['font_px'],
            previous_ink_height=oldreport['whole_labels'][index]['text_box'][3],raster_scale=4,
            palette_alpha_levels=[0,255],minimum_margin_pixels=1,complete_semantic_label_preserved=True))
    if any(a!=b for i,(a,b)in enumerate(zip(old,new))if i not in allowed):raise ValueError('Unselected atlas pixels changed')
    packed=swizzle(new,256,352)
    if unswizzle(packed,256,352)!=new:raise ValueError('Swizzle roundtrip failed')
    p=t['pixel_offset'];result=data[:p]+packed+data[p+len(packed):]
    if result[:p]!=data[:p]or result[p+len(packed):]!=data[p+len(packed):]or len(result)!=len(data):raise ValueError('Nonpixel bytes changed')
    original=Image.frombytes('RGBA',(256,352),b''.join(bytes(palette[i])for i in old))
    proposed=Image.frombytes('RGBA',(256,352),b''.join(bytes(palette[i])for i in new))
    report=dict(schema_version=1,version=VERSION,resource=RESOURCE,base_version='0.1.43',base_resource_sha256=BASE_RESOURCE_SHA,
        candidate_sha256=digest(result),bytes=len(result),texture_offset=t['offset'],pixel_offset=p,pixel_bytes=len(packed),
        dimensions=[256,352],font=str(FONT),font_sha256=digest(FONT.read_bytes()),entries=entries,
        unselected_atlas_pixels_exact=True,all_other_texture_allocations_exact=True,all_headers_palettes_nonpixel_bytes_exact=True,
        native_UV_dimensions_and_arrow_graphics_unchanged=True,swizzle_roundtrip=True,native_battle_display_verified=False,
        scope='Eight shared 32x14 battle-stat labels; full semantic terms remain in translation data. Uppercase abbreviations rendered bold, crisp and opaque inside original rectangles.')
    return result,report,original,proposed

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-review',action='store_true');p.add_argument('--write-asset',action='store_true')
    p.add_argument('--expected-candidate-sha256');a=p.parse_args()
    candidate,r,old,new=prepare();print(json.dumps(r,indent=2))
    if not(a.write_review or a.write_asset):print('DRY RUN: no asset or review writes.');return
    if a.write_review==a.write_asset or a.expected_candidate_sha256!=r['candidate_sha256']:raise ValueError('One guarded write action required')
    if a.write_review:
        if UI.exists():raise ValueError('Fresh review directory required')
        UI.mkdir(parents=True);old.save(UI/'atlas_before.png');new.save(UI/'atlas_after.png')
        sheet=Image.new('RGB',(640,110),'#10182e');d=ImageDraw.Draw(sheet)
        for n,im in enumerate([old,new]):
            d.text((8,n*54+2),'Previous tiny labels'if n==0 else'New bold abbreviations (asset preview)',fill='white')
            strip=im.crop((0,34,256,48)).resize((512,28),Image.Resampling.NEAREST)
            sheet.paste(strip,(8,n*54+18),strip.getchannel('A'))
        sheet.save(UI/'comparison.png')
        defense=Image.new('RGB',(192,84),'#10182e');badge=new.crop((32,34,64,48)).resize((192,84),Image.Resampling.NEAREST)
        defense.paste(badge,(0,0),badge.getchannel('A'));defense.save(UI/'defense_asset_enlarged.png')
        (UI/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    else:
        if OUT.exists():raise ValueError('Fresh asset directory required')
        OUT.mkdir(parents=True);dest=OUT/'sys_all.bin';dest.write_bytes(candidate)
        if digest(dest.read_bytes())!=r['candidate_sha256']:raise ValueError('Asset readback differs')
        (OUT/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
