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


# Low-zero floating constants need no final ORI. Keep the typed-reference
# scanner-safe integer construction and reclaim existing code bytes.
_fconstant_full=fconstant
def fconstant(h,fd,bits):
    if bits&65535:_fconstant_full(h,fd,bits)
    else:h.emit(i(13,0,25,bits>>16),r(0,25,25,0,16),0x44800000|(25<<16)|(fd<<11))


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
    # Each family needs only its largest authored horizontal corner cut plus
    # 10px text clearance. Store half-pixel padding in the audited free bytes.
    for points in native_corners():
        left=min(x for x,y in points);right=max(x for x,y in points)
        cut=max(right-x if n<4 else x-left for n,(x,y)in enumerate(points))
        output.append(round((cut+10)*2))
    output.extend(bytes(864-len(output)))
    for points in native_corners():
        top=min(y for x,y in points);bottom=max(y for x,y in points)
        output.extend(struct.pack('<BB',round((max(points[1][1],points[6][1])-top+9.5)*2),round((bottom-min(points[2][1],points[5][1])+9.5)*2)))
    # Compact descriptors, corner and socket clearances fit the reclaimed912B.
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
    source = source.replace('i(11, 12, 24, 5)', 'i(11, 12, 24, 8)')
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
    # Use this family's real corner clearance instead of a global 44px pad.
    h.emit(i(49,11,0,0x2c));address(h,7,descriptor+848)
    h.emit(i(35,29,24,92),r(7,24,7),i(36,7,24,0),0x44800000|(24<<16)|(6<<11),0x46800020|(6<<11)|(6<<6))
    fconstant(h,7,0x3f000000);fp(h,2,6,6,7);fp(h,0,0,0,6)
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
    fp(h,1,5,3,4);h.emit(i(11,12,24,3));h.branch(4,24,0,'required_height')
    fp(h,0x3c,0,5,2);h.branch(17,8,0,'top_limit')
    h.label('required_height');fp(h,6,2,5)
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
    # The seed preserves the native tip and reverse base-to-tip direction.
    h.emit(i(49,29,8,200),i(49,29,9,204),i(49,29,4,76),i(49,8,5,0x2d4))
    fp(h,1,8,8,4);fp(h,1,9,9,5)
    h.emit(i(57,29,8,112),i(57,29,9,116))
    h.emit(i(35,29,10,96),i(9,10,24,1),i(12,24,24,6),i(9,24,24,-1),i(12,24,24,7),r(0,24,24,0,3),r(29,24,24),i(49,24,4,0),i(49,24,5,4))
    h.emit(i(9,10,24,1),i(12,24,24,6),r(0,24,24,0,3),r(29,24,24),i(49,24,6,0),i(49,24,7,4))
    fp(h,1,6,6,4);fp(h,1,7,7,5)
    h.emit(i(49,29,10,212),i(49,29,11,216))
    fp(h,1,8,8,4);fp(h,1,9,9,5)
    # u = cross(P-A,V)/cross(D,V), preserving the authored ray exactly.
    fp(h,2,8,8,11);fp(h,2,9,9,10);fp(h,1,8,8,9)
    fp(h,2,0,6,11);fp(h,2,1,7,10);fp(h,1,0,0,1);fp(h,3,8,8,0)
    fp(h,2,0,6,6);fp(h,2,1,7,7);fp(h,0,0,0,1);fp(h,4,2,0)
    # A visible sharp tail: half-base <=8px and <=35% of perpendicular
    # reach. Separate inner/outer rails supply the native dark outline.
    h.emit(i(49,29,9,112),i(49,29,10,116))
    fp(h,1,9,9,4);fp(h,1,10,10,5)
    fp(h,2,9,9,7);fp(h,2,10,10,6);fp(h,1,9,9,10);fp(h,5,9,9)
    fconstant(h,1,0x3eb33333);fp(h,2,9,9,1);fp(h,3,9,9,0)
    fconstant(h,1,0x41000000);fp(h,3,1,1,2)
    fp(h,0x3c,0,1,9);h.branch(17,8,0,'width_ready');fp(h,6,9,1)
    h.label('width_ready');h.emit(j(BANK_WIDTH),0)
    h.label('bank_width_ready');h.emit(i(57,29,9,100))
    h.emit(i(49,29,0,100));fp(h,1,9,8,0);fp(h,0,8,8,0)
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
    h.emit(j(hub_rva),0);h.label('hub_done')
    h.emit(i(13,0,24,1),i(43,29,24,196),i(43,8,24,0x5c)) # primary success flag+68
    h.label('return');h.emit(i(9,29,29,128),j(return_rva),0)
    return h.finish(),helper_rva+h.labels['bounds_ready']*4,helper_rva+h.labels['hub_done']*4,helper_rva+h.labels['bank_width_ready']*4

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

from english_bubble_rays_v10 import tail_fit, leaf as serish_leaf, BANK_WIDTH

def socket_hub(return_rva):
    """Place the fill origin just inside the socket; test the native integer fan."""
    h=Block();h.emit(r(0,0,24,0x10),i(43,29,24,112),r(0,0,24,0x12),i(43,29,24,116),i(43,29,13,100),i(35,8,5,0xe0),i(9,5,5,1),i(12,5,5,6));h.branch(5,5,0,'index_ready')
    h.emit(i(13,0,5,8));h.label('index_ready');h.emit(i(13,0,9,4));fconstant(h,4,0x3e000000)
    h.label('candidate');h.emit(r(0,5,24,0,3),r(8,24,24),i(49,24,2,0),i(49,24,3,4),i(49,24,0,16),i(49,24,1,20))
    fp(h,0,2,2,0);fp(h,0,3,3,1);fconstant(h,0,0x3f000000);fp(h,2,2,2,0);fp(h,2,3,3,0)
    h.emit(i(49,29,0,212),i(49,29,1,216));fp(h,2,0,0,4);fp(h,2,1,1,4);fp(h,0,2,2,0);fp(h,0,3,3,1)
    h.emit(i(49,8,10,0x2d0),i(49,8,11,0x2d4));fp(h,0,2,2,10);fp(h,0,3,3,11);h.emit(i(57,8,2,0xe8),i(57,8,3,0xec))
    for fd,rd in ((2,10),(3,11)):
        h.emit(0x4600000d|(fd<<11)|(fd<<6),0x44000000|(rd<<16)|(fd<<11))
    h.emit(r(8,0,4),i(13,0,15,11))
    def vertex(xreg,yreg):
        h.emit(i(49,4,0,0),i(49,4,1,4));fp(h,0,0,0,10);fp(h,0,1,1,11)
        for fd,rd in ((0,xreg),(1,yreg)):
            h.emit(0x4600000d|(fd<<11)|(fd<<6),0x44000000|(rd<<16)|(fd<<11))
    vertex(6,7)
    h.label('edge');h.emit(i(9,4,4,8),i(13,0,24,1));h.branch(5,15,24,'next_point');h.emit(r(8,0,4))
    h.label('next_point');vertex(12,13)
    h.emit(r(6,10,14,0x23),r(13,11,24,0x23),r(14,24,0,0x18),r(0,0,14,0x12),
        r(7,11,25,0x23),r(12,10,24,0x23),r(25,24,0,0x18),r(0,0,24,0x12),r(14,24,14,0x23))
    h.branch(1,14,0,'failed');h.emit(r(12,0,6),r(13,0,7),i(9,15,15,-1));h.branch(5,15,0,'edge');h.branch(4,0,0,'return')
    h.label('failed');fp(h,0,4,4,4);h.emit(i(9,9,9,-1));h.branch(5,9,0,'candidate')
    h.label('return');h.emit(i(35,29,24,112),r(24,0,0,0x11),i(35,29,24,116),r(24,0,0,0x13),i(35,29,13,100),j(return_rva),0);return h.finish()
