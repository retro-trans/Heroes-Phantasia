"""Inspect native texture headers; writing decoded diagnostic PNGs is opt-in."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def texture(data, offset, end=None):
    end = len(data) if end is None else end
    if offset + 128 > end:
        raise ValueError('Short native texture')
    h = struct.unpack_from('<16I', data, offset)
    width, height = h[1], h[4]
    palette, pixels, size = h[7], h[10], h[13]
    if not (width > 0 and height > 0 and palette == 128 and pixels == 1152):
        raise ValueError('Unknown native texture layout')
    if size != pixels + width * height or offset + size > end:
        raise ValueError('Native texture size disagrees with dimensions')
    return dict(offset=offset, width=width, height=height, palette_offset=offset + palette,
                pixel_offset=offset + pixels, byte_size=size,
                palette=data[offset + palette:offset + pixels],
                pixels=data[offset + pixels:offset + size])


def unswizzle(pixels, width, height):
    if width % 16 or height % 8:
        raise ValueError('Swizzle requires 16-byte by 8-row blocks')
    out = bytearray(len(pixels))
    source = 0
    for block_y in range(0, height, 8):
        for block_x in range(0, width, 16):
            for row in range(8):
                dest = (block_y + row) * width + block_x
                out[dest:dest + 16] = pixels[source:source + 16]
                source += 16
    return bytes(out)


def bounds(pixels, width, height):
    occupied = [(i % width,i // width) for i,value in enumerate(pixels) if value]
    if not occupied:
        return None
    xs,ys=zip(*occupied)
    return [min(xs),min(ys),max(xs)+1,max(ys)+1]


def audit():
    root=Path('work/source/cpk')
    assets=[]
    previews=[]
    for name,start,end,cell,count in [
            ('btl/sys_tbl.bin',0x1380,0x7000,12,140),
            ('phase/bin/p000000.bin',0xd00,0xd180,None,None)]:
        data=(root/name).read_bytes()
        info=texture(data,start,end)
        linear=unswizzle(info['pixels'],info['width'],info['height'])
        meta={k:v for k,v in info.items() if k not in ('palette','pixels')}
        meta.update(file=name,format='CI8_RGBA8888_16byte_by_8row_swizzle',
                    sha256=hashlib.sha256(data).hexdigest())
        if cell:
            columns=info['width']//cell
            metrics=[]
            for glyph in range(count):
                x,y=(glyph%columns)*cell,(glyph//columns)*cell
                alpha=bytes(info['palette'][linear[(y+dy)*info['width']+x+dx]*4+3]
                            for dy in range(cell) for dx in range(cell))
                metrics.append(dict(glyph_id=glyph,x=x,y=y,ink_bounds=bounds(alpha,cell,cell)))
            meta.update(cell_width=cell,cell_height=cell,columns=columns,
                        glyph_slots=count,glyph_metrics=metrics,
                        advance_width='unknown; ink bounds are not runtime advances')
        assets.append(meta)
        previews.append((Path(name).stem,info,linear))
    packed=[('gallery','menu/Gallery/prof/GcHelp01001.bin',32,40352,40576),
            ('field','fld/talk/f101010.bin',4160,28352,28448),
            ('resident_first','resident/ALLResidentNML.bin',0x658b0,0x7ccb0,0x7ce80),
            ('resident_second','resident/ALLResidentNML.bin',0x7ce80,0xbfd80,0xc0310)]
    packed_previews=[]
    for label,name,start,font_end,charset_end in packed:
        data=(root/name).read_bytes()
        raw=data[start:font_end]
        if len(raw)%384:
            raise ValueError('Packed font is not a multiple of 384 bytes')
        charset=data[font_end:charset_end].rstrip(b'\0').decode('cp932')
        expanded=bytes(value for byte in raw for value in ((byte&15)*17,(byte>>4)*17))
        slots=len(raw)//384
        charset_base=17 if label=='resident_first' else 0
        if len(charset)+charset_base>slots:
            raise ValueError('Charset exceeds glyph slots')
        metrics=[]
        for glyph in range(slots):
            ink=bounds(expanded[glyph*768:(glyph+1)*768],32,24)
            char_index=glyph-charset_base
            metrics.append(dict(slot=glyph,character=charset[char_index] if 0<=char_index<len(charset) else None,
                                ink_bounds=ink))
        assets.append(dict(file=name,label=label,sha256=hashlib.sha256(data).hexdigest(),
                      offset=start,font_end=font_end,charset_end=charset_end,
                      format='packed_alpha4_low_nibble_first_32x24',
                      cell_width=32,cell_height=24,bytes_per_slot=384,glyph_slots=slots,
                      charset_characters=len(charset),charset_base_slot=charset_base,glyph_metrics=metrics,
                      prefix_symbol_slots=charset_base,
                      nonblank_tail_slots=sum(m['ink_bounds'] is not None for m in metrics[len(charset)+charset_base:]),
                      advance_width='unknown; ink bounds are not runtime advances',
                      mapping_status='charset order visually reviewed; resident_first has 17 leading symbols'))
        packed_previews.append((label,expanded,slots))
    return assets,previews,packed_previews


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    assets,previews,packed=audit()
    print(json.dumps([{k:v for k,v in a.items() if k!='glyph_metrics'} for a in assets],indent=2))
    print('Battle glyph metric sample:',json.dumps(assets[0]['glyph_metrics'][:8]))
    if not args.write:
        print('DRY RUN: would write atlas images and measured ink bounds; no files changed.')
        return
    from PIL import Image,ImageDraw
    out=Path('work/source/font_audit');out.mkdir(parents=True,exist_ok=True)
    (out/'native_font_assets.json').write_text(json.dumps(dict(assets=assets),ensure_ascii=False,indent=2),encoding='utf-8')
    for label,info,linear in previews:
        rgba=b''.join(info['palette'][i*4:i*4+4] for i in linear)
        im=Image.frombytes('RGBA',(info['width'],info['height']),rgba)
        bg=Image.new('RGBA',im.size,(30,30,30,255));bg.alpha_composite(im)
        bg.convert('RGB').resize((im.width*3,im.height*3)).save(out/(label+'_swizzled.png'))
        if label=='sys_tbl':
            grid=Image.new('RGB',(21*48,7*64),(30,30,30));draw=ImageDraw.Draw(grid)
            for glyph in range(140):
                x,y=(glyph%21)*12,(glyph//21)*12
                cell=bg.crop((x,y,x+12,y+12)).convert('RGB').resize((48,48))
                dest=((glyph%21)*48,(glyph//21)*64)
                grid.paste(cell,dest);draw.text((dest[0],dest[1]+48),str(glyph),fill='white')
            grid.save(out/'sys_tbl_numbered.png')
    for label,expanded,slots in packed:
        im=Image.new('L',(32*16,24*((slots+15)//16)))
        for index in range(slots):
            cell=Image.frombytes('L',(32,24),expanded[index*768:(index+1)*768])
            im.paste(cell,((index%16)*32,(index//16)*24))
        im.resize((im.width*2,im.height*2)).save(out/(label+'_packed_32x24.png'))
    print('Wrote verified format previews and ink bounds to',out)


if __name__=='__main__':main()
