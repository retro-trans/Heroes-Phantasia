"""Package authorized 0.1.61 full and published-0.1.50 upgrade patches."""
import argparse, json, subprocess, sys
from pathlib import Path
from package_release import ORIGINAL, ORIGINAL_SHA

VERSION = '0.1.61'
PIN = '2af227800140bc596327459d8849484d6296a247'
UPSTREAM = Path('work/source/release_061/retro-trans-tools')
BASE = Path('work/output/0.1.61-title-credit-vwf-4x-candidate')
TARGET = BASE / 'Heroes-Phantasia-0.1.61-title-credit-vwf-4x-candidate.iso'
TARGET_SHA = '154eba01e36a83d9dac00ae8f5d93d8473e7c5310a398b7942a83c68f2fc5674'
PREVIOUS = Path('work/output/0.1.50-title-credit-vwf-4x-candidate/Heroes-Phantasia-0.1.50-title-credit-vwf-4x-candidate.iso')
PREVIOUS_SHA = 'fa420a494942817a7498615716b8b43bbc5ff4a817abb3cdb4354a90e89df8b8'
OUT = Path('work/output/0.1.61-release')
PRIVATE = Path('work/source/release_061/release-local.json')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-commit', required=True)
    p.add_argument('--write', action='store_true')
    a = p.parse_args()
    commit = subprocess.check_output(['git', 'rev-parse', a.source_commit + '^{commit}'], text=True).strip()
    if commit != a.source_commit or len(commit) != 40:
        raise ValueError('Exact source commit required')
    if subprocess.check_output(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD'], text=True).strip() != PIN:
        raise ValueError('Packager pin differs')
    if subprocess.check_output(['git', '-C', str(UPSTREAM), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Packager working tree differs')
    m = json.loads((BASE / 'manifest.en.json').read_text(encoding='utf8'))
    proof = json.loads(Path('work/ui/dialogue/0.1.61/native_summary.en.json').read_text(encoding='utf8'))
    if m['version'] != VERSION or m['iso_sha256'] != TARGET_SHA or proof['iso_sha256'] != TARGET_SHA:
        raise ValueError('Reviewed build identity differs')
    expected = [('original', ORIGINAL, ORIGINAL_SHA, 1415020544), ('0.1.50', PREVIOUS, PREVIOUS_SHA, 2647455744)]
    if TARGET.stat().st_size != 2868887552 or any(path.stat().st_size != size for _, path, _, size in expected):
        raise ValueError('Input size differs')
    rows = [dict(patch=f'Heroes-Phantasia-English-{VERSION}.xdelta' if v == 'original' else f'Heroes-Phantasia-English-{v}-to-{VERSION}.xdelta',
                 edition='English', language='en', source_version=v, source_format='iso', target_format='iso',
                 source=str(path.resolve()), target=str(TARGET.resolve())) for v, path, _, _ in expected]
    config = dict(game_id='heroes-phantasia', game_name='Heroes Phantasia', platform='PSP', version=VERSION,
                  source_commit=commit, patches=rows)
    print(json.dumps(dict(version=VERSION, source_commit=commit, packager_commit=PIN,
                          patches=[r['patch'] for r in rows], target_sha256=TARGET_SHA, roundtrips_required=2), indent=2), flush=True)
    if not a.write:
        print('DRY RUN: no package writes.'); return
    sys.path.insert(0, str(UPSTREAM.resolve()))
    from retro_trans.release import build_release, validate_directory
    from retro_trans.core import sha256_file
    # Reject an unexpected input before encoding. The canonical builder also rechecks after each round trip.
    for _, path, digest, _ in expected:
        if sha256_file(path) != digest:
            raise ValueError('Frozen source differs: ' + str(path))
    if sha256_file(TARGET) != TARGET_SHA:
        raise ValueError('Reviewed target differs')
    PRIVATE.write_text(json.dumps(config, indent=2) + '\n', encoding='utf8')
    last = None
    def progress(message, fraction=None):
        nonlocal last
        if message != last:
            print(message, flush=True); last = message
    result = build_release(PRIVATE, OUT, progress=progress, cache=Path('work/source/release_045/engine-cache'))
    validate_directory(OUT)
    if len(result['patches']) != 2 or any(r['target_sha256'] != TARGET_SHA for r in result['patches']):
        raise ValueError('Canonical package differs')
    print('Both patches reproduce the exact reviewed 0.1.61 ISO.', flush=True)


if __name__ == '__main__':
    main()
