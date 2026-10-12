"""Pure first1500-frame movie09 cast composite; review PNG/JSON only, no encoder.

Native partial glyphs are correlated with17 complete local row bitmaps. This
recovers offscreen local origins instead of pinning clipped text to viewport y0.
The measured16-gray-level visibility threshold excludes codec residuals; it is
not an exhaustive source-text absence proof or native subpixel-authoring claim.
"""
import argparse
import json
import hashlib
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from prepare_credits_scroll import SOURCE, QUEUES, HEADINGS, discover, panel
from movie_preparation_runtime import fingerprint

def sha(b):
    return hashlib.sha256(b).hexdigest()

def edge_fit(native, templates, entering):
    best = None
    for template_index, template in enumerate(templates):
        for origin in (range(272 - len(template), 273) if entering else range(-len(template), 1)):
            low, high = max(0, origin), min(272, origin + len(template))
            if low >= high:
                continue
            a = native[low:high].astype(np.float64)
            b = template[low - origin:high - origin].astype(np.float64)
            norm = float(np.sqrt(np.square(a).sum() * np.square(b).sum()))
            if norm == 0:
                continue
            score = float((a * b).sum() / norm)
            # Tie-break deterministically; never treat near-black residuals as glyphs.
            key = (score, -template_index, -origin)
            if best is None or key > best[0]:
                best = (key, origin, template_index, int(a.max()))
    if best is None:
        return dict(origin=272 if entering else -len(templates[0]), template_index=0,
                    cosine=0.0, max_gray=0)
    return dict(origin=best[1], template_index=best[2], cosine=best[0][0], max_gray=best[3])

def resolve(gray, track):
    positions = {frame: (top, bottom) for frame, top, bottom in track['positions']}
    templates = []
    for frame, top, bottom in track['positions']:
        if abs(frame - track['seed_frame']) <= 8:
            assert top > 2 and bottom < 270
            templates.append(gray[frame, top - 2:bottom + 2].copy())
    assert len(templates) == 17
    origins, edge_checks = {}, []
    for frame, (top, bottom) in positions.items():
        if top == 0 or bottom == 272:
            fit = edge_fit(gray[frame], templates, bottom == 272)
            assert fit['cosine'] >= .8, (track['physical_row'], frame, fit)
            origins[frame] = fit['origin']
            edge_checks.append(dict(frame=frame, **fit))
        else:
            origins[frame] = top - 2
    # Inspect adjacent outside-threshold frames for a faint first/last source stroke.
    for frame, entering in [(min(positions) - 1, True), (max(positions) + 1, False)]:
        fit = edge_fit(gray[frame], templates, entering)
        accepted = fit['cosine'] >= .8 and fit['max_gray'] >= 16
        edge_checks.append(dict(frame=frame, accepted=accepted, **fit))
        if accepted:
            origins[frame] = fit['origin']
            length = len(templates[fit['template_index']])
            positions[frame] = (max(0, fit['origin']), min(272, fit['origin'] + length))
    ordered = sorted(origins)
    assert ordered == list(range(min(ordered), max(ordered) + 1))
    assert all(-4 <= origins[b] - origins[a] <= 1 for a, b in zip(ordered, ordered[1:])), track['physical_row']
    return origins, positions, edge_checks, templates

def prepare():
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(SOURCE), '-frames:v', '1500',
                              '-an', '-pix_fmt', 'gray', '-f', 'rawvideo', 'pipe:1'], capture_output=True)
    assert not decoded.returncode and not decoded.stderr and len(decoded.stdout) == 1500 * 480 * 272
    gray = np.frombuffer(decoded.stdout, np.uint8).reshape(1500, 272, 480)
    tracks = discover(gray)
    cast = [r for p in QUEUES for r in json.loads(p.read_bytes())['rows'] if r['category'] == 'movie_cast_credit']
    assert len(cast) == 66
    active, rows, pair = {}, [], 0
    for track in tracks:
        index = track['physical_row']
        row = None if index in HEADINGS else cast[pair]
        if row:
            pair += 1
        text = row['target'] if row else HEADINGS[index]
        image, size, widths = panel(text, row is not None)
        ink = np.asarray(image).max(axis=2)
        visible = np.argwhere(ink > 8)
        glyph_box = [int(visible[:, 1].min()), int(visible[:, 0].min()),
                     int(visible[:, 1].max()) + 1, int(visible[:, 0].max()) + 1]
        origins, positions, edge, templates = resolve(gray, track)
        for frame, origin in origins.items():
            top, bottom = positions[frame]
            # Remove the complete bounded native glyph span and paste the English
            # panel with the recovered local origin, clipping to viewport exactly.
            box = [20, max(0, min(top - 2, origin)), 460,
                   min(272, max(bottom + 2, origin + image.height))]
            assert box[1] < box[3]
            active.setdefault(frame, []).append((index, origin, box, image))
        rows.append(dict(physical_row=index, id=row['id'] if row else 'movie09_heading_%02d' % index,
                         target=text, font_px=size, widths_px=widths, english_local_glyph_box=glyph_box,
                         complete_native_template_sha256=[sha(t.tobytes()) for t in templates],
                         first_proposed_frame=min(origins), last_proposed_frame=max(origins),
                         edge_correlations=edge,
                         positions=[[frame, origins[frame], *positions[frame]] for frame in sorted(origins)]))
    samples = sorted(set([180, 300, 430, 560, 700, 840, 980, 1100, 1230, 1370, 1480] +
                         [f for row in rows for f in (row['first_proposed_frame'] - 1,
                          row['first_proposed_frame'], row['last_proposed_frame'], row['last_proposed_frame'] + 1)]))
    native_digest, composite_digest = hashlib.sha256(), hashlib.sha256()
    selected = {}
    process = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(SOURCE), '-frames:v', '1500',
                                '-an', '-pix_fmt', 'rgb24', '-f', 'rawvideo', 'pipe:1'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in range(1500):
            data = process.stdout.read(480 * 272 * 3)
            assert len(data) == 480 * 272 * 3
            native_digest.update(data)
            native = Image.frombytes('RGB', (480, 272), data)
            composite = native.copy()
            entries = active.get(frame, [])
            # All masks precede all English glyphs; neighboring plates cannot erase
            # a previously pasted English row. Actual source row spacing is retained.
            for _, _, box, _ in entries:
                composite.paste((0, 0, 0), box)
            for _, origin, _, image in entries:
                lo, hi = max(0, origin), min(272, origin + image.height)
                if lo < hi:
                    composite.paste(image.crop((0, lo - origin, 440, hi - origin)), (20, lo))
            restored = composite.copy()
            for _, origin, box, image in entries:
                restored.paste(native.crop(box), box)
                # panel extent is included in box; assert contract independently.
                assert box[1] <= max(0, origin) and box[3] >= min(272, origin + image.height)
            assert restored.tobytes() == data, ('Outside-span pixels changed', frame)
            composite_digest.update(composite.tobytes())
            if frame in samples:
                selected[frame] = (native, composite)
        assert not process.stdout.read(1)
        stderr = process.stderr.read()
        assert process.wait() == 0 and not stderr
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    report = dict(status='pure_first1500_cast_composite_review_not_encoded', movie=9,
                  source_sha256=sha(SOURCE.read_bytes()), queue_sha256={str(p): sha(p.read_bytes()) for p in QUEUES},
                  tool_sha256=sha(Path(__file__).read_bytes()), tracker_sha256=sha(Path('tools/prepare_credits_scroll.py').read_bytes()),
                  preparation_runtime=fingerprint(), frame_count=1500, cast_pair_count=66, heading_count=13,
                  native_rgb_sha256=native_digest.hexdigest(), intended_rgb_sha256=composite_digest.hexdigest(),
                  all_outside_proposed_spans_exact=True, glyph_origins_clipped_not_pinned=True,
                  rows=rows, native_assets_written=False, encoded=False, runtime_verified=False,
                  below_16_gray_absence_not_claimed=True,
                  limitations=['Per-frame raster correlation is not original authoring/subpixel timing.',
                               'Only the cast plus13headings are replaced; staff roll stays native.',
                               'No audio, PTS, DTS, PMF packet or native file is modified.',
                               'All boundary contact frames require independent visual review before encoding.'])
    return report, selected

def sheets(report, selected):
    result = {}
    for page in range(8):
        records = report['rows'][page * 10:(page + 1) * 10]
        image = Image.new('RGB', (960, len(records) * 112))
        draw = ImageDraw.Draw(image)
        for line, row in enumerate(records):
            fs = [row['first_proposed_frame'] - 1, row['first_proposed_frame'],
                  row['last_proposed_frame'], row['last_proposed_frame'] + 1]
            for j, frame in enumerate(fs):
                native, intended = selected[frame]
                # Entry bottom24 pixels; exit top24 pixels; adjacent native staff
                # or other cast rows are deliberately retained outside their masks.
                box = (0, 248, 480, 272) if j < 2 else (0, 0, 480, 24)
                y = line * 112 + j * 28
                image.paste(native.crop(box), (0, y + 4))
                image.paste(intended.crop(box), (480, y + 4))
                draw.text((2, y), '%02d frame%d native' % (row['physical_row'], frame), fill='yellow')
                draw.text((482, y), 'Intended English', fill='yellow')
        result['boundary_%02d.png' % page] = image
    full = [180, 300, 430, 560, 700, 840, 980, 1100, 1230, 1370, 1480]
    for page in range(3):
        fs = full[page * 4:(page + 1) * 4]
        image = Image.new('RGB', (960, len(fs) * 294))
        draw = ImageDraw.Draw(image)
        for line, frame in enumerate(fs):
            native, intended = selected[frame]
            image.paste(native, (0, line * 294 + 22));image.paste(intended, (480, line * 294 + 22))
            draw.text((2, line * 294), 'Native frame%d' % frame, fill='white')
            draw.text((482, line * 294), 'Full RAM English composite', fill='white')
        result['full_%02d.png' % page] = image
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('work/ui/media/credits_cast_composite_review'))
    args = parser.parse_args()
    report, selected = prepare()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.write_review:
        args.output.resolve().relative_to(Path('work/ui').resolve())
        assert not args.output.exists()
        args.output.mkdir(parents=True)
        for name, image in sheets(report, selected).items():
            image.save(args.output / name)
        (args.output / 'proposal.en.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

if __name__ == '__main__':
    main()
