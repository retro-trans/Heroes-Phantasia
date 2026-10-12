"""Dry exact native font binary-search bound proof; no game writes."""
import json,struct
from pathlib import Path
from font_vram_hooks import instruction_model
from font_ram_plan import SOURCE


def audit():
    frozen=SOURCE.read_bytes();off=struct.unpack_from('<I',frozen,120)[0]
    payload=frozen[off:off+struct.unpack_from('<I',frozen,132)[0]]
    hi,lo=struct.unpack_from('<II',payload,0x52c)
    table=((hi&65535)<<16)+struct.unpack('<h',struct.pack('<H',lo&65535))[0]-0x16f9b00
    entries=list(struct.iter_unpack('<Iff',payload[table:table+326*12]))
    assert len(entries)==326 and len(set(x[0]for x in entries))==326 and entries==sorted(entries)
    entries=sorted(entries+[(129,326.,-1.),(130,327.,-1.)])
    native=Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf').read_bytes()
    # Execute the native search from after descriptor loads through the exact
    # equality/not-found exit, stopping before FPU size calculation atEA5BC.
    scope=instruction_model();scope['B']=0xea574;code=native[0xea574+192:0xea5bc+192]
    mem={0x200000+n:x for n,x in enumerate(b''.join(struct.pack('<Iff',*e)for e in entries))}
    cases=[]
    for key in [e[0]for e in entries]+[entries[-1][0]+1]:
        regs=[0]*32;regs[4]=key;regs[6]=0x200000;regs[9]=len(entries)-1
        pc,out,reads=scope['execute'](code,regs,mem)
        assert pc==0xea5bc and all(0x200000<=x<0x200000+len(entries)*12 for x in reads)
        index=(out[21]-0x200000)//12
        if key<=entries[-1][0]:assert entries[index][0]==key
        cases.append(dict(key=hex(key),index=index,found=key<=entries[-1][0],passed=True))
    return dict(descriptor_semantics='inclusive_last_record_index',old_record_count=326,old_bound=325,
                new_record_count=328,new_bound=327,native_search_cases=len(cases),
                first_case=cases[0],last_present_case=cases[-2],not_found_after_last=cases[-1],
                no_assets_written=True)


if __name__=='__main__':print(json.dumps(audit(),indent=2))
