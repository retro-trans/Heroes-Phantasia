"""Reversible native main-menu VWF experiment in the isolated PPSSPP session.

Default: inspect only. --install allocates PSP user memory, copies the resident
font, adds Latin glyphs, relocates five menu strings and installs two hooks.
--remove restores every original byte and frees the allocation. No ISO writes.
The decoder hook applies only to the observed menu drawing caller; other text
and measurement paths remain outside this experiment.
"""
import argparse, base64, hashlib, json, pathlib, struct
from PIL import Image, ImageDraw, ImageFont
from ppsspp_debug import Debugger

ELF = pathlib.Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf')
SHA = '03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1'
STATE = pathlib.Path('work/source/font_audit/live_vwf_state.json')
FONT = pathlib.Path('C:/Program Files/PPSSPP/assets/Roboto_Condensed-Regular.ttf')
LABELS = ['New Game', 'Load', 'Options', 'Gallery', 'Data Install']
CHECKPOINT = 0x87d54
ALLOC_SIZE = 0x23000

def swizzle(raw, pitch=64, height=64):
    """PSP 16-byte by 8-row tiles, including a verified inverse."""
    packed = bytearray()
    inverse = bytearray(len(raw))
    for y in range(0,height,8):
        for x in range(0,pitch,16):
            for row in range(8):
                packed.extend(raw[(y+row)*pitch+x:(y+row)*pitch+x+16])
    pos=0
    for y in range(0,height,8):
        for x in range(0,pitch,16):
            for row in range(8):
                inverse[(y+row)*pitch+x:(y+row)*pitch+x+16]=packed[pos:pos+16];pos+=16
    if inverse != raw:raise ValueError('Swizzle round trip failed')
    return packed

def write(d, address, data):
    d.call('memory.write', address=address, base64=base64.b64encode(data).decode())
    if d.read(address, len(data)) != data:
        raise RuntimeError('Memory write verification failed')

def registers(d):
    return d.call('cpu.getAllRegs')['categories']

def gpr(cats):
    c = cats[0]
    return dict(zip(c['registerNames'], c['uintValues']))

def restore_registers(d, saved):
    current = registers(d)
    pc = None
    for old, now in zip(saved, current):
        for i, (name, val, cur) in enumerate(zip(old['registerNames'], old['uintValues'], now['uintValues'])):
            if name == 'pc': pc = val; continue
            if val != cur:
                d.call('cpu.setReg', category=old['id'], register=i, value=val)
    d.call('cpu.setReg', name='pc', value=pc)

def kernel_call(d, base, offset, args):
    saved = registers(d)
    old_pc = gpr(saved)['pc']
    try:
        for name, value in zip(['a0','a1','a2','a3','t0'], args):
            d.call('cpu.setReg', name=name, value=value)
        d.call('cpu.setReg', name='ra', value=old_pc)
        d.call('cpu.setReg', name='pc', value=base+offset)
        d.call('cpu.runUntil', address=old_pc, expect='cpu.stepping')
        if d.call('cpu.status')['pc'] != old_pc:
            raise RuntimeError('Kernel import returned to another checkpoint')
        return gpr(registers(d))['v0']
    finally:
        restore_registers(d, saved)

def j(address): return 0x08000000 | ((address >> 2) & 0x03ffffff)
def i(op, rs, rt, imm): return op<<26 | rs<<21 | rt<<16 | (imm & 0xffff)
def words(values): return struct.pack('<'+'I'*len(values), *values)

def jal(address):return 0x0c000000 | ((address>>2)&0x03ffffff)

class Assembler:
    def __init__(self):self.code=[];self.labels={};self.fixups=[]
    def emit(self,*values):self.code.extend(values)
    def label(self,name):self.labels[name]=len(self.code)
    def branch(self,op,rs,rt,name):
        self.fixups.append((len(self.code),op,rs,rt,name));self.emit(0,0)
    def finish(self):
        for pos,op,rs,rt,name in self.fixups:self.code[pos]=i(op,rs,rt,self.labels[name]-pos-1)
        if len(self.code)*4>0x100:raise ValueError('Hook exceeds reserved slot')
        return words(self.code)

def high_hooks(base, bank, lookup, texture_width=128, *, offset_units=False):
    if texture_width not in (64,128):raise ValueError('Unsupported high-resolution texture width')
    slot_shift=11 if texture_width==64 else 12
    h=Assembler()
    h.emit(i(37,21,24,0),i(11,24,25,32));h.branch(5,25,0,'fallback')
    h.emit(i(11,24,25,129));h.branch(4,25,0,'fallback')
    h.emit(i(13,0,25,127));h.branch(4,24,25,'fallback')
    if offset_units:h.emit((24<<16)|(24<<11)|(1<<6))
    h.emit(i(15,0,25,lookup>>16),i(13,25,25,lookup),
           (25<<21)|(24<<16)|(25<<11)|0x21,i(37 if offset_units else 36,25,24,0),i(13,0,25,65535 if offset_units else 255))
    h.branch(4,24,25,'fallback')
    h.emit((24<<16)|(24<<11)|((8 if offset_units else slot_shift)<<6),i(15,0,25,bank>>16),i(13,25,25,bank),
           (25<<21)|(24<<16)|(8<<11)|0x21,i(13,0,4,0),i(13,0,5,texture_width),
           i(13,0,6,64),i(13,0,7,texture_width),i(13,0,9,0),i(9,0,21,-1),
           i(13,0,22,0),j(base+0xea5ec),0)
    h.label('fallback');h.emit((5<<21)|(8<<11)|0x21,i(13,0,21,0),j(base+0xea5cc),0)
    upload=h.finish()
    h=Assembler();h.emit(i(9,0,24,-1));h.branch(5,21,24,'original')
    h.emit(i(13,0,5,0));h.label('original');h.emit(j(base+0x1b7d28),0)
    mode=h.finish()
    h=Assembler();h.emit(i(9,0,24,-1));h.branch(5,21,24,'original')
    h.emit(i(9,29,29,-32),i(43,29,31,28),i(13,0,24,64),i(43,29,24,0),
           (19<<21)|(7<<11)|0x21,(20<<21)|(8<<11)|0x21,i(13,0,9,0),
           i(13,0,10,0),i(13,0,11,64),jal(base+0xd8e4),0,
           i(35,29,31,28),0x03e00008,i(9,29,29,32))
    h.label('original');h.emit(j(base+0xd7fc),0)
    return upload,mode,h.finish()

def decoder_hook(base):
    # Preserve the decoder's original a3/t0 outputs for all callers. Only the
    # observed draw caller receives an updated classification flag.
    ret = base+0x87d38
    return words([
        i(9,29,29,-16), i(43,29,8,0), i(43,29,7,4),
        i(15,0,8,ret>>16), i(13,8,8,ret), i(5,31,8,12), 0,
        i(37,6,7,0), i(11,7,8,32), i(5,8,0,8), 0,
        i(11,7,8,129), i(4,8,0,5), 0,
        i(13,0,8,127), i(4,7,8,2), 0, i(13,0,2,1),
        i(35,29,8,0), i(35,29,7,4), 0x03e00008, i(9,29,29,16),
    ])

def width_hook(base, lut):
    # t8/t9/f0 are volatile and dead at the next decoder call on this path.
    return words([
        i(37,29,24,8), i(11,24,25,32), i(5,25,0,12), 0,
        i(11,24,25,129), i(4,25,0,9), 0,
        i(15,0,25,lut>>16), i(13,25,25,lut),
        (24<<16)|(24<<11)|(2<<6), (25<<21)|(24<<16)|(25<<11)|0x21,
        i(49,25,0,0), 0x4600b580, j(base+0x87d28), 0,
        0x461ab580, j(base+0x87d28), 0,
    ])

def overlap_glyph_bank(bank, slot_bytes=2048, tile_bytes=256):
    """Share identical swizzled tile runs while retaining every complete glyph."""
    if len(bank)%slot_bytes:raise ValueError('Incomplete glyph bank')
    packed=bytearray();offsets=[]
    for pos in range(0,len(bank),slot_bytes):
        glyph=bank[pos:pos+slot_bytes];overlap=0
        for n in range(min(len(packed),slot_bytes),0,-tile_bytes):
            if packed[-n:]==glyph[:n]:overlap=n;break
        offsets.append(len(packed)-overlap);packed.extend(glyph[overlap:])
    if any(offset%tile_bytes or packed[offset:offset+slot_bytes]!=bank[n*slot_bytes:(n+1)*slot_bytes]
           for n,offset in enumerate(offsets)):raise ValueError('Glyph overlap changed pixels')
    return packed,offsets

def make_payload(d, base, start, descriptor, scale=1, *, high_texture_width=128, full_4x=False, max_payload_bytes=None, compact_font=False):
    if high_texture_width not in (64,128):raise ValueError('Unsupported high-resolution texture width')
    if full_4x and scale!=4:raise ValueError('Full high-resolution repertoire requires scale 4')
    if compact_font and (not full_4x or high_texture_width!=64):raise ValueError('Compact font requires the full 64x64 bank')
    count, table, pixels = struct.unpack('<III', d.read(descriptor,12))
    if count != 230: raise ValueError('First resident bank changed')
    records = [struct.unpack('<Iff', d.read(table+n*12,12)) for n in range(count)]
    if len(set(r[0] for r in records)) != count or any(r[0]<0x8140 for r in records):
        raise ValueError('Resident font map changed')
    font = ImageFont.truetype(str(FONT),16)
    glyphs = list(range(32,127))+[128]
    newpixels = bytearray(d.read(pixels, count*384))
    advances = [0.0]*129
    newrecords = list(records)
    preview = Image.new('L',(512,144))
    highpixels=bytearray()
    highcodes=set(glyphs) if full_4x else set(ord(c) for label in LABELS for c in label) | {128}
    high_slot_bytes=high_texture_width*64//2
    highlookup=[255]*129
    highfont=ImageFont.truetype(str(FONT),64) if scale==4 else None
    highpreview=Image.new('L',(16*high_texture_width,384)) if scale==4 else None
    for n, code in enumerate(glyphs):
        char = chr(code) if code != 128 else '\u00e8'
        im = Image.new('L',(32,24)); draw=ImageDraw.Draw(im)
        draw.text((0,12),char,font=font,anchor='ls',fill=255)
        bbox=im.getbbox()
        if bbox and (bbox[2]>16 or bbox[3]>16):
            raise ValueError('Glyph exceeds observed 16px draw rectangle: '+repr(char))
        a=list(im.get_flattened_data())
        newpixels.extend((a[k]//17)|((a[k+1]//17)<<4) for k in range(0,len(a),2))
        advance=font.getlength(char)
        advances[code]=advance
        newrecords.append((code,float(count+n),-1.0))
        preview.paste(im,((n%16)*32,(n//16)*24))
        if scale==4 and code in highcodes:
            highlookup[code]=len(highpixels)//high_slot_bytes
            high=Image.new('L',(high_texture_width,64));ImageDraw.Draw(high).text((0,48),char,font=highfont,anchor='ls',fill=255)
            bbox=high.getbbox()
            if bbox and (bbox[2]>64 or bbox[3]>64):raise ValueError('4x glyph exceeds source rectangle')
            values=list(high.get_flattened_data())
            raw=bytearray((values[k]//17)|((values[k+1]//17)<<4) for k in range(0,len(values),2))
            highpixels.extend(swizzle(raw,pitch=high_texture_width//2))
            highpreview.paste(high,((n%16)*high_texture_width,(n//16)*64))
    compact_offsets=None
    if compact_font:
        highpixels,compact_offsets=overlap_glyph_bank(highpixels)
        highlookup=[65535]*129
        for code,offset in zip(sorted(highcodes),compact_offsets):
            if offset//256>=65535:raise ValueError('Packed glyph offset exceeds lookup')
            highlookup[code]=offset//256
    newrecords.sort(key=lambda r:r[0])
    payload=bytearray(0x800 if scale==4 else 0x400)
    lut=start+len(payload);payload.extend(struct.pack('<129f',*advances))
    while len(payload)%16:payload.append(0)
    textptr=[]
    for label in LABELS:
        textptr.append(start+len(payload));payload.extend(label.encode('ascii')+b'\0')
    while len(payload)%16:payload.append(0)
    newtable=start+len(payload)
    for record in newrecords:payload.extend(struct.pack('<Iff',*record))
    while len(payload)%16:payload.append(0)
    newpixelptr=start+len(payload);payload.extend(newpixels)
    while len(payload)%16:payload.append(0)
    highptr=start+len(payload);payload.extend(highpixels)
    payload[:len(decoder_hook(base))]=decoder_hook(base)
    wh=width_hook(base,lut);payload[0x100:0x100+len(wh)]=wh
    if scale==4:
        lookup_bytes=struct.pack('<129H',*highlookup) if compact_font else bytes(highlookup)
        payload[0x600:0x600+len(lookup_bytes)]=lookup_bytes
        for offset,hook in zip((0x200,0x300,0x400),high_hooks(base,highptr,start+0x600,high_texture_width,offset_units=compact_font)):
            payload[offset:offset+len(hook)]=hook
    limit=max_payload_bytes if max_payload_bytes is not None else (0x39000 if scale==4 else ALLOC_SIZE)
    if len(payload)>limit:raise ValueError('Allocation too small')
    info={
        'resident_glyphs':count,'latin_glyphs':len(glyphs),'width_i':advances[105],
        'width_W':advances[87],'label_widths':{s:sum(advances[ord(c)] for c in s) for s in LABELS},
        'payload_bytes':len(payload),'native_baseline':12,'slot':[32,24],'draw_rect':[16,16],
        'font_scale':scale,'high_texture_slot':[high_texture_width,64] if scale==4 else None,
        'high_source_rect':[64,64] if scale==4 else None,'high_bank':highptr if scale==4 else None,
        'high_glyph_count':len(highcodes) if compact_font else len(highpixels)//high_slot_bytes,'high_codes':sorted(highcodes) if scale==4 else [],
        'atlas':highpreview if scale==4 else preview,
    }
    if compact_font:info.update(high_bank_bytes=len(highpixels),high_lookup_entry_bytes=2,
        high_lookup_unit=256,high_glyph_offsets=dict(zip(map(str,sorted(highcodes)),compact_offsets)),
        high_bank_packing='Identical overlapping 256-byte swizzled tile runs; each 2048-byte glyph region unchanged')
    return payload, words([len(newrecords)-1,newtable,newpixelptr]), textptr, info

def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group();mode.add_argument('--install',action='store_true');mode.add_argument('--remove',action='store_true')
    p.add_argument('--scale',type=int,choices=(1,4),default=1)
    a=p.parse_args()
    alloc_size=0x39000 if a.scale==4 else ALLOC_SIZE
    if hashlib.sha256(ELF.read_bytes()).hexdigest()!=SHA:raise ValueError('Executable hash changed')
    d=Debugger(); paused=False;allocation=None; applied=[]
    try:
        mod=next(m for m in d.call('hle.module.list')['modules'] if m['name']=='hp_proj')
        base=mod['address']
        # runUntil accepts a running CPU and creates its own temporary breakpoint.
        d.call('cpu.runUntil',address=base+CHECKPOINT,expect='cpu.stepping');paused=True
        if d.call('cpu.status')['pc']!=base+CHECKPOINT:raise RuntimeError('Unexpected breakpoint')
        if a.remove:
            state=json.loads(STATE.read_text())
            if not state['status'].startswith('installed'):raise ValueError('Experiment is already removed')
            if state['module_base']!=base:raise ValueError('State belongs to another load')
            for change in state['changes']:
                replacement=base64.b64decode(change['replacement'])
                if d.read(change['address'],len(replacement))!=replacement:
                    raise ValueError('Runtime patch changed or stale state; no rollback attempted')
            if hashlib.sha256(d.read(state['allocation'],state['payload_bytes'])).hexdigest()!=state['payload_sha256']:
                raise ValueError('Allocation differs from this experiment; no rollback attempted')
            for change in reversed(state['changes']):
                write(d,change['address'],base64.b64decode(change['original']))
            # Let two ordinary frames complete with restored font pointers
            # before the allocator may reuse pixels from queued GPU commands.
            for _ in range(2):d.call('cpu.runUntil',address=base+0x29414c,expect='cpu.stepping')
            d.call('cpu.runUntil',address=base+CHECKPOINT,expect='cpu.stepping')
            if struct.unpack('<I',d.read(base+0x11f48b4,4))[0]!=0:
                raise RuntimeError('Allocator lock held; allocation retained for manual cleanup')
            kernel_call(d,base,0x128180,[state['allocation']])
            state['status']='removed_and_allocation_freed';STATE.write_text(json.dumps(state,indent=2)+'\n')
            print('Restored code/font pointers/menu pointers; freed PSP allocation.');return
        regs=gpr(registers(d))
        # The resident descriptor is obtained from the same state getter used
        # by the draw routine, without trusting a previous run's heap address.
        stateptr=kernel_call(d,base,0xe928c,[])
        descriptor=struct.unpack('<I',d.read(stateptr+4,4))[0]
        ptrloc=base+0x948d4
        menu_ptrs=struct.unpack('<5I',d.read(ptrloc,20))
        expected=[base+x for x in (0x94e83,0x94e90,0x94e97,0x94ea2,0x94ead)]
        if list(menu_ptrs)!=expected:raise ValueError('Original menu pointers changed; remove existing experiment first')
        elf=ELF.read_bytes()
        for off in (0xe9cc8,0x87dc0):
            if d.read(base+off,8)!=elf[off+0xc0:off+0xc8]:raise ValueError('Original hook bytes changed')
        if a.scale==4:
            if d.read(base+0xea5c4,8)!=elf[0xea684:0xea68c]:raise ValueError('Upload hook changed')
            for off,target in ((0xea6a0,0x1b7d28),(0xea6e4,0xd7fc)):
                if d.read(base+off,4)!=words([jal(base+target)]):raise ValueError('Relocated call hook changed')
        # Dry-run still uses only reads plus register-restored state getter.
        payload,_,_,info=make_payload(d,base,0x09000000,descriptor,a.scale)
        atlas=info.pop('atlas')
        print(json.dumps({'mode':'isolated_runtime_only','module_base':hex(base),'descriptor':hex(descriptor),
            'allocate_bytes':alloc_size,'labels':LABELS,**info},indent=2))
        if not a.install:print('DRY RUN: no memory/data/code patch installed.');return
        # The game reserves the remaining kernel partition for its heap.
        # Allocate an owned block through its public malloc, outside its lock.
        if struct.unpack('<I',d.read(base+0x11f48b4,4))[0]!=0:
            raise RuntimeError('Game allocator lock is held; try a later frame')
        start=kernel_call(d,base,0x12815c,[alloc_size])
        if start==0:raise RuntimeError('Game heap allocation failed')
        allocation=start
        if not 0x08800000<=start<0x0a000000 or start+alloc_size>0x0a000000:
            raise ValueError('Unexpected allocation address')
        payload,newdesc,textptr,info=make_payload(d,base,start,descriptor,a.scale)
        atlas=info.pop('atlas')
        write(d,start,payload)
        changes=[(descriptor,newdesc),(ptrloc,words(textptr)),
                 (base+0xe9cc8,words([j(start),0])),(base+0x87dc0,words([j(start+0x100),0]))]
        if a.scale==4:
            changes.extend([(base+0xea5c4,words([j(start+0x200),0])),
                (base+0xea6a0,words([jal(start+0x300)])),(base+0xea6e4,words([jal(start+0x400)]))])
        state={'version':'0.1.0','status':'installed_menu_experiment_not_full_game',
            'module_base':base,'allocation_method':'game_malloc_0x12815c','allocation':start,'allocation_size':alloc_size,
            'payload_sha256':hashlib.sha256(payload).hexdigest(),
            'font_sha256':hashlib.sha256(FONT.read_bytes()).hexdigest(),'elf_sha256':SHA,
            **info,'labels':LABELS,'changes':[]}
        STATE.parent.mkdir(parents=True,exist_ok=True)
        # Record rollback bytes before the first patch.
        for address,new in changes:
            state['changes'].append({'address':address,'original':base64.b64encode(d.read(address,len(new))).decode(),
                'replacement':base64.b64encode(new).decode()})
        STATE.write_text(json.dumps(state,indent=2)+'\n')
        for address,new in changes:
            original=d.read(address,len(new));applied.append((address,original));write(d,address,new)
        pathlib.Path('work/ui/vwf').mkdir(parents=True,exist_ok=True)
        atlas.save('work/ui/vwf/4x_menu_glyphs.png' if a.scale==4 else 'work/ui/vwf/native_menu_glyphs.png')
        print('Installed at',hex(start),'; rollback recorded locally.')
        allocation=None;applied=[]
    except Exception:
        if paused:
            for address,original in reversed(applied):write(d,address,original)
            if allocation is not None:kernel_call(d,base,0x128180,[allocation])
        raise
    finally:
        if paused:d.call('cpu.resume',expect='cpu.resume')
        d.close()

if __name__=='__main__':main()
