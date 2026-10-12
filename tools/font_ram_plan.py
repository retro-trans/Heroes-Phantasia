"""Read-only .16 font RAM proposal and bounded raw LZ4 model. No asset writer."""
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from live_vwf import FONT, swizzle

SOURCE = Path('work/output/0.1.15-dialogue-assets/EBOOT.BIN')
SHA = '378649b06adc9427f6208bed57be92a6f791eddc04de40019bf1f2087e6630b2'


def raster_glyph(char):
    font = ImageFont.truetype(str(FONT),64)
    im = Image.new('L',(64,64))
    ImageDraw.Draw(im).text((0,48),char,font=font,anchor='ls',fill=255)
    values = list(im.get_flattened_data())
    return bytes(swizzle(bytes((values[n]//17)|((values[n+1]//17)<<4)
                              for n in range(0,len(values),2)),pitch=32))


def extension(n):
    out = bytearray()
    while n >= 255:
        out.append(255); n -= 255
    out.append(n)
    return out


def encode(data):
    out = bytearray(); seen = {}; anchor = pos = 0
    while pos+4 <= len(data):
        key = data[pos:pos+4]; prior = seen.get(key); seen[key] = pos
        if prior is None or not 0 < pos-prior <= 65535:
            pos += 1; continue
        stop = pos+4
        while stop < len(data) and data[prior+stop-pos] == data[stop]:
            stop += 1
        literal = pos-anchor; match = stop-pos-4
        out.append(min(literal,15)*16+min(match,15))
        if literal >= 15: out.extend(extension(literal-15))
        out.extend(data[anchor:pos]); out.extend(struct.pack('<H',pos-prior))
        if match >= 15: out.extend(extension(match-15))
        for n in range(pos+1, stop):
            if n+4 <= len(data): seen[data[n:n+4]] = n
        anchor = pos = stop
    literal = len(data)-anchor
    out.append(min(literal,15)*16)
    if literal >= 15: out.extend(extension(literal-15))
    out.extend(data[anchor:])
    return bytes(out)


def decode(data, expected):
    """Every input lookahead and output count is guarded before access/write."""
    pos = 0; out = bytearray()
    def length(n):
        nonlocal pos
        if n != 15: return n
        while True:
            if pos == len(data): raise ValueError('Truncated extended length')
            value = data[pos]; pos += 1; n += value
            if n > expected: raise ValueError('Length exceeds destination')
            if value != 255: return n
    while pos < len(data):
        token = data[pos]; pos += 1; n = length(token >> 4)
        if n > len(data)-pos or n > expected-len(out):
            raise ValueError('Literal exceeds input/destination')
        out.extend(data[pos:pos+n]); pos += n
        if pos == len(data): break
        if len(data)-pos < 2: raise ValueError('Truncated match distance')
        distance = data[pos] | data[pos+1] << 8; pos += 2
        if distance == 0 or distance > len(out): raise ValueError('Invalid distance')
        n = length(token & 15)+4
        if n > expected-len(out): raise ValueError('Match exceeds destination')
        for _ in range(n): out.append(out[-distance])
    if len(out) != expected: raise ValueError('Output length mismatch')
    return bytes(out)


def build():
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA: raise ValueError('Frozen input changed')
    report = json.loads(SOURCE.with_name('setup_patch.en.json').read_text())
    ph = struct.unpack_from('<8I',raw,116)
    start = ph[1]+report['high_bank']-ph[2]
    bank = raw[start:start+report['high_bank_bytes']]
    if hashlib.sha256(bank).hexdigest() != report['high_bank_sha256']:
        raise ValueError('Font bank changed')
    packed = encode(bank)
    assert decode(packed,len(bank)) == bank
    glyph = raster_glyph
    for code, offset in report['high_glyph_offsets'].items():
        assert bank[offset:offset+2048] == glyph('\u00e8' if int(code)==128 else chr(int(code)))
    extended_bank = bank+glyph('\u00e1')+glyph('\u00e9')
    extended_packed = encode(extended_bank)
    assert decode(extended_packed,len(extended_bank)) == extended_bank
    cases = []
    for sample in (b'',b'A',b'A'*2048,bytes(range(256))*256,b'ABC'*16384):
        assert decode(encode(sample),len(sample)) == sample
        cases.append({'bytes':len(sample),'roundtrip':True})
    bad = [(b'\xF0',1),(b'\x20A',2),(b'\x10A\x00\x00',5),
           (b'\x10A\x02\x00',5),(b'\x1FA\x01\x00',100),
           (b'\x10A\x01\x00',4),(b'\x10A',2)]
    for encoded,count in bad:
        try: decode(encoded,count)
        except ValueError: cases.append({'malformed_hex':encoded.hex(),'rejected':True})
        else: raise AssertionError('Malformed stream accepted')
    projected = report['payload_bytes']-len(bank)+len(packed)
    return dict(status='dry_proposal_not_native_decoder',source_sha256=SHA,
        original_font_bytes=len(bank),compressed_bytes=len(packed),
        decoded_sha256=hashlib.sha256(bank).hexdigest(),
        compressed_sha256=hashlib.sha256(packed).hexdigest(),
        accent_extension=dict(private_glyph_ids={'128':'U+00E8','129':'U+00E1','130':'U+00E9'},
            encoded_bytes_not_approved=True, original_96_glyphs_raster_exact=True,
            raster_font=str(FONT),raster_font_sha256=hashlib.sha256(Path(FONT).read_bytes()).hexdigest(),
            bank_bytes=len(extended_bank),compressed_bytes=len(extended_packed),
            decoded_sha256=hashlib.sha256(extended_bank).hexdigest(),
            compressed_sha256=hashlib.sha256(extended_packed).hexdigest(),
            projected_payload_before_decoder=report['payload_bytes']-len(bank)+len(extended_packed),
            notes=['Glyph IDs129/130 cannot be raw CP932 lead bytes.',
                   'A reviewed private escape grammar and decoder/count/advance changes are needed.',
                   'All original glyph offsets/pixels retained; new glyphs appended.']),
        projected_payload_before_decoder=projected,
        recovery_before_decoder=len(bank)-len(packed),
        headroom_over_observed_fpl_deficit=len(bank)-len(packed)-133376,
        cases=cases, native_pool=dict(initializer_rva='0xB90',startup_call_rva='0xFEC',
            allocate_rva='0xC70',free_rva='0xCA0',alignment=64,
            descriptor_rva='0x16F5540',start_offset=0xCC000,end_offset=0x200000,
            backup_restore_rvas=['0x6174','0x4D674']),
        hook_plan=['Replace static high-bank address construction with load from owned payload state.',
            'Initialize after native VRAM pool and before first high glyph; allocate once through C70.',
            'Bound decode by compressed end and exact188928-byte destination, then publish pointer.',
            'Preserve all lookup offsets/native fallback descriptors and original palette.',
            'Handle allocation/decode failure explicitly; no partial pointer publication.'],
        outstanding=['Native decoder instruction tests/relocations not implemented.',
            'Actual free contiguous VRAM and worst-case texture demand across scenes unverified.',
            'Initialization thread/lifetime and failure behavior require independent review.',
            'New executable translations consume remaining RAM headroom.',
            'No emulator access, executable preparation, archive or ISO writes.'])


if __name__ == '__main__':
    print(json.dumps(build(),indent=2))
