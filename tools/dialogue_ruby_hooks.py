"""Dry stage3 hook definitions; no executable writer or emulator operations.

Latin ruby uses the existing 4x source bank with the requested 8x8 destination.
Japanese keeps its original 8px font. Association/centering must be supplied
separately; enabling these blocks alone does not fix translated base spans.
"""
from dialogue_vwf_hooks import Block, address, decoder, r
from live_vwf import i, j
import struct

NAME_COUNT_CALLS=(0xEAF4C,0xEAFA4,0xEAFE0,0xEB024)


def name_glyph_units(private_pairs=False):
    """Scoped replacement for four strlen calls followed by division by two.

    A0 unchanged; returns two units per printable ASCII/native two-byte glyph.
    Halfwidth/invalid/overlong input tail-calls original strlen without rewriting.
    """
    h=Block();h.emit(r(4,0,8),i(13,0,2,0),i(13,0,11,0))
    h.label('next');h.emit(i(36,8,9,0));h.branch(4,9,0,'done')
    h.emit(i(11,11,10,128));h.branch(4,10,0,'fallback')
    h.emit(i(11,9,10,32));h.branch(5,10,0,'fallback')
    h.emit(i(11,9,10,127));h.branch(5,10,0,'ascii')
    if private_pairs:
        h.emit(i(13,0,10,128));h.branch(4,9,10,'ascii')
    h.emit(i(11,9,10,129));h.branch(5,10,0,'fallback')
    h.emit(i(11,9,10,160));h.branch(5,10,0,'pair')
    h.emit(i(11,9,10,224));h.branch(5,10,0,'fallback')
    h.emit(i(11,9,10,253));h.branch(4,10,0,'fallback')
    h.label('pair');h.emit(i(11,11,10,127));h.branch(4,10,0,'fallback')
    h.emit(i(36,8,9,1),i(11,9,10,64));h.branch(5,10,0,'fallback')
    h.emit(i(11,9,10,253));h.branch(4,10,0,'fallback')
    h.emit(i(13,0,10,127));h.branch(4,9,10,'fallback')
    h.emit(i(9,8,8,1),i(9,11,11,1))
    h.label('ascii');h.emit(i(9,8,8,1),i(9,11,11,1),i(9,2,2,2));h.branch(4,0,0,'next')
    h.label('done');h.emit(0x03e00008,0)
    h.label('fallback');h.emit(j(0x128B64),0)
    return h.finish()


def association_records(audit,body_widths):
    """Deduplicated translated signatures; source count bytes stay untouched."""
    small=ruby_widths(body_widths);records={}
    for row in audit['rows']:
        if not row['target_base_bytes']:raise ValueError('Unresolved ruby association')
        base=bytes.fromhex(row['target_base_bytes']);gap=bytes.fromhex(row['target_gap_bytes'])
        reading=bytes.fromhex(row['target_reading_bytes']);signature=bytes.fromhex(row['runtime_signature_hex'])
        if any(n<32 or n>=129 or n==127 for n in base+gap+reading):
            raise ValueError('Non-Latin signature needs separate native handling')
        delta=sum(body_widths[n] for n in gap)+sum(body_widths[n] for n in base)//2+sum(small[n] for n in reading)//2
        value=(len(base)+len(gap)+2,len(signature),int(delta),signature)
        if signature in records and records[signature]!=value:raise ValueError('Conflicting ruby signature')
        records[signature]=value
    return sorted(records.values(),key=lambda x:x[3])


def pack_associations(records,address_value):
    """R32 pointer sites returned separately for executable integration review."""
    table=bytearray(16*(len(records)+1));relocations=[]
    for index,(back,length,delta,signature) in enumerate(records):
        ptr=address_value+len(table)
        struct.pack_into('<4I',table,index*16,back,length,delta,ptr)
        relocations.append(address_value+index*16+12);table.extend(signature)
    return bytes(table),relocations


def ruby_center(table):
    """F0D2C two-word replacement. Bounded signature match or native replay.

    S3 is reading start; S0+4 original line start; *S0 current closing delimiter.
    EE974/EE980 initialize cursor/start; F0D18 leaves cursor at closing0F.
    These object bounds need independent review before asset integration.
    """
    h=Block();regs=list(range(8,16))+[24,25]
    h.emit(i(9,29,29,-48))
    for n,reg in enumerate(regs):h.emit(i(43,29,reg,n*4))
    address(h,8,table)
    h.label('entry');h.emit(i(35,8,9,0));h.branch(4,9,0,'native')
    h.emit(i(35,8,10,4),i(35,8,11,8),i(35,8,12,12),r(19,9,13,0x23),i(35,16,14,4),r(13,14,15,0x2b))
    h.branch(5,15,0,'following')
    h.emit(r(13,10,14),i(9,14,14,-1),i(35,16,15,0),r(15,14,24,0x2b))
    h.branch(5,24,0,'following')
    h.label('compare');h.emit(i(36,13,14,0),i(36,12,15,0));h.branch(5,14,15,'following')
    h.emit(i(9,13,13,1),i(9,12,12,1),i(9,10,10,-1));h.branch(5,10,0,'compare')
    h.emit(i(35,16,9,0x30),r(9,11,17,0x23))
    for n,reg in enumerate(regs):h.emit(i(35,29,reg,n*4))
    # Skip native F0D6C subtraction: complete translated displacement applied.
    h.emit(i(9,29,29,48),j(0xF0D70),i(35,16,21,0x34))
    h.label('following');h.emit(i(9,8,8,16));h.branch(4,0,0,'entry')
    h.label('native')
    for n,reg in enumerate(regs):h.emit(i(35,29,reg,n*4))
    h.emit(i(9,29,29,48),r(0,4,5,0,4),j(0xF0D34),r(5,4,5,0x23))
    return h.finish()

RUBY_VISIBLE_RETURNS = (0xF0CF0, 0xF0D98)


def ruby_decoder():
    return decoder(speaker_labels=True, extra_return_gates=RUBY_VISIBLE_RETURNS)


def small_latin_font(max_glyph=129):
    """EA4AC replacement, keeping original MOVE S4,T0 in its branch delay."""
    h=Block()
    # Block.branch inserts NOP; replay native delay MOVE on both paths first.
    h.emit(r(8,0,20))
    h.branch(5,7,9,'large')  # Original BNE A3,T1 (T1=8).
    h.emit(i(11,4,24,32));h.branch(5,24,0,'native_small')
    h.emit(i(11,4,24,max_glyph));h.branch(4,24,0,'native_small')
    h.emit(i(13,0,24,127));h.branch(4,4,24,'native_small')
    h.emit(i(35,29,24,0x20))
    # EE2B0 is native mode0/resident-font drawing, including runtime02 expansion.
    for caller in (0xEE430,0xEE404,0xEE2B0):
        address(h,25,caller);h.branch(4,24,25,'large')
    h.label('native_small');h.emit(j(0xEA4B4),0)
    # Select the Latin-capable large lookup, preserving S3/S4 destination8px.
    h.label('large');h.emit(j(0xEA550),0)
    return h.finish()


def ruby_advance(lut,max_glyph=129):
    """F0DCC branch+delay replacement; never put a jump in a delay slot.

    SP+0 holds the decoded glyph in the native frame.
    """
    h=Block();h.emit(i(37,29,24,0),i(11,24,25,32));h.branch(5,25,0,'native')
    h.emit(i(11,24,25,max_glyph));h.branch(4,25,0,'native')
    h.emit(i(13,0,25,127));h.branch(4,24,25,'native')
    address(h,25,lut);h.emit(r(0,24,24,0,2),r(25,24,25),i(35,25,24,0),
                           r(17,24,17),j(0xF0DDC),0)
    h.label('native');h.emit(j(0xF0DDC),i(9,17,17,8))
    return h.finish()


def ruby_widths(body_widths):
    """Half-size integer advances; same rule must feed centering and drawing."""
    return [0 if n<32 or n==127 else max(1,(int(width)+1)//2)
            for n,width in enumerate(body_widths)]


def plan(body_widths):
    widths=ruby_widths(body_widths)
    return dict(decoder_extra_visible_returns=list(map(hex,RUBY_VISIBLE_RETURNS)),
                decoder_bytes=len(ruby_decoder()),small_font_site='0xea4ac',
                small_font_block_bytes=len(small_latin_font()),
                advance_site='0xf0dcc',advance_replacement_words=2,
                advance_block_bytes=len(ruby_advance(0x1740000)),
                latin_ruby_advance_lut=widths,requested_destination_px=[8,8],
                original_japanese_small_font_preserved=True,
                center_site='0xf0d2c',center_replacement_words=2,
                center_block_bytes=len(ruby_center(0x1760000)),
                name_count_calls=list(map(hex,NAME_COUNT_CALLS)),
                name_count_block_bytes=len(name_glyph_units()),
                centering_ready=True,association_ledger_required=True,
                object_bounds_need_independent_review=True,
                runtime_verified=False)


def main():
    """Read-only plan against reviewed .12; no output files or emulator access."""
    import hashlib,json
    from pathlib import Path
    from audit_ruby_spans import audit
    data=Path('work/output/0.1.12-dialogue-assets/EBOOT.BIN').read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if digest!='3d2271c1e91fc8198886ed0d81922d0ff48d1217076a5340d6ddf5fc07648da5':
        raise ValueError('Expected reviewed .12 executable')
    ph=struct.unpack_from('<I',data,28)[0]
    offset=struct.unpack_from('<I',data,ph+68)[0]
    body=[round(n) for n in struct.unpack_from('<129f',data,offset+0x800)]
    associations=audit();records=association_records(associations,body)
    packed,rel=pack_associations(records,0x1760000)
    result=plan(body);result.pop('latin_ruby_advance_lut')
    result.update(input_sha256=digest,ruby_spans=associations['ruby_spans'],
                  association_counts=associations['counts'],unique_signatures=len(records),
                  ledger_bytes=len(packed),ledger_R32_relocations=len(rel),
                  sample=[dict(back=n,length=l,displacement_px=d,signature=s.hex())
                          for n,l,d,s in records[:6]],
                  limitations=['No native runtime-expansion pixel measurement.',
                               'No automatic wrapping or global panel-capacity claim.',
                               'Mode0 8px glyph visibility is scoped; its body advance needs runtime QA.',
                               'Unknown ruby signatures retain original centering.',
                               'Halfwidth/invalid/overlong name counts retain original strlen.'])
    print(json.dumps(result,indent=2))
    print('DRY RUN: no drafts, assets, or emulator memory written.')


if __name__=='__main__':main()
