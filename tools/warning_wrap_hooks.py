"""Dry warning span scanner: emitted MIPS and instruction-model checks only.

The complete four-line preflight/draw wrapper is deliberately not installed.
This leaf scanner returns a byte span and exact pixel width for one visual line.
"""
import struct
from dialogue_vwf_hooks import Block, r
from live_vwf import i, j, jal
from dialogue_vwf_hooks import address
from font_vram_hooks import instruction_model


def span_scanner():
    """A0=text, A1=integer width LUT, A2=pixel limit, A3=readable byte bound.

    V0=span bytes excluding NUL, V1=pixels, T9=1 supported / 0 fallback.
    Never writes memory or changes A/S/SP/RA registers. Maximum span95bytes
    permits a reused96-byte NUL-terminated drawing scratch. A caller must
    preflight every remaining span before rendering anything.
    """
    h=Block();h.emit(i(13,0,8,0),i(13,0,9,0),i(13,0,10,0),i(13,0,11,0))
    h.label('next');h.emit(r(8,7,15,0x2b));h.branch(4,15,0,'fail')
    h.emit(r(4,8,15),i(36,15,12,0));h.branch(4,12,0,'done')
    h.emit(i(13,0,13,1),i(13,0,15,0x82));h.branch(4,12,15,'digit')
    h.emit(i(13,0,15,0xf0));h.branch(4,12,15,'pair')
    h.emit(i(11,12,15,32));h.branch(5,15,0,'fail')
    h.emit(i(11,12,15,129));h.branch(4,15,0,'fail')
    h.emit(i(13,0,15,127));h.branch(4,12,15,'fail')
    h.branch(4,0,0,'lut')
    h.label('digit');h.emit(i(9,8,15,1),r(15,7,15,0x2b));h.branch(4,15,0,'fail')
    h.emit(r(4,8,15),i(36,15,14,1),i(9,14,14,-0x4f),i(11,14,15,10))
    h.branch(4,15,0,'fail');h.emit(i(13,0,13,2),i(13,0,14,13));h.branch(4,0,0,'width')
    h.label('pair');h.emit(i(9,8,15,1),r(15,7,15,0x2b));h.branch(4,15,0,'fail')
    h.emit(r(4,8,15),i(36,15,12,1),i(9,12,12,-0x40),i(11,12,15,2))
    h.branch(4,15,0,'fail');h.emit(i(9,12,12,129),i(13,0,13,2))
    h.label('lut');h.emit(r(0,12,15,0,2),r(5,15,15),i(35,15,14,0),i(11,14,15,65))
    h.branch(4,15,0,'fail')
    h.label('width');h.emit(r(8,13,15),i(11,15,15,96));h.branch(4,15,0,'wrap')
    h.emit(r(9,14,24),r(6,24,15,0x2b));h.branch(5,15,0,'wrap')
    h.emit(i(13,0,15,32));h.branch(5,12,15,'consume')
    h.emit(r(8,0,10),r(9,0,11))
    h.label('consume');h.emit(r(8,13,8),r(24,0,9));h.branch(4,0,0,'next')
    h.label('wrap');h.branch(4,10,0,'done')
    h.emit(r(10,0,8),r(11,0,9))
    h.label('done');h.emit(r(8,0,2),r(9,0,3),i(13,0,25,1),0x03e00008,0)
    h.label('fail');h.emit(i(13,0,2,0),i(13,0,3,0),i(13,0,25,0),0x03e00008,0)
    return h.finish()


def block_wrapper(scanner_rva, lut_rva):
    """Dry replacement entry9319C. Complete preflight before graphics/drawing.

    Stack192bytes: original five arguments0..19, savedS0..S7/FP/RA20..59,
    reusable96byte drawing scratch64..159. Original9319C fallback prologue
    is replayed only after restoring this frame. Caller arrays stay untouched.
    """
    h=Block();h.emit(i(9,29,29,-192))
    for n,reg in enumerate([4,5,6,7,8]):h.emit(i(43,29,reg,n*4))
    for n,reg in enumerate([*range(16,24),30,31]):h.emit(i(43,29,reg,20+n*4))
    h.emit(r(4,0,16),i(13,0,20,0),i(13,0,21,0),i(13,0,30,0))
    def pass_loop(render):
        pre='draw' if render else 'probe'
        h.emit(i(13,0,18,0))
        h.label(pre+'_input');h.emit(r(0,18,24,0,2),r(29,24,24),i(35,24,19,4),i(13,0,23,512))
        h.branch(4,19,0,'fallback')
        if not render:
            h.emit(i(36,19,24,0));h.branch(5,24,0,pre+'_nonempty')
            h.emit(i(13,0,30,1));h.branch(4,0,0,pre+'_next_input')
            h.label(pre+'_nonempty');h.branch(5,30,0,'fallback')
        h.label(pre+'_span');h.emit(r(23,0,24))
        h.branch(4,24,0,'fallback')
        h.emit(i(36,19,24,0));h.branch(4,24,0,pre+'_next_input')
        h.emit(r(19,0,4));address(h,5,lut_rva)
        h.emit(i(13,0,6,432),r(23,0,7),jal(scanner_rva),0)
        h.branch(4,25,0,'fallback');h.branch(4,2,0,'fallback')
        h.emit(r(2,0,22))
        if render:
            h.emit(i(13,0,8,0),i(9,29,9,64))
            h.label(pre+'_copy');h.emit(r(19,8,24),i(36,24,10,0),r(9,8,24),i(40,24,10,0),i(9,8,8,1))
            h.emit(r(8,22,24,0x2b));h.branch(5,24,0,pre+'_copy')
            h.emit(r(9,22,24),i(40,24,0,0),r(16,0,4),i(9,29,5,64),r(21,0,6),r(20,0,7),jal(0x92d70),0)
            h.emit(i(9,20,20,16))
        else:
            h.emit(i(9,20,20,1),i(11,20,24,7));h.branch(4,24,0,'fallback')
            h.emit(r(21,3,24,0x2b));h.branch(4,24,0,pre+'_width_done');h.emit(r(3,0,21))
            h.label(pre+'_width_done')
        h.emit(r(19,22,19),r(23,22,23,0x23))
        h.label(pre+'_spaces');h.branch(4,23,0,'fallback')
        h.emit(i(36,19,24,0),i(13,0,25,32));h.branch(5,24,25,pre+'_span')
        h.emit(i(9,19,19,1),i(9,23,23,-1));h.branch(4,0,0,pre+'_spaces')
        h.label(pre+'_next_input');h.emit(i(9,18,18,1),i(11,18,24,4));h.branch(5,24,0,pre+'_input')
    pass_loop(False)
    h.branch(4,20,0,'fallback')
    # The complete native graphics/font setup from931DC..93208 remains.
    for value in [9,0,1]:h.emit(i(13,0,4,value),jal(0x1b7730),0)
    h.emit(i(9,0,4,-1),jal(0x1b7cac),0,jal(0xe928c),0,i(13,0,4,4),i(43,2,4,0x3a0))
    h.emit(i(13,0,24,480),r(24,21,21,0x23),r(0,21,21,2,1))
    for count,y in [(1,120),(2,96),(3,88),(4,84),(5,76),(6,68)]:
        h.emit(i(13,0,24,count));h.branch(4,20,24,'rows_'+str(count))
    h.branch(4,0,0,'fallback')
    for count,y in [(1,120),(2,96),(3,88),(4,84),(5,76),(6,68)]:
        h.label('rows_'+str(count));h.emit(i(13,0,20,y));h.branch(4,0,0,'render')
    h.label('render');pass_loop(True)
    for n,reg in enumerate([*range(16,24),30,31]):h.emit(i(35,29,reg,20+n*4))
    h.emit(0x03e00008,i(9,29,29,192))
    h.label('fallback')
    for n,reg in enumerate([4,5,6,7,8]):h.emit(i(35,29,reg,n*4))
    for n,reg in enumerate([*range(16,24),30,31]):h.emit(i(35,29,reg,20+n*4))
    h.emit(i(9,29,29,192),i(9,29,29,-48),i(43,29,16,4),j(0x931a4),0)
    return h.finish()


def instruction_cases():
    code=span_scanner();scope=instruction_model();cases=[]
    widths=[0]*131
    for n in range(32,127):widths[n]=8
    widths[128:]=[7,9,7]
    samples=[(b'ABC\0',432,4,(3,24,1)),
        (b'ABC DEF\0',32,8,(3,24,1)),(b'ABCD\0',16,5,(2,16,1)),
        (b'\x82\x4f\x82\x58\0',432,5,(4,26,1)),
        (b'A\x80\xf0\x40\xf0\x41\0',432,7,(6,31,1)),
        (b'A'*100+b'\0',800,101,(95,760,1)),
        (b'ABC\x1b\0',432,5,(0,0,0)),(b'\x82\x40\0',432,3,(0,0,0)),
        (b'\xf0',432,1,(0,0,0)),(b'\x82',432,1,(0,0,0)),
        (b'ABC',432,3,(0,0,0)),(b'\0',432,1,(0,0,1))]
    for raw,limit,bound,expected in samples:
        mem={0x200000+n:x for n,x in enumerate(raw)}
        mem.update({0x300000+n:x for n,x in enumerate(struct.pack('<131I',*widths))})
        regs=[0]+[0x12340000+n for n in range(1,32)]
        regs[4:8]=[0x200000,0x300000,limit,bound];regs[31]=0xdeadbeec;before=regs[:]
        original=dict(mem);pc,out,reads=scope['execute'](code,regs,mem)
        assert pc==0xdeadbeec and (out[2],out[3],out[25])==expected,(raw,out[2:4],out[25])
        assert out[4:8]==before[4:8] and out[16:24]==before[16:24] and out[26:32]==before[26:32]
        assert mem==original
        assert all(0x200000<=a<0x200000+bound or 0x300000<=a<0x300000+524 for a in reads)
        cases.append(dict(input_hex=raw.hex(),pixel_limit=limit,read_bound=bound,span_bytes=out[2],pixels=out[3],supported=bool(out[25]),passed=True))
    # Signed int32 native digit loops stop at the leading minus, before adding
    # any native digit glyph; preserve that existing behavior for INT_MIN.
    for value in [-2147483648,-1,0,2147483647]:
        encoded=str(value).encode('ascii');visible=encoded if value>=0 else b''
        assert len(encoded)+1<=16 and len(visible)*2<=20
    return dict(status='dry_leaf_scanner_only_not_installed',code_bytes=len(code),
        instruction_cases=cases,signed_int32_formatter_cases=4,
        no_external_calls=True,no_absolute_addresses=True,no_memory_writes=True,
        limitations=['Complete9319C preflight/render wrapper is tested separately by wrapper_cases; no hooks are installed.',
          'Caller must handle word-boundary spaces and zero-length oversized glyph fallback without looping.',
          'Final incoming build LUT/codeword hashes remain required.'])


def wrapper_cases():
    scope=instruction_model(); scan_scope=instruction_model()
    scan_rva=0x1758000;scan_scope['execute'].__globals__['B']=scan_rva
    code=block_wrapper(scan_rva,0x300000);scanner=span_scanner();cases=[]
    widths=[0]*131
    for n in range(32,127):widths[n]=8
    widths[128:]=[7,9,7]
    samples=[([b'ABC',b'DEF',b'',b''],True,2),
             ([b'A'*60,b'B'*55,b'CCC',b''],True,5),
             ([b'AB \x82\x4f\x82\x58',b'',b'',b''],True,1),
             ([b'ABC',b'\x1bcontrol',b'',b''],False,0),
             ([b'A'*500,b'',b'',b''],False,0),
             ([b'ABC',b'',b'DEF',b''],False,0),
             ([b'ABC',None,None,None],False,0),
             ([b'ABC',None,b'DEF',b''],False,0),
             ([None,None,None,None],False,0),
             ([b'',b'',b'',b''],False,0)]
    for lines,success,expected_rows in samples:
        regs=[0]+[0x76540000+n for n in range(1,32)]
        regs[4]=0x400000;regs[5:9]=[0x200000+n*1024 for n in range(4)]
        for n,line in enumerate(lines):
            if line is None:regs[5+n]=0
        regs[29]=0x600000;regs[31]=0xdeadbeec;before=regs[:]
        mem={0x300000+n:x for n,x in enumerate(struct.pack('<131I',*widths))}
        for n,line in enumerate(lines):
            if line is not None:mem.update({0x200000+n*1024+k:x for k,x in enumerate(line+b'\0')})
        source_before={a:x for a,x in mem.items() if 0x200000<=a<0x204000}
        events=[];draws=[];pc=scope['B']
        for step in range(1000):
            pc,regs,reads=scope['execute'](code,regs,mem,pc)
            if pc in (0xdeadbeec,0x931a4):break
            resume=regs[31]
            if pc==scan_rva:
                pc,regs,_=scan_scope['execute'](scanner,regs,mem)
                assert pc==resume
            elif pc==0x92d70:
                text=[];a=regs[5]
                while mem[a]:text.append(mem[a]);a+=1
                draws.append({'text_hex':bytes(text).hex(),'x':regs[6],'y':regs[7]})
                events.append(pc);pc=resume
            elif pc in (0x1b7730,0x1b7cac,0xe928c):
                events.append(pc)
                if pc==0xe928c:regs[2]=0x500000
                pc=resume
            else:raise AssertionError('Unexpected native call '+hex(pc))
        else:raise AssertionError('Wrapper did not return')
        assert len(draws)==expected_rows and (pc==0xdeadbeec)==success
        assert regs[16:24]==before[16:24] and regs[30:32]==before[30:32]
        if success:assert regs[29]==before[29]
        else:
            assert not events and regs[4:9]==before[4:9] and regs[29]==before[29]-48
            assert bytes(mem[before[29]-44+n]for n in range(4))==struct.pack('<I',before[16])
        assert all(mem[a]==x for a,x in source_before.items())
        assert len(set(d['x']for d in draws))<=1
        if success:
            expected_x=228 if lines[0]==b'ABC' else 24 if len(lines[0])==60 else 215
            assert all(d['x']==expected_x for d in draws)
            # These supported cases contain no wrap-discarded spaces, so even
            # hard word splits must reconstruct every original byte exactly.
            assert b''.join(bytes.fromhex(d['text_hex'])for d in draws)==b''.join(lines)
        if expected_rows==5:assert [d['y']for d in draws]==[76,92,108,124,140]
        cases.append(dict(input_byte_lengths=[len(x)if x is not None else None for x in lines],supported=success,
                          expected_visual_rows=expected_rows,draws=draws,passed=True))
    return dict(status='dry_assembled_wrapper_not_installed',wrapper_bytes=len(code),
                scanner_bytes=len(scanner),stack_bytes=192,cases=cases,
                complete_preflight_before_graphics=True,source_bytes_preserved=True,
                original_fallback_prologue_preserved=True,
                limitations=['Synthetic native call model; actual emulator route remains unverified.',
                             'Existing codeword guards/currentfont LUT must be independently checked before installation.'])


if __name__=='__main__':
    import json
    print(json.dumps(dict(scanner=instruction_cases(),wrapper=wrapper_cases()),indent=2))
