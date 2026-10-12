"""Improve the remaining shared battle bitmap labels; default dry-run."""
import argparse, json, math, struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from unpack_cpk import inventory
from inspect_font_assets import texture, unswizzle
from title_stamp import swizzle
from inspect_battle_fragment_groups import prepare as inspect_groups, SOURCE as NATIVE_SOURCE
from prepare_battle_badges_044 import digest, extract, FONT, RESOURCE, QUEUE

VERSION = '0.1.45'
BASE = Path('work/output/0.1.44-title-credit-vwf-4x-candidate/HP.CPK')
BASE_RESOURCE_SHA = '4c0a57060aad0fd9d6d3ab70d58ee011fc0b420acca89744110af40b32e37a59'
UI = Path('work/ui/battle/0.1.45')
OUT = Path('work/output/0.1.45-battle-label-assets')
DISPLAYS = ['OBS', 'Dodge', 'Turn', 'None', 'Overcharge', 'PP Cost',
            'Assist Effect', 'HP MOD', 'Max Chain', 'Foe', 'Ally', 'Field Effect']
HEADINGS = {5: ('Failed', ['FAILED']),
            6: ('First Strike Formation', ['FIRST STRIKE', 'FORMATION']),
            8: ('Ambush', ['AMBUSH'])}

def lettering(lines, width, height, maximum, shadow=False):
    """Fit complete lines with margins; render at 4x into opaque palette pixels."""
    for size in range(maximum, 7, -1):
        font = ImageFont.truetype(str(FONT), size * 4)
        boxes = [font.getbbox(s) for s in lines]
        dims = [(math.ceil((b[2]-b[0])/4), math.ceil((b[3]-b[1])/4)) for b in boxes]
        gap = 1 if len(lines)>1 else 0
        total = sum(h for w,h in dims) + gap*(len(lines)-1)
        if max(w for w,h in dims) <= width-4-int(shadow) and total <= height-2-int(shadow):
            break
    else:
        raise ValueError('Complete display text cannot fit with margins')
    canvas = Image.new('RGBA', (width,height)); textboxes=[]
    yy=(height-total-int(shadow))//2
    for line,bb,(mw,mh) in zip(lines,boxes,dims):
        mask=Image.new('L',(mw*4,mh*4))
        ImageDraw.Draw(mask).text((-bb[0],-bb[1]),line,font=font,fill=255)
        mask=mask.resize((mw,mh),Image.Resampling.LANCZOS).point(lambda a:255 if a>=112 else 0)
        xx=(width-mw-int(shadow))//2
        if shadow:canvas.paste((0,0,0,255),(xx+1,yy+1,xx+1+mw,yy+1+mh),mask)
        canvas.paste((255,255,255,255),(xx,yy,xx+mw,yy+mh),mask)
        assert mask.getbbox() is not None
        textboxes.append(dict(text=line,box=[xx,yy,mw,mh],ink_height=mask.getbbox()[3]-mask.getbbox()[1]))
        yy+=mh+gap
    return canvas, size, textboxes

def prepare():
    _, rows=inventory(BASE)
    data=extract(BASE,next(r for r in rows if r['path']==RESOURCE))
    if digest(data)!=BASE_RESOURCE_SHA:raise ValueError('Reviewed 0.1.44 battle resource changed')
    queue=json.loads(QUEUE.read_text(encoding='utf8'))['rows']
    previous=json.loads(Path('work/ui/battle/combined_bitmap_proposal_v2/proposal.en.json').read_text(encoding='utf8'))
    offsets=struct.unpack_from('<80I',data); result=bytearray(data); allocations=[];entries=[];previews=[]
    models,_=inspect_groups(); container=models['containers'][0]
    native_data=NATIVE_SOURCE.read_bytes()
    for group in container['groups']:
        for record in group['records']:
            at=record['file_offset']
            assert data[at:at+56]==native_data[at:at+56]
    for header in [3,72]:
        t=texture(data,offsets[header],offsets[header+1]);w,h=t['width'],t['height']
        palette=[tuple(t['palette'][i:i+4]) for i in range(0,1024,4)]
        transparent=next(i for i,c in enumerate(palette) if c[3]==0)
        indices={(255,255,255,255):palette.index((255,255,255,255))}
        if header==72:indices[(0,0,0,255)]=palette.index((0,0,0,255))
        raw=unswizzle(t['pixels'],w,h);pixels=bytearray(raw);allowed=set();canvases={}
        def image_from(p):return Image.frombytes('RGBA',(w,h),b''.join(bytes(palette[i]) for i in p))
        before=image_from(raw)
        def install(canvas,rect):
            x,y,cw,ch=rect
            assert canvas.size==(cw,ch)
            for py in range(ch):
                for px in range(cw):
                    pos=(y+py)*w+x+px;allowed.add(pos);c=canvas.getpixel((px,py))
                    pixels[pos]=indices[c] if c[3] else transparent
        if header==3:
            assert (w,h)==(256,352)
            for n,display in enumerate(DISPLAYS,8):
                row=queue[n];x,y,cw,ch=row['proposed_crop_rect'];owned=[x,y,cw,ch]
                # Historical crop boxes overlap transparent padding by 1-2 pixels.
                right=[r['proposed_crop_rect'][0] for r in queue[n+1:]
                       if r['proposed_crop_rect'][1]==y and x<r['proposed_crop_rect'][0]<x+cw]
                if right:owned[2]=min(right)-x
                canvas,size,boxes=lettering([display],owned[2],ch,18)
                install(canvas,owned)
                previews.append((row['target'],before.crop((x,y,x+owned[2],y+ch)),canvas))
                entries.append(dict(id=row['id'],target=row['target'],displayed_text=display,
                    original_crop_rect=row['proposed_crop_rect'],texture_rect=owned,font_native_pixels=size,
                    previous_font_native_pixels=previous['whole_labels'][n]['font_px'],text_boxes=boxes,
                    complete_semantic_label_preserved=True))
            for n in range(8):
                x,y,cw,ch=queue[n]['proposed_crop_rect']
                assert all(pixels[yy*w+xx]==raw[yy*w+xx] for yy in range(y,y+ch) for xx in range(x,x+cw))
        else:
            for gid,(target,lines) in HEADINGS.items():
                group=container['groups'][gid];assert group['unit_scale_zero_rotation_model']
                x0,y0,x1,y1=group['modeled_destination_bounds'];cw,ch=x1-x0,y1-y0
                canvas,size,boxes=lettering(lines,cw,ch,28,shadow=True);canvases[gid]=canvas
                oldmodel=Image.new('RGBA',(cw,ch))
                for rec in group['records']:
                    u0,v0,u1,v1=rec['uv_corners'];dx=rec['position'][0]-rec['pivot'][0]-x0;dy=rec['position'][1]-rec['pivot'][1]-y0
                    install(canvas.crop((dx,dy,dx+u1-u0,dy+v1-v0)),[u0,v0,u1-u0,v1-v0])
                    oldmodel.alpha_composite(before.crop(rec['uv_corners']),(dx,dy))
                previews.append((target,oldmodel,canvas))
                entries.append(dict(group_id=gid,target=target,displayed_text=' / '.join(lines),font_native_pixels=size,
                    text_boxes=boxes,source_destination_bounds=group['modeled_destination_bounds'],
                    part_indices=[r['index'] for r in group['records']],native_uv_corners=[r['uv_corners'] for r in group['records']],
                    partition_geometry_retained=True,complete_semantic_label_preserved=True))
            for g in container['groups']:
                if g['group_id'] in HEADINGS:continue
                for rec in g['records']:
                    u0,v0,u1,v1=rec['uv_corners']
                    assert all(yy*w+xx not in allowed for yy in range(v0,v1) for xx in range(u0,u1))
        assert all(a==b for i,(a,b) in enumerate(zip(raw,pixels)) if i not in allowed)
        after=image_from(pixels)
        if header==72:
            for gid,canvas in canvases.items():
                g=container['groups'][gid];x0,y0,x1,y1=g['modeled_destination_bounds'];assembled=Image.new('RGBA',canvas.size)
                for rec in g['records']:
                    assembled.alpha_composite(after.crop(rec['uv_corners']),(rec['position'][0]-rec['pivot'][0]-x0,rec['position'][1]-rec['pivot'][1]-y0))
                # Opaque lettering avoids doubled alpha at the native overlapping seams.
                assert assembled.tobytes()==canvas.tobytes()
        encoded=swizzle(pixels,w,h);assert unswizzle(encoded,w,h)==pixels
        p=t['pixel_offset'];result[p:p+len(encoded)]=encoded
        allocations.append(dict(header_index=header,pixel_offset=p,pixel_bytes=len(encoded),dimensions=[w,h],
            changed_pixels=sum(a!=b for a,b in zip(raw,pixels)),unselected_pixels_exact=True))
    alloc_ranges=[(r['pixel_offset'],r['pixel_offset']+r['pixel_bytes']) for r in allocations]
    assert len(result)==len(data)
    assert all(a==b for i,(a,b) in enumerate(zip(data,result)) if not any(start<=i<end for start,end in alloc_ranges))
    report=dict(schema_version=1,version=VERSION,resource=RESOURCE,base_version='0.1.44',base_resource_sha256=BASE_RESOURCE_SHA,
        candidate_sha256=digest(result),bytes=len(result),entries=entries,changed_labels=15,total_category_labels=23,
        previously_fixed_stat_badges_preserved=8,font=str(FONT),font_sha256=digest(FONT.read_bytes()),raster_scale=4,
        allocations=allocations,all_nonpixel_bytes_exact=True,all_other_atlas_pixels_exact=True,
        native_geometry_palette_and_arrows_preserved=True,fragment_models_roundtrip_exact=True,native_battle_display_verified=False)
    return bytes(result),report,previews

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-review',action='store_true');p.add_argument('--write-asset',action='store_true');p.add_argument('--expected-candidate-sha256');a=p.parse_args()
    candidate,r,previews=prepare();print(json.dumps(r,indent=2))
    if not(a.write_review or a.write_asset):print('DRY RUN: no writes.');return
    if a.write_review==a.write_asset or a.expected_candidate_sha256!=r['candidate_sha256']:raise ValueError('One guarded action required')
    dest=UI if a.write_review else OUT
    if dest.exists():raise ValueError('Fresh directory required')
    dest.mkdir(parents=True)
    if a.write_asset:(dest/'sys_all.bin').write_bytes(candidate)
    else:
        sheet=Image.new('RGB',(850,60+len(previews)*62),'#10182e');d=ImageDraw.Draw(sheet)
        d.text((10,10),'Battle label assets - 2x pixel preview (not gameplay)',fill='white')
        d.text((240,32),'Previous',fill='white');d.text((530,32),'Larger / bolder',fill='white')
        for n,(target,before,after) in enumerate(previews):
            yy=60+n*62;d.text((10,yy+8),target,fill='white')
            for xx,im in [(240,before),(530,after)]:
                im=im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST)
                sheet.paste(im,(xx,yy),im.getchannel('A'))
        sheet.save(dest/'comparison.png')
    (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
