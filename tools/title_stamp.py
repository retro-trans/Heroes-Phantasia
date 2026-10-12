"""Generate the title version/credit from one build configuration.

Original title data stays read-only. Only covered background pixel indices
change; palette, texture headers, layout and other title textures are retained.
"""
import hashlib
import math
import pathlib
import re
import struct

from PIL import Image, ImageDraw, ImageFont
from inspect_font_assets import texture, unswizzle

SOURCE = pathlib.Path('work/source/cpk/menu/TitleMenu_Data.bin')
SOURCE_SHA = '5bff5e0e0c105664281b39d2bc5ef2fe231bf6acbb748fbfffb96cfd14e083ce'
FONT = pathlib.Path('work/source/ppsspp/assets/Roboto_Condensed-Regular.ttf')
RESOURCE = 'menu/TitleMenu_Data.bin'


def version_tuple(version):
    if not re.fullmatch(r'0\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise ValueError('Build version must be 0.x.y without leading zeros')
    return tuple(map(int, version.split('.')))


def swizzle(linear, width, height):
    if len(linear) != width * height or width % 16 or height % 8:
        raise ValueError('Invalid CI8 swizzle dimensions')
    result = bytearray()
    for by in range(0, height, 8):
        for bx in range(0, width, 16):
            for y in range(by, by + 8):
                result.extend(linear[y * width + bx:y * width + bx + 16])
    return bytes(result)


def prepare(config):
    version = config['version']; version_tuple(version)
    credit = config['title_credit']
    if not credit or not credit.isascii() or any(ord(c) < 32 for c in credit):
        raise ValueError('Credit must be one printable ASCII line')
    data = SOURCE.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA:
        raise ValueError('Original title resource changed')
    offsets = struct.unpack_from('<9I', data)
    if offsets != (0x60, 0x2a10, 0x13710, 0x33990, 0x43e10, 0x54290, 0x74710, 0x80410, 0x80510):
        raise ValueError('Title sections changed')
    t = texture(data, offsets[2], offsets[3])
    width, height = t['width'], t['height']
    if (width, height) != (480, 272):
        raise ValueError('Unexpected title background dimensions')
    linear = unswizzle(t['pixels'], width, height)
    if swizzle(linear, width, height) != t['pixels']:
        raise ValueError('Original texture round trip failed')
    palette = [tuple(t['palette'][i * 4:i * 4 + 4]) for i in range(256)]
    original = Image.frombytes('RGBA', (width, height), b''.join(bytes(palette[i]) for i in linear))
    settings = config['title_stamp']
    scale = settings['raster_scale']
    if scale != 4 or not 7 <= settings['font_size_px'] <= 14:
        raise ValueError('Use 4x source text and a readable small title font')
    if not FONT.is_file():
        raise ValueError('Bundled PPSSPP Roboto Condensed font is required')
    font = ImageFont.truetype(str(FONT), settings['font_size_px'] * scale)
    masks = []
    for text in ['v' + version, credit]:
        box = font.getbbox(text)
        w, h = math.ceil((box[2] - box[0]) / scale), math.ceil((box[3] - box[1]) / scale)
        hi = Image.new('L', (w * scale, h * scale))
        ImageDraw.Draw(hi).text((-box[0], -box[1]), text, font=font, fill=255)
        masks.append((text, hi.resize((w, h), Image.Resampling.LANCZOS)))
    right = width - settings['right_margin_px']
    y = height - settings['bottom_margin_px'] - sum(m.height for _, m in masks) - settings['line_gap_px']
    if y < 232 or right > 476 or right < 400:
        raise ValueError('Stamp must stay in the bottom-right safe area')
    full = Image.new('L', (width, height)); boxes = []
    for text, mask in masks:
        x = right - mask.width
        if x < 288:
            raise ValueError('Stamp is too wide for the title safe area')
        full.paste(mask, (x, y))
        boxes.append(dict(text=text, x=x, y=y, width=mask.width, height=mask.height, right=right))
        y += mask.height + settings['line_gap_px']
    shadow = Image.new('L', (width, height))
    shadow.paste(full.crop((0, 0, width - 1, height - 1)), (1, 1))
    composed = original.copy()
    composed.paste((27, 21, 18, 255), (0, 0, width, height), shadow)
    composed.paste((251, 238, 242, 255), (0, 0, width, height), full)
    coverage = bytes(max(a, b) for a, b in zip(full.tobytes(), shadow.tobytes()))
    proposed = bytearray(linear); rgba = composed.tobytes(); cache = {}
    for pos, alpha in enumerate(coverage):
        if not alpha:
            continue
        color = tuple(rgba[pos * 4:pos * 4 + 4])
        if color not in cache:
            cache[color] = min(range(256), key=lambda i: sum((a - b) ** 2 for a, b in zip(color, palette[i])))
        proposed[pos] = cache[color]
    assert all(a == b for a, b, mask in zip(linear, proposed, coverage) if not mask)
    encoded = swizzle(proposed, width, height)
    result = bytearray(data); start = t['pixel_offset']; end = start + len(encoded)
    result[start:end] = encoded
    assert result[:start] == data[:start] and result[end:] == data[end:]
    assert unswizzle(encoded, width, height) == proposed
    logo_report = None
    if config.get('english_title_logo', False):
        from prepare_title_logo_proposal import prepare as prepare_logo
        logo_data, logo_report, _ = prepare_logo()
        if logo_report['proposed_resource_sha256'] != 'd47b65122805be7870436883f9d98cdc6816915237ce25ed70452be9d8c856e6':
            raise ValueError('Reviewed English title logo pixels differ')
        if logo_data[start:end] != data[start:end] or len(logo_data) != len(data):
            raise ValueError('Title logo proposal overlaps version/credit background')
        result = bytearray(logo_data)
        result[start:end] = encoded
    preview = Image.frombytes('RGBA', (width, height), b''.join(bytes(palette[i]) for i in proposed))
    report = dict(version=version, credit=credit, resource=RESOURCE, original_sha256=SOURCE_SHA,
                  output_sha256=hashlib.sha256(result).hexdigest(), bytes=len(result),
                  source_font_sha256=hashlib.sha256(FONT.read_bytes()).hexdigest(),
                  source_raster_scale=scale, display_size=[width, height], alignment='bottom-right',
                  lines=boxes, changed_pixels=sum(a != b for a, b in zip(linear, proposed)),
                  original_palette_preserved=True, all_uncovered_pixels_preserved=True,
                  all_other_resource_bytes_preserved=logo_report is None, runtime_verified=False)
    if logo_report:
        report['title_logo_translation'] = logo_report
    return bytes(result), report, original, preview
