"""Use the actually truncated tail rails to select the native fill origin.

Only fan-origin selection changes. Geometry, speaker endpoints and text widths
remain untouched. Two reclaimed spans retain the original loaded extent.
"""
import inspect, struct
import english_bubble_layout_v10 as original
from dialogue_vwf_hooks import Block, r
from live_vwf import i, j
from english_bubble_layout_v10 import fp, fconstant

def generate(return_rva,hub_rva,spare_rva,capacity,spare_capacity=128):
    source=inspect.getsource(original.socket_hub).replace('def socket_hub(return_rva):','def generated(return_rva,head_rva):')
    start=source.index("    h.label('candidate')")
    end=source.index('    for fd,rd in ((2,10),(3,11)):',start)
    source=source[:start]+"    h.label('candidate');h.emit(j(head_rva),0)\n    h.label('after_candidate')\n"+source[end:]
    source=source.replace('i(13,0,9,4)', 'i(13,0,9,8)').replace('0x3e000000','0x3d800000')
    env=globals().copy();labels=[]
    class Capture(Block):
        def finish(self): labels.append(self.labels.copy());return super().finish()
    env['Block']=Capture;exec(source,env)
    # Main loop now leaves enough room for the first half of the candidate
    # calculation. The second half occupies a verified unused native pool.
    probe=env['generated'](return_rva,0);head_rva=hub_rva+len(probe)
    code=env['generated'](return_rva,head_rva);resume=hub_rva+labels[-1]['after_candidate']*4
    h=Block();h.emit(i(49,8,10,0x2d0),i(49,8,11,0x2d4),r(0,5,24,0,3),r(8,24,24))
    for fd,off,axis in ((2,0,10),(3,4,11),(0,16,10),(1,20,11)):
        h.emit(i(49,24,fd,off));fp(h,0,fd,fd,axis)
        h.emit(0x4600000d|(fd<<11)|(fd<<6),0x46800020|(fd<<11)|(fd<<6))
    fp(h,0,2,2,0);fp(h,0,3,3,1);fconstant(h,0,0x3f000000);fp(h,2,2,2,0);fp(h,2,3,3,0)
    # E5010 submits bank zero as a triangle fan. E50CC..E518C instead
    # interleaves banks one and two into a border triangle strip: they do
    # not use a hub and can have disjoint kernels after raster rounding.
    # Select and validate only the actually rendered fan's integer cone.
    for fd,off,axis in ((0,8,10),(1,12,11)):
        h.emit(i(49,24,fd,off));fp(h,0,fd,fd,axis)
        h.emit(0x4600000d|(fd<<11)|(fd<<6),0x46800020|(fd<<11)|(fd<<6))
    fp(h,1,0,2,0);fp(h,1,1,3,1);fp(h,2,0,0,4);fp(h,2,1,1,4);fp(h,0,2,2,0);fp(h,0,3,3,1)
    h.emit(i(57,8,2,0xe8),i(57,8,3,0xec));head=h.finish()
    # Leave two words for each cross-span continuation; no heap allocation.
    first_bytes=capacity-len(code)-8
    if first_bytes<0 or first_bytes%4: raise ValueError('Hub split capacity differs')
    first=head[:first_bytes]+struct.pack('<II',j(spare_rva),0)
    spare=head[first_bytes:]+struct.pack('<II',j(resume),0)
    if len(spare)>spare_capacity or len(code)+len(first)>capacity: raise ValueError('Quantized hub exceeds reclaimed padding')
    return code+first,spare,dict(main_bytes=len(code)+len(first),spare_bytes=len(spare),candidate_math_bytes=len(head),quantized_tail_cone=True,native_integer_fan_checked=True,border_banks_rendered_as_strip=True,vertices_and_tail_endpoints_unchanged=True)
