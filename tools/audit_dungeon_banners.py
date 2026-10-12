"""Inspect native dungeon-name bitmap allocations; review PNGs are opt-in."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image, ImageDraw
from inspect_font_assets import texture, unswizzle


def digest(b):
    return hashlib.sha256(b).hexdigest()


def audit():
    rows, pictures = [], []
    for path in sorted(Path('work/source/cpk/fld/dngn').glob('*.bin')):
        data = path.read_bytes()
        offsets = struct.unpack_from('<4I', data)
        if offsets[0] == 32:
            rows.append(dict(resource=path.relative_to(Path('work/source/cpk')).as_posix(),
                             source_sha256=digest(data), bytes=len(data), offsets=list(offsets),
                             scope='Different 32-byte container; no banner decoded or counted.'))
            continue
        if offsets[0] != 64 or not offsets[0] < offsets[1] < offsets[2] < offsets[3] == len(data):
            raise ValueError('Unexpected dungeon container: ' + str(path))
        t = texture(data, offsets[2], offsets[3])
        if (t['width'], t['height']) != (256, 32):
            raise ValueError('Unexpected dungeon banner dimensions: ' + str(path))
        linear = unswizzle(t['pixels'], 256, 32)
        rgba = b''.join(t['palette'][i*4:i*4+4] for i in linear)
        im = Image.frombytes('RGBA', (256, 32), rgba)
        row = dict(resource=path.relative_to(Path('work/source/cpk')).as_posix(),
                   source_sha256=digest(data), bytes=len(data), offsets=list(offsets),
                   texture_offset=t['offset'], pixel_offset=t['pixel_offset'],
                   dimensions=[256, 32], format='CI8_RGBA8888_swizzled_16x8',
                   palette_sha256=digest(t['palette']), pixels_sha256=digest(t['pixels']),
                   rgba_sha256=digest(rgba), native_consumer_verified=False)
        rows.append(row)
        pictures.append((path.stem, im))
    return rows, pictures


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write-review', action='store_true')
    p.add_argument('--output', type=Path, default=Path('work/ui/map_banners/source_snapshot'))
    a = p.parse_args()
    rows, pictures = audit()
    print(json.dumps(rows, indent=2))
    if not a.write_review:
        return
    dest = a.output.resolve()
    if dest.exists() or not dest.is_relative_to(Path('work/ui').resolve()):
        raise ValueError('Fresh review directory inside work/ui required')
    dest.mkdir(parents=True)
    sheet = Image.new('RGB', (576, 56 * ((len(pictures)+1)//2)), '#d8d8d8')
    draw = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(pictures):
        im.save(dest/(name+'.png'))
        x, y = (i % 2)*288, (i//2)*56
        draw.text((x+4, y+2), name, fill='black')
        sheet.paste(im, (x+4, y+18), im)
    sheet.save(dest/'all_banners.png')
    (dest/'inventory.en.json').write_text(json.dumps(dict(rows=rows,
        scope='Resource bitmap observations; source wording requires human review.',
        assets_written=False), indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
