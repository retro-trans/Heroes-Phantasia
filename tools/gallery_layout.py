"""Measured gallery soft breaks using the existing packed 4x VWF candidate.

Working translations are never changed. Only ASCII spaces become additional
line delimiters in the rebuilt asset; a reversible offset ledger verifies this.
Native symbols, runtime substitutions and unaudited controls reject.
"""
import hashlib
import json
import math
import pathlib
import re
import struct

from rebuild_dialogue import PERCENT

CANDIDATE = pathlib.Path('work/output/0.1.6-opening-vwf-4x-candidate')
ELF_SHA = '8d310d47f903d2dfdcb86d8ba63ced77b06a1d80aa4590c255b50c26ecdc0bf1'
CODES = tuple(range(32, 127)) + (128,)


def advances():
    raw = (CANDIDATE / 'EBOOT.BIN').read_bytes()
    if hashlib.sha256(raw).hexdigest() != ELF_SHA:
        raise ValueError('Reference 4x VWF executable changed')
    manifest = json.loads((CANDIDATE / 'manifest.en.json').read_text(encoding='utf8'))
    if manifest['output_elf_sha256'] != ELF_SHA or manifest['font_scale'] != 4:
        raise ValueError('Reference font manifest differs')
    ph = struct.unpack_from('<8I', raw, 0x34 + 64)
    start, address, size = ph[1], ph[2], ph[4]
    if ph[0] != 1 or start + size > len(raw) or size < 0xA04:
        raise ValueError('Reference font load segment differs')
    widths = struct.unpack_from('<129f', raw, start + 0x800)
    if any(not math.isfinite(widths[c]) or not 0 < widths[c] <= 16 for c in CODES):
        raise ValueError('Reference font advances are unsupported')
    if widths[105] != 4 or widths[87] != 12:
        raise ValueError('Reference font proportional metrics differ')
    lookup = struct.unpack_from('<129H', raw, start + 0x600)
    bank_start = start + manifest['high_bank'] - address
    bank_size = manifest['high_bank_bytes']
    if not start <= bank_start < bank_start + bank_size <= start + size:
        raise ValueError('Reference high-resolution bank is out of bounds')
    if manifest['high_codes'] != list(CODES) or manifest['high_lookup_unit'] != 256:
        raise ValueError('Reference font repertoire differs')
    if any(lookup[c] == 65535 or lookup[c] * 256 + 2048 > bank_size for c in CODES):
        raise ValueError('Reference glyph mapping is incomplete')
    for c in CODES:
        if manifest['high_glyph_offsets'][str(c)] != lookup[c] * 256:
            raise ValueError('Reference glyph offset differs')
    return {c: round(widths[c]) for c in CODES}, dict(
        executable_sha256=ELF_SHA, source_version='0.1.6',
        bank_sha256=hashlib.sha256(raw[bank_start:bank_start + bank_size]).hexdigest(),
        glyph_source_scale=4, source_rect=[64, 64], destination_rect=[16, 16],
        advance_policy='Same rounded integer advances as the dialogue cursor',
        extent_policy='Conservative 16px destination rectangle for each non-space glyph; spaces have no ink')


def dimensions(line, widths):
    pen = extent = 0
    for code in line:
        if code != 32:
            extent = max(extent, pen + 16)
        pen += widths[code]
    return pen, extent


def wrap(encoded, width, widths, glyph_limit=45):
    if not 16 <= width <= 480:
        raise ValueError('Gallery wrap width must be 16 through 480 pixels')
    if not 1 <= glyph_limit <= 1024:
        raise ValueError('Gallery glyph limit must be 1 through 1024')
    if PERCENT.search(encoded.decode('cp932')):
        raise ValueError('Runtime format expansion has no verified pixel width')
    if any(c not in widths and c not in (0x11, 0x12, 0x0E) for c in encoded):
        raise ValueError('Gallery wrapping supports Latin and 11/12/0E controls only; native symbols/ruby need separate measured handling')
    out = bytearray(encoded)
    breaks = []
    # Each original control boundary survives at exactly its original byte offset.
    pos = 0
    while pos < len(encoded):
        if encoded[pos] < 32:
            pos += 1
            continue
        stop = pos
        while stop < len(encoded) and encoded[stop] >= 32:
            stop += 1
        line_start = pos
        for match in re.finditer(rb'[^ ]+', encoded[pos:stop]):
            word_start, word_end = pos + match.start(), pos + match.end()
            if word_end - word_start > glyph_limit or dimensions(encoded[word_start:word_end], widths)[1] > width:
                raise ValueError(f'Unbreakable gallery word exceeds width at encoded offset {word_start}')
            if word_end - line_start <= glyph_limit and dimensions(out[line_start:word_end], widths)[1] <= width:
                continue
            # Break at the last separating space; other spaces remain untouched.
            split = word_start - 1
            if split < line_start or out[split] != 32:
                raise ValueError('No safe word boundary for gallery soft break')
            out[split] = 0x11
            breaks.append(split)
            line_start = word_start
        pos = stop
    restored = bytearray(out)
    for offset in breaks:
        if encoded[offset] != 32 or out[offset] != 0x11:
            raise ValueError('Soft-break ledger differs')
        restored[offset] = 32
    if restored != encoded:
        raise ValueError('Wrapping changed wording or original controls')
    lines = []
    for line in re.split(rb'[\x11\x12\x0e]', bytes(out)):
        pen, extent = dimensions(line, widths)
        lines.append(dict(advance_px=pen, destination_extent_px=extent,
                          glyphs=len(line)))
    if any(line['destination_extent_px'] > width or line['glyphs'] > glyph_limit for line in lines):
        raise ValueError('Wrapped line exceeds the measured area')
    return bytes(out), dict(width_px=width, glyph_limit=glyph_limit, soft_breaks=len(breaks),
                           space_to_linebreak_offsets=breaks, lines=lines,
                           original_controls_preserved_at_original_offsets=True,
                           wording_reconstructed_byte_exact=True,
                           runtime_verified=False)
