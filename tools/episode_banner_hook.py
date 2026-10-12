"""Exact Episode 1 inline payload remap before the common styled-text parser."""
import hashlib, struct
from pathlib import Path
from dialogue_vwf_hooks import Block, address, r
from live_vwf import i,j
from font_vram_hooks import instruction_model

SITE=0xecf48
EXPECTED=struct.pack('<II',i(35,20,4,0x14),i(43,29,21,0x24))
TARGET='{1A}2{17}2Episode 1{11}The First Investigation Request{12}{0E}'
def source_payload():
    data=Path('work/source/cpk/fld/event/d01.evt').read_bytes()
    raw=data[0x10949:0x1096d]
    if len(raw)!=36 or raw[:4]!=b'\x1a2\x172' or raw[-3:]!=b'\x12\x0e\0' or data[0x10947:0x10949]!=b'\x07\0':
        raise ValueError('Original event payload/opcode boundaries differ')
    # Exact expected UI title, independent of the arbitrary surrounding script.
    if raw[4:-3]!=('エピソード１\x11始まりの調査依頼').encode('cp932'):
        raise ValueError('Original Episode 1 header/title differs')
    return raw

def hook(key,target,length):
    h=Block();h.emit(i(35,20,4,0x14),i(9,29,29,-32))
    regs=(8,9,10,11,24)
    for n,reg in enumerate(regs):h.emit(i(43,29,reg,n*4))
    h.branch(4,4,0,'restore');h.emit(r(4,0,8));address(h,9,key);h.emit(i(13,0,10,length))
    h.label('compare');h.emit(i(36,8,11,0),i(36,9,24,0));h.branch(5,11,24,'restore')
    h.emit(i(9,8,8,1),i(9,9,9,1),i(9,10,10,-1));h.branch(5,10,0,'compare')
    address(h,4,target);h.emit(i(43,20,4,0x14))
    h.label('restore')
    for n,reg in enumerate(regs):h.emit(i(35,29,reg,n*4))
    h.emit(i(9,29,29,32),i(43,29,21,0x24),j(SITE+8),0)
    return h.finish()

def cases(code,base,key,target,original,continuation=None):
    model=instruction_model();model['execute'].__globals__['B']=base
    samples=[('exact',original,True),('null',None,False),('empty',b'\0',False)]
    for n in range(len(original)):
        b=bytearray(original);b[n]^=1;samples.append((f'mismatch_{n}',bytes(b),False))
    for n in range(1,len(original)-1):samples.append((f'truncated_{n}',original[:n]+b'\0',False))
    results=[]
    for name,raw,matched in samples:
        regs=[0]+[0x12340000+n for n in range(1,32)];regs[20]=0x220000;regs[29]=0x250000
        before=regs[:];mem={};ptr=0x230000 if raw is not None else 0
        def put(a,b):mem.update({a+n:x for n,x in enumerate(b)})
        put(0x220014,struct.pack('<I',ptr));put(key,original)
        if raw is not None:put(ptr,raw)
        pc,out,reads=model['execute'](code,regs,mem)
        expected=before[:];expected[4]=target if matched else ptr
        if pc!=(continuation if continuation is not None else ((base&0xf0000000)|(j(SITE+8)&0x3ffffff)*4)) or out!=expected:
            raise ValueError('Emitted remap ABI/continuation differs: '+name)
        stored=lambda a:int.from_bytes(bytes(mem[a+n]for n in range(4)),'little')
        if stored(0x220014)!=(target if matched else ptr) or stored(0x250024)!=before[21]:
            raise ValueError('Cursor/replayed native save differs')
        source_reads=[a for a in reads if ptr and ptr<=a<ptr+0x100]
        if raw is not None and any(a>=ptr+len(raw)for a in source_reads):raise ValueError('Source read beyond complete input')
        results.append(dict(case=name,matched=matched,source_reads=len(source_reads),passed=True))
    return results
