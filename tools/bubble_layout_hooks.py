"""Stationary, control-light English bubble geometry experiment."""
import hashlib
from dialogue_vwf_hooks import Block, address, r
from live_vwf import i, j, words
from bubble_metrics import load_templates, catalog, TEMPLATE_BASE, TEMPLATE_COUNT

def constant(h, reg, value):
    # Constants must not look like relocatable LUI/address pairs.
    h.emit(i(13, 0, reg, value >> 16), r(0, reg, reg, 0, 16), i(13, reg, reg, value))

def fconstant(h, fd, bits):
    constant(h, 25, bits)
    h.emit(0x44800000 | 25 << 16 | fd << 11)

def fp(h, funct, fd, fs, ft=0):
    h.emit(0x46000000 | ft << 16 | fs << 11 | fd << 6 | funct)

def guard_pointer(h, reg, aligned=True):
    constant(h, 25, 0x08800000)
    h.emit(r(reg, 25, 24, 0x2b)); h.branch(5, 24, 0, 'return')
    constant(h, 25, 0x09fff000)
    h.emit(r(reg, 25, 24, 0x2b)); h.branch(4, 24, 0, 'return')
    if aligned:
        h.emit(i(12, reg, 24, 3)); h.branch(5, 24, 0, 'return')

def geometry(metrics, compact_catalog=False, association_fix=False,hideo_ruby=False,glyph_limit=129,serish_mouth=False):
    h = Block()
    h.emit(i(9, 29, 29, -160))
    regs = list(range(4, 16)) + [24, 25]
    for n, reg in enumerate(regs): h.emit(i(43, 29, reg, n * 4))
    h.emit(0x4448f800, i(43, 29, 8, 56))  # FCSR
    for n in range(12): h.emit(i(57, 29, n, 96 + 4*n))
    h.emit(r(4, 0, 8)); guard_pointer(h, 8)
    if serish_mouth:
        # Capture the scene updater's center before the English width clamp.
        h.emit(i(35,8,24,0x2d0),i(43,29,24,80),i(35,8,24,0x2d4),i(43,29,24,84))
    h.emit(i(37, 8, 10, 0x318), i(11, 10, 24, TEMPLATE_COUNT))
    h.branch(4, 24, 0, 'return')
    # Immutable template address: ID * (512 - 16 - 4).
    h.emit(r(0, 10, 9, 0, 9), r(0, 10, 24, 0, 4), r(9, 24, 9, 0x23),
           r(0, 10, 24, 0, 2), r(9, 24, 9, 0x23))
    address(h, 24, TEMPLATE_BASE); h.emit(r(9, 24, 9), i(43, 29, 9, 64), i(43, 29, 0, 68))
    fconstant(h, 0, 0x3f800000); fconstant(h, 5, 0x3f000000)
    # Restore native geometry before every decision, including reused JP windows.
    h.label('copy'); h.emit(i(35, 29, 9, 64), i(37, 9, 10, 0), i(11, 10, 24, 31))
    h.branch(4, 24, 0, 'return'); h.branch(4, 10, 0, 'return'); h.emit(r(8, 0, 11))
    h.label('vertex')
    for fd, off in ((6, 0x0c), (7, 0x10), (8, 0xfc), (9, 0x100)): h.emit(i(49, 9, fd, off))
    fp(h, 2, 6, 6, 0); fp(h, 2, 8, 8, 0)
    for fs, off in ((6, 0xf0), (7, 0xf4), (8, 0x1e0), (9, 0x1e4)): h.emit(i(57, 11, fs, off))
    fp(h, 0, 10, 6, 8); fp(h, 2, 10, 10, 5)
    fp(h, 0, 11, 7, 9); fp(h, 2, 11, 11, 5)
    h.emit(i(57, 11, 10, 0), i(57, 11, 11, 4), i(9, 9, 9, 8), i(9, 11, 11, 8), i(9, 10, 10, -1))
    h.branch(5, 10, 0, 'vertex'); h.emit(i(35, 29, 25, 68)); h.branch(5, 25, 0, 'tail_repair' if serish_mouth else 'return')
    # Unit-scale, unrotated geometry only. Animated states keep native geometry.
    for off in (0x2e0, 0x2e4, 0x2e8):
        h.emit(i(35, 8, 24, off)); h.branch(5, 24, 0, 'return')
    constant(h, 25, 0x3f800000)
    for off in (0x2f0, 0x2f4, 0x2f8):
        h.emit(i(35, 8, 24, off)); h.branch(5, 24, 25, 'return')
    h.emit(i(35, 8, 5, 0x348)); guard_pointer(h, 5)
    h.emit(i(35, 5, 6, 0x98)); guard_pointer(h, 6)
    h.emit(i(35, 6, 14, 0x30), i(35, 5, 15, 0xec))
    # Original F1058/F105C target LOAD1, whose vaddr is 0x47AF58.
    # Correct module offset is 0x11F436C+0x47AF58, not the raw HI/LO.
    address(h, 5, 0x166f2c4 if association_fix else 0x11f436c)
    h.emit(i(35, 5, 24, 0)); h.branch(4, 24, 0, 'return')
    h.emit(i(35, 5, 12, 0x28),
           i(9 if association_fix else 35, 5, 13, 0x2c))  # manager is flag+4; fixed array is embedded
    h.emit(i(11, 12, 24, 1025)); h.branch(4, 24, 0, 'return'); h.branch(4, 12, 0, 'return')
    guard_pointer(h, 13)
    h.label('search'); h.emit(i(35, 13, 11, 0)); guard_pointer(h, 11)
    h.emit(i(35, 11, 5, 8)); h.branch(5, 5, 14, 'next')
    h.emit(i(35, 11, 5, 0x0c)); h.branch(4, 5, 15, 'found')
    h.label('next'); h.emit(i(9, 13, 13, 4), i(9, 12, 12, -1)); h.branch(5, 12, 0, 'search')
    h.branch(4, 0, 0, 'return')
    h.label('found'); h.emit(i(35, 11, 5, 0x18), i(35, 11, 6, 0x20),
                            i(35, 11, 12, 0x1c), i(11, 5, 24, 33))
    h.branch(4, 24, 0, 'return'); h.branch(4, 5, 0, 'return')
    if association_fix:
        # +18 is overwritten with current page line count at ED178.
        # Bound the start/sum now; verify against source-derived total later.
        h.emit(i(11, 6, 24, 33)); h.branch(4, 24, 0, 'return')
        h.emit(r(6, 12, 7), i(11, 7, 24, 33)); h.branch(4, 24, 0, 'return')
        h.emit(i(43, 29, 7, 72))
    else:
        h.emit(r(5, 6, 24, 0x2b)); h.branch(5, 24, 0, 'return')
        h.emit(r(6, 12, 7), r(5, 7, 24, 0x2b)); h.branch(5, 24, 0, 'return')
    h.emit(i(11, 12, 24, 5))
    h.branch(4, 24, 0, 'return'); h.branch(4, 12, 0, 'return')
    h.emit(i(35, 11, 5, 0x14)); guard_pointer(h, 5, aligned=False)
    if serish_mouth:h.emit(i(43,29,5,92))
    h.emit(i(13, 0, 6, 0))
    if association_fix: h.emit(i(13, 0, 10, 1))
    h.label('byte'); h.emit(i(36, 5, 7, 0)); h.branch(4, 7, 0, 'validated')
    h.emit(i(13, 0, 24, 14)); h.branch(4, 7, 24, 'validated')
    for control in (0x10, 0x11, 0x12):
        h.emit(i(13, 0, 24, control))
        h.branch(4, 7, 24, 'line' if association_fix and control != 0x12 else 'advance')
    if hideo_ruby:
        h.emit(i(13,0,24,0x0f));h.branch(4,7,24,'hideo_reading')
    h.emit(i(11, 7, 24, 32)); h.branch(5, 24, 0, 'return')
    h.emit(i(11, 7, 24, glyph_limit)); h.branch(4, 24, 0, 'return')
    h.emit(i(13, 0, 24, 127)); h.branch(4, 7, 24, 'return')
    if association_fix:
        h.branch(4, 0, 0, 'advance')
        h.label('line'); h.emit(i(9, 10, 10, 1), i(11, 10, 24, 33))
        h.branch(4, 24, 0, 'return')
    h.label('advance'); h.emit(i(9, 5, 5, 1), i(9, 6, 6, 1), i(11, 6, 24, 4096))
    h.branch(4, 24, 0, 'return'); h.branch(4, 0, 0, 'byte')
    if hideo_ruby:
        h.label('hideo_reading')
        h.emit(i(11,6,24,4088));h.branch(4,24,0,'return')
        for n,value in enumerate(b'2Hideo\x0f',1):
            h.emit(i(36,5,7,n),i(13,0,24,value));h.branch(5,7,24,'return')
        h.emit(i(9,5,5,8),i(9,6,6,8));h.branch(4,0,0,'byte')
    h.label('validated'); h.branch(4, 6, 0, 'return')
    if association_fix:
        h.emit(i(35, 29, 7, 72), r(10, 7, 24, 0x2b))
        h.branch(5, 24, 0, 'return')
    # Reject nonpositive/nonfinite width and nonfinite window center.
    h.emit(i(35, 11, 5, 0x2c)); h.branch(6, 5, 0, 'return')
    constant(h, 25, 0x7f800000); h.emit(r(5, 25, 24, 0x24)); h.branch(4, 24, 25, 'return')
    h.emit(i(35, 8, 5, 0x2d0), r(5, 25, 24, 0x24)); h.branch(4, 24, 25, 'return')
    if compact_catalog:
        # T2 = ID*24; T4 remains the validated visible count (1..4).
        h.emit(i(49, 11, 4, 0x2c), i(37, 8, 10, 0x318),
               r(0, 10, 24, 0, 4), r(0, 10, 10, 0, 3), r(10, 24, 10))
        address(h, 9, metrics)
        h.emit(r(9, 10, 9), i(49, 9, 2, 16), i(49, 9, 3, 20),
               i(9, 12, 10, -1), r(0, 10, 10, 0, 2), r(9, 10, 9), i(49, 9, 1, 0))
    else:
        h.emit(i(49, 11, 4, 0x2c), i(37, 8, 10, 0x318), r(0, 10, 10, 0, 2),
               r(10, 12, 10), i(9, 10, 10, -1), r(0, 10, 24, 0, 3), r(0, 10, 10, 0, 2), r(10, 24, 10))
        address(h, 9, metrics); h.emit(r(9, 10, 9), i(49, 9, 1, 0), i(49, 9, 2, 4), i(49, 9, 3, 8))
    h.emit(0x44800000 | 6 << 11); fp(h, 0x3c, 0, 6, 1); h.branch(17, 8, 0, 'return')
    fconstant(h, 5, 0x41000000); fp(h, 0, 4, 4, 5); fp(h, 3, 0, 4, 1)
    fconstant(h, 6, 0x3f800000); fp(h, 0x3c, 0, 0, 6); h.branch(17, 8, 0, 'ratio_ready')
    fp(h, 6, 0, 6)
    h.label('ratio_ready'); fp(h, 2, 2, 2, 0); fp(h, 2, 3, 3, 0)
    fp(h, 1, 6, 5, 2); fconstant(h, 7, 0x43ec0000); fp(h, 1, 7, 7, 3)
    fp(h, 0x3e, 0, 6, 7); h.branch(17, 8, 0, 'return')
    h.emit(i(49, 8, 4, 0x2d0)); fp(h, 0x3c, 0, 4, 6); h.branch(17, 8, 0, 'upper')
    fp(h, 6, 4, 6)
    h.label('upper'); fp(h, 0x3c, 0, 7, 4); h.branch(17, 8, 0, 'fit')
    fp(h, 6, 4, 7)
    h.label('fit'); h.emit(i(57, 8, 4, 0x2d0), i(13, 0, 25, 1), i(43, 29, 25, 68))
    fconstant(h, 5, 0x3f000000); h.branch(4, 0, 0, 'copy')
    if serish_mouth:
        h.label('tail_repair')
        # This is a reviewed shot correction, not face detection. The original
        # phase track ends at shape8 / (369,99), portrait center (222,148).
        # Its lip landmark is (21,-14) in portrait space: screen (243,134).
        # All other templates, positions and records keep the inherited hook.
        h.emit(i(37,8,24,0x318),i(13,0,25,8));h.branch(5,24,25,'return')
        for off,bits in ((80,0x43b88000),(84,0x42c60000)):
            h.emit(i(35,29,24,off));constant(h,25,bits);h.branch(5,24,25,'return')
        h.emit(i(35,29,5,92))
        for n,value in enumerate(b'Who will accompany you?\x12\x0e'):
            h.emit(i(36,5,24,n),i(13,0,25,value));h.branch(5,24,25,'return')
        # Move only tip6. Native border offsets remain +3.5/-1 and -3.5/+1;
        # neither the body polygon nor speaker/text positions are changed.
        fconstant(h,0,0x43730000);h.emit(i(49,8,1,0x2d0));fp(h,1,0,0,1)
        fconstant(h,1,0x43060000);h.emit(i(49,8,2,0x2d4));fp(h,1,1,1,2)
        h.emit(i(57,8,0,48),i(57,8,1,52))
        fconstant(h,2,0x40600000);fconstant(h,3,0x3f800000)
        fp(h,0,4,0,2);fp(h,1,5,1,3);h.emit(i(57,8,4,0x120),i(57,8,5,0x124))
        fp(h,1,4,0,2);fp(h,0,5,1,3);h.emit(i(57,8,4,0x210),i(57,8,5,0x214))
    h.label('return')
    for n in range(12): h.emit(i(49, 29, n, 96 + 4*n))
    h.emit(i(35, 29, 8, 56), 0x44c8f800)
    for n, reg in enumerate(regs): h.emit(i(35, 29, reg, n * 4))
    h.emit(i(9, 29, 29, 160), i(9, 29, 29, -224), i(35, 4, 5, 0x31c), j(0xe4e14), 0)
    return h.finish()

def append(payload, start, compact_catalog=False, association_fix=False):
    entries, packed = catalog(load_templates(), compact_catalog=compact_catalog)
    while len(payload) % 16: payload.append(0)
    metrics = start + len(payload); payload.extend(packed)
    while len(payload) % 16: payload.append(0)
    offset = len(payload)
    code = geometry(metrics, compact_catalog=compact_catalog, association_fix=association_fix)
    payload.extend(code)
    change = (0xe4e0c, words([j(start+offset), 0]), False, i(9, 29, 29, -224))
    return [(offset, len(code))], [change], {
        'catalog_address': metrics, 'catalog_bytes': len(packed),
        'catalog_sha256': hashlib.sha256(packed).hexdigest(),
        'templates': TEMPLATE_COUNT, 'supported_template_page_combinations': sum(e['usable_half_width'] > 0 for e in entries),
        'hook_site': '0xe4e0c', 'hook_bytes': len(code),
        'scope': 'stationary unrotated centered control-light Latin, visible page 1..4 lines',
        'text_padding_per_side': 8, 'screen_margin': 8,
        'tail_exact_shape_preserved': False, 'native_animation_resize_verified': False,
        'runtime_verified': False,
    }
