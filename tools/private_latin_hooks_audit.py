"""Dry emitted-instruction checks for private-pair decoding/reveal/name count."""
import json,struct
from font_vram_hooks import instruction_model
from dialogue_vwf_hooks import decoder
from dialogue_wrap import literal_reveal_cap
from dialogue_ruby_hooks import name_glyph_units
from private_latin import cases


def build():
    scope=instruction_model();execute=scope['execute'];results=[]
    def put(mem,a,data):mem.update({a+n:x for n,x in enumerate(data)})
    gates=(0xf0cf0,0xf0d98,0xec644)
    code=decoder(True,gates,private_pairs=True)
    for glyph in (31,32,126,127,128,0x81,0x82,0x8140,0x8260,0xf040,0xf041,0xf042):
        for ra in (0xee678,0xf0cf0,0xec644,0x123456):
            regs=[0]+[0x12340000+n for n in range(1,32)];regs[2]=int(glyph>=0x8140)
            regs[4]=2;regs[6]=0x200000;regs[29]=0x220000;regs[31]=ra;before=regs[:]
            mem={};put(mem,regs[6],struct.pack('<H',glyph))
            pc,out,reads=execute(code,regs,mem)
            actual=int.from_bytes(bytes(mem[0x200000+n]for n in range(2)),'little')
            mapped={0xf040:129,0xf041:130}.get(glyph,glyph)
            assert pc==ra and actual==mapped and out[4:8]==before[4:8]
            assert out[8:]==before[8:]
            assert out[2]==(1 if ra!=0x123456 and (32<=mapped<131 and mapped!=127) else before[2])
            results.append(dict(glyph=hex(glyph),return_gate=hex(ra),mapped=mapped,passed=True))
    cap=literal_reveal_cap(True,True,True);capcases=[]
    samples=[(b'\xf0\x40'*60+b'\x12',60,61),(b'A'*45+b'\xf0\x41\x11',46,47),
             (b'A'*60+b'\x0f2\xf0\x40\xf0\x41\x0f\x12',60,61),
             (b'A'*1022+b'\xf0\x40\x12',1023,1024),
             (b'A'*1023+b'\xf0\x40\x12',1024,45),
             (b'A'*60+b'\xf0',61,45),(b'A'*60+b'\xf0\x42\x12',61,45),
             (b'A'*60+b'\x0f2\xf0\x42\x0f\x12',60,45),
             (b'A'*60+b'\xf0\x40\x172100\x12',64,65)]
    for raw,count,expected in samples:
        regs=[0]*32;regs[6]=0x200000;regs[7]=count;regs[17]=0x210000;regs[29]=0x220000
        for r in range(8,16):regs[r]=0x12340000+r
        before=regs[:];mem={};put(mem,regs[6],raw+b'\0')
        pc,out,reads=execute(cap,regs,mem)
        assert pc==0xee98c and out[6]==expected and out[8:16]==before[8:16] and out[29]==before[29]
        assert max(x for x in reads if 0x200000<=x<0x210000)<=0x200000+min(len(raw),1024)
        capcases.append(dict(source_bytes=len(raw),count=count,cap=expected,passed=True))
    namecases=[];code2=name_glyph_units(True)
    for raw,count in [(b'Guaruj\xf0\x40',14),(b'lyc\xf0\x41e',10),(b'A\x80\xf0\x40\xf0\x41',8),(b'\x82\x60\xf0\x40A',6)]:
        regs=[0]*32;regs[4]=0x200000;regs[31]=0xdeadbeec;mem={};put(mem,regs[4],raw+b'\0')
        pc,out,reads=execute(code2,regs,mem);assert pc==regs[31] and out[2]==count and out[4]==0x200000
        namecases.append(dict(bytes=raw.hex(),glyph_units=count,passed=True))
    return dict(dry_only=True,codec=cases(),decoder_bytes=len(code),decoder_cases=results,
                cap_bytes=len(cap),cap_cases=capcases,name_count_cases=namecases,
                control_args_untouched=True,native_cp932_outputs_except_two_pua_pairs_unchanged=True,
                remaining='Width FPU/hook relocations/full ELF integration and runtime font lifetime.',runtime_verified=False)


if __name__=='__main__':print(json.dumps(build(),indent=2))
