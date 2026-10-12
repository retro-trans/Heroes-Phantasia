"""Static bubble catalog and horizontal-fit model; no emulator access.

Packed catalog order is template-major, then visible line count 1..4. Each
12-byte little-endian entry is (usable_half_width, geometry_min_x,
geometry_max_x). Zero half width means unsupported. Horizontal scaling
stretches tails; this model does not preserve their exact shape or world target.
The screen clamp assumes zero rotation and unit native animation scale.
"""
import argparse
import hashlib
import json
import math
import pathlib
import struct

ROOT = pathlib.Path(__file__).resolve().parents[1]
ELF = ROOT / 'work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf'
SHA = '03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1'
TEMPLATE_BASE = 0x45E2C8
TEMPLATE_COUNT = 152
TEMPLATE_STRIDE = 0x1EC
EPSILON = 0.0001


def load_templates(path=ELF):
    data = pathlib.Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError('Original executable hash changed')
    phoff = struct.unpack_from('<I', data, 28)[0]
    phnum = struct.unpack_from('<H', data, 44)[0]
    loads = [struct.unpack_from('<8I', data, phoff + n * 32)
             for n in range(phnum)]
    end = TEMPLATE_BASE + TEMPLATE_COUNT * TEMPLATE_STRIDE
    containing = [p for p in loads if p[0] == 1 and
                  p[2] <= TEMPLATE_BASE and end <= p[2] + p[4]]
    if len(containing) != 1:
        raise ValueError('Template range is not in one file-backed load segment')
    segment = containing[0]
    file_base = segment[1] + TEMPLATE_BASE - segment[2]
    result = []
    for template_id in range(TEMPLATE_COUNT):
        offset = file_base + template_id * TEMPLATE_STRIDE
        count, reserved, text_x, text_y, speaker_x, speaker_y = struct.unpack_from('<H5h', data, offset)
        if not 1 <= count <= 30 or reserved != 0:
            raise ValueError(f'Template {template_id}: unsupported header')
        banks = []
        for bank_offset in (0x0C, 0xFC):
            coordinates = struct.unpack_from('<60f', data, offset + bank_offset)
            if not all(math.isfinite(v) and abs(v) <= 4096 for v in coordinates):
                raise ValueError(f'Template {template_id}: unsafe coordinates')
            banks.append(list(zip(coordinates[::2][:count], coordinates[1::2][:count])))
        outline = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                   for a, b in zip(*banks)]
        result.append(dict(template_id=template_id, count=count,
                           text_offset=[text_x, text_y],
                           speaker_offset=[speaker_x, speaker_y],
                           banks=banks, outline=outline))
    return result


def centered_interval(polygon, y):
    """Even/odd polygon scan conversion; return the interval containing x=0."""
    if not math.isfinite(y) or len(polygon) < 3:
        return None
    intersections = []
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
        if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
            return None
        if (y1 <= y < y2) or (y2 <= y < y1):
            intersections.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    intersections.sort()
    if len(intersections) % 2:
        return None
    intervals = [(a, b) for a, b in zip(intersections[::2], intersections[1::2])
                 if a < 0 < b]
    return intervals[0] if len(intervals) == 1 else None


def usable_half_width(template, line_count):
    if line_count not in (1, 2, 3, 4):
        return 0.0
    polygon = template['banks'][0]
    half = math.inf
    for line in range(line_count):
        top = template['text_offset'][1] + 22 * line
        bottom = top + 16
        samples = {top + EPSILON, bottom - EPSILON}
        for _, vertex_y in polygon:
            for y in (vertex_y - EPSILON, vertex_y + EPSILON):
                if top < y < bottom:
                    samples.add(y)
        for y in samples:
            interval = centered_interval(polygon, y)
            if interval is None:
                return 0.0
            half = min(half, -interval[0], interval[1])
    return max(0.0, half - EPSILON) if math.isfinite(half) else 0.0


def catalog(templates, compact_catalog=False):
    entries, packed = [], bytearray()
    for template in templates:
        xs = [x for bank in template['banks'] for x, _ in bank]
        min_x, max_x = min(xs), max(xs)
        for lines in range(1, 5):
            half = usable_half_width(template, lines)
            # Report exactly the float32 values consumers receive.
            blob = struct.pack('<3f', half, min_x, max_x)
            half, low, high = struct.unpack('<3f', blob)
            entries.append(dict(template_id=template['template_id'], line_count=lines,
                                usable_half_width=half, min_x=low, max_x=high))
            packed.extend(blob)
    assert len(packed) == TEMPLATE_COUNT * 4 * 12
    if compact_catalog:
        # Capacities keep their exact float32 representation; shared bounds
        # occur once per template, after the four visible-line capacities.
        packed = bytearray()
        for first in range(0, len(entries), 4):
            group = entries[first:first + 4]
            assert len(group) == 4
            assert all(e['min_x'] == group[0]['min_x'] and
                       e['max_x'] == group[0]['max_x'] for e in group)
            packed.extend(struct.pack('<6f', *(e['usable_half_width'] for e in group),
                                      group[0]['min_x'], group[0]['max_x']))
        assert len(packed) == TEMPLATE_COUNT * 24
    return entries, bytes(packed)


def model(template, line_count, width, center, padding=8, screen_width=480, screen_margin=8):
    """Reconstruct from the immutable template on every call, never prior output."""
    values = (width, center, padding, screen_width, screen_margin)
    if not all(math.isfinite(v) for v in values) or min(width, padding, screen_margin) < 0:
        raise ValueError('Invalid model dimensions')
    half = usable_half_width(template, line_count)
    if half <= 0:
        return dict(supported=False, reason='Glyph bands are outside the centered white interior')
    ratio = max(1.0, (width / 2 + padding) / half)
    banks = [[(x * ratio, y) for x, y in bank] for bank in template['banks']]
    outline = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
               for a, b in zip(*banks)]
    xs = [x for bank in banks for x, _ in bank]
    min_x, max_x = min(xs), max(xs)
    allowed_low = screen_margin - min_x
    allowed_high = screen_width - screen_margin - max_x
    if allowed_low > allowed_high:
        return dict(supported=False, reason='Widened full geometry cannot fit the screen',
                    ratio=ratio, allowed_center_range=[allowed_low, allowed_high])
    clamped_center = min(max(center, allowed_low), allowed_high)
    return dict(supported=True, usable_half_width=half, width=width, padding_per_side=padding,
                ratio=ratio, original_center=center, clamped_center=clamped_center,
                center_shift=clamped_center-center, allowed_center_range=[allowed_low, allowed_high],
                screen_bounds=[clamped_center+min_x, clamped_center+max_x],
                banks=banks, outline=outline, tail_exact_shape_preserved=False,
                assumptions='Centered text; zero rotation; unit native animation scale; XY is regenerated from immutable templates')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--output-dir', type=pathlib.Path, default=ROOT / 'work/ui/bubble_metrics')
    args = parser.parse_args()
    templates = load_templates()
    entries, packed = catalog(templates)
    sample = [e for e in entries if e['template_id'] == 79]
    fit = model(templates[79], 2, 185, 369)
    # Analytic rectangle, unsupported band and immutable reconstruction checks.
    rectangle = dict(banks=[[(-50., -10.), (50., -10.), (50., 50.), (-50., 50.)]], text_offset=[0, 0])
    assert abs(usable_half_width(rectangle, 2) - (50-EPSILON)) < 1e-8
    assert usable_half_width(rectangle, 4) == 0
    assert fit == model(templates[79], 2, 185, 369)
    assert templates[79]['outline'] == [((a[0]+b[0])/2, (a[1]+b[1])/2)
                                       for a, b in zip(*templates[79]['banks'])]
    info = dict(schema_version=1, source_elf_sha256=SHA,
                template_base=hex(TEMPLATE_BASE), template_stride=TEMPLATE_STRIDE,
                templates=TEMPLATE_COUNT, entries=len(entries), packed_bytes=len(packed),
                packed_sha256=hashlib.sha256(packed).hexdigest(),
                packed_layout='template-major; line_count1..4; little-endian float32 half/minX/maxX; 12 bytes per entry',
                glyph_band_height=16, line_pitch=22, scanline_epsilon=EPSILON,
                geometry_bounds='Both source XY banks, including tails and border',
                unsupported_entries=sum(e['usable_half_width'] == 0 for e in entries),
                runtime_verified=False, tail_exact_shape_preserved=False,
                notes='Pure static model. Tail geometry stretches horizontally. No original asset, ISO, executable or hardware writes.',
                shape79_metrics=sample, shape79_width185_model=fit, catalog=entries)
    print(json.dumps({k:v for k,v in info.items() if k != 'catalog'}, indent=2))
    if not args.write:
        print('DRY RUN: no catalog data written.')
        return
    output = args.output_dir.resolve()
    allowed = (ROOT / 'work/ui').resolve()
    if allowed not in output.parents:
        raise ValueError('Output directory must be under work/ui')
    if output.exists():
        raise ValueError('Use a fresh catalog output directory')
    output.mkdir(parents=True)
    (output / 'catalog.bin').write_bytes(packed)
    (output / 'catalog.en.json').write_text(json.dumps(info, indent=2)+'\n', encoding='utf8')
    print('Wrote static catalog; runtime resize remains unverified.')


if __name__ == '__main__':
    main()
