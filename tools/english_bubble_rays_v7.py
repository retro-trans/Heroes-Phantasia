"""Original Japanese tail rays, clipped to the English body viewport.

All coordinates are native pixels. Helpers use the existing saved geometry ABI
and reclaimed code spans; no allocation, layer timing or portrait changes.
"""
import inspect, struct
from bubble_layout_hooks import fconstant, fp
from dialogue_vwf_hooks import Block, r,address
from live_vwf import i,j,jal

LEAF=0x2e5200
SEED=LEAF+16
CLIP=LEAF+720
HORIZONTAL=LEAF+896

def fc(h,fd,value):fconstant(h,fd,struct.unpack('<I',struct.pack('<f',value))[0])
def load(h,fd,off):h.emit(i(49,29,fd,off))
def store(h,fd,off):h.emit(i(57,29,fd,off))
def clamp(h,fd,lo,hi,label):
    fp(h,0x3c,0,fd,lo);h.branch(17,8,0,label+'_hi');fp(h,6,fd,lo)
    h.label(label+'_hi');fp(h,0x3c,0,hi,fd);h.branch(17,8,0,label+'_end');fp(h,6,fd,hi)
    h.label(label+'_end')

def seed():
    """F8/9 world tip; saved reverse native ray in primary free locals84/88."""
    h=Block();h.emit(i(35,29,10,64),i(9,10,24,1),r(0,24,24,0,3),i(35,29,7,68),r(7,24,7))
    fc(h,6,.5)
    for fd,off in ((8,0x0c),(9,0x10)):
        h.emit(i(49,7,fd,off),i(49,7,4,off+0xf0));fp(h,0,fd,fd,4);fp(h,2,fd,fd,6)
    fc(h,6,.25)
    for fd,off,tip in ((4,0x0c,8),(5,0x10,9)):
        h.emit(i(49,7,fd,off-8))
        for delta in (8,0xf0-8,0xf0+8):
            h.emit(i(49,7,7,off+delta));fp(h,0,fd,fd,7)
        fp(h,2,fd,fd,6);fp(h,1,fd,fd,tip)
    store(h,4,212);store(h,5,216)
    load(h,4,72);h.emit(i(49,8,5,0x2d4));fp(h,0,8,8,4);fp(h,0,9,9,5)
    # Preserve the already reviewed Serish exception, now before fitting.
    h.emit(i(37,8,24,0x318),i(13,0,25,8));h.branch(5,24,25,'return')
    for off,bits in ((0x2d0,0x43b88000),(0x2d4,0x42c60000)):
        h.emit(i(35,8,24,off));from bubble_layout_hooks import constant
        constant(h,25,bits);h.branch(5,24,25,'return')
    h.emit(i(35,29,7,220))
    for n,value in enumerate(b'Who will accompany you?\x12\x0e'):
        h.emit(i(36,7,24,n),i(13,0,25,value));h.branch(5,24,25,'return')
    fc(h,8,243);fc(h,9,134)
    h.label('return');store(h,8,112);store(h,9,116);store(h,8,200);store(h,9,204);h.emit(0x03e00008,0)
    return h.finish()

def clip():
    """Intersect k interval F8..9 with lo<=P+kV<=hi (F4..7)."""
    h=Block();fc(h,0,.00001);fp(h,5,1,5);fp(h,0x3c,0,1,0);h.branch(17,8,1,'parallel')
    fp(h,1,0,6,4);fp(h,3,0,0,5);fp(h,1,1,7,4);fp(h,3,1,1,5)
    fp(h,0x3c,0,1,0);h.branch(17,8,0,'ordered');fp(h,6,2,0);fp(h,6,0,1);fp(h,6,1,2)
    h.label('ordered');fp(h,0x3c,0,8,0);h.branch(17,8,0,'upper');fp(h,6,8,0)
    h.label('upper');fp(h,0x3c,0,1,9);h.branch(17,8,0,'return');fp(h,6,9,1);h.branch(4,0,0,'return')
    h.label('parallel');fp(h,0x3c,0,4,6);h.branch(17,8,1,'invalid');fp(h,0x3c,0,7,4);h.branch(17,8,0,'return')
    h.label('invalid');fc(h,8,2);fc(h,9,1)
    h.label('return');h.emit(0x03e00008,0);return h.finish()

def intervals(h):fc(h,8,1);fc(h,9,1024)
def callclip(h):h.emit(jal(CLIP),0)
def tail_fit(return_rva):
    h=Block();h.emit(i(43,29,31,120),i(43,29,0,124),jal(SEED),0)
    load(h,2,84);load(h,3,88);fp(h,1,2,3,2);store(h,2,100)
    h.label('retry_vertical');intervals(h);h.emit(i(35,29,24,124));h.branch(4,24,0,'minimum_ready');fc(h,8,.25)
    h.label('minimum_ready');load(h,4,116);load(h,5,216)
    # The outer border expands1.5px. Keep every socket bank on the same
    # side of the anchor, including nearly horizontal Japanese rays.
    fp(h,5,0,5);fc(h,1,.00001);fp(h,0x3c,0,0,1);h.branch(17,8,1,'horizontal')
    fc(h,1,3);fp(h,3,1,1,0);fp(h,0x3c,0,8,1);h.branch(17,8,0,'reach_ready');fp(h,6,8,1)
    h.label('reach_ready');fc(h,6,36);fc(h,7,252)
    h.emit(0x44800000|(0<<11));fp(h,0x3c,0,0,5);h.branch(17,8,0,'bottom_bounds')
    load(h,2,100);fp(h,1,7,7,2);h.emit(i(13,0,24,7),i(43,29,24,96));h.branch(4,0,0,'vertical_clip')
    h.label('bottom_bounds');load(h,2,100);fp(h,0,6,6,2);h.emit(i(13,0,24,3),i(43,29,24,96))
    h.label('vertical_clip');callclip(h)
    # Use each native family's real top/bottom corner insets, rather than
    # a global40px reserve which needlessly excludes anchors near the edge.
    address(h,7,0x2e7460+608);h.emit(i(35,29,24,92),r(0,24,24,0,4),r(7,24,7))
    h.emit(i(35,29,24,96),i(13,0,25,7));h.branch(5,24,25,'bottom_cuts')
    h.emit(i(36,7,24,14),i(36,7,25,0));h.branch(4,0,0,'cuts_ready')
    h.label('bottom_cuts');h.emit(i(36,7,24,8),i(36,7,25,6))
    h.label('cuts_ready');h.emit(0x44800000|(24<<16)|(6<<11),0x44800000|(25<<16)|(7<<11),0x46800020|(6<<11)|(6<<6),0x46800020|(7<<11)|(7<<6))
    fc(h,0,.5);fp(h,2,6,6,0);fp(h,2,7,7,0);fc(h,0,4);fp(h,0,6,6,0);fp(h,0,7,7,0);store(h,6,104);store(h,7,108)
    fc(h,0,9.5);fp(h,0,6,6,0);fc(h,0,470.5);fp(h,1,7,0,7)
    load(h,4,112);load(h,5,212);callclip(h)
    fp(h,0x3c,0,9,8);h.branch(17,8,1,'retry')
    # Attachment lies on the original reverse ray. Keep the body center as
    # close to the authored fit as the available long edge allows.
    load(h,4,112);load(h,5,212);fp(h,2,5,5,8);fp(h,0,4,4,5)
    load(h,0,80);load(h,6,108);fp(h,1,6,6,0);fp(h,0,6,4,6)
    load(h,7,104);fp(h,1,7,0,7);fp(h,0,7,4,7)
    load(h,1,76);clamp(h,1,6,7,'center');load(h,0,80);fc(h,6,9.5);fp(h,0,6,6,0);fc(h,7,470.5);fp(h,1,7,7,0);clamp(h,1,6,7,'viewport')
    store(h,1,76);h.emit(i(57,8,1,0x58))
    load(h,4,116);load(h,5,216);fp(h,2,5,5,8);fp(h,0,4,4,5)
    h.emit(i(35,29,24,96),i(13,0,25,7));h.branch(4,24,25,'top_ready');load(h,2,100);fp(h,1,4,4,2)
    h.label('top_ready');h.emit(i(49,8,11,0x2d4));fp(h,1,4,4,11);store(h,4,84);load(h,2,100);fp(h,0,4,4,2);store(h,4,88)
    h.emit(i(35,29,31,120),i(13,0,24,1),j(return_rva),0)
    h.label('retry');h.emit(i(35,29,24,124));h.branch(5,24,0,'horizontal');h.emit(i(13,0,24,1),i(43,29,24,124));h.branch(4,0,0,'retry_vertical')
    h.label('horizontal');h.emit(i(43,29,0,124),j(HORIZONTAL),0)
    return h.finish()

def horizontal(return_rva):
    h=Block();h.label('retry_horizontal');intervals(h);h.emit(i(35,29,24,124));h.branch(4,24,0,'minimum_ready');fc(h,8,.5)
    h.label('minimum_ready');load(h,4,112);load(h,5,212);load(h,0,80);fp(h,0,0,0,0);fc(h,6,9.5);fc(h,7,470.5)
    h.emit(0x44800000|(1<<11));fp(h,0x3c,0,1,5);h.branch(17,8,0,'right_bounds')
    fp(h,1,7,7,0);h.emit(i(13,0,24,6),i(43,29,24,96));h.branch(4,0,0,'horizontal_clip')
    h.label('right_bounds');fp(h,0,6,6,0);h.emit(i(13,0,24,1),i(43,29,24,96))
    h.label('horizontal_clip');callclip(h);load(h,4,116);load(h,5,216);fc(h,6,56);fc(h,7,232);callclip(h)
    fp(h,0x3c,0,9,8);h.branch(17,8,1,'retry')
    load(h,4,112);load(h,5,212);fp(h,2,5,5,8);fp(h,0,4,4,5);load(h,0,80)
    h.emit(i(35,29,24,96),i(13,0,25,6));h.branch(5,24,25,'right_center');fp(h,0,1,4,0);h.branch(4,0,0,'center_ready')
    h.label('right_center');fp(h,1,1,4,0)
    h.label('center_ready');store(h,1,76);h.emit(i(57,8,1,0x58))
    load(h,4,116);load(h,5,216);fp(h,2,5,5,8);fp(h,0,4,4,5);load(h,0,100)
    fc(h,6,20);fp(h,1,7,4,6);fp(h,1,6,4,0);fc(h,5,20);fp(h,0,6,6,5)
    load(h,1,84);h.emit(i(49,8,11,0x2d4));fp(h,0,1,1,11);clamp(h,1,6,7,'attachment')
    fc(h,6,37.5);fc(h,7,250.5);fp(h,1,7,7,0);clamp(h,1,6,7,'viewport')
    fp(h,1,1,1,11);store(h,1,84);fp(h,0,1,1,0);store(h,1,88)
    h.emit(i(35,29,31,120),i(13,0,24,1),j(return_rva),0)
    h.label('retry');h.emit(i(35,29,24,124));h.branch(5,24,0,'fail');h.emit(i(13,0,24,1),i(43,29,24,124));h.branch(4,0,0,'retry_horizontal')
    h.label('fail');load(h,0,208);h.emit(i(57,8,0,0x58),i(35,29,31,120),i(13,0,24,0),j(return_rva),0)
    return h.finish()

def leaf(size,return_rva):
    h=Block();h.branch(4,0,0,'footer');h.emit(0,0)
    out=bytearray(size);out[:len(h.code)*4]=struct.pack('<'+str(len(h.code))+'I',*h.code)
    # Entry skips helpers and keeps the historic native footer site/relocation.
    struct.pack_into('<I',out,0,i(4,0,0,(size-8)//4-1))
    for pos,code,end in ((16,seed(),720),(720,clip(),896),(896,horizontal(return_rva),size-8)):
        if pos+len(code)>end:raise ValueError('Ray helper exceeds reclaimed Serish padding: '+str((pos,len(code),end)))
        out[pos:pos+len(code)]=code
    struct.pack_into('<II',out,size-8,j(0xe4e14),0);return bytes(out)
