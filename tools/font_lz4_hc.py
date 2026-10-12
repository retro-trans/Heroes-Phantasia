"""Deterministic deeper-match encoder for the existing bounded raw-LZ4 decoder."""
from collections import deque
from font_ram_plan import extension
import struct


def encode(data,chain_limit=1024):
    if chain_limit!=1024:raise ValueError('Reviewed deterministic chain limit required')
    out=bytearray();seen={};pos=anchor=0
    def insert(n):
        seen.setdefault(data[n:n+4],deque(maxlen=chain_limit)).append(n)
    while pos+4<=len(data):
        best=0;prior=0
        for previous in reversed(seen.get(data[pos:pos+4],())):
            if pos-previous>65535:break
            stop=pos+4
            while stop<len(data)and data[previous+stop-pos]==data[stop]:stop+=1
            if stop-pos>best:best=stop-pos;prior=previous
            if stop==len(data):break
        insert(pos)
        if best<4:pos+=1;continue
        literal=pos-anchor;match=best-4
        out.append(min(literal,15)*16+min(match,15))
        if literal>=15:out.extend(extension(literal-15))
        out.extend(data[anchor:pos]);out.extend(struct.pack('<H',pos-prior))
        if match>=15:out.extend(extension(match-15))
        for n in range(pos+1,pos+best):
            if n+4<=len(data):insert(n)
        pos+=best;anchor=pos
    literal=len(data)-anchor;out.append(min(literal,15)*16)
    if literal>=15:out.extend(extension(literal-15))
    out.extend(data[anchor:]);return bytes(out)
