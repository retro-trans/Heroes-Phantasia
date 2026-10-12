"""Capture a bounded native-frame sequence in an isolated emulator; preview first."""
import argparse
import contextlib
import io
import json
import pathlib
import sys
import time

import capture_frame
from ppsspp_debug import Debugger


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--count', type=int, default=100)
    p.add_argument('--interval', type=float, default=.25)
    p.add_argument('--skip-intro-at', type=float, help='Press Start once after this many seconds, to skip the intro')
    p.add_argument('--write', action='store_true')
    a = p.parse_args()
    if not 1 <= a.count <= 150 or not .05 <= a.interval <= 2:
        raise ValueError('Sequence must be bounded')
    if a.output.exists():
        raise ValueError('Sequence folder must be fresh')
    info = json.loads(a.manifest.read_text(encoding='utf8'))
    planned = dict(version=info['version'], frames=a.count, interval_seconds=a.interval,
                   output=str(a.output), skip_intro_at_seconds=a.skip_intro_at,
                   capture_method='software_renderer_emulated_VRAM', input='one optional Start press; no memory edits')
    print(json.dumps(planned, indent=2), flush=True)
    if not a.write:
        old = sys.argv
        try:
            sys.argv = ['capture_frame', '--build-manifest', str(a.manifest), '--output', str(a.output/'frame_000.png')]
            capture_frame.main()
        finally:
            sys.argv = old
        print('DRY RUN: no sequence written and no button pressed.')
        return
    a.output.mkdir(parents=True)
    records = []; started = time.monotonic(); skipped = False
    for n in range(a.count):
        elapsed = time.monotonic() - started
        if a.skip_intro_at is not None and elapsed >= a.skip_intro_at and not skipped:
            d = Debugger()
            try:
                d.tap('start', frames=4)
            finally:
                d.close()
            skipped = True
        path = a.output / ('frame_%03d.png' % n)
        old = sys.argv
        try:
            sys.argv = ['capture_frame', '--build-manifest', str(a.manifest), '--output', str(path), '--write']
            with contextlib.redirect_stdout(io.StringIO()):
                capture_frame.main()
        finally:
            sys.argv = old
        records.append(dict(index=n, elapsed_seconds=round(elapsed,3), path=str(path)))
        if n % 20 == 0:
            print('Captured frame', n, 'at', round(elapsed,1), 'seconds', flush=True)
        time.sleep(a.interval)
    planned.update(records=records, skip_intro_pressed=skipped, runtime_content_visually_reviewed=False)
    (a.output/'sequence.en.json').write_text(json.dumps(planned, indent=2)+'\n', encoding='utf8')
    print('Captured', a.count, 'native frames for visual review.', flush=True)


if __name__ == '__main__':
    main()
