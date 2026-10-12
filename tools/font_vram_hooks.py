"""Dry bounded font decompressor candidate. No executable or emulator writer."""
import ast
import struct
from pathlib import Path
from dialogue_vwf_hooks import Block, r
from live_vwf import i
from font_ram_plan import encode, decode, raster_glyph


def uploader(state, lookup, max_glyph=131):
    """Dynamic 4x glyph bank; clean native epilogue on initialization failure.

    Japanese/control/DEL routes replay the prior native fallback. Private glyph
    IDs129/130 require a separately reviewed decoder mapping, never raw bytes.
    Lookup offsets are256-byte units; only a published owned bank is sampled.
    """
    if max_glyph !=131:raise ValueError('Expected explicit98-glyph repertoire')
    h=Block();relocations=[]
    def addr(reg,value):
        pos=len(h.code)*4;h.emit(i(15,0,reg,(value+0x8000)>>16),i(9,reg,reg,value))
        relocations.extend([(pos,5),(pos+4,6)])
    def jump(value):
        relocations.append((len(h.code)*4,4));h.emit(0x08000000|(value>>2),0)
    h.emit(i(37,21,24,0),i(11,24,25,32));h.branch(5,25,0,'fallback')
    h.emit(i(11,24,25,max_glyph));h.branch(4,25,0,'fallback')
    h.emit(i(13,0,25,127));h.branch(4,24,25,'fallback')
    h.emit(r(0,24,24,0,1));addr(25,lookup)
    h.emit(r(25,24,25),i(37,25,24,0),i(13,0,25,65535));h.branch(4,24,25,'fallback')
    h.emit(r(0,24,24,0,8));addr(25,state);h.emit(i(35,25,25,0));h.branch(4,25,0,'skip')
    h.emit(r(25,24,8),i(13,0,4,0),i(13,0,5,64),i(13,0,6,64),i(13,0,7,64),
           i(13,0,9,0),i(9,0,21,-1),i(13,0,22,0));jump(0xea5ec)
    h.label('skip');jump(0xea6ec)
    h.label('fallback');h.emit(r(5,0,8),i(13,0,21,0));jump(0xea5cc)
    return h.finish(),relocations


def initialize(legacy, state, packed, packed_bytes, decoded_bytes, decoder):
    """Preserve legacy font initialization, allocate/decode once on its thread.

    State words: pointer0, status4 (0new,1allocation failure,2decode failure,3ready).
    Failed decoding frees its allocation. Renderer must skip Latin if pointer0.
    Return explicit relocation sites; scalar LUI constants must NOT be relocated.
    """
    if not 0 < packed_bytes <= 0x40000 or not 0 < decoded_bytes <= 0x40000:
        raise ValueError('Font packet exceeds bounded decoder capacity')
    h=Block();relocations=[]
    def constant(reg,value):
        if value < 65536:h.emit(i(13,0,reg,value))
        else:h.emit(i(15,0,reg,value>>16),i(13,reg,reg,value))
    def addr(reg,value):
        pos=len(h.code)*4
        h.emit(i(15,0,reg,(value+0x8000)>>16),i(9,reg,reg,value))
        relocations.extend([(pos,5),(pos+4,6)])
    def call(value):
        relocations.append((len(h.code)*4,4))
        h.emit(0x0c000000|(value>>2),0)
    regs=[2,3,4,5,6,7,*range(8,16),24,25]
    h.emit(i(9,29,29,-96),i(43,29,31,92));call(legacy)
    for n,reg in enumerate(regs):h.emit(i(43,29,reg,16+n*4))
    addr(8,state);h.emit(i(35,8,9,0));h.branch(5,9,0,'restore')
    h.emit(i(35,8,9,4));h.branch(5,9,0,'restore')
    constant(4,decoded_bytes);call(0xc70)
    h.branch(4,2,0,'allocation_failed');h.emit(i(43,29,2,80))
    addr(4,packed);constant(5,packed_bytes);h.emit(r(2,0,6));constant(7,decoded_bytes)
    call(decoder);h.branch(4,2,0,'decode_failed')
    addr(8,state);h.emit(i(13,0,9,3),i(43,8,9,4),i(35,29,9,80),i(43,8,9,0))
    h.branch(4,0,0,'restore')
    h.label('decode_failed');h.emit(i(35,29,4,80));call(0xca0)
    h.emit(i(13,0,9,2));h.branch(4,0,0,'failed')
    h.label('allocation_failed');h.emit(i(13,0,9,1))
    h.label('failed');addr(8,state);h.emit(i(43,8,9,4))
    h.label('restore')
    for n,reg in enumerate(regs):h.emit(i(35,29,reg,16+n*4))
    h.emit(i(35,29,31,92),0x03e00008,i(9,29,29,96))
    return h.finish(),relocations


def decompress():
    """Leaf ABI: A0 input, A1 bytes, A2 destination, A3 bytes; V0=success.

    Input/output bounds checked before each byte access; matches may overlap.
    Each buffer length is limited to256KiB, preventing length-accumulator wrap.
    Only V0,T0..T9 are changed. No external calls or absolute addresses.
    """
    h = Block()
    h.emit(i(15,0,24,4),r(24,5,25,0x2b));h.branch(5,25,0,'fail')
    h.emit(r(24,7,25,0x2b));h.branch(5,25,0,'fail')
    h.emit(r(4,0,8),r(4,5,9),r(6,0,10),r(6,7,11),r(6,0,12))
    h.emit(r(9,8,24,0x2b));h.branch(5,24,0,'fail')
    h.emit(r(11,10,24,0x2b));h.branch(5,24,0,'fail')
    h.label('token');h.branch(4,8,9,'done')
    h.emit(i(36,8,13,0),i(9,8,8,1),r(0,13,14,2,4))
    h.emit(i(13,0,24,15));h.branch(5,14,24,'literal_ready')
    h.label('literal_extension');h.branch(4,8,9,'fail')
    h.emit(i(36,8,24,0),i(9,8,8,1),r(14,24,14),r(11,10,25,0x23),r(25,14,25,0x2b))
    h.branch(5,25,0,'fail');h.emit(i(13,0,25,255));h.branch(4,24,25,'literal_extension')
    h.label('literal_ready')
    for end,ptr in ((9,8),(11,10)):
        h.emit(r(end,ptr,24,0x23),r(24,14,24,0x2b));h.branch(5,24,0,'fail')
    h.branch(4,14,0,'literal_done')
    h.label('literal_copy');h.emit(i(36,8,24,0),i(40,10,24,0),i(9,8,8,1),i(9,10,10,1),i(9,14,14,-1))
    h.branch(5,14,0,'literal_copy')
    h.label('literal_done');h.branch(4,8,9,'done')
    h.emit(r(9,8,24,0x23),i(11,24,24,2));h.branch(5,24,0,'fail')
    h.emit(i(36,8,15,0),i(36,8,24,1),r(0,24,24,0,8),r(15,24,15,0x25),i(9,8,8,2))
    h.branch(4,15,0,'fail');h.emit(r(10,12,24,0x23),r(24,15,24,0x2b));h.branch(5,24,0,'fail')
    h.emit(i(12,13,14,15),i(13,0,24,15));h.branch(5,14,24,'match_ready')
    h.label('match_extension');h.branch(4,8,9,'fail')
    h.emit(i(36,8,24,0),i(9,8,8,1),r(14,24,14),r(11,10,25,0x23),r(25,14,25,0x2b))
    h.branch(5,25,0,'fail');h.emit(i(13,0,25,255));h.branch(4,24,25,'match_extension')
    h.label('match_ready');h.emit(i(9,14,14,4),r(11,10,24,0x23),r(24,14,24,0x2b))
    h.branch(5,24,0,'fail');h.emit(r(10,15,25,0x23))
    h.label('match_copy');h.emit(i(36,25,24,0),i(40,10,24,0),i(9,25,25,1),i(9,10,10,1),i(9,14,14,-1))
    h.branch(5,14,0,'match_copy');h.branch(4,0,0,'token')
    h.label('done');h.branch(5,10,11,'fail')
    h.emit(i(13,0,2,1),0x03e00008,0)
    h.label('fail');h.emit(i(13,0,2,0),0x03e00008,0)
    return h.finish()


def instruction_model():
    # Extend only the persisted small interpreter's opcode coverage; execute
    # actual emitted bytes, not a parallel decompressor implementation.
    text = Path('work/source/ruby_instruction_check.py').read_text()
    tree = ast.parse(text)
    fn = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
    source = ast.get_source_segment(text,fn)
    source = source.replace('range(100000)','range(5000000)')
    source = source.replace('elif f==33:', 'elif f==2:regs[d]=regs[t]>>((w>>6)&31)\n            elif f==37:regs[d]=regs[s]|regs[t]\n            elif f==33:')
    source = source.replace('elif f==33:', 'elif f==3:regs[d]=(regs[t] if regs[t]<0x80000000 else regs[t]-0x100000000)>>((w>>6)&31)\n            elif f==33:')
    source = source.replace('elif f==43:', 'elif f==42:regs[d]=int((regs[s] if regs[s]<0x80000000 else regs[s]-0x100000000)<(regs[t] if regs[t]<0x80000000 else regs[t]-0x100000000))\n            elif f==43:')
    source = source.replace('elif op==13:', 'elif op==12:regs[t]=regs[s]&v\n        elif op==40:mem[(regs[s]+sv)&0xffffffff]=regs[t]&255\n        elif op==13:')
    source = source.replace('elif op in (35,36):', 'elif op==37:\n            a=(regs[s]+sv)&0xffffffff;reads.extend(range(a,a+2));regs[t]=int.from_bytes(bytes(mem[a+i] for i in range(2)),\'little\')\n        elif op in (35,36):')
    source = source.replace('elif op==43:', 'elif op==41:\n            a=(regs[s]+sv)&0xffffffff\n            for n,x in enumerate((regs[t]&65535).to_bytes(2,\'little\')):mem[a+n]=x\n        elif op==43:')
    source = source.replace('def execute(code,regs,mem):', 'def execute(code,regs,mem,initial_pc=None):')
    source = source.replace('pc=B;pending=None', 'pc=B if initial_pc is None else initial_pc;pending=None')
    source = source.replace('elif op==2:', 'elif op==3:\n            regs[31]=pc+8;nextjump=((pc+4)&0xf0000000)|(w&0x3ffffff)*4\n        elif op==2:')
    scope = dict(struct=struct,B=0x1750000)
    exec(compile(source,'<font instruction model>','exec'),scope)
    return scope


def instruction_cases():
    scope = instruction_model()
    code = decompress(); cases = []
    samples = [(b'',0,True),(encode(b'A'),1,True),(encode(b'A'*2048),2048,True),
               (encode(bytes(range(256))*16),4096,True),(encode(b'ABC'*16384),49152,True),
               (b'\xF0',1,False),(b'\x20A',2,False),(b'\x10A\x00\x00',5,False),
               (b'\x10A\x02\x00',5,False),(b'\x1FA\x01\x00',100,False),
               (b'\x10A\x01\x00',4,False),(b'\x10A',2,False)]
    frozen=Path('work/output/0.1.15-dialogue-assets/EBOOT.BIN').read_bytes()
    import json
    meta=json.loads(Path('work/output/0.1.15-dialogue-assets/setup_patch.en.json').read_text())
    ph=struct.unpack_from('<8I',frozen,116)
    start=ph[1]+meta['high_bank']-ph[2]
    bank=frozen[start:start+meta['high_bank_bytes']]
    samples.append((encode(bank),len(bank),True))
    extended=bank+raster_glyph('\u00e1')+raster_glyph('\u00e9')
    samples.append((encode(extended),len(extended),True))
    for encoded,size,valid in samples:
        regs = [0]*32
        for n in range(16,30):regs[n]=0x76540000+n
        regs[4:8]=[0x200000,len(encoded),0x300000,size];regs[31]=0xDEADBEE0
        before=regs[:]
        class Memory(dict):
            def __setitem__(self,address,value):
                assert 0x300000 <= address < 0x300000+size, 'Write outside destination'
                super().__setitem__(address,value)
        mem=Memory({0x200000+n:x for n,x in enumerate(encoded)})
        pc,out,reads=scope['execute'](code,regs,mem)
        assert pc==0xDEADBEE0 and out[2]==int(valid)
        assert out[4:8]==before[4:8] and out[16:24]==before[16:24] and out[26:32]==before[26:32]
        assert all(0x200000 <= a < 0x200000+len(encoded) or 0x300000 <= a < 0x300000+size for a in reads)
        if valid:assert bytes(mem[0x300000+n] for n in range(size)) == decode(encoded,size)
        cases.append(dict(input_bytes=len(encoded),output_bytes=size,valid=valid,passed=True))
    return dict(native_code_bytes=len(code),native_instruction_cases=cases,
                no_external_calls=True,no_absolute_addresses=True,no_assets_written=True)


def initializer_cases():
    scope=instruction_model(); base=scope['B']; state=0x210000; packed=0x230000
    legacy=0x16fa000; decoder=0x1760000; allocated=0x40cc040
    code,relocs=initialize(legacy,state,packed,24790,193024,decoder)
    cases=[]
    for mode in ('success','allocation_failed','decode_failed','already_ready','failed_no_retry'):
        regs=[0]+[0x87650000+n for n in range(1,32)];regs[29]=0x300000;regs[31]=0xdeadbeec
        original=regs[:];mem={};events=[]
        def put(address,value):
            for n,x in enumerate(struct.pack('<I',value)):mem[address+n]=x
        def word(address):return int.from_bytes(bytes(mem[address+n] for n in range(4)),'little')
        put(state,allocated if mode=='already_ready' else 0)
        put(state+4,3 if mode=='already_ready' else 1 if mode=='failed_no_retry' else 0)
        pc=base; expected=None
        for _ in range(6):
            pc,regs,reads=scope['execute'](code,regs,mem,pc)
            if pc==original[31]:break
            events.append(pc);resume=regs[31]
            if pc==legacy:
                # The wrapper must preserve exactly the legacy result, not
                # restore pre-initialization A/V/T register values.
                for n in [2,3,4,5,6,7,*range(8,16),24,25]:regs[n]=0x45670000+n
                expected=regs[:];expected[29]=original[29];expected[31]=original[31]
            elif pc==0xc70:
                assert regs[4]==193024 and word(state)==0
                result=0 if mode=='allocation_failed' else allocated
                for n in [2,3,4,5,6,7,*range(8,16),24,25]:regs[n]=0x98760000+n
                regs[2]=result
            elif pc==decoder:
                assert regs[4:8]==[packed,24790,allocated,193024] and word(state)==0
                result=int(mode!='decode_failed')
                for n in [2,3,4,5,6,7,*range(8,16),24,25]:regs[n]=0x98760000+n
                regs[2]=result
            elif pc==0xca0:
                assert mode=='decode_failed' and regs[4]==allocated and word(state)==0
                for n in [2,3,4,5,6,7,*range(8,16),24,25]:regs[n]=0x98760000+n
            else:raise AssertionError(hex(pc))
            pc=resume
        else:raise AssertionError('Initializer did not return')
        assert regs==expected, (mode,'ABI corruption')
        target_status={'success':3,'allocation_failed':1,'decode_failed':2,'already_ready':3,'failed_no_retry':1}[mode]
        assert word(state+4)==target_status
        assert word(state)==(allocated if mode in ('success','already_ready') else 0)
        expected_events=[legacy]+([] if mode in ('already_ready','failed_no_retry') else [0xc70]+([] if mode=='allocation_failed' else [decoder]+([0xca0] if mode=='decode_failed' else [])))
        assert events==expected_events
        cases.append(dict(mode=mode,status=target_status,pointer=word(state),calls=[hex(x) for x in events],passed=True))
    return dict(code_bytes=len(code),explicit_relocations=[dict(offset=x,type=y) for x,y in relocs],
                cases=cases,post_legacy_volatile_registers_preserved=True,no_assets_written=True)


def uploader_cases():
    scope=instruction_model();state=0x210000;lookup=0x230000;bank=0x40cc040
    code,relocs=uploader(state,lookup);cases=[]
    for glyph in (0,31,32,65,126,127,128,129,130,131,0x81,0x8140,0xf040):
        for ready in (False,True):
            regs=[0]*32;regs[21]=0x200000;regs[5]=0x987654;regs[31]=0xdeadbeec
            mem={0x200000:glyph&255,0x200001:glyph>>8}
            for n,x in enumerate(struct.pack('<I',bank if ready else 0)):mem[state+n]=x
            for n in range(131):
                value=n if n in range(32,127) or n in (128,129,130) else 65535
                for k,x in enumerate(struct.pack('<H',value)):mem[lookup+2*n+k]=x
            pc,out,reads=scope['execute'](code,regs,mem)
            latin=glyph in range(32,127) or glyph in (128,129,130)
            expected=0xea5ec if latin and ready else 0xea6ec if latin else 0xea5cc
            assert pc==expected
            if latin and ready:
                assert out[8]==bank+glyph*256 and out[4:8]==[0,64,64,64]
                assert out[21]==0xffffffff and out[22]==0
            elif not latin:assert out[8]==0x987654 and out[21]==0
            assert all(x in range(0x200000,0x200002) or x in range(state,state+4) or x in range(lookup,lookup+262) for x in reads)
            cases.append(dict(glyph=hex(glyph),ready=ready,continuation=hex(pc),passed=True))
    return dict(code_bytes=len(code),explicit_relocations=[dict(offset=x,type=y) for x,y in relocs],cases=cases,
                failure_skips_latin_and_fails_candidate_qa=True,japanese_native_fallback_preserved=True)


if __name__ == '__main__':
    import json
    print(json.dumps(dict(decoder=instruction_cases(),initializer=initializer_cases(),uploader=uploader_cases()),indent=2))
