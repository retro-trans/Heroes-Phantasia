"""Bounded literal width for the separate Field Tutorial constructor.

93D08 currently computes 13*S7, although its row renderer advances Latin by
the integer VWF LUT. S6 is the unchanged source cursor; only A0 changes.
Unknown controls, ruby, substitutions and malformed pairs retain 13*S7.
"""
from dialogue_vwf_hooks import Block,address,r
from live_vwf import i,j
from font_vram_hooks import instruction_model
import struct

SITE=0x93d08
CONTINUATION=0x93d18
EXPECTED=struct.pack('<4I',r(0,23,4,0,4),r(4,23,4,0x23),r(4,23,4,0x23),r(4,23,4,0x23))

def hook(lut):
    h=Block();h.emit(i(9,29,29,-32))
    regs=(8,9,10,11,12,13,14,15)
    for n,reg in enumerate(regs):h.emit(i(43,29,reg,n*4))
    h.emit(r(22,0,8),i(13,0,9,0),i(13,0,10,0));address(h,14,lut)
    h.branch(4,8,0,'native')
    h.label('next');h.emit(i(11,9,15,1025));h.branch(4,15,0,'native')
    h.emit(i(36,8,11,0));h.branch(4,11,0,'done')
    for c in (0x0e,0x10,0x11,0x12):
        h.emit(i(13,0,15,c));h.branch(4,11,15,'done')
    h.emit(i(11,9,15,1024));h.branch(4,15,0,'native')
    for c in (5,0x16,0x17,0x1a):
        h.emit(i(13,0,15,c));h.branch(4,11,15,f'arg{c}')
    h.emit(i(11,11,15,32));h.branch(5,15,0,'native')
    h.emit(i(13,0,15,0xf0));h.branch(4,11,15,'private')
    h.emit(i(11,11,15,129));h.branch(4,15,0,'pair')
    h.emit(i(13,0,15,127));h.branch(4,11,15,'native')
    h.emit(i(9,8,8,1),i(9,9,9,1));h.branch(4,0,0,'add')
    h.label('private');h.emit(i(11,9,15,1023));h.branch(4,15,0,'native')
    h.emit(i(36,8,12,1),i(9,12,15,-0x40),i(11,15,15,2));h.branch(4,15,0,'pair')
    h.emit(i(9,12,11,65),i(9,8,8,2),i(9,9,9,2));h.branch(4,0,0,'add')
    h.label('pair');h.emit(i(11,11,15,0x81));h.branch(5,15,0,'native')
    h.emit(i(11,11,15,0xa0));h.branch(5,15,0,'trail')
    h.emit(i(11,11,15,0xe0));h.branch(5,15,0,'native')
    h.emit(i(11,11,15,0xfd));h.branch(4,15,0,'native')
    h.label('trail');h.emit(i(11,9,15,1023));h.branch(4,15,0,'native')
    h.emit(i(36,8,12,1),i(11,12,15,0x40));h.branch(5,15,0,'native')
    h.emit(i(11,12,15,0xfd));h.branch(4,15,0,'native')
    h.emit(i(13,0,15,0x7f));h.branch(4,12,15,'native')
    h.emit(i(9,10,10,13),i(9,8,8,2),i(9,9,9,2));h.branch(4,0,0,'next')
    h.label('add');h.emit(r(0,11,15,0,2),r(14,15,15),i(35,15,15,0),r(10,15,10));h.branch(4,0,0,'next')
    for c,count in ((5,3),(0x16,2),(0x17,1),(0x1a,1)):
        h.label(f'arg{c}');h.emit(i(11,9,15,1024-count));h.branch(4,15,0,'native')
        for n in range(1,count+1):
            h.emit(i(36,8,12,n),i(9,12,15,-48),i(11,15,15,10));h.branch(4,15,0,'native')
        h.emit(i(9,8,8,count+1),i(9,9,9,count+1));h.branch(4,0,0,'next')
    h.label('done');h.emit(r(10,0,4));h.branch(4,0,0,'return')
    h.label('native');h.emit(r(0,23,4,0,4),r(4,23,4,0x23),r(4,23,4,0x23),r(4,23,4,0x23))
    h.label('return')
    for n,reg in enumerate(regs):h.emit(i(35,29,reg,n*4))
    h.emit(j(CONTINUATION),i(9,29,29,32));return h.finish()

def cases(widths,code=None,base=0x1750000,continuation=CONTINUATION,lut=0x240000):
    model=instruction_model();model['execute'].__globals__['B']=base
    texts=[(b'Use this object to save your data.\x11',True),
      (b'It also restores HP and PP to their maximum values.\x0e',True),
      (b'\x1602\x81\x77Save Points\x81\x78\x0e',True),
      (b'\x1a2\x172Field Tutorial\x12',True),
      (b'A\xf0\x40\xf0\x41\x0e',True),(b'A\x05001B\x0e',True),
      (b'A\x01'+b'0B\x0e',False),(b'A\x0f1A\x0f\x0e',False),
      (b'A\x16X2\x0e',False),(b'A\x16\0',False),
      (b'A\x82\0',False),(b'A\x7f\0',False),
      (b'A'*1022+b'\x172\x0e',True),(b'A'*1023+b'\x172\x0e',False)]
    from dialogue_tokens import tokenize_bytes
    result=[]
    for raw,supported in texts:
        regs=[0]+[0x12340000+n for n in range(1,32)];regs[22]=0x220000;regs[23]=49;regs[29]=0x250000;old=regs[:]
        mem={0x220000+n:x for n,x in enumerate(raw+b'\0')};mem.update({lut+n:x for n,x in enumerate(struct.pack('<131I',*widths))})
        expected=13*49
        if supported:expected=sum(widths[t.code] if t.kind=='latin' else 13 if t.kind=='native' else 0 for t in tokenize_bytes(raw,True))
        pc,out,reads=model['execute'](code or hook(lut),regs,mem);old[4]=expected
        if pc!=continuation or out!=old:raise ValueError('Field Tutorial width ABI/fallback differs')
        if any(a>0x220000+min(len(raw),1024)for a in reads if 0x220000<=a<0x230000):raise ValueError('Probe exceeds source bound')
        result.append(dict(bytes=len(raw),supported=supported,width_px=expected,passed=True))
    return result
