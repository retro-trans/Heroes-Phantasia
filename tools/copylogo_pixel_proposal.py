"""Pure, guarded English CopyLogo CI8 proposal. CLI writes review PNG/JSON only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from PIL import Image, ImageDraw, ImageFont
from inspect_font_assets import texture, unswizzle
from title_stamp import swizzle

SOURCE_SHA = '8e653688e43711ff3b171430941a0538932930b9c52c016f984ffdefe9683e1a'
QUEUE_SHA = 'eee6053d4d2556de00c23609a1492784da367e483139e3e5094b0ff4f3096c80'
LAYOUT_SHA = '80f6685ed96697592b57bbdb9002c48640a5aad70ea85021a8524c0f0ad7a401'
FONT_SHA = 'd8e6f7c5a1356d41dd82b0c00219febd21c791cc5cd1ecf8a0323cbeafe6496c'
OFFSETS = (96, 4992, 136704, 268416, 400128, 531840, 663552, 795264, 843648, 843904)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require_hash(data, expected, label):
    if sha(data) != expected:
        raise ValueError(label + ' changed; renew independent review before using it')


def prepare(data, queue_bytes, layout_bytes, font_path):
    """Return candidate bytes, English report and decoded native images; never write."""
    require_hash(data, SOURCE_SHA, 'Original resource')
    require_hash(queue_bytes, QUEUE_SHA, 'Approved meaning queue')
    require_hash(layout_bytes, LAYOUT_SHA, 'Approved layout')
    require_hash(Path(font_path).read_bytes(), FONT_SHA, 'Raster font')
    if len(data) != 843904 or struct.unpack_from('<10I', data) != OFFSETS:
        raise ValueError('Original length/section table changed')
    queue = json.loads(queue_bytes); layout = json.loads(layout_bytes)
    rows = queue['rows']
    if len(rows) != 14 or any(r['status'] != 'draft' or not r['target'] for r in rows):
        raise ValueError('Expected all 14 approved semantic records')
    result = bytearray(data); ranges = []; sections = []; images = {}
    for spec in layout['sections']:
        index = spec['section']
        if index not in (1, 6):
            raise ValueError('Only warning/copyright pixel arrays are authorized')
        t = texture(data, OFFSETS[index], OFFSETS[index + 1])
        if (t['width'], t['height']) != (480, 272):
            raise ValueError('Unexpected native dimensions')
        require_hash(data[t['offset']:t['offset'] + 128], spec['header_sha256'], 'Texture header')
        require_hash(t['palette'], spec['palette_sha256'], 'Texture palette')
        require_hash(t['pixels'], spec['source_pixels_sha256'], 'Original pixel array')
        linear = unswizzle(t['pixels'], 480, 272)
        if swizzle(linear, 480, 272) != t['pixels']:
            raise ValueError('Original swizzle round trip failed')
        selected = sorted((r for r in rows if r['section'] == index), key=lambda r:r['source_semantic_record'])
        for r in selected:
            lines = [b['text'] for b in spec['measured_lines'] if b['record'] == r['source_semantic_record']]
            if ' '.join(lines) != r['target']:
                raise ValueError('Layout does not retain complete approved record: ' + r['id'])
        high = Image.new('RGBA', (1920, 1088), (255, 255, 255, 255))
        draw = ImageDraw.Draw(high)
        for line in spec['measured_lines']:
            x, y, w, h = (line[k] for k in ('x', 'y', 'width', 'height'))
            if x < 24 or x + w > 456 or y < 0 or y + h > 256:
                raise ValueError('Text crosses reviewed safe bounds')
            font = ImageFont.truetype(str(font_path), line['font_size_px'] * 4)
            color = (255, 0, 0, 255) if index == 1 and line['record'] in (0, 1) else (0, 0, 0, 255)
            draw.text((x * 4, y * 4), line['text'], font=font, fill=color, anchor='lt')
        rgb = high.resize((480, 272), Image.Resampling.LANCZOS)
        palette = [tuple(t['palette'][i:i + 4]) for i in range(0, 1024, 4)]
        cache = {}; proposed = bytearray(); errors = []; ink_errors = []
        for color in rgb.getdata():
            if color not in cache:
                cache[color] = min(range(256), key=lambda i: sum((a-b)**2 for a,b in zip(color, palette[i])))
            choice = cache[color]; proposed.append(choice)
            error = sum((color[k]-palette[choice][k])**2 for k in range(3))
            errors.append(error)
            if color[:3] != (255,255,255):
                ink_errors.append(error)
        encoded = swizzle(proposed, 480, 272)
        if unswizzle(encoded, 480, 272) != proposed:
            raise ValueError('Candidate swizzle round trip failed')
        start = t['pixel_offset']; end = start + len(encoded)
        result[start:end] = encoded; ranges.append((start, end))
        decoded = Image.frombytes('RGBA', (480, 272), b''.join(bytes(palette[i]) for i in unswizzle(encoded, 480, 272)))
        images[index] = decoded
        sections.append(dict(section=index, dimensions=[480,272], pixel_range=[start,end],
            original_header_sha256=spec['header_sha256'], palette_sha256=sha(t['palette']),
            original_pixels_sha256=sha(t['pixels']), candidate_pixels_sha256=sha(encoded),
            changed_pixel_indices=sum(a!=b for a,b in zip(linear,proposed)),
            measured_lines=spec['measured_lines'], raster_scale=4,
            quantization=dict(method='nearest original RGBA palette; no dithering',
                exact_black=(0,0,0,255) in palette,exact_white=(255,255,255,255) in palette,
                exact_red=(255,0,0,255) in palette if index==1 else None,
                rgb_rmse=(sum(errors)/(len(errors)*3))**0.5,
                ink_rgb_rmse=(sum(ink_errors)/(len(ink_errors)*3))**0.5,
                max_channel_error=max(max(abs(color[k]-palette[c][k]) for k in range(4)) for color,c in cache.items()),
                unique_requested_colors=len(cache),unique_palette_indices=len(set(proposed)))))
    if sorted(s['section'] for s in sections) != [1,6]:
        raise ValueError('Exactly two reviewed sections required')
    changed = [i for i,(a,b) in enumerate(zip(data,result)) if a!=b]
    if any(not any(start<=i<end for start,end in ranges) for i in changed):
        raise ValueError('Change escaped authorized pixel arrays')
    if len(result)!=len(data) or result[:96]!=data[:96]:
        raise ValueError('Resource header/length changed')
    report = dict(mode='dry_guarded_native_ci8_pixel_proposal',resource='menu/CopyLogo_Data.bin',
        source_sha256=sha(data),candidate_sha256=sha(result),bytes=len(result),
        queue_sha256=sha(queue_bytes),layout_sha256=sha(layout_bytes),font_sha256=FONT_SHA,
        semantic_records=14,already_Latin_records=2,sections=sections,
        original_24_header_words=list(struct.unpack_from('<24I',data)),
        actual_section_offsets=list(OFFSETS),actual_section_count=9,
        all_24_header_words_preserved=True,all_texture_headers_and_palettes_preserved=True,
        only_sections_1_and_6_pixels_changed=True,changed_resource_bytes=len(changed),
        all_other_bytes_preserved=True,runtime_verified=False,
        limitations=['Native-palette static PNG review only; emulator/hardware readability remains unverified.',
          'The first 24 words are preserved; only the first ten are valid monotonic section offsets.',
          'Red emphasis covers the complete first legal paragraph, as in the approved layout.',
          'No resource/archive/executable/build asset is written by this tool.'])
    return bytes(result),report,images


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--preview-dir',type=Path,help='Opt-in review PNG/JSON output only')
    args=p.parse_args()
    root=Path('work/source/copyright_audit')
    _,report,images=prepare(Path('work/source/cpk/menu/CopyLogo_Data.bin').read_bytes(),
        Path('work/translation/en/copyright_0001.json').read_bytes(),
        (root/'copylogo_layout_proposal.en.json').read_bytes(),
        Path('work/source/ppsspp/assets/Roboto_Condensed-Regular.ttf'))
    if args.preview_dir:
        args.preview_dir.mkdir(parents=True,exist_ok=True)
        for index,image in images.items():
            image.save(args.preview_dir/f'copylogo_{index}_native_english.png')
        (args.preview_dir/'pixel_proposal.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
