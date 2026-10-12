"""Dry dialogue width audit and candidate control-aware runtime measurement.

No executable/archive writer and no automatic wrapping. Runtime substitutions,
ruby, unknown controls and unsupported native glyphs retain native measurement.
"""
from dialogue_tokens import tokenize_bytes
from dialogue_vwf_hooks import Block, address, r
from live_vwf import i, j

FENCES = frozenset((0x0E, 0x10, 0x11, 0x12))
WIDTH_NEUTRAL_ARGUMENTS = {0x05: 3, 0x16: 2, 0x17: 1}


def measure_bytes(data, widths):
    tokens = tokenize_bytes(data, private_latin=True)
    lines = [0]
    for token in tokens:
        if token.kind in ('ruby_open', 'ruby_close') or token.ruby:
            return dict(supported=False, reason='Ruby span width requires translated-base association')
        if token.kind == 'latin':
            lines[-1] += widths[token.code]
        elif token.kind == 'native' and len(token.data) == 2:
            lines[-1] += 13
        elif token.kind == 'control' and token.code in FENCES:
            lines.append(0)
        elif token.kind == 'control' and token.code in WIDTH_NEUTRAL_ARGUMENTS:
            pass
        else:
            return dict(supported=False, reason=f'Unverified token at byte{token.offset}: {token.kind}/{token.code}')
    return dict(supported=True, advance_px=lines, maximum_advance_px=max(lines),
                controls_and_arguments_excluded=True, runtime_verified=False)


def measure(lut,private_pairs=False,hideo_ruby=False):
    """Candidate replacement for the ED15C hook; caller/geometry scopes unchanged.

This only enlarges accepted controls to link IDs and color/line mode arguments.
It does not enable ruby/runtime expansions, alter native line allocation, or
claim that fitting the measured width verifies panel clipping/page capacity.
"""
    h=Block();h.emit(i(57,20,12,0x2c),i(43,4,23,0x48),i(9,29,29,-192))
    regs=list(range(8,16))+[24,25]
    for n,reg in enumerate(regs):h.emit(i(43,29,reg,n*4))
    h.emit(i(57,29,0,40),i(57,29,1,44),i(35,20,9,0x18),i(11,9,15,33))
    h.branch(4,15,0,'return');h.branch(4,9,0,'return')
    h.emit(i(35,20,8,4),i(13,0,10,0),i(13,0,24,0));address(h,14,lut)
    h.label('line');h.emit(i(35,8,11,4),i(13,0,12,0),i(13,0,25,0))
    # The 1024-byte cap allows one terminal NUL/fence probe at byte1024,
    # but never a glyph/argument lookahead beyond that probe.
    h.label('char');h.emit(i(11,25,15,1025));h.branch(4,15,0,'return')
    h.emit(i(36,11,13,0));h.branch(4,13,0,'endline')
    for stop in sorted(FENCES):
        h.emit(i(13,0,15,stop));h.branch(4,13,15,'endline')
    h.emit(i(11,25,15,1024));h.branch(4,15,0,'return')
    for control in WIDTH_NEUTRAL_ARGUMENTS:
        h.emit(i(13,0,15,control));h.branch(4,13,15,f'argument_{control}')
    if hideo_ruby:
        h.emit(i(13,0,15,0x0f));h.branch(4,13,15,'hideo_reading')
    h.emit(i(11,13,15,32));h.branch(5,15,0,'return')
    if private_pairs:
        h.emit(i(13,0,15,0xf0));h.branch(4,13,15,'private_pair')
    h.emit(i(11,13,15,129));h.branch(4,15,0,'native_pair')
    h.emit(i(13,0,15,127));h.branch(4,13,15,'return')
    h.emit(r(0,13,15,0,2),r(14,15,15),i(35,15,15,0),r(12,15,12),
           i(9,11,11,1),i(9,25,25,1))
    h.branch(4,0,0,'bound')
    if private_pairs:
        h.label('private_pair');h.emit(i(11,25,15,1023));h.branch(4,15,0,'return')
        h.emit(i(36,11,13,1),i(9,13,15,-0x40),i(11,15,15,2));h.branch(4,15,0,'native_pair_reloaded')
        h.emit(i(9,13,13,65),r(0,13,15,0,2),r(14,15,15),i(35,15,15,0),r(12,15,12),
               i(9,11,11,2),i(9,25,25,2));h.branch(4,0,0,'bound')
        h.label('native_pair_reloaded');h.emit(i(36,11,13,0))
    h.label('native_pair')
    h.emit(i(11,13,15,0xa0));h.branch(5,15,0,'trail')
    h.emit(i(11,13,15,0xe0));h.branch(5,15,0,'return')
    h.emit(i(11,13,15,0xfd));h.branch(4,15,0,'return')
    h.label('trail');h.emit(i(11,25,15,1023));h.branch(4,15,0,'return')
    h.emit(i(36,11,13,1),i(11,13,15,0x40));h.branch(5,15,0,'return')
    h.emit(i(11,13,15,0xfd));h.branch(4,15,0,'return')
    h.emit(i(13,0,15,0x7f));h.branch(4,13,15,'return')
    h.emit(i(9,12,12,13),i(9,11,11,2),i(9,25,25,2));h.branch(4,0,0,'bound')
    for control,count in WIDTH_NEUTRAL_ARGUMENTS.items():
        h.label(f'argument_{control}')
        h.emit(i(11,25,15,1024-count));h.branch(4,15,0,'return')
        # Verify every decimal argument before advancing; malformed input must
        # keep native measurement and never skip into another control/glyph.
        for n in range(1,count+1):
            h.emit(i(36,11,13,n),i(9,13,15,-48),i(11,15,15,10))
            h.branch(4,15,0,'return')
        h.emit(i(9,11,11,count+1),i(9,25,25,count+1));h.branch(4,0,0,'bound')
    h.label('bound');h.emit(i(11,25,15,1025))
    h.branch(4,15,0,'return');h.branch(4,0,0,'char')
    if hideo_ruby:
        # Exact, redundant Latin reading only. The original span digit2 stays
        # intact; the five-letter translated base is measured normally.
        h.label('hideo_reading')
        h.emit(i(11,25,15,1017));h.branch(4,15,0,'return')
        for n,value in enumerate(b'2Hideo\x0f',1):
            h.emit(i(36,11,13,n),i(13,0,15,value));h.branch(5,13,15,'return')
        h.emit(i(9,11,11,8),i(9,25,25,8));h.branch(4,0,0,'char')
    h.label('endline');h.emit(r(0,10,15,0,2),r(29,15,15),i(43,15,12,64),r(24,12,15,0x2b))
    h.branch(4,15,0,'keepmax');h.emit(r(12,0,24));h.label('keepmax')
    h.emit(i(9,10,10,1),i(9,8,8,0xe8));h.branch(5,10,9,'line')
    h.emit(i(35,20,8,4),i(13,0,10,0),i(13,0,15,0x3f00),r(0,15,15,0,16),0x448f0800)
    h.label('storeline');h.emit(r(0,10,15,0,2),r(29,15,15),i(35,15,12,64),0x448c0000,
        0x46800020,0x46010002,i(57,8,0,0x20),i(9,8,8,0xe8),i(9,10,10,1))
    h.branch(5,10,9,'storeline');h.emit(0x44980000,0x46800020,0x46010002,i(57,20,0,0x2c))
    h.label('return');h.emit(i(49,29,0,40),i(49,29,1,44))
    for n,reg in enumerate(regs):h.emit(i(35,29,reg,n*4))
    h.emit(j(0xed164),i(9,29,29,192))
    return h.finish()
