"""Scoped opening-scene Latin hooks; Japanese and control paths retain originals."""
import struct
from live_vwf import Assembler,i,j,jal,words

def r(rs,rt,rd,funct=0x21,shift=0):return rs<<21|rt<<16|rd<<11|shift<<6|funct
def address(h,reg,value):h.emit(i(15,0,reg,value>>16),i(13,reg,reg,value))

class Block(Assembler):
    def finish(self):
        for pos,op,rs,rt,name in self.fixups:self.code[pos]=i(op,rs,rt,self.labels[name]-pos-1)
        return words(self.code)

def decoder(speaker_labels=False, extra_return_gates=(), private_pairs=False):
    h=Block();h.emit(i(9,29,29,-16),i(43,29,8,0),i(43,29,7,4))
    if private_pairs:
        # Native decoder has already consumed2 bytes and returned flag1.
        # Only the output halfword changes; A0/A3 and consumed-byte count stay.
        h.emit(i(37,6,7,0),i(13,0,8,0xf040));h.branch(4,7,8,'private_a')
        h.emit(i(13,0,8,0xf041));h.branch(5,7,8,'classified')
        h.emit(i(13,0,7,130));h.branch(4,0,0,'private_store')
        h.label('private_a');h.emit(i(13,0,7,129))
        h.label('private_store');h.emit(i(41,6,7,0))
        h.label('classified')
    # Visible glyph classification only; numeric/control argument scanners stay unchanged.
    for ret in (0x87d38,0xeade8,0xee678,0xee888,0xeeab4)+((0xebff8,) if speaker_labels else ())+tuple(extra_return_gates):
        address(h,8,ret);h.branch(4,31,8,'visible')
    h.branch(4,0,0,'return')
    h.label('visible');h.emit(i(37,6,7,0),i(11,7,8,32));h.branch(5,8,0,'return')
    h.emit(i(11,7,8,131 if private_pairs else 129));h.branch(4,8,0,'return')
    h.emit(i(13,0,8,127));h.branch(4,7,8,'return');h.emit(i(13,0,2,1))
    h.label('return');h.emit(i(35,29,8,0),i(35,29,7,4),0x03e00008,i(9,29,29,16))
    data=h.finish()
    if len(data)>0x100 and not private_pairs:raise ValueError('Decoder slot overflow')
    return data

def route(original,max_glyph=129):
    # Caller's delay slot has already placed the character in t1.
    h=Block();h.emit(i(11,9,24,32));h.branch(5,24,0,'original')
    h.emit(i(11,9,24,max_glyph));h.branch(4,24,0,'original')
    h.emit(i(13,0,24,127));h.branch(4,9,24,'original')
    h.emit(j(0xea45c),0);h.label('original');h.emit(j(original),0)
    return h.finish()

def cursor(lut,max_glyph=129):
    h=Block();h.emit(i(37,29,24,0),i(11,24,25,32));h.branch(5,25,0,'original')
    h.emit(i(11,24,25,max_glyph));h.branch(4,25,0,'original')
    h.emit(i(13,0,25,127));h.branch(4,24,25,'original')
    address(h,25,lut);h.emit(r(0,24,24,0,2),r(25,24,25),i(35,25,24,0),r(4,24,4))
    h.branch(4,0,0,'store');h.label('original');h.emit(i(9,4,4,13))
    h.label('store');h.emit(i(43,16,4,0x30),j(0xee92c),0)
    return h.finish()

def measure(lut):
    # First validate all lines before changing any width. Unknown controls, ruby,
    # Japanese, excessive lengths or unexpected object counts keep original layout.
    h=Block();h.emit(i(57,20,12,0x2c),i(43,4,23,0x48),i(9,29,29,-192))
    regs=list(range(8,16))+[24,25]
    for n,reg in enumerate(regs):h.emit(i(43,29,reg,n*4))
    h.emit(i(57,29,0,40),i(57,29,1,44),i(35,20,9,0x18),i(11,9,15,33))
    h.branch(4,15,0,'return');h.branch(4,9,0,'return')
    h.emit(i(35,20,8,4),i(13,0,10,0),i(13,0,24,0));address(h,14,lut)
    h.label('line');h.emit(i(35,8,11,4),i(13,0,12,0),i(13,0,25,0))
    h.label('char');h.emit(i(36,11,13,0));h.branch(4,13,0,'endline')
    for stop in (0x0e,0x10,0x11,0x12):
        h.emit(i(13,0,15,stop));h.branch(4,13,15,'endline')
    h.emit(i(11,13,15,32));h.branch(5,15,0,'return')
    h.emit(i(11,13,15,129));h.branch(4,15,0,'return')
    h.emit(i(13,0,15,127));h.branch(4,13,15,'return')
    h.emit(r(0,13,15,0,2),r(14,15,15),i(35,15,15,0),r(12,15,12),
           i(9,11,11,1),i(9,25,25,1),i(11,25,15,1025))
    h.branch(4,15,0,'return');h.branch(4,0,0,'char')
    h.label('endline');h.emit(r(0,10,15,0,2),r(29,15,15),i(43,15,12,64),r(24,12,15,0x2b))
    h.branch(4,15,0,'keepmax');h.emit(r(12,0,24));h.label('keepmax')
    h.emit(i(9,10,10,1),i(9,8,8,0xe8));h.branch(5,10,9,'line')
    h.emit(i(35,20,8,4),i(13,0,10,0),i(13,0,15,0x3f00),r(0,15,15,0,16),0x448f0800)
    h.label('storeline');h.emit(r(0,10,15,0,2),r(29,15,15),i(35,15,12,64),0x448c0000,
        0x46800020,0x46010002,i(57,8,0,0x20),i(9,8,8,0xe8),i(9,10,10,1))
    h.branch(5,10,9,'storeline');h.emit(0x44980000,0x46800020,0x46010002,i(57,20,0,0x2c))
    h.label('return');h.emit(i(49,29,0,40),i(49,29,1,44))
    for n,reg in enumerate(regs):h.emit(i(35,29,reg,n*4))
    h.emit(j(0xed164),i(9,29,29,192))
    return h.finish()

def label_cursor(lut):
    h=Block();h.emit(i(37,29,24,0x20),i(11,24,25,32));h.branch(5,25,0,'original')
    h.emit(i(11,24,25,129));h.branch(4,25,0,'original')
    h.emit(i(13,0,25,127));h.branch(4,24,25,'original')
    address(h,25,lut);h.emit(r(0,24,24,0,2),r(25,24,25),i(35,25,24,0),r(16,24,16),
        i(9,24,25,-13),i(9,29,29,-16),i(57,29,0,0),0x44990000,0x46800020,
        0x4600d680,i(49,29,0,0),i(9,29,29,16))
    h.branch(4,0,0,'compare');h.label('original');h.emit(i(9,16,16,13))
    h.label('compare');h.emit(r(17,30,4,0x2a));h.branch(5,4,0,'loop')
    h.emit(j(0xec058),0);h.label('loop');h.emit(j(0xebfb8),0)
    return h.finish()

def append(payload,start,speaker_labels=False):
    decoder_code=decoder(speaker_labels);payload[:len(decoder_code)]=decoder_code
    while len(payload)%256:payload.append(0)
    lut=start+len(payload)
    # Cursor coordinates are integer pixels. Layout uses the same rounded advances.
    widths=[round(v) for v in struct.unpack_from('<129f',payload,0x800)]
    payload.extend(words(widths));blocks=[(0,len(decoder_code))];changes=[]
    definitions=[
        ('body_renderer',route(0xe9ff4),0xee2d4,jal(0xe9ff4),True),
        ('name_renderer',route(0xeab10),0xee35c,jal(0xeab10),True),
        ('cursor',cursor(lut),0xee8d4,i(9,4,4,13),False),
        ('layout',measure(lut),0xed15c,i(57,20,12,0x2c),False)]
    if speaker_labels:definitions.extend([
        ('speaker_renderer',route(0xe9ff4),0xec040,jal(0xe9ff4),True),
        ('speaker_cursor',label_cursor(lut),0xec04c,r(17,30,4,0x2a),False)])
    for label,code,site,old,existing in definitions:
        while len(payload)%16:payload.append(0)
        offset=len(payload);payload.extend(code);blocks.append((offset,len(code)))
        changes.append((site,words([jal(start+offset)]) if existing else words([j(start+offset),0]),existing,old))
    return blocks,changes,{'integer_advance_lut':lut,'hook_blocks':blocks,
        'scope':'control-light opening scene; ruby and mixed-language measurement retain original layout',
        'decoder_return_gates':[hex(x) for x in (0x87d38,0xeade8,0xee678,0xee888,0xeeab4)+((0xebff8,) if speaker_labels else ())],
        'speaker_label_normal_path':speaker_labels,'speaker_label_resource_path':False,
        'maximum_measured_lines':32,'maximum_measured_bytes_per_line':1024}
