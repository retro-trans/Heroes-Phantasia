"""Dry scoped tutorial heading measurement; no assets or runtime writes."""
from dialogue_vwf_hooks import Block,address,r
from live_vwf import i,j
from font_vram_hooks import instruction_model


def title_width(lut):
    """A0 unchanged; V0=highbit|pixelwidth or native strlen for JP/unknown.

    Bounded256-byte literal probe. Existing controls/runtime strings keep native
    behavior. Tagged S2 is scoped to the reviewed tutorial category/detail flow.
    """
    h=Block();h.emit(r(4,0,8),i(13,0,9,0),i(13,0,10,0));address(h,12,lut)
    h.label('next');h.emit(i(11,9,13,257));h.branch(4,13,0,'native')
    h.emit(i(36,8,11,0));h.branch(4,11,0,'done')
    h.emit(i(11,9,13,256));h.branch(4,13,0,'native')
    h.emit(i(13,0,13,0xf0));h.branch(4,11,13,'pair')
    h.emit(i(11,11,13,32));h.branch(5,13,0,'native')
    h.emit(i(11,11,13,129));h.branch(4,13,0,'native')
    h.emit(i(13,0,13,127));h.branch(4,11,13,'native')
    h.emit(i(9,8,8,1),i(9,9,9,1));h.branch(4,0,0,'add')
    h.label('pair');h.emit(i(11,9,13,255));h.branch(4,13,0,'native')
    h.emit(i(36,8,11,1),i(9,11,13,-0x40),i(11,13,13,2));h.branch(4,13,0,'native')
    h.emit(i(9,11,11,65),i(9,8,8,2),i(9,9,9,2))
    h.label('add');h.emit(r(0,11,13,0,2),r(12,13,13),i(35,13,13,0),i(11,13,14,65))
    h.branch(4,14,0,'native');h.emit(r(10,13,10));h.branch(4,0,0,'next')
    h.label('done');h.emit(i(13,0,2,1),r(0,2,2,0,31),r(2,10,2,0x25),0x03e00008,0)
    h.label('native');h.emit(j(0x128b64),0)
    return h.finish()


CENTERS={0x94040:0x9407c,0x941a0:0x941dc,0x942e4:0x94320}
STRLEN_CALLS=(0x94038,0x94198,0x942dc,0x94464,0x944ac,0x944d8)


def center(entry=0x94040):
    if entry not in CENTERS:raise ValueError('Unreviewed heading branch')
    h=Block();h.emit(r(2,0,18),r(18,0,24,0x2a));h.branch(4,24,0,'native')
    h.emit(r(0,18,4,0,1),r(0,4,4,2,1),r(0,4,4,2,1),i(13,0,5,240),r(5,4,4,0x23),j(CENTERS[entry]),0)
    h.label('native');h.emit(r(0,18,4,3,1),j(entry+8),0)
    return h.finish()


def trailing_icon():
    h=Block();h.emit(r(18,0,24,0x2a));h.branch(4,24,0,'native')
    h.emit(r(0,18,4,0,1),r(0,4,4,2,1),j(0x943c8),0)
    h.label('native');h.emit(r(0,18,4,3,1),r(0,4,4,2,31),j(0x943b0),0)
    return h.finish()


def detail_center():
    """S2 tag -> actual pixel width; preserve A0 category and native F20 setup.

    Positive S2 keeps the original signed rounding path at944EC..944F4.
    Native94520 assigns computed center toF20;94618 later uses S2 full width.
    """
    h=Block();h.emit(r(18,0,24,0x2a));h.branch(4,24,0,'native')
    h.emit(r(0,18,18,0,1),r(0,18,18,2,1),r(0,18,5,2,1),i(13,0,6,240),r(6,5,5,0x23),j(0x94520),0)
    h.label('native');h.emit(r(0,5,5,2,31),r(18,5,5),j(0x944f4),0)
    return h.finish()


def menu_advance(lut):
    """Scoped88270: same integer LUT as title_width; native F26 fallback.

    Preserve T8/T9/F0 and replay original branch continuation881D8. The glyph
    is the same decoded halfword at callerSP+8 used by native88224/88254.
    """
    h=Block();h.emit(i(9,29,29,-16),i(43,29,24,0),i(43,29,25,4),i(57,29,0,8),i(37,29,24,24))
    h.emit(i(11,24,25,32));h.branch(5,25,0,'native')
    h.emit(i(11,24,25,131));h.branch(4,25,0,'native')
    h.emit(i(13,0,25,127));h.branch(4,24,25,'native')
    address(h,25,lut);h.emit(r(0,24,24,0,2),r(25,24,25),i(35,25,24,0),0x44980000,0x46800020,0x4600b580)
    h.branch(4,0,0,'done');h.label('native');h.emit(0x461ab580)
    h.label('done');h.emit(i(49,29,0,8),i(35,29,24,0),i(35,29,25,4),j(0x881d8),i(9,29,29,16))
    return h.finish()


def cases():
    scope=instruction_model()
    widths=[0]*131
    for n in range(32,127):widths[n]=5+n%5
    widths[128:]=[8,9,7]
    results=[]
    for raw,expected in [(b'A',widths[65]),(b'Cinq Fl\x80ches',sum(widths[x]for x in b'Cinq Fl\x80ches')),
                         (b'Guaruj\xf0\x40',sum(widths[x]for x in b'Guaruj')+9),(b'lyc\xf0\x41e',sum(widths[x]for x in b'lyce')+7),
                         (b'\x82\x60',None),(b'A\x172',None),(b'A\x7f',None),(b'A\xf0\x42',None),
                         (b'A'*254+b'\xf0\x40',254*widths[65]+9),(b'A'*255+b'\xf0\x40',None)]:
        regs=[0]*32;regs[4]=0x200000;regs[31]=0xdeadbeec;mem={0x200000+n:x for n,x in enumerate(raw+b'\0')}
        import struct
        mem.update({0x210000+n:x for n,x in enumerate(struct.pack('<131I',*widths))})
        pc,out,reads=scope['execute'](title_width(0x210000),regs,mem)
        assert out[4]==0x200000 and pc==(0x128b64 if expected is None else 0xdeadbeec)
        if expected is not None:assert out[2]==0x80000000|expected
        assert max(x for x in reads if 0x200000<=x<0x210000)<=0x200000+min(len(raw),256)
        results.append(dict(source_bytes=len(raw),pixel_width=expected,passed=True))
    placement=[]
    for width in (0,1,13,73,240,479):
        regs=[0]*32;regs[2]=0x80000000|width
        for entry,continuation in CENTERS.items():
            pc,out,_=scope['execute'](center(entry),regs,{})
            assert pc==continuation and out[4]==(240-(width>>1))&0xffffffff and out[18]==regs[2]
        pc,out,_=scope['execute'](trailing_icon(),out,{})
        assert pc==0x943c8 and out[4]==width
        regs[18]=regs[2];regs[4]=7;regs[5]=regs[18]>>1
        pc,detail,_=scope['execute'](detail_center(),regs,{})
        assert pc==0x94520 and detail[18]==width and detail[5]==(240-(width>>1))&0xffffffff and detail[4]==7
        placement.append(dict(width=width,center=240-(width>>1),trailing=width,passed=True))
    for length in (0,2,8,20):
        regs=[0]*32;regs[2]=length
        for entry in CENTERS:
            pc,out,_=scope['execute'](center(entry),regs,{})
            assert pc==entry+8 and out[4]==length>>1 and out[18]==length
        pc,out,_=scope['execute'](trailing_icon(),out,{})
        assert pc==0x943b0 and out[4]==0
        regs[18]=length;regs[5]=length>>1;regs[4]=7
        pc,detail,_=scope['execute'](detail_center(),regs,{})
        assert pc==0x944f4 and detail[5]==length and detail[4]==7 and detail[18]==length
    return dict(measurement_cases=results,placement_cases=placement,native_positive_length_replay_cases=4,
                menu_advance_cases=advance_cases(),scoped_decoder_route_cases=decoder_route_cases(),
                actual_emitted_instructions_executed=True,
                category_branches_tested=list(CENTERS),detail_branch_tested=True,
                code_bytes=dict(width=len(title_width(0x210000)),center=len(center()),trailing=len(trailing_icon()),detail=len(detail_center())),no_assets_written=True)


def advance_cases():
    """Execute the scoped persisted instructions including single-precision FPU."""
    import struct
    result=[];code=menu_advance(0x210000);words=struct.unpack('<%dI'%(len(code)//4),code)
    for glyph in (0,31,32,65,126,127,128,129,130,131,0x8260):
        regs=[0]*32;regs[29]=0x220000;regs[24]=0x12345678;regs[25]=0x87654321
        f=[0]*32;f[0]=struct.unpack('<I',struct.pack('<f',17.25))[0];f[22]=struct.unpack('<I',struct.pack('<f',83.5))[0];f[26]=struct.unpack('<I',struct.pack('<f',13.))[0]
        mem={0x220008+n:b for n,b in enumerate(struct.pack('<H',glyph))}
        mem.update({0x210000+n:b for n,b in enumerate(struct.pack('<131I',*[0]*32,*[7]*95,0,8,9,6))})
        pc=0x1750000;pending=None
        for _ in range(100):
            if not 0x1750000<=pc<0x1750000+len(code):break
            w=words[(pc-0x1750000)//4];op=w>>26;s=w>>21&31;t=w>>16&31;d=w>>11&31;v=w&65535;sv=v if v<32768 else v-65536;nextjump=None
            if op==0:
                if w&63==0:regs[d]=regs[t]<<((w>>6)&31)
                elif w&63==33:regs[d]=regs[s]+regs[t]
                else:raise ValueError('Unmodelled R instruction')
            elif op==9:regs[t]=regs[s]+sv
            elif op==11:regs[t]=int(regs[s]<(sv&0xffffffff))
            elif op==13:regs[t]=regs[s]|v
            elif op==15:regs[t]=v<<16
            elif op in (35,37,49):
                a=(regs[s]+sv)&0xffffffff;n=2 if op==37 else 4;x=int.from_bytes(bytes(mem[a+k]for k in range(n)),'little')
                if op==49:f[t]=x
                else:regs[t]=x
            elif op in (43,57):
                a=(regs[s]+sv)&0xffffffff;x=regs[t]if op==43 else f[t]
                mem.update({a+k:b for k,b in enumerate(struct.pack('<I',x))})
            elif op in (4,5):
                if (regs[s]==regs[t])==(op==4):nextjump=pc+4+sv*4
            elif op==2:nextjump=((pc+4)&0xf0000000)|(w&0x3ffffff)*4
            elif op==17:
                fd=w>>6&31
                if s==4:f[d]=regs[t]
                elif s==20 and w&63==32:f[fd]=struct.unpack('<I',struct.pack('<f',struct.unpack('<i',struct.pack('<I',f[d]))[0]))[0]
                elif s==16 and w&63==0:f[fd]=struct.unpack('<I',struct.pack('<f',struct.unpack('<f',struct.pack('<I',f[d]))[0]+struct.unpack('<f',struct.pack('<I',f[t]))[0]))[0]
                else:raise ValueError('Unmodelled FPU instruction')
            else:raise ValueError('Unmodelled opcode')
            regs=[x&0xffffffff for x in regs];regs[0]=0;pc=pending if pending is not None else pc+4;pending=nextjump
        advance=7 if 32<=glyph<=126 else {128:8,129:9,130:6}.get(glyph,13)
        assert pc==0x881d8 and regs[29]==0x220000 and regs[24]==0x12345678 and regs[25]==0x87654321
        assert f[0]==struct.unpack('<I',struct.pack('<f',17.25))[0]and struct.unpack('<f',struct.pack('<I',f[22]))[0]==83.5+advance
        result.append(dict(glyph=glyph,advance=advance,passed=True))
    return result


def decoder_route_cases():
    from dialogue_vwf_hooks import decoder,route
    scope=instruction_model();results=[]
    for glyph in (0,31,32,65,126,127,128,129,130,131,0x8260,0xf040,0xf041):
        regs=[0]*32;regs[6]=0x210000;regs[29]=0x220000;regs[31]=0x881e8;regs[2]=0
        mem={0x210000+n:b for n,b in enumerate(glyph.to_bytes(2,'little'))}
        pc,out,_=scope['execute'](decoder(True,(0x881e8,),True),regs,mem)
        decoded={0xf040:129,0xf041:130}.get(glyph,glyph)
        assert pc==0x881e8 and out[29]==0x220000
        assert int.from_bytes(bytes(mem[0x210000+n]for n in range(2)),'little')==decoded
        visible=32<=decoded<131 and decoded!=127
        assert out[2]==int(visible)
        for native in (0xe9918,0xeab10):
            regs=[0]*32;regs[9]=decoded
            pc,out,_=scope['execute'](route(native,131),regs,{})
            assert pc==(0xea45c if visible else native)and out[9]==decoded
        results.append(dict(source_glyph=glyph,decoded_glyph=decoded,latin_visible=visible,native_fallback=not visible,passed=True))
    return results
