"""Pure movie09 cast-scroll proposal from all first1500 decoded native frames.

No PMF writer. Threshold tracking is a placement proposal, not a proof of absence
below the threshold or exact authoring/subpixel positions.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from prepare_title_logo_proposal import FONT
from movie_preparation_runtime import fingerprint

SOURCE = Path('work/source/media_audit/PSP_GAME_USRDIR_MOVIE_HPMOVE09.PMF')
QUEUES = [Path('work/translation/en/media_0001.json'), Path('work/translation/en/media_0002.json')]
HEADINGS = {0: 'Heroes Phantasia', 1: 'Cast', 2: 'Sorcerous Stabber Orphen',
            7: 'Rune Soldier', 16: 'R.O.D -READ OR DIE-', 22: 's-CRY-ed',
            33: 'Sgt. Frog', 44: 'My-HiME', 53: 'BLOOD+',
            58: 'Darker than Black: The Black Contractor',
            61: 'Darker than Black: Gemini of the Meteor',
            65: 'Slayers REVOLUTION', 71: 'Original'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def bands(frame):
    active = np.flatnonzero((frame > 80).sum(axis=1) > 3)
    return [(int(g[0]), int(g[-1]) + 1) for g in
            np.split(active, np.where(np.diff(active) > 1)[0] + 1) if len(g)]

def discover(gray):
    per_frame = [bands(frame) for frame in gray]
    events = []
    for frame, native_bands in enumerate(per_frame):
        for top, bottom in native_bands:
            if 132 <= top <= 134 and bottom - top >= 7:
                if not events or frame - events[-1]['seed_frame'] > 5:
                    events.append(dict(seed_frame=frame, seed_top=top, seed_bottom=bottom))
    # Human-read crossing contact identifies first79 bands as13 headings+66pairs.
    # Later bands are the staff roll and deliberately excluded here.
    assert len(events) == 83 and events[78]['seed_frame'] == 1373
    result = []
    for index, event in enumerate(events[:79]):
        positions = {event['seed_frame']: (event['seed_top'], event['seed_bottom'])}
        for direction in (-1, 1):
            previous = event['seed_top']
            for frame in range(event['seed_frame'] + direction,
                               -1 if direction < 0 else len(gray), direction):
                choices = [b for b in per_frame[frame] if
                           (-1 <= b[0] - previous <= 3 if direction < 0
                            else -3 <= b[0] - previous <= 1)]
                if not choices:
                    break
                assert len(choices) == 1, 'Ambiguous neighboring native row'
                selected = choices[0]
                positions[frame] = selected
                previous = selected[0]
        first, last = min(positions), max(positions)
        assert positions[first][1] == 272 and positions[last][0] == 0
        assert len(positions) == last - first + 1
        assert 207 <= last - first <= 213
        result.append(dict(physical_row=index, **event, first_threshold_frame=first,
                           last_threshold_frame=last, positions=[[k, *positions[k]] for k in sorted(positions)]))
    return result

def panel(text, pair):
    size = 12 if pair else 14
    while True:
        font = ImageFont.truetype(str(FONT), size * 4)
        image = Image.new('RGB', (440 * 4, 16 * 4))
        draw = ImageDraw.Draw(image)
        parts = text.split('\n') if pair else [text]
        assert len(parts) == (2 if pair else 1)
        widths = [draw.textlength(t, font=font) / 4 for t in parts]
        if max(widths) <= (208 if pair else 440):
            break
        size -= 1
        assert size >= 10, 'Full wording does not fit safe cast column'
    for i, (part, width) in enumerate(zip(parts, widths)):
        x = (212 - width) if pair and i == 0 else 232 if pair else (440 - width) / 2
        draw.text((x * 4, 0), part, font=font, fill='white', anchor='lt')
    return image.resize((440, 16), Image.Resampling.LANCZOS), size, widths

def prepare():
    result = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(SOURCE), '-frames:v', '1500',
                             '-an', '-pix_fmt', 'gray', '-f', 'rawvideo', 'pipe:1'], capture_output=True)
    assert not result.returncode and not result.stderr and len(result.stdout) == 1500 * 480 * 272
    gray = np.frombuffer(result.stdout, np.uint8).reshape(1500, 272, 480)
    tracks = discover(gray)
    rows = [r for p in QUEUES for r in json.loads(p.read_bytes())['rows']
            if r['category'] == 'movie_cast_credit']
    assert len(rows) == 66 and all(r['target'] for r in rows)
    sheet = Image.new('RGB', (960, 60 * 40))
    draw = ImageDraw.Draw(sheet)
    pair_index = 0
    for track in tracks:
        i = track['physical_row']
        is_pair = i not in HEADINGS
        row = rows[pair_index] if is_pair else None
        target = row['target'] if row else HEADINGS[i]
        if is_pair:
            pair_index += 1
        rendered, font_size, widths = panel(target, is_pair)
        track.update(id=row['id'] if row else 'movie09_heading_%02d' % i,
                     target=target, type='cast_pair' if is_pair else 'heading',
                     font_px=font_size, widths_px=widths,
                     native_seed_gray_sha256=sha(gray[track['seed_frame']].tobytes()))
        col, line = i % 2, i // 2
        native = Image.fromarray(gray[track['seed_frame']]).convert('RGB')
        box = (20, track['seed_top'] - 1, 460, track['seed_bottom'] + 1)
        crop = native.crop(box)
        # Center-frame strips show all logical lines, not an encoded movie.
        sheet.paste(crop, (col * 480 + 20, line * 60 + 18))
        sheet.paste(rendered, (col * 480 + 20, line * 60 + 40))
        draw.text((col * 480 + 3, line * 60), '%02d frame%d' % (i, track['seed_frame']), fill='white')
    assert pair_index == 66
    report = dict(status='complete_cast_scroll_pixel_and_threshold_tracking_proposal',
                  movie=9, source_sha256=sha(SOURCE.read_bytes()),
                  queue_sha256={str(p): sha(p.read_bytes()) for p in QUEUES},
                  font_sha256=sha(Path(FONT).read_bytes()), preparation_runtime=fingerprint(),
                  decoded_frames_inspected=1500, cast_pair_count=66, heading_count=13,
                  physical_rows=tracks, source_projection_threshold=80,
                  bounded_per_frame_position_tracking=True, guessed_constant_scroll_speed_used=False,
                  staff_blocks_not_modified=True, native_assets_written=False, encoded_candidate=False,
                  exact_boundary_timing_verified=False, whole_movie_text_absence_verified=False,
                  limits=['First/last visibility below projection threshold needs actual boundary review.',
                          'Clipped-edge English placement must use native un-clipped row origin, not pin text to y0.',
                          'Heading wording is a proposal and needs full source/title review.',
                          'This report covers cast rows only;77staff drafts and17unresolved blocks remain separate.',
                          'Gray tracking frames are native decode; contact strips are unencoded intended English.'])
    return report, sheet

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('work/ui/media/credits_cast_scroll_proposal'))
    args = parser.parse_args()
    report, image = prepare()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.write_review:
        args.output.resolve().relative_to(Path('work/ui').resolve())
        assert not args.output.exists()
        args.output.mkdir(parents=True)
        (args.output / 'proposal.en.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        image.save(args.output / 'all_cast_native_intended.png')

if __name__ == '__main__':
    main()
