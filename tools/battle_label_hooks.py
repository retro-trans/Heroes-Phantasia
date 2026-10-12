"""Dry scoped CPL battle-name render proposal; no executable or asset writer."""
import hashlib
import json
from pathlib import Path

from dialogue_vwf_hooks import Block, address, decoder, r, route
from live_vwf import i, j, jal, words

SOURCE = Path('work/output/0.1.13-dialogue-assets/EBOOT.BIN')
SHA = '4cb5fb279a080e5dfd97e74b0da1c2e2fdf8b8f61fb28f2402f03c33a5917d67'


def label_decoder():
    # Preserve the reviewed ruby gates and add only this actual visible caller.
    return decoder(speaker_labels=True, extra_return_gates=(0xf0cf0, 0xf0d98, 0xec644))


def label_renderer():
    return route(0xea900)


def label_advance(lut):
    # Replace EC684..EC690 as a unit: increment, compare, branch and delay slot.
    # Never put a jump in the original conditional branch's delay slot.
    h = Block()
    h.emit(i(9, 19, 19, 1), i(9, 29, 29, -16),
           i(43, 29, 24, 0), i(43, 29, 25, 4), i(37, 29, 24, 16))
    h.emit(i(11, 24, 25, 32)); h.branch(5, 25, 0, 'native')
    h.emit(i(11, 24, 25, 129)); h.branch(4, 25, 0, 'native')
    h.emit(i(13, 0, 25, 127)); h.branch(4, 24, 25, 'native')
    address(h, 25, lut)
    h.emit(r(0, 24, 24, shift=2, funct=0), r(25, 24, 25),
           i(35, 25, 24, 0), r(17, 24, 17))
    h.branch(4, 0, 0, 'restore')
    h.label('native'); h.emit(i(9, 17, 17, 13))
    h.label('restore')
    h.emit(i(35, 29, 24, 0), i(35, 29, 25, 4), i(9, 29, 29, 16),
           r(19, 20, 4, funct=0x2a))
    h.branch(5, 4, 0, 'loop')
    h.emit(j(0xec694), 0)
    h.label('loop'); h.emit(j(0xec62c), 0)
    return h.finish()


def label_palette():
    # Keep the prior Select Gender correction, add the native HUD palette0.
    # EA45C saved its outer caller RA at SP+20 before calling E9264.
    h = Block(); h.emit(i(35, 29, 24, 0x20))
    for caller in (0x4fca8, 0xec684):
        address(h, 25, caller); h.branch(4, 24, 25, 'white')
    h.emit(j(0xe9264), 0)
    h.label('white'); h.emit(i(13, 0, 5, 0), j(0xe9264), 0)
    return h.finish()


def label_native_skip():
    # EC658's taken BEQL already increments S3 in its native delay slot.
    # Enter separately: no second increment, no glyph read or Latin advance.
    h = Block(); h.emit(r(19, 20, 4, funct=0x2a), i(9, 17, 17, 13))
    h.branch(5, 4, 0, 'loop'); h.emit(j(0xec694), 0)
    h.label('loop'); h.emit(j(0xec62c), 0)
    return h.finish()


def main():
    data = SOURCE.read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError('Expected immutable reviewed .13 executable')
    expected = {
        0xec67c: words([jal(0xea900)]),
        0xec684: words([i(9, 19, 19, 1), r(19, 20, 4, funct=0x2a),
                       i(5, 4, 0, -25), i(9, 17, 17, 13)]),
    }
    for site, raw in expected.items():
        if data[site + 192:site + 192 + len(raw)] != raw:
            raise ValueError(f'Unexpected original site {site:x}')
    blocks = {'decoder': label_decoder(), 'renderer': label_renderer(),
              'advance': label_advance(0x1000000), 'palette': label_palette(),
              'classifier_false': label_native_skip()}
    print(json.dumps({
        'dry_run': True, 'blocks': {k: {'bytes': len(v), 'sha256': hashlib.sha256(v).hexdigest()}
                                     for k, v in blocks.items()},
        'verified_live': {'caller': 'B06CC', 'source_reader': '978D8',
                          'draw_loop': 'EC5BC', 'decoder_return': 'EC644',
                          'renderer_return': 'EC684', 'source_cpl': 'cpl0197.bin+7D0'},
        'proposed_sites': ['E9CC8 decoder retarget', 'EC67C existing R26 call',
                           'EC684..EC690 new R26 continuation',
                           'EA6AC existing palette-call R26 retarget'],
        'limits': ['Native 32-byte scratch still permits only31 encoded bytes plus NUL.',
                   'CPL string-list pointer/content rebuilding belongs to archive stage.',
                   'Other labels/skill names and custom long labels remain unverified.'],
    }, indent=2))


if __name__ == '__main__':
    main()
