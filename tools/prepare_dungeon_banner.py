"""Prepare one reviewed dungeon bitmap; default dry-run, fresh outputs only."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from PIL import Image, ImageDraw, ImageFont
from inspect_font_assets import texture, unswizzle
from title_stamp import swizzle

RESOURCE = 'fld/dngn/d06.bin'
SOURCE = Path('work/source/cpk') / RESOURCE
SOURCE_SHA = '0f95e4700307ea1c7ced52659e6092c7ffb63710c252849b50c5b46f0825efc0'
FONT = Path('work/source/ppsspp/assets/Roboto_Condensed-Italic.ttf')
TARGET = 'Forest of Encounters'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def prepare():
    data = SOURCE.read_bytes()
    if digest(data) != SOURCE_SHA:
        raise ValueError('Reviewed source resource changed')
    offsets = struct.unpack_from('<4I', data)
    if offsets != (64, 351008, 352576, 361920):
        raise ValueError('Dungeon section layout changed')
    t = texture(data, offsets[2], offsets[3])
    if (t['width'], t['height']) != (256, 32):
        raise ValueError('Reviewed texture dimensions changed')
    old = unswizzle(t['pixels'], 256, 32)
    if swizzle(old, 256, 32) != t['pixels']:
        raise ValueError('Source swizzle roundtrip failed')
    pal = [tuple(t['palette'][i:i+4]) for i in range(0, 1024, 4)]
    original = Image.frombytes('RGBA', (256, 32), b''.join(bytes(pal[i]) for i in old))
    if original.getbbox() != (1, 2, 100, 23):
        raise ValueError('Reviewed source lettering bounds changed')
    font = ImageFont.truetype(str(FONT), 26*4)
    bb = font.getbbox(TARGET)
    width, height = math.ceil((bb[2]-bb[0])/4), math.ceil((bb[3]-bb[1])/4)
    if width > 254 or height > 28:
        raise ValueError('Complete target does not fit native allocation')
    # Keep the original top/left alignment, tint and palette; no source UV edit.
    mask4 = Image.new('L', (256*4, 32*4))
    ImageDraw.Draw(mask4).text((4-bb[0], 8-bb[1]), TARGET, font=font, fill=255)
    mask = mask4.resize((256, 32), Image.Resampling.LANCZOS)
    nearest = [min(range(256), key=lambda i: sum((a-b)**2 for a,b in zip((255,255,255,alpha),pal[i])))
               for alpha in range(256)]
    linear = bytes(nearest[alpha] for alpha in mask.tobytes())
    packed = swizzle(linear, 256, 32)
    if unswizzle(packed, 256, 32) != linear:
        raise ValueError('Proposed swizzle roundtrip failed')
    result = data[:t['pixel_offset']] + packed + data[t['pixel_offset']+len(packed):]
    if len(result) != len(data) or result[:t['pixel_offset']] != data[:t['pixel_offset']]:
        raise ValueError('Nonpixel resource data changed')
    proposed = Image.frombytes('RGBA', (256, 32), b''.join(bytes(pal[i]) for i in linear))
    report = dict(schema_version=1, resource=RESOURCE, source_sha256=SOURCE_SHA,
        candidate_sha256=digest(result), bytes=len(result), offsets=list(offsets),
        texture_offset=t['offset'], pixel_offset=t['pixel_offset'], pixel_bytes=len(packed),
        dimensions=[256,32], format='CI8_RGBA8888_swizzled_16x8',
        palette_sha256=digest(t['palette']), original_pixel_sha256=digest(t['pixels']),
        candidate_pixel_sha256=digest(packed), source_ink_bounds=list(original.getbbox()),
        candidate_ink_bounds=list(proposed.getbbox()), target=TARGET,
        glossary='work/glossary/initial_terms.en.json', font=FONT.as_posix(),
        font_sha256=digest(FONT.read_bytes()), font_native_pixels=26, raster_scale=4,
        swizzle_roundtrip=True, all_nonpixel_bytes_preserved=True,
        allocation_dimensions_and_palette_preserved=True,
        runtime_verified=False, native_consumer_verified=False,
        scope='One dungeon bitmap replaces all its source lettering. Other dungeon banners are outside this patch.')
    return result, report, original, proposed


def comparison(original, proposed):
    sheet = Image.new('RGB', (528, 128), '#ececec')
    draw = ImageDraw.Draw(sheet)
    draw.text((8,8), 'Original asset (black tint preview)', fill='black')
    draw.text((272,8), 'English asset (black tint preview)', fill='black')
    for x, im in [(8, original), (272, proposed)]:
        sheet.paste(Image.new('RGB', im.size, 'black'), (x,32), im.getchannel('A'))
    draw.text((8,80), '256 x 32 native allocation; lettering rasterized at 4x.', fill='black')
    draw.text((8,101), 'Asset preview only; native gameplay display remains unverified.', fill='black')
    return sheet


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write-review', type=Path)
    p.add_argument('--write-asset', type=Path)
    p.add_argument('--expected-candidate-sha256')
    a = p.parse_args()
    data, report, original, proposed = prepare()
    if a.write_review and a.write_asset:
        raise ValueError('Review and asset writes are separate operations')
    print(json.dumps(report, indent=2))
    if a.write_review:
        dest = a.write_review.resolve()
        if dest.exists() or not dest.is_relative_to(Path('work/ui').resolve()):
            raise ValueError('Fresh review directory inside work/ui required')
        dest.mkdir(parents=True)
        original.save(dest/'original.png')
        proposed.save(dest/'english.png')
        comparison(original, proposed).save(dest/'comparison.png')
        (dest/'proposal.en.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    elif a.write_asset:
        dest = a.write_asset.resolve()
        metadata = Path(str(dest)+'.en.json')
        if report['candidate_sha256'] != a.expected_candidate_sha256:
            raise ValueError('Asset differs from reviewed candidate hash')
        if dest.exists() or metadata.exists() or not dest.is_relative_to(Path('work/output').resolve()):
            raise ValueError('Fresh asset inside work/output required')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        if digest(dest.read_bytes()) != report['candidate_sha256']:
            raise ValueError('Written asset readback differs')
        report['status'] = 'written_bitmap_candidate_runtime_unverified'
        metadata.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    else:
        print('DRY RUN: no asset or review files written.')


if __name__ == '__main__':
    main()
