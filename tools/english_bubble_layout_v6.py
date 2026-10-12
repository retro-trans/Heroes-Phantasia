"""Custom standard-tail polygons and control-aware English geometry generators.

Uses the native renderer with eleven fitted vertices and source tail endpoints. No helper allocation,
text mutation or automatic mouth tracking occurs in the runtime helper.
"""
import inspect, struct
import bubble_layout_hooks as legacy
from bubble_layout_hooks import constant, fconstant, fp
from dialogue_vwf_hooks import Block, address, r
from live_vwf import i, j
from bubble_metrics import load_templates

# Historical ten-point selector order is used only to recover common native
# corner coordinates. Runtime ledgers contain eight body and three tail points.
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

KEYS=[(2,0),(3,1),(3,2),(2,3),(1,3),(0,2),(0,1),(1,0)]

def native_corners():
    """Common eight corners for each of the fifteen authored size families.

    Tail sockets replace one corner in the source. Recover that corner from
    the sibling sockets; majority coordinates avoid socket-specific miters.
    Every returned coordinate comes from an original Japanese template.
    """
    templates=load_templates();result=[]
    for group in range(15):
        votes=[[]for _ in KEYS]
        for family in range(8):
            t=templates[3+group*10+family]
            for n,key in enumerate(CORNERS[family]):
                if key in KEYS:votes[KEYS.index(key)].append(t['outline'][n])
        result.append([max(sorted(set(v)),key=v.count)for v in votes])
    return result

def descriptors():
    output=bytearray()
    for t in load_templates():
        f=(t['template_id']-3)%10;supported=f<8 and t['count']==10
        ys=[y for n,(_,y)in enumerate(t['outline'])if n!=f+1]
        output.extend(struct.pack('<BbbB',f if supported else 255,
            round(min(ys)*2)if supported else 0,round(max(ys)*2)if supported else 0,
            (t['template_id']-3)//10 if supported else 0))
    for points in native_corners():
        L=min(x for x,y in points);R=max(x for x,y in points)
        T=min(y for x,y in points);B=max(y for x,y in points)
        for n,(x,y)in enumerate(points):
            output.extend(struct.pack('<BB',round((R-x if n<4 else x-L)*2),
                round((y-T if n in (0,1,6,7)else B-y)*2)))
    # Compact descriptors plus native corner table fit the reclaimed 912B.
    output.extend(bytes(912-len(output)))
    for family in range(8):
        edge=(((family+1)&6)-1)&7
        for corner in range(8):
            output.append(corner)
            if corner==edge:output.extend((13,14,15))
    return bytes(output)

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
    h.emit(i(13,0,24,1));h.branch(4,7,24,'name_arg')
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
    h.label('name_arg');h.emit(i(11,6,24,1023));h.branch(4,24,0,'return')
    h.emit(i(36,5,7,1),i(9,7,24,-48),i(11,24,24,4));h.branch(4,24,0,'return')
    h.emit(i(9,5,5,2),i(9,6,6,2));h.branch(4,0,0,'byte')
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
    # Point twenty-nine is outside every original/fitted contour. Initialize
    # an absolute fill origin before fallback; native counts retain their hub.
    source = source.replace("    h.label('copy');", "    h.emit(i(35,8,7,0x2d0),i(43,8,7,0xe8),i(43,8,7,0x58),i(43,8,0,0x5c),i(35,8,7,0x2d4),i(43,8,7,0xec))\n    h.label('copy');")
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

def secondary(descriptor, return_rva, fit_rva, helper_rva, contour_rva,hub_rva=0):
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
    h.emit(r(0,10,24,0,2),r(9,24,9),i(36,9,10,0))
    h.emit(i(11,10,24,8));h.branch(4,24,0,'return')
    h.emit(i(43,29,10,64),i(43,29,7,68))
    h.emit(i(36,9,24,3),i(43,29,24,92))
    for off,fd in ((1,2),(2,3)):
        h.emit(i(32,9,24,off),0x44800000|(24<<16)|(fd<<11),0x46800020|(fd<<11)|(fd<<6))
    fconstant(h,6,0x3f000000);fp(h,2,2,2,6);fp(h,2,3,3,6)
    # 33.5px maximum native corner inset plus >10px text clearance.
    h.emit(i(49,11,0,0x2c));fconstant(h,6,0x42300000);fp(h,0,0,0,6)
    h.emit(i(49,8,1,0x2d0),i(49,8,11,0x2d4))
    # Preserve the authored X, even when the body is clamped independently.
    h.emit(i(49,29,10,208),i(57,29,10,72))
    fconstant(h,6,0x41180000);fp(h,0,6,0,6)
    fconstant(h,7,0x43eb4000);fp(h,1,7,7,0)
    fp(h,0x3c,0,7,6);h.branch(17,8,1,'return')
    fp(h,0x3c,0,1,6);h.branch(17,8,0,'clamp_right');fp(h,6,1,6)
    h.label('clamp_right');fp(h,0x3c,0,7,1);h.branch(17,8,0,'center_ready');fp(h,6,1,7)
    h.label('center_ready');h.emit(i(57,8,1,0x58),i(57,29,1,76),i(57,29,0,80))
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
    # Keep the scene's center intact. Nameplate and text use a separate body X.
    h.emit(i(49,29,10,76),i(49,29,11,72));fp(h,1,10,10,11)
    h.emit(i(33,7,24,8),0x44800000|(24<<16)|(4<<11),0x46800020|(4<<11)|(4<<6))
    fp(h,0,4,4,10);h.emit(i(57,8,4,0x304))
    h.emit(i(13,0,13,0));h.label('bank')
    # Each fill bank has a 1.5px inset/outset; outline uses the midpoint.
    h.emit(0x44800000|(6<<11));h.branch(4,13,0,'border_ready')
    fconstant(h,6,0xbfc00000);h.emit(i(13,0,24,1));h.branch(4,13,24,'border_ready')
    fconstant(h,6,0x3fc00000)
    h.label('border_ready');h.emit(i(49,29,0,80),i(49,29,2,84),i(49,29,3,88))
    fp(h,0,0,0,6);fp(h,1,2,2,6);fp(h,0,3,3,6)
    # Rebuild the eight native corners. Stretch the long spans and retain
    # each family's signed side slope and unequal corner cuts in pixel units.
    address(h,15,descriptor+608);h.emit(i(35,29,24,92),r(0,24,24,0,4),r(15,24,15))
    h.emit(r(29,0,4),i(13,0,14,0));fconstant(h,9,0x3f000000)
    h.label('corner')
    for off,fd in ((0,4),(1,5)):
        h.emit(i(36,15,24,off),0x44800000|(24<<16)|(fd<<11),0x46800020|(fd<<11)|(fd<<6));fp(h,2,fd,fd,9)
    h.emit(i(11,14,24,4));h.branch(4,24,0,'corner_left')
    fp(h,1,4,0,4);h.branch(4,0,0,'corner_y')
    h.label('corner_left');fp(h,7,6,0);fp(h,0,4,6,4)
    h.label('corner_y');h.emit(i(9,14,24,-2),i(11,24,24,4));h.branch(5,24,0,'corner_bottom')
    fp(h,0,5,2,5);h.branch(4,0,0,'corner_store')
    h.label('corner_bottom');fp(h,1,5,3,5)
    h.label('corner_store');h.emit(i(57,4,4,0),i(57,4,5,4),i(9,4,4,8),i(9,15,15,2),i(9,14,14,1),i(11,14,24,8));h.branch(5,24,0,'corner')
    # Original outline tip remains independent of the stretched body.
    h.emit(i(35,29,10,64),i(9,10,24,1),r(0,24,24,0,3),i(35,29,7,68),r(7,24,7))
    h.emit(i(49,7,8,0x0c),i(49,7,9,0x10),i(49,7,4,0xfc),i(49,7,5,0x100))
    fp(h,0,8,8,4);fp(h,0,9,9,5);fconstant(h,6,0x3f000000);fp(h,2,8,8,6);fp(h,2,9,9,6)
    h.emit(i(49,29,4,72),i(49,29,5,76));fp(h,0,8,8,4);fp(h,1,8,8,5)
    h.emit(i(57,29,8,112),i(57,29,9,116))
    # Project onto the actual sloping socket edge, not the bounding rectangle.
    # Each pair of neighboring socket families shares one complete side edge.
    h.emit(i(35,29,10,96),i(9,10,24,1),i(12,24,24,6),i(9,24,24,-1),i(12,24,24,7),r(0,24,24,0,3),r(29,24,24),i(49,24,4,0),i(49,24,5,4))
    h.emit(i(9,10,24,1),i(12,24,24,6),r(0,24,24,0,3),r(29,24,24),i(49,24,6,0),i(49,24,7,4))
    fp(h,1,6,6,4);fp(h,1,7,7,5)
    fp(h,1,8,8,4);fp(h,1,9,9,5)
    fp(h,2,8,8,6);fp(h,2,9,9,7);fp(h,0,8,8,9)
    fp(h,2,0,6,6);fp(h,2,1,7,7);fp(h,0,0,0,1);fp(h,3,8,8,0)
    fp(h,4,2,0);fconstant(h,3,0x3fc00000);fp(h,2,2,3,2)
    fconstant(h,0,0x3e19999a);fp(h,0x3c,0,8,0);h.branch(17,8,0,'projection_high');fp(h,6,8,0)
    h.label('projection_high');fconstant(h,0,0x3f59999a);fp(h,0x3c,0,0,8);h.branch(17,8,0,'projection_ready');fp(h,6,8,0)
    h.label('projection_ready')
    # Keep the fan hub 1.5px inside the edge, on the reverse tail ray, so both
    # the float contour and native integer contour contain its triangle fan.
    h.branch(5,13,0,'hub_done');h.emit(j(hub_rva),0);h.label('hub_done')
    fconstant(h,0,0x3d75c28f) # 6% either side of the projection
    fp(h,1,9,8,0);fp(h,0,8,8,0)
    fp(h,2,0,6,9);fp(h,0,0,4,0);h.emit(i(57,29,0,104))
    fp(h,2,1,7,9);fp(h,0,1,5,1);h.emit(i(57,29,1,108))
    fp(h,2,6,6,8);fp(h,0,6,4,6);h.emit(i(57,29,6,120))
    fp(h,2,7,7,8);fp(h,0,7,5,7);h.emit(i(57,29,7,124))
    h.emit(i(35,29,10,96),i(43,8,10,0xe0));address(h,15,contour_rva)
    h.emit(r(0,10,24,0,3),r(0,10,25,0,1),r(24,25,24),r(24,10,24),r(15,24,15))
    h.emit(i(49,29,10,76),i(49,29,11,72));fp(h,1,10,10,11)
    h.emit(r(0,13,24,0,8),r(0,13,25,0,4),r(24,25,24,0x23),r(8,24,4),i(13,0,14,11))
    h.label('vertex');h.emit(i(36,15,24,0),r(0,24,24,0,3),r(29,24,24),i(49,24,4,0),i(49,24,5,4))
    fp(h,0,4,4,10)
    h.emit(i(57,4,4,0),i(57,4,5,4),i(9,4,4,8),i(9,15,15,1),i(9,14,14,-1));h.branch(5,14,0,'vertex')
    h.emit(i(9,13,13,1),i(11,13,24,3));h.branch(5,24,0,'bank')
    h.emit(i(13,0,24,1),i(43,29,24,196),i(43,8,24,0x5c)) # primary success flag+68
    h.label('return');h.emit(i(9,29,29,128),j(return_rva),0)
    return h.finish(),helper_rva+h.labels['bounds_ready']*4,helper_rva+h.labels['hub_done']*4

def socket_hub(return_rva):
    """Move inside the socket along the reverse tail ray, inside its kernel.

    Moving just along the side normal can leave a shallow oblique tail's
    visibility wedge. F2 is 1.5 * edge length; F4/5 anchor, F6/7 edge delta.
    """
    h=Block()
    fp(h,2,0,6,8);fp(h,0,0,4,0);fp(h,2,1,7,8);fp(h,0,1,5,1)
    h.emit(i(49,29,3,112),i(49,29,9,116));fp(h,1,3,0,3);fp(h,1,9,1,9)
    fp(h,2,10,6,9);fp(h,2,11,7,3);fp(h,1,10,10,11);fp(h,3,2,2,10)
    fp(h,2,10,3,2);fp(h,2,11,9,2);fp(h,0,0,0,10);fp(h,0,1,1,11)
    h.emit(i(49,29,10,76),i(49,8,11,0x2d4));fp(h,0,0,0,10);fp(h,0,1,1,11)
    h.emit(i(57,8,0,0xe8),i(57,8,1,0xec),j(return_rva),0)
    return h.finish()

def serish_leaf(size):
    """Keep the reviewed scene guard/lip, adapting only its contour indexing."""
    from prepare_serish_tail_compact import leaf
    source=inspect.getsource(leaf).replace('def leaf(', 'def generated(')
    marker='    fconstant(h,0,0x43730000);'
    setup="""    h.emit(i(35,4,24,0xe0),i(9,24,24,1),i(12,24,24,6));h.branch(5,24,0,'tip_index')
    h.emit(i(13,0,24,8));h.label('tip_index');h.emit(i(9,24,24,1),r(0,24,24,0,3),r(4,24,8))
"""
    source=source.replace(marker,setup+marker)
    for old,new in (("i(57,4,0,48)","i(57,8,0,0)"),("i(57,4,1,52)","i(57,8,1,4)"),
            ("i(57,4,4,0x120)","i(57,8,0,0xf0)"),("i(57,4,5,0x124)","i(57,8,1,0xf4)"),
            ("i(57,4,4,0x210)","i(57,8,0,0x1e0)"),("i(57,4,5,0x214)","i(57,8,1,0x1e4)")):
        if old not in source:raise ValueError('Reviewed leaf store differs')
        source=source.replace(old,new)
    env=globals().copy();exec(source,env)
    return env['generated'](size)

def fan_origin():
    h=Block();h.emit(i(49,23,12,0x2d0),i(49,23,13,0x2d4),i(13,0,24,11))
    h.branch(5,16,24,'return');h.emit(i(49,23,12,0xe8),i(49,23,13,0xec))
    h.label('return');h.emit(j(0xe4ec4),0)
    return h.finish()

def vertex_count():
    """Change only successfully fitted standard draws to eleven vertices."""
    h=Block();h.emit(i(37,4,16,0),i(35,23,8,0x5c),i(9,8,8,-1));h.branch(5,8,0,'native')
    h.emit(i(13,0,16,11));h.label('native');h.emit(j(0xe4e70),r(29,0,4))
    return h.finish()

def text_origin():
    """ECE3C: substitute only the fitted text X; retain the native scene center."""
    h=Block();h.emit(i(49,8,12,0),i(35,8,9,-0x274),i(9,9,9,-1))
    h.branch(5,9,0,'return');h.emit(i(49,8,12,-0x278))
    h.label('return');h.emit(j(0xece40),0)
    return h.finish()

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
    # Try vertical placement first: a long English line must not push a
    # corner tail's body across the portrait to the opposite horizontal side.
    h.emit(i(43,29,0,100));h.emit(0x44800000|(6<<11));fp(h,0x3c,0,9,6)
    h.branch(17,8,0,'try_above');h.emit(i(13,0,24,1),i(43,29,24,100));h.branch(4,0,0,'try_below')
    # If neither vertical placement fits, use bounded horizontal alternatives.
    h.label('horizontal')
    h.emit(i(9,10,24,-5),i(11,24,24,2));h.branch(5,24,0,'try_right_body')
    h.branch(4,0,0,'try_left_body')
    h.label('try_right_body');candidate_x(h,True,'right_body_valid','try_left_body')
    h.label('try_left_body');candidate_x(h,False,'left_body_valid','try_right_again')
    h.label('try_right_again');candidate_x(h,True,'right_body_valid','fail')
    h.label('right_body_valid');fp(h,0,8,8,1);fp(h,1,8,8,4);fp(h,6,1,4)
    h.emit(i(57,29,1,76),i(57,8,1,0x58));h.branch(4,0,0,'left')
    h.label('left_body_valid');fp(h,0,8,8,1);fp(h,1,8,8,4);fp(h,6,1,4)
    h.emit(i(57,29,1,76),i(57,8,1,0x58));h.branch(4,0,0,'right')
    h.label('try_above');fp(h,1,5,3,2);fconstant(h,6,0x40400000);fp(h,1,4,9,6);fp(h,1,7,4,5)
    fconstant(h,6,0x42100000);fp(h,1,6,6,11);fp(h,0x3c,0,7,6);h.branch(17,8,1,'above_failed')
    fp(h,6,3,4);fp(h,6,2,7);h.emit(i(57,29,2,84),i(57,29,3,88));h.branch(4,0,0,'bottom')
    h.label('try_below');fp(h,1,5,3,2);fconstant(h,6,0x40400000);fp(h,0,4,9,6);fp(h,0,7,4,5)
    fconstant(h,6,0x437c0000);fp(h,1,6,6,11);fp(h,0x3c,0,6,7);h.branch(17,8,1,'below_failed')
    fp(h,6,2,4);fp(h,6,3,7);h.emit(i(57,29,2,84),i(57,29,3,88));h.branch(4,0,0,'top')
    h.label('above_failed');h.emit(i(35,29,24,100));h.branch(5,24,0,'horizontal');h.branch(4,0,0,'try_below')
    h.label('below_failed');h.emit(i(35,29,24,100));h.branch(5,24,0,'try_above');h.branch(4,0,0,'horizontal')
    # Choose the corner whose omitted bevel lies closest to the tail base.
    h.label('right');fp(h,0,4,2,3);fconstant(h,6,0x3f000000);fp(h,2,4,4,6)
    h.emit(i(13,0,10,1));fp(h,0x3c,0,9,4);h.branch(17,8,1,'chosen');h.emit(i(13,0,10,2));h.branch(4,0,0,'chosen')
    h.label('left');fp(h,0,4,2,3);fconstant(h,6,0x3f000000);fp(h,2,4,4,6)
    h.emit(i(13,0,10,6));fp(h,0x3c,0,9,4);h.branch(17,8,1,'chosen');h.emit(i(13,0,10,5));h.branch(4,0,0,'chosen')
    h.label('top');h.emit(0x44800000|(6<<11));h.emit(i(13,0,10,0));fp(h,0x3c,0,8,6);h.branch(17,8,0,'chosen');h.emit(i(13,0,10,7));h.branch(4,0,0,'chosen')
    h.label('bottom');h.emit(0x44800000|(6<<11));h.emit(i(13,0,10,3));fp(h,0x3c,0,8,6);h.branch(17,8,0,'chosen');h.emit(i(13,0,10,4))
    h.label('chosen');h.emit(i(43,29,10,96),i(13,0,24,1),j(return_rva),0)
    h.label('fail');h.emit(i(49,29,0,208),i(57,8,0,0x58),i(13,0,24,0),j(return_rva),0)
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
