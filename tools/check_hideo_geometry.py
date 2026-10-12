"""Execute the emitted geometry scanner in a bounded test harness; no writer."""
import json,struct
import bubble_layout_hooks as g
from dialogue_vwf_hooks import Block
from font_vram_hooks import instruction_model
from live_vwf import j

def cases():
    captured=[]
    class Capture(Block):
        def finish(self):
            code=super().finish();captured.append((code,self.labels.copy()));return code
    original=g.Block
    try:
        g.Block=Capture;g.geometry(0x2e43c0,True,True,True,131)
    finally:g.Block=original
    data,labels=captured[0];model=instruction_model();base=model['B'];code=bytearray(data)
    # Only entry/exit scaffolding is replaced. All actual scanner instructions
    # and relative branches execute unchanged, including both probe bounds.
    struct.pack_into('<II',code,0,j(base+labels['byte']*4),0)
    for label,destination in (('return',0x0eadbe00),('validated',0x0eadbe20)):
        struct.pack_into('<II',code,labels[label]*4,j(destination),0)
    samples=[(b"I shall now leave for Hideo\x0f2Hideo\x0f's\x11world, bound\x11for Japan.\x12\x0e",True,3),
             (b'Hideo\x0f2Hideo\x0f\0',True,1),(b'Hideo\x0f2Other\x0f\0',False,None),
             (b'Hideo\x0fXHideo\x0f\0',False,None),(b'Hideo\x0f2Hi\0',False,None),
             (b'Hideo\x0f2Hideo\x11\0',False,None),(b'A'*4087+b'\x0f2Hideo\x0f\0',True,1),
             (b'A'*4088+b'\x0f2Hideo\x0f\0',False,None),
             (b'Preparations for the\x11tracking Gift are\x11finally complete.\x12\x0e',True,3)]
    out=[]
    for raw,supported,lines in samples:
        regs=[0]*32;regs[5]=0x220000;regs[10]=1
        mem={0x220000+n:v for n,v in enumerate(raw)}
        pc,result,reads=model['execute'](bytes(code),regs,mem)
        if pc!=(0x0eadbe20 if supported else 0x0eadbe00):raise ValueError('Scanner decision differs')
        if supported and result[10]!=lines:raise ValueError('Ruby altered body line count')
        if max(reads,default=0)>0x220000+min(len(raw)-1,4095):raise ValueError('Out-of-bound scanner probe')
        out.append(dict(bytes=len(raw),supported=supported,body_lines=result[10],passed=True))
    return out
if __name__=='__main__':print(json.dumps(cases(),indent=2))
