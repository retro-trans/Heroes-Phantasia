"""Execute emitted bootstrap/CRC/decoder instructions with bounded native ABI mocks."""
import hashlib,json,struct,zlib
from pathlib import Path
from font_trailer_hooks import initialize,checksum,MAGIC,IO
from font_vram_hooks import decompress
from font_ram_plan import decode

ELF=Path('work/output/0.1.17-dialogue-assets/EBOOT.BIN');R=ELF.with_name('setup_patch.en.json')
SHA='321d1e5918ddb9ea7258163acc9185fe6a0e54c04d38d50e2cc8ee6fb14c1235'
B=0x1750000;CRC=0x1760000;DEC=0x1770000;STATE=0x1780000;PATH=0x1780100;LEGACY=0x16fa000;FILE_OFFSET=6000000

def run(fault=None,chunk=20268,prior=(0,0)):
    raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
    report=json.loads(R.read_text());ph=struct.unpack_from('<8I',raw,116);p=ph[1]+report['high_bank']-ph[2];packed=raw[p:p+20268]
    bank=decode(packed,193024)
    if fault=='decode':packed=bytes(20268) # CRC-valid but invalid zero-offset LZ4.
    code,rel,scalars=initialize(LEGACY,STATE,PATH,FILE_OFFSET,20268,193024,DEC,CRC,zlib.crc32(packed))
    programs={B:code,CRC:checksum(),DEC:decompress()}
    instructions={base+n:struct.unpack_from('<I',data,n)[0]for base,data in programs.items()for n in range(0,len(data),4)}
    regs=[0x12340000+n for n in range(32)];regs[0]=0;regs[29]=0x200000;regs[31]=0xdeadbeec
    memory={};reads=[];writes=[];owned=set();calls=[];allocation=0;file_cursor=0;file_open=False;expected=None
    stream=MAGIC+struct.pack('<II',20268,193024)+packed
    if fault=='header':stream=b'BADMAGIC'+stream[8:]
    if fault=='crc':stream=stream[:-1]+bytes([stream[-1]^1])
    def put(address,data):memory.update({address+n:value for n,value in enumerate(data)})
    put(STATE,struct.pack('<2I',*prior));put(PATH,b'disc0:/PSP_GAME/SYSDIR/EBOOT.BIN\0')
    def native(pc):
        nonlocal allocation,file_cursor,file_open,expected
        args=regs[:];calls.append(dict(target=hex(pc),arguments=[args[n]for n in range(4,10)]))
        result=0;high=0
        if pc==LEGACY:
            for n in [2,3,4,5,6,7,*range(8,16),24,25]:regs[n]=0x43210000+n
            expected=regs[:];expected[29]+=176;expected[31]=0xdeadbeec;return
        if pc==0xc70:
            allocation+=1;result=0x04100000 if allocation==1 else 0x040cc000
            if fault==('bank'if allocation==1 else 'scratch'):result=0
            if result:owned.add(result)
            assert args[4]==(193024 if allocation==1 else 20272)
        elif pc==0xca0:
            assert args[4]in owned;owned.remove(args[4])
        elif pc==IO['open']:
            assert args[4]==PATH and args[5:7]==[1,0]
            if fault=='open':result=-5
            else:result=7;file_open=True
        elif pc==IO['seek64']:
            assert file_open and args[4]==7 and args[6:9]==[FILE_OFFSET,0,0]
            result=FILE_OFFSET if fault!='seek'else FILE_OFFSET-1
            high=1 if fault=='seek_hi'else 0
        elif pc==IO['read']:
            assert file_open and args[4]==7;dest,size=args[5:7]
            if fault=='read'or(fault=='read_late'and file_cursor>=16):result=-6
            elif fault=='eof'or(fault=='eof_late'and file_cursor>=16):result=0
            elif fault=='oversize':result=size+1
            else:
                result=min(size,chunk,len(stream)-file_cursor);content=stream[file_cursor:file_cursor+result]
                if file_cursor<16:assert 0x1fff50+112<=dest and dest+result<=0x1fff50+128
                else:assert 0x040cc000<=dest and dest+result<=0x040cc000+20268
                put(dest,content);file_cursor+=result
        elif pc==IO['close']:
            assert args[4]==7
            if fault=='close'and file_open:result=-8
            else:file_open=False
        else:raise AssertionError('Unmodeled native call '+hex(pc))
        for n in [2,3,4,5,6,7,*range(8,16),24,25]:regs[n]=0xabcdef00+n
        regs[2]=result&0xffffffff;regs[3]=high
    pc=B;pending=None
    def signed(value):return value if value<0x80000000 else value-0x100000000
    for cycles in range(5000000):
        if pc==0xdeadbeec:break
        if pc not in instructions:
            native(pc);pc=regs[31];pending=None;continue
        w=instructions[pc];op=w>>26;s=w>>21&31;t=w>>16&31;d=w>>11&31;v=w&65535;sv=v if v<32768 else v-65536;nextjump=None
        if op==0:
            f=w&63;shift=w>>6&31
            if f==0:regs[d]=regs[t]<<shift
            elif f==2:regs[d]=regs[t]>>shift
            elif f==33:regs[d]=regs[s]+regs[t]
            elif f==35:regs[d]=regs[s]-regs[t]
            elif f==37:regs[d]=regs[s]|regs[t]
            elif f==38:regs[d]=regs[s]^regs[t]
            elif f==39:regs[d]=~(regs[s]|regs[t])
            elif f==42:regs[d]=int(signed(regs[s])<signed(regs[t]))
            elif f==43:regs[d]=int(regs[s]<regs[t])
            elif f==8:nextjump=regs[s]
            else:raise AssertionError(hex(w))
        elif op==9:regs[t]=regs[s]+sv
        elif op==11:regs[t]=int(regs[s]<(sv&0xffffffff))
        elif op==12:regs[t]=regs[s]&v
        elif op==13:regs[t]=regs[s]|v
        elif op==15:regs[t]=v<<16
        elif op in (35,36):
            address=(regs[s]+sv)&0xffffffff;n=4 if op==35 else 1
            reads.extend(range(address,address+n));regs[t]=int.from_bytes(bytes(memory[address+k]for k in range(n)),'little')
        elif op in (40,43):
            address=(regs[s]+sv)&0xffffffff;n=4 if op==43 else 1
            writes.extend(range(address,address+n));put(address,(regs[t]&((1<<(8*n))-1)).to_bytes(n,'little'))
        elif op in (4,5):
            if (regs[s]==regs[t])==(op==4):nextjump=pc+4+sv*4
        elif op in (2,3):
            if op==3:regs[31]=pc+8
            nextjump=((pc+4)&0xf0000000)|(w&0x3ffffff)*4
        else:raise AssertionError(hex(w))
        regs=[x&0xffffffff for x in regs];regs[0]=0;pc=pending if pending is not None else pc+4;pending=nextjump
    else:raise AssertionError('Instruction limit')
    assert expected is not None and regs==[x&0xffffffff for x in expected]
    state=struct.unpack('<2I',bytes(memory[STATE+k]for k in range(8)))
    expected_status={'bank':1,'scratch':5,'open':4,'seek':4,'seek_hi':4,'read':4,'read_late':4,'eof':4,'eof_late':4,'oversize':4,'close':4,'header':6,'crc':6,'decode':2}.get(fault,3)
    if prior!=(0,0):assert state==prior and len(calls)==1
    elif fault:
        assert state==(0,expected_status)and not owned
        # A native close error is recorded as failure; inability to close cannot
        # be repaired by retrying forever. Both bounded attempts are exercised.
        if fault!='close':assert not file_open
    else:
        assert state==(0x04100000,3)and owned=={0x04100000}and not file_open
        assert bytes(memory[0x04100000+k]for k in range(193024))==bank
    allowed=lambda address:0x1fff50<=address<0x200000 or STATE<=address<STATE+8 or 0x040cc000<=address<0x040cc000+20268 or 0x04100000<=address<0x04100000+193024
    assert all(allowed(address)for address in reads+writes)
    return dict(fault=fault,read_chunk=chunk,prior_state=prior,status=state[1],native_calls=len(calls),instruction_cycles=cycles,abi_preserved=True,all_accesses_bounded=True)

def tests():
    return [run(),run(chunk=257),run(chunk=7),*[run(fault=f)for f in ('bank','scratch','open','seek','seek_hi','read','read_late','eof','eof_late','oversize','close','header','crc','decode')],run(prior=(0x04100000,3)),run(prior=(0,4))]

if __name__=='__main__':print(json.dumps(dict(cases=tests(),assets_written=False),indent=2))
