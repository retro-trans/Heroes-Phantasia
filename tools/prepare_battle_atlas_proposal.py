"""Pure combined battle bitmap proposal; --write saves review images/JSON only."""
import argparse, hashlib, json, math, struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from inspect_font_assets import texture, unswizzle
from prepare_title_logo_proposal import FONT, swizzle
from prepare_battle_fragment_proposal import prepare as fragments

QUEUE = Path('work/translation/en/bitmap_battle_0001.json')
SOURCE = Path('work/source/cpk/btl/sys_all.bin')
SHA = '5eb0b94feb90861f921cc84de6b8421b44c1ffc1f649eaaf042e5b4bd5c197a8'

def digest(data): return hashlib.sha256(data).hexdigest()

def prepare():
    data = SOURCE.read_bytes(); assert digest(data) == SHA
    queue_raw = QUEUE.read_bytes(); queue = json.loads(queue_raw)
    assert len(queue['rows']) == 20
    combined, fragment_report, _, _, models = fragments()
    reader_path=Path('work/ui/battle/fragment_native_reader.en.json')
    reader_raw=reader_path.read_bytes();reader=json.loads(reader_raw)
    assert reader['source_resource_sha256']==SHA
    result = bytearray(combined)
    offsets = struct.unpack_from('<80I', data)
    t = texture(data, offsets[3], offsets[4]); w, h = t['width'], t['height']
    assert (t['offset'], w, h) == (0x28D0, 256, 352)
    palette = [tuple(t['palette'][i*4:i*4+4]) for i in range(256)]
    linear = unswizzle(t['pixels'], w, h); pixels = bytearray(linear)
    original = Image.frombytes('RGBA', (w,h), b''.join(bytes(palette[k]) for k in linear))
    allowed = set(); entries = []; cache = {}; overlaps = []
    for row in queue['rows']:
        target = row['target']; assert target and target.isascii()
        displayed={'Enemy Side':'Enemy','Ally Side':'Ally'}.get(target,target)
        x,y,cw,ch = row['proposed_crop_rect']; assert 0<=x<x+cw<=w and 0<=y<y+ch<=h
        if row['id'].endswith('_03'): assert target == 'Teamwork'
        box = (x,y,x+cw,y+ch)
        region = {(xx,yy) for yy in range(y,y+ch) for xx in range(x,x+cw)}
        overlap = region & allowed
        if overlap: overlaps.append(dict(id=row['id'],pixels=len(overlap),note='Reviewed crop padding overlaps; English foreground must remain outside previous crop and text extents.'))
        allowed |= region
        for size in range(12,3,-1):
            font = ImageFont.truetype(str(FONT), size*4); bb = font.getbbox(displayed)
            mw,mh = math.ceil((bb[2]-bb[0])/4),math.ceil((bb[3]-bb[1])/4)
            if mw <= cw-6 and mh <= ch-2: break
        else: raise ValueError('Cannot fit reviewed label: '+row['id'])
        if displayed != target: assert size >= 7
        mask = Image.new('L',(mw*4,mh*4)); ImageDraw.Draw(mask).text((-bb[0],-bb[1]),displayed,font=font,fill=255)
        mask = mask.resize((mw,mh),Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA',(cw,ch)); tx,ty=(cw-mw)//2,(ch-mh)//2
        foreground={(xx,yy) for yy in range(y+ty,y+ty+mh) for xx in range(x+tx,x+tx+mw)}
        assert not foreground & overlap
        for previous in entries:
            bx,by,bw,bh=previous['text_box']
            assert not region & {(xx,yy) for yy in range(by,by+bh) for xx in range(bx,bx+bw)}
        canvas.paste((255,255,255,255),(tx,ty,tx+mw,ty+mh),mask)
        for yy in range(ch):
            for xx in range(cw):
                color=canvas.getpixel((xx,yy))
                index=cache.setdefault(color,min(range(256),key=lambda i:sum((a-b)**2 for a,b in zip(color,palette[i]))))
                pixels[(y+yy)*w+x+xx]=index
        entries.append(dict(id=row['id'],target=target,displayed_text=displayed,
            displayed_abbreviation=displayed if displayed!=target else None,
            reviewed_pixel_box=list(box),font_px=size,
            text_box=[x+tx,y+ty,mw,mh],native_uv_verified=False,
            source_region_sha256=digest(original.crop(box).tobytes()),
            notes='Original reviewed crop replaced by transparent background and palette-quantized English; this crop is not yet a proven native UV/destination contract.'))
    assert all(a==b for p,(a,b) in enumerate(zip(linear,pixels)) if (p%w,p//w) not in allowed)
    encoded=swizzle(pixels,w,h); assert unswizzle(encoded,w,h)==pixels
    result[t['pixel_offset']:t['pixel_offset']+len(encoded)]=encoded
    proposed=Image.frombytes('RGBA',(w,h),b''.join(bytes(palette[k]) for k in pixels))
    # Only the two original pixel allocations may change, never their metadata/palettes.
    second=texture(data,offsets[72],offsets[73]); masked=bytearray(result)
    for tex in (t,second):
        start=tex['pixel_offset']; end=start+len(tex['pixels']); masked[start:end]=data[start:end]
    assert masked==data
    report=dict(schema_version=1,status='combined_battle_bitmap_pure_candidate_runtime_unverified',
        source=SOURCE.as_posix(),source_sha256=SHA,queue_sha256=digest(queue_raw),
        proposed_resource_sha256=digest(result),resource_bytes=len(result),
        whole_labels=entries,whole_label_count=20,fragment_label_count=3,crop_padding_overlaps=overlaps,
        fragment_proposal=fragment_report,texture_headers=[3,72],
        fragment_native_reader_proof=dict(path=reader_path.as_posix(),sha256=digest(reader_raw),scope='Native animation selectors, ascending part order, flags0/no flip, unit scale and zero rotation. Global playback remains unverified.'),
        main_texture=dict(offset=t['offset'],dimensions=[w,h],palette_sha256=digest(t['palette']),
            original_pixels_sha256=digest(t['pixels']),proposed_pixels_sha256=digest(encoded)),
        unselected_main_pixels_exact=True,all_nonselected_texture_allocations_exact=True,
        all_nonpixel_bytes_exact=True,assets_written=False,runtime_verified=False,
        limitations=['Main20 rectangles are human-reviewed pixel extents; actual native UVs, filters and destination widths remain unproved.',
            'Small native slots require font sizes4..12; readability needs native screen review.',
            'Fragment reader/order/flip geometry is separately proven; actual global placement/animation playback still needs runtime QA.'])
    return bytes(result),report,original,proposed,models

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--output',type=Path,default=Path('work/ui/battle/combined_bitmap_proposal'));a=p.parse_args()
    _,r,orig,new,models=prepare();print(json.dumps(r,indent=2))
    if a.write:
        dest=a.output;assert not dest.exists();dest.mkdir(parents=True)
        orig.save(dest/'main_original.png');new.save(dest/'main_proposed.png')
        comparison=Image.new('RGBA',(orig.width*2,orig.height),(35,35,35,255));comparison.alpha_composite(orig,(0,0));comparison.alpha_composite(new,(orig.width,0));comparison.save(dest/'main_comparison.png')
        for gid,im in models:im.save(dest/f'group{gid}_english_model.png')
        (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
