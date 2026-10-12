"""Pure bounded font bootstrap from an unloaded EBOOT trailer. No writer."""
import struct
from dialogue_vwf_hooks import Block,r
from live_vwf import i

IO={'open':0x29444c,'read':0x2943fc,'seek64':0x294454,'close':0x29440c}
MAGIC=b'HPVF018\0'
HEADER_BYTES=16

def checksum():
    """Leaf CRC32: A0 input/A1 exact length; V0 CRC. Changes T0..T4 only."""
    h=Block();h.emit(i(9,0,2,-1),r(4,0,8),r(5,0,9),i(15,0,12,0xedb8),i(13,12,12,0x8320))
    h.label('byte');h.branch(4,9,0,'done');h.emit(i(36,8,10,0),r(2,10,2,0x26),i(13,0,11,8))
    h.label('bit');h.emit(i(12,2,10,1),r(0,2,2,2,1));h.branch(4,10,0,'nextbit');h.emit(r(2,12,2,0x26))
    h.label('nextbit');h.emit(i(9,11,11,-1));h.branch(5,11,0,'bit');h.emit(i(9,8,8,1),i(9,9,9,-1));h.branch(4,0,0,'byte')
    h.label('done');h.emit(r(2,0,2,0x27),0x03e00008,0)
    return h.finish()

def initialize(legacy,state,path,trailer_offset,packed_bytes,decoded_bytes,decoder,crc_function,expected_crc):
    """Legacy init first; allocate bank/scratch, read/check/decode, free scratch.

    FD/allocations tracked in stack locals; every failing branch closes FD and
    frees both allocations. Publish bank only after successful complete decode.
    Native IO is user-mode existing imports; seek64 follows o32 alignment.
    Status:1 bank allocation,2 decode,3 ready,4 IO,5 scratch,6 integrity failure.
    """
    if packed_bytes!=20268 or decoded_bytes!=193024 or not 0<trailer_offset<0x7fffffff:raise ValueError('Reviewed exact font/trailer bounds required')
    h=Block();rel=[];scalar_sites=[]
    def constant(reg,value,label=None):
        if label:scalar_sites.append(dict(name=label,offset=len(h.code)*4,value=value))
        if 0<=value<65536:h.emit(i(13,0,reg,value))
        else:h.emit(i(15,0,reg,value>>16),i(13,reg,reg,value))
    def addr(reg,value):
        p=len(h.code)*4;h.emit(i(15,0,reg,(value+0x8000)>>16),i(9,reg,reg,value));rel.extend([(p,5),(p+4,6)])
    def call(value):rel.append((len(h.code)*4,4));h.emit(0x0c000000|(value>>2),0)
    def fail(status):h.emit(i(13,0,8,status),i(43,29,8,100));h.branch(4,0,0,'cleanup')
    regs=[2,3,4,5,6,7,*range(8,16),24,25]
    h.emit(i(9,29,29,-176),i(43,29,31,172));call(legacy)
    for n,reg in enumerate(regs):h.emit(i(43,29,reg,16+n*4))
    addr(8,state);h.emit(i(35,8,9,0));h.branch(5,9,0,'restore');h.emit(i(35,8,9,4));h.branch(5,9,0,'restore')
    h.emit(i(43,29,0,80),i(43,29,0,84),i(9,0,8,-1),i(43,29,8,88))
    constant(4,decoded_bytes);call(0xc70);h.branch(4,2,0,'bank_failed');h.emit(i(43,29,2,80))
    constant(4,(packed_bytes+15)&~15);call(0xc70);h.branch(4,2,0,'scratch_failed');h.emit(i(43,29,2,84))
    addr(4,path);h.emit(i(13,0,5,1),i(13,0,6,0));call(IO['open'])
    h.emit(r(2,0,8,0x2a));h.branch(5,8,0,'io_failed');h.emit(i(43,29,2,88))
    h.emit(r(2,0,4),i(13,0,5,0));constant(6,trailer_offset,'trailer_file_offset');h.emit(i(13,0,7,0),i(13,0,8,0));call(IO['seek64'])
    constant(8,trailer_offset,'seek_result_file_offset');h.branch(5,2,8,'io_failed');h.branch(5,3,0,'io_failed')
    def exact_read(label,total,header=False):
        h.emit(i(43,29,0,92));h.label(label)
        h.emit(i(35,29,4,88),i(35,29,8,92))
        if header:h.emit(i(9,29,5,112))
        else:h.emit(i(35,29,5,84))
        h.emit(r(5,8,5));constant(6,total);h.emit(r(6,8,6,0x23),i(43,29,6,96));call(IO['read'])
        h.emit(r(0,2,8,0x2a));h.branch(4,8,0,'io_failed');h.emit(i(35,29,8,96),r(8,2,8,0x2b));h.branch(5,8,0,'io_failed')
        h.emit(i(35,29,8,92),r(8,2,8),i(43,29,8,92));constant(9,total);h.branch(5,8,9,label)
    exact_read('read_header',HEADER_BYTES,True)
    for offset,value in enumerate(struct.unpack('<4I',MAGIC+struct.pack('<II',packed_bytes,decoded_bytes))):
        h.emit(i(35,29,8,112+offset*4));constant(9,value);h.branch(5,8,9,'integrity_failed')
    exact_read('read_font',packed_bytes)
    h.emit(i(35,29,4,88));call(IO['close']);h.branch(5,2,0,'io_failed');h.emit(i(9,0,8,-1),i(43,29,8,88))
    h.emit(i(35,29,4,84));constant(5,packed_bytes);call(crc_function);constant(8,expected_crc);h.branch(5,2,8,'integrity_failed')
    h.emit(i(35,29,4,84));constant(5,packed_bytes);h.emit(i(35,29,6,80));constant(7,decoded_bytes);call(decoder)
    h.emit(i(13,0,8,1));h.branch(5,2,8,'decode_failed')
    h.emit(i(35,29,4,84));call(0xca0);h.emit(i(43,29,0,84));addr(8,state)
    h.emit(i(13,0,9,3),i(43,8,9,4),i(35,29,9,80),i(43,8,9,0));h.branch(4,0,0,'restore')
    for label,status in [('bank_failed',1),('scratch_failed',5),('io_failed',4),('integrity_failed',6),('decode_failed',2)]:h.label(label);fail(status)
    h.label('cleanup');h.emit(i(35,29,4,88),r(4,0,8,0x2a));h.branch(5,8,0,'scratch_cleanup');call(IO['close'])
    h.label('scratch_cleanup');h.emit(i(35,29,4,84));h.branch(4,4,0,'bank_cleanup');call(0xca0)
    h.label('bank_cleanup');h.emit(i(35,29,4,80));h.branch(4,4,0,'publish_failure');call(0xca0)
    h.label('publish_failure');addr(8,state);h.emit(i(35,29,9,100),i(43,8,9,4),i(43,8,0,0))
    h.label('restore')
    for n,reg in enumerate(regs):h.emit(i(35,29,reg,16+n*4))
    h.emit(i(35,29,31,172),0x03e00008,i(9,29,29,176))
    return h.finish(),rel,scalar_sites
