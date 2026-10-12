"""Bounded physical line wrap for the reviewed formation tutorial.

Logical translations retain every original control. Only one existing ASCII
space becomes a physical 11 line fence; the ledger reverses that edit exactly.
No asset writer. Native four-line layout and runtime geometry need validation.
"""
import hashlib
import struct
from pathlib import Path
from dialogue_tokens import tokenize_bytes, control_signature

ROW_ID = '145dcee8cbe76518230a'
LOGICAL_SHA = '70d48788a1d90ad94bf1ebab15f979751466009f8867d2a409e74f0c03914ec3'
RESOURCES = frozenset(('btl/skit/s999910.bin', 'btl/skit/s999911.bin'))
OLD = b'Front-row characters in the back row and back-row characters in the front row'
NEW = b'Front-row characters in the back row and\x11back-row characters in the front row'

def widths_input():
    from executable_text_patch import Elf
    path = Path('work/output/0.1.19-dialogue-assets/EBOOT.BIN')
    raw = path.read_bytes()
    if sha(raw) != '401c720c9a76e8d89112c9026f5620e0bb0c20217a5753ab15f4c67aed3c33f3':
        raise ValueError('Reviewed body LUT executable changed')
    elf = Elf(raw)
    table = raw[elf.file_offset(3031040, 524):elf.file_offset(3031040, 524)+524]
    return struct.unpack('<131I', table), [dict(path=str(path), sha256=sha(raw)),
        dict(path=str(Path(__file__)), sha256=sha(Path(__file__).read_bytes()))]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def prepare(resource, row_id, target, encoded, widths):
    if resource not in RESOURCES or row_id != ROW_ID:
        return encoded, None
    if sha(target.encode('utf8')) != LOGICAL_SHA or encoded.count(OLD) != 1:
        raise ValueError('Reviewed formation target changed')
    if not encoded.startswith(b'\x1a6') or not encoded.endswith(b'\x12\x0e'):
        raise ValueError('Reviewed formation mode/fences changed')
    position = encoded.index(OLD) + OLD.index(b' and ') + len(b' and')
    if encoded[position] != 32:
        raise ValueError('Formation wrap is not an existing space')
    result = encoded[:position] + b'\x11' + encoded[position+1:]
    if NEW not in result or result[:position] + b' ' + result[position+1:] != encoded:
        raise ValueError('Physical wrap cannot reconstruct exact logical bytes')
    old_tokens = tokenize_bytes(encoded, private_latin=True)
    new_tokens = tokenize_bytes(result, private_latin=True)
    stripped = [t for t in new_tokens if t.offset != position]
    if control_signature(old_tokens) != control_signature(stripped):
        raise ValueError('Original logical control/argument sequence changed')
    lines = result[2:-2].split(b'\x11')
    if len(lines) != 4 or any(any(c < 32 or c > 126 for c in line) for line in lines):
        raise ValueError('Formation must have four literal ASCII body lines')
    advances = [sum(widths[c] for c in line) for line in lines]
    if max(advances) > 464:
        raise ValueError('Formation physical lines exceed reviewed width')
    return result, dict(policy='formation_existing_space_to_physical_line_fence',
        logical_sha256=sha(encoded), physical_sha256=sha(result),
        replaced_byte_offset=position, original_byte_hex='20', physical_byte_hex='11',
        original_controls_and_arguments_exact_after_undo=True,
        all_words_and_punctuation_exact_after_undo=True,
        original_line_count=3, physical_line_count=4, line_advances_px=advances,
        width_limit_px=464, runtime_verified=False)
