"""Explicit candidate-only accent codec; native CP932 lead bytes are preserved.

IDs129/130 are decoded glyph IDs, never byte values. F040/F041 are syntactically
valid CP932 private-use glyphs with native two-byte advance. Existing source
assets must be audited for collisions before installing any global remapping.
"""
CHAR_BYTES={'\u00e8':b'\x80','\u00e1':b'\xf0\x40','\u00e9':b'\xf0\x41'}
BYTES_CHAR={value:key for key,value in CHAR_BYTES.items()}
CHAR_GLYPH={'\u00e8':128,'\u00e1':129,'\u00e9':130}
PAIR_GLYPH={0xf040:129,0xf041:130}
GLYPH_CODES=list(range(32,127))+[128,129,130]


def encode_character(char):
    return CHAR_BYTES.get(char) or char.encode('cp932',errors='strict')


def decode_bytes(data):
    """Inspect matching candidate bytes without rewriting unknown CP932 glyphs."""
    out=[];pos=0
    while pos<len(data):
        first=data[pos];size=2 if 0x81<=first<=0x9f or 0xe0<=first<=0xfc else 1
        glyph=data[pos:pos+size]
        if len(glyph)!=size:raise ValueError('Truncated CP932 glyph')
        out.append(BYTES_CHAR[glyph] if glyph in BYTES_CHAR else glyph.decode('cp932',errors='strict'))
        pos+=size
    return ''.join(out)


def cases():
    for text in ('Cinq Fl\u00e8ches','Guaruj\u00e1','lyc\u00e9e','A\u00e1B\u00e9C\u00e8','\u6e21\u00e1\u8fba'):
        raw=b''.join(encode_character(c) for c in text)
        assert decode_bytes(raw)==text
    assert '\u00e1'.encode('cp932',errors='replace')!=CHAR_BYTES['\u00e1']
    assert b'\x81\x40'.decode('cp932')==decode_bytes(b'\x81\x40')
    assert b'\x82\x60'.decode('cp932')==decode_bytes(b'\x82\x60')
    return dict(roundtrips=5,native_leads_preserved=True,raw129_130_never_emitted=True,
                model='cp932-pua-f040-f041-v1',runtime_verified=False)
