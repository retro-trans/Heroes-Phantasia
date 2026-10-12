"""Read-only atomic dialogue tokenization, grounded in the native control parser.

E9C04 / table2EF1C0 supplies fixed argument byte counts. Paired0F is special:
F0CB4 reads one base-span digit after the opening marker and scans the reading
until the closing marker. No argument is attached to the closing marker.
Tokens preserve bytes and offsets; this module never rewrites Japanese or adds
controls. Unknown controls remain atomic but make pixel measurement uncertain.
"""
from dataclasses import dataclass
import re
from private_latin import CHAR_BYTES, BYTES_CHAR, CHAR_GLYPH

FIXED_ARGUMENT_BYTES = {
    0x01: 1, 0x02: 4, 0x03: 4, 0x05: 3, 0x06: 6,
    0x0C: 2, 0x13: 1, 0x16: 2, 0x17: 1, 0x19: 2, 0x1A: 1,
}
# These argument formats are also grounded in their actual native handlers.
DECIMAL_ARGUMENTS = frozenset((0x01, 0x02, 0x05, 0x16, 0x17))
KNOWN_ZERO_ARGUMENTS = frozenset((4, 7, 8, 9, 10, 11, 13, 14,
                                16, 17, 18, 20, 21, 24, 0x1C))
MARKERS = re.compile(r'\{([0-9A-Fa-f]{2})\}')


@dataclass(frozen=True)
class Token:
    offset: int
    data: bytes
    kind: str
    code: int = None
    argument: bytes = b''
    ruby: bool = False


def tokenize_bytes(data, private_latin=False):
    """Return atomic glyph/control tokens, rejecting truncation and broken ruby."""
    result = []
    pos = 0
    ruby = False
    while pos < len(data):
        start = pos
        code = data[pos]
        pos += 1
        if code == 0:
            raise ValueError(f'Embedded NUL at byte{start}')
        if code == 0x0F:
            if ruby:
                result.append(Token(start, data[start:pos], 'ruby_close', code, ruby=True))
                ruby = False
            else:
                if pos == len(data) or not 48 <= data[pos] <= 57:
                    raise ValueError(f'Ruby opening requires one base-span digit at byte{start}')
                pos += 1
                result.append(Token(start, data[start:pos], 'ruby_open', code,
                                    data[pos-1:pos], ruby=False))
                ruby = True
            continue
        if code < 32:
            count = FIXED_ARGUMENT_BYTES.get(code, 0)
            if pos + count > len(data):
                raise ValueError(f'Truncated control{code:02X} at byte{start}')
            argument = data[pos:pos+count]
            if code in DECIMAL_ARGUMENTS and any(not 48 <= x <= 57 for x in argument):
                raise ValueError(f'Nondecimal control{code:02X} argument at byte{start}')
            if any(x < 32 for x in argument):
                raise ValueError(f'Control embedded in fixed argument at byte{start}')
            pos += count
            known = code in FIXED_ARGUMENT_BYTES or code in KNOWN_ZERO_ARGUMENTS
            result.append(Token(start, data[start:pos], 'control' if known else 'unknown_control',
                                code, argument, ruby))
            continue
        if 32 <= code <= 126 or private_latin and code == 128:
            kind = 'latin'
        elif 0x81 <= code <= 0x9F or 0xE0 <= code <= 0xFC:
            if pos == len(data) or not (0x40 <= data[pos] <= 0xFC and data[pos] != 0x7F):
                raise ValueError(f'Invalid CP932 pair at byte{start}')
            pos += 1
            data[start:pos].decode('cp932', errors='strict')
            if private_latin and data[start:pos] in BYTES_CHAR:
                kind = 'latin'
                code = CHAR_GLYPH[BYTES_CHAR[data[start:pos]]]
            else:kind = 'native'
        elif 0xA1 <= code <= 0xDF:
            kind = 'native'
        else:
            raise ValueError(f'Unsupported glyph byte{code:02X} at byte{start}')
        result.append(Token(start, data[start:pos], kind, code, ruby=ruby))
    if ruby:
        raise ValueError('Unclosed ruby span')
    if b''.join(t.data for t in result) != data:
        raise AssertionError('Tokenization changed source bytes')
    return result


def text_bytes(text, private_latin=False, signature_only=False):
    """Encode notation for inspection; unsupported private glyphs still reject."""
    output = bytearray()
    pos = 0
    def plain(value):
        for char in value:
            if private_latin and char in CHAR_BYTES:
                output.extend(CHAR_BYTES[char])
            else:
                try:output.extend(char.encode('cp932', errors='strict'))
                except UnicodeEncodeError:
                    # Control validation is independent of the output glyph
                    # policy; an explicit punctuation mapper may run later.
                    # Unknown prose cannot become a control/decimal argument.
                    if not signature_only:raise
                    output.append(63)
    for marker in MARKERS.finditer(text):
        plain(text[pos:marker.start()])
        code = int(marker.group(1), 16)
        if not 1 <= code < 32:
            raise ValueError('Only low-byte nonzero control notation is supported')
        output.append(code)
        pos = marker.end()
    plain(text[pos:])
    return bytes(output)


def tokenize_text(text, private_latin=False):
    return tokenize_bytes(text_bytes(text, private_latin), private_latin)


def control_signature(tokens):
    """Compare fixed arguments and ruby opening/closing roles, excluding prose."""
    return [(t.code, t.argument, t.kind) for t in tokens
            if t.kind in ('control', 'unknown_control', 'ruby_open', 'ruby_close')]


def validate_controls(source, target):
    """Reject changes to markers, fixed arguments and paired ruby roles."""
    if [m.group() for m in MARKERS.finditer(source)] != [m.group() for m in MARKERS.finditer(target)]:
        raise ValueError('Control sequence changed')
    a = control_signature(tokenize_bytes(text_bytes(source, signature_only=True)))
    b = control_signature(tokenize_bytes(text_bytes(target, True, signature_only=True), True))
    if a != b:
        raise ValueError('Control argument or ruby role changed')


def control_arguments(text):
    """Stable ASCII metadata for actual arguments, excluding visible digits."""
    return [f'{t.code:02X}:{t.argument.hex()}:{t.kind}'
            for t in tokenize_bytes(text_bytes(text, True, signature_only=True), True) if t.argument]


def visible_literal_text(text):
    """Literal body text only; runtime expansions are not counted as known text."""
    return ''.join((BYTES_CHAR[t.data] if t.data in BYTES_CHAR else t.data.decode('cp932'))
                   for t in tokenize_text(text, private_latin=True)
                   if t.kind in ('latin', 'native') and not t.ruby)


def visible_count(tokens):
    """Count literal body glyphs; mark runtime expansions and ruby as uncertain."""
    return dict(literal_body_glyphs=sum(t.kind in ('latin', 'native') and not t.ruby for t in tokens),
                runtime_expansion_present=any(t.code in (1, 2, 3) and t.kind == 'control' for t in tokens),
                ruby_present=any(t.kind == 'ruby_open' for t in tokens),
                unknown_control_present=any(t.kind == 'unknown_control' for t in tokens))
