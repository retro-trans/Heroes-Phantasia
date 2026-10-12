"""Custom standard-tail polygons and control-aware English geometry generators.

Uses the existing ten-vertex renderer and source tail endpoints. No allocation,
text mutation or automatic mouth tracking occurs in the runtime helper.
"""
import inspect, struct
import bubble_layout_hooks as legacy
from bubble_layout_hooks import constant, fconstant, fp
from dialogue_vwf_hooks import Block, address, r
from live_vwf import i, j
from bubble_metrics import load_templates

# Selectors X: L,L+8,R-8,R,tailX-3,tailX+3,tipX.
# Y: T,T+8,B-8,B,tailY-3,tailY+3,tipY.
CORNERS = [
 [(4,0),(6,6),(5,0),(3,1),(3,2),(2,3),(1,3),(0,2),(0,1),(1,0)],
 [(2,0),(3,4),(6,6),(3,5),(3,2),(2,3),(1,3),(0,2),(0,1),(1,0)],
 [(2,0),(3,1),(3,4),(6,6),(3,5),(2,3),(1,3),(0,2),(0,1),(1,0)],
 [(2,0),(3,1),(3,2),(5,3),(6,6),(4,3),(1,3),(0,2),(0,1),(1,0)],
 [(2,0),(3,1),(3,2),(2,3),(5,3),(6,6),(4,3),(0,2),(0,1),(1,0)],
 [(2,0),(3,1),(3,2),(2,3),(1,3),(0,5),(6,6),(0,4),(0,1),(1,0)],
 [(2,0),(3,1),(3,2),(2,3),(1,3),(0,2),(0,5),(6,6),(0,4),(1,0)],
 [(2,0),(3,1),(3,2),(2,3),(1,3),(0,2),(0,1),(4,0),(6,6),(5,0)],
]

def descriptors():
    output = bytearray()
    for t in load_templates():
        family = (t['template_id']-3)%10
        supported = family < 8 and t['count'] == 10
        tip = family+1 if supported else 0
        ys = [y for n,(_,y) in enumerate(t['outline']) if n != tip]
        if any(y*2!=round(y*2)for y in ys):raise ValueError('Non-half-pixel source bound')
        output.extend(struct.pack('<BBhh', family if supported else 255, tip, round(min(ys)*2), round(max(ys)*2)))
    return bytes(output)+bytes(v for row in CORNERS for pair in row for v in pair)

def primary(helper, descriptor, core, epilogue_rva):
    """Keep the proved native association and ABI; replace scan/fit decisions."""
    source = inspect.getsource(legacy.geometry)
    source = source.replace('def geometry(', 'def generated(')
    start = source.index("    h.label('byte')")
    end = source.index("    h.label('validated')", start)
    scanner = '''    h.label('byte')
    h.emit(i(11,6,24,1024));h.branch(4,24,0,'return')
    h.emit(i(36,5,7,0));h.branch(4,7,0,'row_end')
    h.emit(i(13,0,24,14));h.branch(4,7,24,'row_end')
    for c in (0x10,0x11,0x12):
        h.emit(i(13,0,24,c));h.branch(4,7,24,'row_end')
    for c,count in ((5,3),(0x16,2),(0x17,1),(0x1a,1)):
        h.emit(i(13,0,24,c));h.branch(4,7,24,'args'+str(count))
    h.emit(i(13,0,24,0x0f));h.branch(4,7,24,'hideo_reading')
    h.emit(i(13,0,24,0xf0));h.branch(4,7,24,'pair')
    h.emit(i(11,7,24,32));h.branch(5,24,0,'return')
    h.emit(i(11,7,24,131));h.branch(4,24,0,'return')
    h.emit(i(13,0,24,127));h.branch(4,7,24,'return')
    h.branch(4,0,0,'advance')
    for count in (1,2,3):
        h.label('args'+str(count));h.emit(i(11,6,24,1024-count));h.branch(4,24,0,'return')
        for n in range(1,count+1):
            h.emit(i(36,5,7,n),i(9,7,24,-48),i(11,24,24,10));h.branch(4,24,0,'return')
        h.emit(i(9,5,5,count+1),i(9,6,6,count+1));h.branch(4,0,0,'byte')
    h.label('pair');h.emit(i(11,6,24,1023));h.branch(4,24,0,'return')
    h.emit(i(36,5,7,1),i(9,7,24,-64),i(11,24,24,2));h.branch(4,24,0,'return')
    h.emit(i(9,5,5,2),i(9,6,6,2));h.branch(4,0,0,'byte')
    h.label('advance');h.emit(i(9,5,5,1),i(9,6,6,1));h.branch(4,0,0,'byte')
    h.label('hideo_reading');h.emit(i(11,6,24,1016));h.branch(4,24,0,'return')
    for n,value in enumerate(b'2Hideo\\x0f',1):
        h.emit(i(36,5,7,n),i(13,0,24,value));h.branch(5,7,24,'return')
    h.emit(i(9,5,5,8),i(9,6,6,8));h.branch(4,0,0,'byte')
    h.label('row_end');h.emit(i(35,29,24,76),i(9,24,24,-1),i(43,29,24,76));h.branch(4,24,0,'validated')
    h.emit(i(35,29,24,60),i(9,24,24,0xe8),i(43,29,24,60),i(35,24,5,4));guard_pointer(h,5,aligned=False)
    h.emit(i(13,0,6,0));h.branch(4,0,0,'byte')
'''
    source = source[:start]+scanner+source[end:]
    start = source.index('    if compact_catalog:', source.index("    h.label('validated')"))
    end = source.index("    h.label('return')", start)
    source = source[:start]+"    h.emit(j(HELPER),0)\n"+source[end:]
    source = source.replace("    h.label('copy');", "    h.emit(i(35,8,7,0x2d0),i(43,29,7,80))\n    h.label('copy');")
    source = source.replace("    h.emit(i(13, 0, 6, 0))", "    h.emit(i(43,29,5,92),i(13,0,6,0))")
    # Validate each actual visible row, including later pages/speakers.
    setup = """    h.emit(i(43,29,5,92),i(35,11,5,4));guard_pointer(h,5)
    h.emit(i(35,11,6,0x20),r(0,6,7,0,8),r(0,6,24,0,4),r(7,24,7,0x23),r(0,6,24,0,3),r(7,24,7,0x23),r(5,7,5))
    h.emit(r(0,12,7,0,8),r(0,12,24,0,4),r(7,24,7,0x23),r(0,12,24,0,3),r(7,24,7,0x23),r(5,7,7));guard_pointer(h,7)
    h.emit(i(43,29,5,60),i(43,29,12,76),i(35,5,5,4));guard_pointer(h,5,aligned=False)
    h.emit(i(13,0,6,0))"""
    source = source.replace("    h.emit(i(43,29,5,92),i(13,0,6,0))",setup)
    source = source.replace("    if association_fix:\n        h.emit(i(35, 29, 7, 72), r(10, 7, 24, 0x2b))\n        h.branch(5, 24, 0, 'return')","")
    source = source.replace('j(0xe4e14)', 'j(0x2e5200)')
    source = source.replace("    h.emit(r(4, 0, 8));", "    h.emit(i(43,29,0,64),i(43,29,0,68))\n    h.emit(r(4, 0, 8));")
    # No second copy pass is used by custom geometry; remove its old flag test.
    source = source.replace("h.emit(i(35, 29, 25, 68)); h.branch(5, 25, 0, 'tail_repair' if serish_mouth else 'return')", "pass")
    source = source.replace("    h.emit(i(35, 8, 5, 0x2d0), r(5, 25, 24, 0x24)); h.branch(4, 24, 25, 'return')", "    for off in (0x2d0,0x2d4):\n        h.emit(i(35,8,5,off),r(5,25,24,0x24));h.branch(4,24,25,'return')")
    captures = []
    class Capture(Block):
        def finish(self):
            result = super().finish(); captures.append(self.labels.copy()); return result
    env = legacy.__dict__.copy(); env.update(HELPER=helper, Block=Capture)
    exec(source,env)
    data = env['generated'](descriptor,True,True,True,131)
    pos = captures[0]['return']*4
    # Fallback must restore floating-point native offsets on reused windows.
    # E5424..E546C converts source signed shorts to float before storing them.
    h = Block();h.emit(i(35,29,24,68));h.branch(5,24,0,'restore')
    h.emit(i(35,29,9,64));h.branch(4,9,0,'restore')
    for off,dest in ((4,0x30c),(6,0x310),(8,0x304),(10,0x308)):
        h.emit(i(33,9,24,off),0x44800000|(24<<16))
        h.emit(0x46800020,i(57,8,0,dest))
    h.label('restore');epilogue = h.finish()+data[pos:]
    return data[:pos]+struct.pack('<II',j(epilogue_rva),0), core+pos, epilogue

def secondary(descriptor, return_rva, fit_rva, helper_rva, contour_rva):
    h=Block();h.emit(i(9,29,29,-128))
    # Native +70 selects each row's X origin. Only the reviewed default
    # centered rows share this body/halfwidth contract.
    h.emit(i(35,11,5,4));legacy.guard_pointer(h,5)
    # Native new[] header: payload bytes and complemented row count.
    h.emit(i(35,5,6,-12),r(6,0,6,0x27),i(11,6,24,33));h.branch(4,24,0,'return');h.branch(4,6,0,'return')
    h.emit(r(0,6,7,0,8),r(0,6,24,0,4),r(7,24,7,0x23),r(0,6,24,0,3),r(7,24,7,0x23),i(35,5,24,-16));h.branch(5,7,24,'return')
    h.emit(i(35,11,24,0x20),r(24,12,24),r(6,24,24,0x2b));h.branch(5,24,0,'return')
    h.emit(r(5,7,7));legacy.guard_pointer(h,7)
    h.emit(i(35,11,6,0x20),i(11,6,24,4096));h.branch(4,24,0,'return')
    h.emit(r(0,6,7,0,8),r(0,6,24,0,4),r(7,24,7,0x23),r(0,6,24,0,3),r(7,24,7,0x23),r(5,7,5))
    h.emit(r(12,0,6))
    h.label('alignment_row');h.emit(i(9,5,7,0xe8));legacy.guard_pointer(h,7)
    h.emit(i(35,5,7,0x70),i(9,7,7,1));h.branch(5,7,0,'return')
    h.emit(i(9,5,5,0xe8),i(9,6,6,-1));h.branch(5,6,0,'alignment_row')
    # Original immutable template pointer is in the primary frame at +64.
    h.emit(i(35,29,7,192),i(37,8,10,0x318))
    address(h,9,descriptor)
    h.emit(r(0,10,24,0,2),r(0,10,25,0,1),r(24,25,24),r(9,24,9),i(36,9,10,0))
    h.emit(i(11,10,24,8));h.branch(4,24,0,'return')
    h.emit(i(43,29,10,64),i(43,29,7,68))
    for off,fd in ((2,2),(4,3)):
        h.emit(i(33,9,24,off),0x44800000|(24<<16)|(fd<<11),0x46800020|(fd<<11)|(fd<<6))
    fconstant(h,6,0x3f000000);fp(h,2,2,2,6);fp(h,2,3,3,6)
    h.emit(i(49,11,0,0x2c));fconstant(h,6,0x41200000);fp(h,0,0,0,6)
    fconstant(h,6,0x41c00000);fp(h,0x3c,0,0,6);h.branch(17,8,0,'width_ready');fp(h,6,0,6)
    h.label('width_ready');h.emit(i(49,8,1,0x2d0),i(49,8,11,0x2d4))
    # Preserve the authored X, even when the body is clamped independently.
    h.emit(i(49,29,10,208),i(57,29,10,72))
    fconstant(h,6,0x41180000);fp(h,0,6,0,6)
    fconstant(h,7,0x43eb4000);fp(h,1,7,7,0)
    fp(h,0x3c,0,7,6);h.branch(17,8,1,'return')
    fp(h,0x3c,0,1,6);h.branch(17,8,0,'clamp_right');fp(h,6,1,6)
    h.label('clamp_right');fp(h,0x3c,0,7,1);h.branch(17,8,0,'center_ready');fp(h,6,1,7)
    h.label('center_ready');h.emit(i(57,8,1,0x2d0),i(57,29,1,76),i(57,29,0,80))
    # Keep the old bottom where possible. Additional height grows upward first.
    fconstant(h,6,0x437c0000);fp(h,1,6,6,11)
    fp(h,0x3c,0,6,3);h.branch(17,8,0,'bottom_ready');fp(h,6,3,6)
    h.label('bottom_ready');h.emit(i(9,12,24,-1),0x44800000|(24<<16)|(4<<11))
    h.emit(0x46800020|(4<<11)|(4<<6));fconstant(h,6,0x41b00000);fp(h,2,4,4,6)
    fconstant(h,6,0x42100000);fp(h,0,4,4,6) # 16px glyph +20px padding
    fp(h,1,5,3,4);fp(h,0x3c,0,5,2);h.branch(17,8,0,'top_limit');fp(h,6,2,5)
    h.label('top_limit');fconstant(h,6,0x42100000);fp(h,1,6,6,11)
    fp(h,0x3c,0,2,6);h.branch(17,8,0,'height_ready');fp(h,6,2,6)
    fp(h,0,5,2,4);fp(h,0x3c,0,3,5);h.branch(17,8,0,'height_ready');fp(h,6,3,5)
    h.label('height_ready');h.emit(i(57,29,2,84),i(57,29,3,88),j(fit_rva),0)
    h.label('bounds_ready');h.branch(4,24,0,'return')
    h.emit(i(49,29,2,84),i(49,29,3,88),i(35,29,7,68))
    # Body and speaker offsets shift with the new upper edge; center/tail Y stay.
    fconstant(h,6,0x41200000);fp(h,0,4,2,6)
    h.emit(i(33,7,24,6),0x44800000|(24<<16)|(5<<11),0x46800020|(5<<11)|(5<<6))
    fp(h,1,5,4,5);h.emit(i(57,8,4,0x310))
    h.emit(i(33,7,24,10),0x44800000|(24<<16)|(4<<11),0x46800020|(4<<11)|(4<<6))
    fp(h,0,4,4,5);h.emit(i(57,8,4,0x308))
    h.emit(i(13,0,13,0));h.label('bank')
    # Each fill bank has a 1.5px inset/outset; outline uses the midpoint.
    fconstant(h,6,0);h.branch(4,13,0,'border_ready')
    fconstant(h,6,0xbfc00000);h.emit(i(13,0,24,1));h.branch(4,13,24,'border_ready')
    fconstant(h,6,0x3fc00000)
    h.label('border_ready');h.emit(i(49,29,0,80),i(49,29,2,84),i(49,29,3,88))
    fp(h,0,0,0,6);fp(h,1,2,2,6);fp(h,0,3,3,6)
    fp(h,7,4,0);h.emit(i(57,29,4,0));fconstant(h,7,0x41000000)
    fp(h,0,5,4,7);h.emit(i(57,29,5,4));fp(h,1,5,0,7);h.emit(i(57,29,5,8),i(57,29,0,12))
    h.emit(i(57,29,2,28));fp(h,0,5,2,7);h.emit(i(57,29,5,32))
    fp(h,1,5,3,7);h.emit(i(57,29,5,36),i(57,29,3,40))
    # Source tip belongs to index family+1. Read source banks independently.
    h.emit(i(35,29,10,64),i(9,10,24,1),r(0,24,24,0,3),i(35,29,7,68),r(7,24,7))
    h.emit(i(49,7,8,0x0c),i(49,7,9,0x10));h.emit(i(13,0,24,1));h.branch(4,13,24,'tip_ready')
    h.emit(i(49,7,4,0xfc),i(49,7,5,0x100));h.branch(5,13,0,'outer_tip')
    fp(h,0,8,8,4);fp(h,0,9,9,5);fconstant(h,6,0x3f000000);fp(h,2,8,8,6);fp(h,2,9,9,6)
    h.branch(4,0,0,'tip_ready');h.label('outer_tip');fp(h,6,8,4);fp(h,6,9,5)
    h.label('tip_ready');h.emit(i(49,29,4,72),i(49,29,5,76));fp(h,0,8,8,4);fp(h,1,8,8,5)
    h.emit(i(57,29,8,24),i(57,29,9,52));fconstant(h,6,0x41300000)
    fp(h,7,4,0);fp(h,0,4,4,6);fp(h,1,5,0,6)
    fp(h,0x3c,0,8,4);h.branch(17,8,0,'tx_high');fp(h,6,8,4)
    h.label('tx_high');fp(h,0x3c,0,5,8);h.branch(17,8,0,'ty_low');fp(h,6,8,5)
    h.label('ty_low');fp(h,0,4,2,6);fp(h,1,5,3,6)
    fp(h,0x3c,0,9,4);h.branch(17,8,0,'ty_high');fp(h,6,9,4)
    h.label('ty_high');fp(h,0x3c,0,5,9);h.branch(17,8,0,'base_ready');fp(h,6,9,5)
    h.label('base_ready');fconstant(h,6,0x40400000)
    fp(h,1,4,8,6);fp(h,0,5,8,6);h.emit(i(57,29,4,16),i(57,29,5,20))
    fp(h,1,4,9,6);fp(h,0,5,9,6);h.emit(i(57,29,4,44),i(57,29,5,48))
    # The contour ledger keeps the original winding and exactly ten vertices.
    h.emit(i(35,29,10,96));address(h,15,contour_rva)
    h.emit(r(0,10,24,0,4),r(0,10,25,0,2),r(24,25,24),r(15,24,15))
    h.emit(r(0,13,24,0,8),r(0,13,25,0,4),r(24,25,24,0x23),r(8,24,4),i(13,0,14,10))
    h.label('vertex');h.emit(i(36,15,24,0),r(0,24,24,0,2),r(29,24,24),i(49,24,4,0))
    h.emit(i(36,15,24,1),r(0,24,24,0,2),r(29,24,24),i(49,24,5,28))
    h.emit(i(57,4,4,0),i(57,4,5,4),i(9,4,4,8),i(9,15,15,2),i(9,14,14,-1));h.branch(5,14,0,'vertex')
    h.emit(i(9,13,13,1),i(11,13,24,3));h.branch(5,24,0,'bank')
    h.emit(i(13,0,24,1),i(43,29,24,196)) # primary success flag+68
    h.label('return');h.emit(i(9,29,29,128),j(return_rva),0)
    return h.finish(),helper_rva+h.labels['bounds_ready']*4

def tail_fit(return_rva):
    """Keep an external tip and select its contour separately from source ID.

    Uses the secondary 128-byte frame and primary's saved caller registers.
    A supported tip stays fixed in world space; the body moves when necessary.
    """
    h=Block()
    h.emit(i(35,29,10,64),i(9,10,24,1),r(0,24,24,0,3),i(35,29,7,68),r(7,24,7))
    h.emit(i(49,7,8,0x0c),i(49,7,9,0x10),i(49,7,4,0xfc),i(49,7,5,0x100))
    fp(h,0,8,8,4);fp(h,0,9,9,5);fconstant(h,6,0x3f000000);fp(h,2,8,8,6);fp(h,2,9,9,6)
    h.emit(i(49,29,4,72),i(49,29,1,76),i(49,29,0,80),i(49,29,2,84),i(49,29,3,88),i(49,8,11,0x2d4))
    fp(h,0,8,8,4);fp(h,1,8,8,1) # tip relative to the clamped center
    fconstant(h,6,0x40c00000);fp(h,0,4,0,6)
    fp(h,0x3c,0,8,4);h.branch(17,8,0,'right')
    fp(h,7,4,4);fp(h,0x3c,0,4,8);h.branch(17,8,0,'left')
    fp(h,1,4,2,6);fp(h,0x3c,0,4,9);h.branch(17,8,0,'top')
    fp(h,0,4,3,6);fp(h,0x3c,0,9,4);h.branch(17,8,0,'bottom')
    # The tip is enclosed or too close to the border. Try the authored side,
    # then the opposite horizontal side and finally vertical placement.
    h.emit(i(9,10,24,-5),i(11,24,24,2));h.branch(5,24,0,'try_right_body')
    h.branch(4,0,0,'try_left_body')
    h.label('try_right_body');candidate_x(h,True,'right_body_valid','try_left_body')
    h.label('try_left_body');candidate_x(h,False,'left_body_valid','try_right_again')
    h.label('try_right_again');candidate_x(h,True,'right_body_valid','try_above')
    h.label('right_body_valid');fp(h,0,8,8,1);fp(h,1,8,8,4);fp(h,6,1,4)
    h.emit(i(57,29,1,76),i(57,8,1,0x2d0));h.branch(4,0,0,'left')
    h.label('left_body_valid');fp(h,0,8,8,1);fp(h,1,8,8,4);fp(h,6,1,4)
    h.emit(i(57,29,1,76),i(57,8,1,0x2d0));h.branch(4,0,0,'right')
    h.label('try_above');fp(h,1,5,3,2);fconstant(h,6,0x41400000);fp(h,1,4,9,6);fp(h,1,7,4,5)
    fconstant(h,6,0x42100000);fp(h,1,6,6,11);fp(h,0x3c,0,7,6);h.branch(17,8,1,'try_below')
    fp(h,6,3,4);fp(h,6,2,7);h.emit(i(57,29,2,84),i(57,29,3,88));h.branch(4,0,0,'bottom')
    h.label('try_below');fconstant(h,6,0x41400000);fp(h,0,4,9,6);fp(h,0,7,4,5)
    fconstant(h,6,0x437c0000);fp(h,1,6,6,11);fp(h,0x3c,0,6,7);h.branch(17,8,1,'fail')
    fp(h,6,2,4);fp(h,6,3,7);h.emit(i(57,29,2,84),i(57,29,3,88));h.branch(4,0,0,'top')
    # Choose the corner whose omitted bevel lies closest to the tail base.
    h.label('right');fp(h,0,4,2,3);fconstant(h,6,0x3f000000);fp(h,2,4,4,6)
    h.emit(i(13,0,10,1));fp(h,0x3c,0,9,4);h.branch(17,8,1,'chosen');h.emit(i(13,0,10,2));h.branch(4,0,0,'chosen')
    h.label('left');fp(h,0,4,2,3);fconstant(h,6,0x3f000000);fp(h,2,4,4,6)
    h.emit(i(13,0,10,6));fp(h,0x3c,0,9,4);h.branch(17,8,1,'chosen');h.emit(i(13,0,10,5));h.branch(4,0,0,'chosen')
    h.label('top');fconstant(h,6,0);h.emit(i(13,0,10,0));fp(h,0x3c,0,8,6);h.branch(17,8,0,'chosen');h.emit(i(13,0,10,7));h.branch(4,0,0,'chosen')
    h.label('bottom');fconstant(h,6,0);h.emit(i(13,0,10,3));fp(h,0x3c,0,8,6);h.branch(17,8,0,'chosen');h.emit(i(13,0,10,4))
    h.label('chosen');h.emit(i(43,29,10,96),i(13,0,24,1),j(return_rva),0)
    h.label('fail');h.emit(i(49,29,0,208),i(57,8,0,0x2d0),i(13,0,24,0),j(return_rva),0)
    return h.finish()

def candidate_x(h,right_body,valid,invalid):
    # Candidate center uses immutable world tip X, retaining its endpoint.
    fp(h,0,4,8,1);fconstant(h,6,0x41400000);fp(h,0,5,0,6)
    fp(h,0 if right_body else 1,4,4,5)
    fconstant(h,6,0x41180000);fp(h,0,6,0,6)
    fp(h,0x3c,0,4,6);h.branch(17,8,1,invalid)
    fconstant(h,6,0x43eb4000);fp(h,1,6,6,0)
    fp(h,0x3c,0,6,4);h.branch(17,8,1,invalid)
    h.branch(4,0,0,valid)
