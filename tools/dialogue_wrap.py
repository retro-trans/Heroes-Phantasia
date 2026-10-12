"""Dry bounded virtual-row plans; source/control bytes are never rewritten.

Geometry is an explicit caller-proven input, not a global screen-width guess.
Native integration must update reveal caps, subsequent-row positions and page
height atomically; this planner alone does not install runtime wrapping.
"""
from dialogue_tokens import tokenize_bytes

NEUTRAL={0x05,0x16,0x17}


def literal_reveal_cap(ruby=False, terminal_room=False, private_pairs=False):
    """Dry EE984 two-word replacement; validated Latin count or native45.

    EE968 input A3 is EAD20's glyph count. Reject mismatches/unhandled tokens
    before replacing the cap; no line allocation or page geometry is changed.
    """
    from dialogue_vwf_hooks import Block,r
    from live_vwf import i,j
    h=Block();h.emit(i(9,29,29,-32))
    for n,reg in enumerate(range(8,16)):h.emit(i(43,29,reg,n*4))
    h.emit(r(6,0,8),i(13,0,9,0),i(13,0,10,0))
    h.label('next');h.emit(i(11,9,12,1025));h.branch(4,12,0,'native')
    h.emit(i(36,8,11,0));h.branch(4,11,0,'complete')
    for stop in (0x0e,0x10,0x11,0x12):
        h.emit(i(13,0,12,stop));h.branch(4,11,12,'complete')
    h.emit(i(11,9,12,1024));h.branch(4,12,0,'native')
    h.emit(i(11,11,12,32));h.branch(5,12,0,'control')
    if private_pairs:
        h.emit(i(13,0,12,0xf0));h.branch(4,11,12,'private_body')
    h.emit(i(11,11,12,129));h.branch(4,12,0,'native')
    h.emit(i(13,0,12,127));h.branch(4,11,12,'native')
    h.emit(i(9,10,10,1),i(9,8,8,1),i(9,9,9,1));h.branch(4,0,0,'next')
    if private_pairs:
        h.label('private_body');h.emit(i(11,9,12,1023));h.branch(4,12,0,'native')
        h.emit(i(36,8,13,1),i(9,13,13,-0x40),i(11,13,12,2));h.branch(4,12,0,'native')
        h.emit(i(9,10,10,1),i(9,8,8,2),i(9,9,9,2));h.branch(4,0,0,'next')
    h.label('control')
    if ruby:
        h.emit(i(13,0,12,0x0f));h.branch(4,11,12,'ruby')
    for code,n in ((5,3),(0x16,2),(0x17,1)):
        h.emit(i(13,0,12,code));h.branch(4,11,12,f'arg{n}')
    h.branch(4,0,0,'native')
    for n in (1,2,3):
        h.label(f'arg{n}');h.emit(i(11,9,12,1024-n));h.branch(4,12,0,'native')
        for offset in range(1,n+1):
            h.emit(i(36,8,13,offset),i(9,13,13,-48),i(11,13,12,10));h.branch(4,12,0,'native')
        h.emit(i(9,8,8,n+1),i(9,9,9,n+1));h.branch(4,0,0,'next')
    if ruby:
        h.label('ruby');h.emit(i(11,9,12,1023));h.branch(4,12,0,'native')
        h.emit(i(36,8,13,1),i(9,13,13,-48),i(11,13,12,10));h.branch(4,12,0,'native')
        h.emit(i(9,8,8,2),i(9,9,9,2))
        h.label('reading');h.emit(i(11,9,12,1024));h.branch(4,12,0,'native')
        h.emit(i(36,8,13,0),i(13,0,12,0x0f));h.branch(4,13,12,'close_ruby')
        h.emit(i(11,13,12,32));h.branch(5,12,0,'native')
        if private_pairs:
            h.emit(i(13,0,12,0xf0));h.branch(4,13,12,'private_reading')
        h.emit(i(11,13,12,129));h.branch(4,12,0,'native')
        h.emit(i(13,0,12,127));h.branch(4,13,12,'native')
        h.emit(i(9,8,8,1),i(9,9,9,1));h.branch(4,0,0,'reading')
        if private_pairs:
            h.label('private_reading');h.emit(i(11,9,12,1023));h.branch(4,12,0,'native')
            h.emit(i(36,8,13,1),i(9,13,13,-0x40),i(11,13,12,2));h.branch(4,12,0,'native')
            h.emit(i(9,8,8,2),i(9,9,9,2));h.branch(4,0,0,'reading')
        h.label('close_ruby');h.emit(i(9,8,8,1),i(9,9,9,1));h.branch(4,0,0,'next')
    h.label('complete');h.branch(5,10,7,'native');h.branch(4,10,0,'native')
    if terminal_room:
        # Native reveal replays from the row start. It must reach the next
        # control (11/12/0E/NUL), whose dispatcher stops before later text.
        # Preserve native short-row capacity; grow long rows by one slot.
        h.emit(i(11,10,12,45));h.branch(5,12,0,'native')
        h.emit(i(9,10,6,1))
    else:
        h.emit(r(10,0,6))
    h.branch(4,0,0,'return')
    h.label('native');h.emit(i(13,0,6,45))
    h.label('return')
    for n,reg in enumerate(range(8,16)):h.emit(i(35,29,reg,n*4))
    h.emit(i(9,29,29,32),j(0xEE98C),i(43,17,30,8))
    return h.finish()


def plan_line(data,widths,available_px,capacity_rows,max_bytes=1024):
    """Return an all-or-nothing row map or a native fallback reason.

    Each rendered glyph retains its original byte offset. Spaces at a wrap
    boundary stay in the source/reveal sequence and receive zero visual advance.
    Runtime expansions/ruby/native mixed input require separate verified plans.
    """
    def fallback(reason):return dict(supported=False,reason=reason,source_rewritten=False)
    if not 1<=available_px<=480 or not 1<=capacity_rows<=32:
        return fallback('Unverified geometry or capacity')
    if len(data)>max_bytes:return fallback('Source exceeds bounded probe')
    try:tokens=tokenize_bytes(data,private_latin=True)
    except (ValueError,UnicodeError):return fallback('Malformed or unsupported atomic token stream')
    glyphs=[]
    for t in tokens:
        if t.kind=='latin' and not t.ruby:
            glyphs.append(dict(offset=t.offset,code=t.code,width=int(widths[t.code])))
        elif t.kind=='control' and t.code in NEUTRAL:pass
        else:return fallback('Runtime, ruby, native or other control needs verified expansion plan')
    if not glyphs:return dict(supported=True,rows=[],glyph_count=0,source_rewritten=False)
    rows=[];start=0
    while start<len(glyphs):
        used=0;end=start;last_space=None
        while end<len(glyphs) and used+glyphs[end]['width']<=available_px:
            used+=glyphs[end]['width']
            if glyphs[end]['code']==32:last_space=end
            end+=1
        if end==start:return fallback('One glyph exceeds destination width')
        # Prefer the last complete-word boundary. Long words split by glyph.
        if end<len(glyphs) and last_space is not None and last_space>=start:
            end=last_space+1
        row=[];x=0
        for n in range(start,end):
            g=glyphs[n];advance=g['width']
            if n==end-1 and end<len(glyphs) and g['code']==32:advance=0
            row.append(dict(byte_offset=g['offset'],code=g['code'],x=x,advance=advance))
            x+=advance
        rows.append(dict(width=x,glyphs=row))
        if len(rows)>capacity_rows:return fallback('Wrapped text exceeds proven page capacity')
        start=end
    assert [g['byte_offset'] for r in rows for g in r['glyphs']]==[g['offset'] for g in glyphs]
    assert all(r['width']<=available_px for r in rows)
    return dict(supported=True,rows=rows,glyph_count=len(glyphs),
                additional_rows=len(rows)-1,source_rewritten=False,
                controls_and_arguments_preserved=True,runtime_verified=False)
