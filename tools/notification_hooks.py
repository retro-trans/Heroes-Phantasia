"""Pure bounded notification helper proposals; no executable writer."""
from dialogue_vwf_hooks import Block, r
from live_vwf import i,j

def gold_terminate():
    """81074: S1 is completed digit-byte count; SP14 begins numeric scratch.

    Native104D8 caps count at8, hence at most16 bytes before this NUL.
    The branch's saved registers beginSP40. No numeric semantics change.
    """
    # Loop81058 leaves A1=SP+S1-2 after its81070 delay increments S1.
    # Replay both words displaced by the new J/NOP at81074/81078.
    h=Block();h.emit(i(40,5,0,0x16),i(9,30,5,0x100),j(0x8107c),i(9,29,7,0x14))
    return h.finish()

def cases():
    from font_vram_hooks import instruction_model
    scope=instruction_model(); results=[]
    for value in (0,1,999999,9999999,99999999,2147483647,-2147483648):
        # Exact signed-count semantics; native absolute INT_MIN stays negative.
        magnitude=-value if value<0 else value
        signed_magnitude=magnitude if magnitude<0x80000000 else magnitude-0x100000000
        digits=next((n for n,bound in enumerate((10,100,1000,10000,100000,1000000,10000000),1)
                     if signed_magnitude<bound),8)
        scratch=0x600014; emitted=digits*2
        memory={scratch+n:0xaa for n in range(44)}
        for n in range(emitted):memory[scratch+n]=0x82 if n%2==0 else 0x4f
        regs=[0]*32;regs[5]=0x600000+emitted-2;regs[17]=emitted;regs[29]=0x600000;regs[30]=0x305dc8
        pc,out,reads=scope['execute'](gold_terminate(),regs,memory)
        assert pc==0x8107c and out[5]==0x305ec8 and out[7]==scratch and out[29]==0x600000
        assert memory[scratch+emitted]==0
        assert all(memory[scratch+n]==0xaa for n in range(emitted+1,44))
        assert out[17]==emitted and out[30]==0x305dc8
        results.append(dict(value=value,native_count=digits,digit_bytes=emitted,nul_written_after_digits=True,passed=True))
    return dict(status='dry_gold_termination_not_installed',bytes=len(gold_terminate()),cases=results,
        guarded_entry_rva='0x81074',expected_word='0x27c50100',return_rva='0x8107c',
        native_signed_numeric_semantics_preserved=True,runtime_verified=False)
