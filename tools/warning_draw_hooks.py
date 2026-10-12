"""Pure paired warning decode/draw/advance blocks; no executable writer."""
from dialogue_vwf_hooks import Block, r, address, route
from live_vwf import i,j,jal


def supported(h,code,scratch,fallback):
    h.emit(i(11,code,scratch,32));h.branch(5,scratch,0,fallback)
    h.emit(i(11,code,scratch,131));h.branch(4,scratch,0,fallback)
    h.emit(i(13,0,scratch,127));h.branch(4,code,scratch,fallback)


def classify():
    h=Block();h.emit(i(9,29,29,-16),i(43,29,31,12),i(43,29,6,8),jal(0xe9c64),0)
    h.emit(i(35,29,24,8),i(37,24,25,0),i(13,0,8,0xf040));h.branch(4,25,8,'acute_a')
    h.emit(i(13,0,8,0xf041));h.branch(5,25,8,'check')
    h.emit(i(13,0,25,130));h.branch(4,0,0,'store')
    h.label('acute_a');h.emit(i(13,0,25,129))
    h.label('store');h.emit(i(41,24,25,0))
    h.label('check');supported(h,25,8,'return');h.emit(i(13,0,2,1))
    h.label('return');h.emit(i(35,29,31,12),0x03e00008,i(9,29,29,16))
    return h.finish()


def advance(lut):
    h=Block();h.emit(i(9,29,29,-16),i(43,29,24,0),i(43,29,25,4),i(37,29,24,20))
    supported(h,24,25,'native');address(h,25,lut)
    h.emit(r(0,24,24,0,2),r(25,24,25),i(35,25,24,0),r(17,24,17))
    h.branch(4,0,0,'done');h.label('native');h.emit(i(9,17,17,13))
    h.label('done');h.emit(i(35,29,24,0),i(35,29,25,4),j(0x92db0),i(9,29,29,16))
    return h.finish()


def blocks(lut):
    return {'warning_classify':classify(),'warning_route':route(0xea900,max_glyph=131),
            'warning_advance':advance(lut)}


def instruction_cases():
    import struct
    from font_vram_hooks import instruction_model
    scope=instruction_model();code=blocks(0x300000);widths=[0]*131
    for n in range(32,127):widths[n]=8
    widths[128:]=[7,9,7]
    cases=[]
    for decoded,flag,expected in [(65,0,65),(128,0,128),(0xf040,1,129),
        (0xf041,1,130),(0x824f,1,0x824f),(15,0,15),(127,0,127)]:
        regs=[0]+[0x76540000+n for n in range(1,32)];regs[6]=0x200000;regs[29]=0x600000;regs[31]=0xdeadbeec
        before=regs[:];mem={0x200000:0,0x200001:0}
        pc,out,_=scope['execute'](code['warning_classify'],regs,mem)
        assert pc==0xe9c64
        resume=out[31];out[2]=flag
        mem[0x200000]=decoded&255;mem[0x200001]=decoded>>8
        pc,out,_=scope['execute'](code['warning_classify'],out,mem,resume)
        assert pc==0xdeadbeec and out[29]==before[29] and out[31]==before[31]
        actual=mem[0x200000]|mem[0x200001]<<8
        latin=32<=expected<131 and expected!=127
        assert actual==expected and out[2]==(1 if latin else flag)
        # The same decoded glyph must select the matching draw and advance.
        out[9]=actual;pc,out,_=scope['execute'](code['warning_route'],out,mem)
        assert pc==(0xea45c if latin else 0xea900)
        out[17]=100;out[29]=0x600000
        mem.update({0x600004:actual&255,0x600005:actual>>8})
        mem.update({0x300000+n:x for n,x in enumerate(struct.pack('<131I',*widths))})
        before=out[:];pc,out,_=scope['execute'](code['warning_advance'],out,mem)
        assert pc==0x92db0 and out[17]==100+(widths[actual]if latin else 13)
        assert out[29]==before[29] and out[24:26]==before[24:26]
        cases.append(dict(native_decoded=hex(decoded),stored_glyph=hex(actual),latin=latin,
            expected_draw=hex(0xea45c if latin else 0xea900),cursor_advance=out[17]-100,passed=True))
    return dict(status='dry_paired_warning_draw_blocks_not_installed',code_bytes={k:len(v)for k,v in code.items()},
        cases=cases,native_decimal_glyph_advance=13,private_pair_codes=[129,130],
        limitations=['Synthetic decoder/draw stubs; actual encoded native draw trace and screen QA remain pending.',
          'Do not install without exact incoming executable/hook guards.'])
