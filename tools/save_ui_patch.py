"""Dry-only save UI proposal from frozen .14; optional ignored previews, no asset writer.

Relocates UTF-8 utility labels into the existing payload. Lossless RGB icons reuse
their original allocations by default; --relocate-icons compares the RAM cost.
Episode titles
are inventoried but deliberately excluded pending contextual translation review.
"""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import struct

from PIL import Image, ImageDraw, ImageFont
from build_menu_patch import START, align

SOURCE = Path('work/output/0.1.14-dialogue-assets/EBOOT.BIN')
SHA = '00971b998b817c19221e8744e8deaba736d3186f86dd705ed0877faf6370dbbd'
PREFIX = Path('work/source/save_ui_015')
FONT = Path('C:/Windows/Fonts/arialbd.ttf')
LABELS = [
 (0x2f3182, 'Heroes Phantasia'),
 (0x2f31a4, 'Installation Data'),
 (0x2f31c0, 'New Installation Data'),
 (0x2f31e4, 'This is installation data for Heroes Phantasia.'),
 (0x2f3238, 'System Save Data'),
 (0x2f3258, 'New System Save Data'),
 (0x2f3280, 'This is system save data for Heroes Phantasia.'),
 (0x2f32e0, 'Game Save Data'),
 (0x2f32fc, 'New Game Save Data'),
 (0x2f3320, 'This is game save data for Heroes Phantasia.'),
 (0x2f336c, 'Limited Edition System Save Data'),
 (0x2f33a0, 'New Limited Edition System Save Data'),
 (0x2f33d8, 'This is system save data for the limited edition of Heroes Phantasia.'),
]
ICONS = [
 ('play', 0x294ed0, 32302, 0x470a7c, 'Save Data', False),
 ('play_dim', 0x29cd00, 29379, 0x470a88, 'Save Data', True),
 ('system', 0x2a3fd0, 22435, 0x470a58, 'System Data', False),
 ('system_dim', 0x2a9780, 21843, 0x470a64, 'System Data', True),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make_icon(data, text, dim):
    original = Image.open(io.BytesIO(data)).convert('RGBA')
    if original.size != (144, 80):
        raise ValueError('Unexpected save icon dimensions')
    # Replace only the 16px lower caption band; never synthesize or redraw logo.
    # Reconstruct a dark background from each source row's outside edges.
    band = Image.new('RGBA', (144, 16))
    for y in range(16):
        left, right = original.getpixel((0, 64+y)), original.getpixel((143, 64+y))
        for x in range(144):
            rgb = tuple(round((left[c]*(143-x)+right[c]*x)/143*0.45) for c in range(3))
            band.putpixel((x, y), (*rgb, 255))
    scale = 4
    high = band.resize((576, 64), Image.Resampling.NEAREST)
    font = ImageFont.truetype(str(FONT), 14*scale)
    draw = ImageDraw.Draw(high)
    box = draw.textbbox((0, 0), text, font=font, stroke_width=scale)
    width = box[2]-box[0]
    if width > 136*scale:
        raise ValueError('Save caption exceeds independently selected image width')
    x = (576-width)//2-box[0]
    y = (64-(box[3]-box[1]))//2-box[1]
    draw.text((x,y), text, font=font, fill=(175,175,175,255) if dim else (255,255,255,255),
              stroke_width=scale, stroke_fill=(20,20,20,255))
    result = original.copy()
    result.paste(high.resize((144,16), Image.Resampling.LANCZOS), (0,64))
    if result.crop((0,0,144,64)).tobytes() != original.crop((0,0,144,64)).tobytes():
        raise ValueError('Logo pixels changed')
    out = io.BytesIO()
    if result.getextrema()[3] != (255,255):
        raise ValueError('RGB proposal would lose source alpha')
    result.convert('RGB').save(out, 'PNG', optimize=True)
    encoded = out.getvalue()
    if Image.open(io.BytesIO(encoded)).convert('RGBA').tobytes() != result.tobytes():
        raise ValueError('PNG round-trip changed pixels')
    return encoded, result


def build(relocate_icons=False):
    original = SOURCE.read_bytes()
    inherited = json.loads(SOURCE.with_name('setup_patch.en.json').read_text())
    if sha(original) != SHA or inherited['output_elf_sha256'] != SHA:
        raise ValueError('Frozen .14 executable/report differs')
    phoff, shoff = struct.unpack_from('<II', original, 28)
    phnum, shnum = struct.unpack_from('<H', original, 44)[0], struct.unpack_from('<H', original, 48)[0]
    ph = [list(struct.unpack_from('<8I', original, phoff+32*n)) for n in range(phnum)]
    sections = [list(struct.unpack_from('<10I', original, shoff+40*n)) for n in range(shnum)]
    if phnum != 4 or ph[2][2] != START or ph[3][0] != 0x700000a0:
        raise ValueError('Unexpected compact .14 segment layout')
    prefix = original[ph[2][1]:ph[2][1]+ph[2][4]]
    rel = original[ph[3][1]:ph[3][1]+ph[3][4]]
    sites = set(struct.iter_unpack('<II', rel))
    payload, patch = bytearray(prefix), bytearray(original)
    changes, labels, icons, previews = [], [], [], {}

    def append(data):
        payload.extend(bytes((-len(payload)) % 4))
        address = START+len(payload)
        payload.extend(data)
        return address

    def replace(file_offset, data, expected):
        if original[file_offset:file_offset+len(expected)] != expected:
            raise ValueError(f'Unexpected source at {file_offset:x}')
        if any(max(file_offset,int(c['file_offset'],16)) < min(file_offset+len(data),int(c['file_offset'],16)+len(bytes.fromhex(c['replacement_hex']))) for c in changes):
            raise ValueError('Overlapping patch')
        patch[file_offset:file_offset+len(data)] = data
        changes.append(dict(file_offset=hex(file_offset),rva=hex(file_offset-192),
                            expected_hex=expected.hex(),replacement_hex=data.hex()))

    def pointer(file_offset, expected, target):
        if (file_offset-192,2) not in sites:
            raise ValueError(f'Native R32 missing at {file_offset:x}')
        replace(file_offset,struct.pack('<I',target),struct.pack('<I',expected))

    for offset,target in LABELS:
        end = original.index(0,offset)
        source = original[offset:end].decode('utf8')
        encoded = target.encode('utf8')+b'\0'
        capacity = 1024 if source.endswith('\u3067\u3059\u3002') else 128
        if len(encoded)>capacity:
            raise ValueError('PSP utility destination capacity exceeded')
        addr = append(encoded)
        refs = [p for p in range(0x4716d0,0x47172c,4) if struct.unpack_from('<I',original,p)[0] == offset-192]
        pairs = []
        if offset == 0x2f3182:
            high,low=0x1151c8,0x1151d8
            hi,lo = struct.unpack_from('<I',original,high+192)[0],struct.unpack_from('<I',original,low+192)[0]
            decoded=((hi&65535)<<16)+struct.unpack('<h',struct.pack('<H',lo&65535))[0]
            if hi>>26!=15 or lo>>26!=9 or decoded!=offset-192 or (high,5) not in sites or (low,6) not in sites:
                raise ValueError('Game title HI/LO proof failed')
            replace(high+192,struct.pack('<I',(hi&0xffff0000)|((addr+0x8000)>>16)),struct.pack('<I',hi))
            replace(low+192,struct.pack('<I',(lo&0xffff0000)|(addr&65535)),struct.pack('<I',lo))
            pairs=[[hex(high),hex(low)]]
        elif not refs:
            raise ValueError('Save string has no known table reference')
        for p in refs:pointer(p,offset-192,addr)
        labels.append(dict(original_file_offset=hex(offset),source=source,target=target,
                           target_bytes=len(encoded),capacity_including_nul=capacity,payload_rva=hex(addr),
                           pointer_file_offsets=list(map(hex,refs)),address_pairs=pairs,status='draft'))
    for name,offset,length,table,text,dim in ICONS:
        src=original[offset:offset+length]
        encoded,image=make_icon(src,text,dim)
        if src[25]!=2 or encoded[25]!=2 or src[24]!=8 or encoded[24]!=8:
            raise ValueError('Expected native 8bit RGB PNG format')
        if relocate_icons:
            addr=append(encoded)
            pointer(table,offset-192,addr)
        else:
            if len(encoded)>length:raise ValueError('RGB image exceeds original allocation')
            if (table-192,2) not in sites or struct.unpack_from('<I',original,table)[0]!=offset-192:
                raise ValueError('Original icon pointer/relocation differs')
            addr=offset-192
            replace(offset,encoded,src[:len(encoded)])
        for p in (table+4,table+8):replace(p,struct.pack('<I',len(encoded)),struct.pack('<I',length))
        previews[name]=(src,encoded,image)
        icons.append(dict(name=name,original_file_offset=hex(offset),original_bytes=length,
                          replacement_bytes=len(encoded),input_sha256=sha(src),output_sha256=sha(encoded),
                          pointer_file_offset=hex(table),size_file_offsets=[hex(table+4),hex(table+8)],
                          payload_rva=hex(addr),caption=text,dim=dim,
                          storage_strategy='appended' if relocate_icons else 'original_allocation',
                          original_pointer_preserved=not relocate_icons,
                          original_unused_tail_preserved=not relocate_icons,
                          png_color_type=2,png_bit_depth=8,
                          source_png_color_type=src[25],source_png_bit_depth=src[24],
                          logo_rgba_sha256=sha(image.crop((0,0,144,64)).tobytes()),
                          source_logo_rgba_sha256=sha(Image.open(io.BytesIO(src)).convert('RGBA').crop((0,0,144,64)).tobytes()),
                          decoded_rgba_sha256=sha(image.tobytes()),
                          unchanged_pixel_region=[0,0,144,64],changed_pixel_region=[0,64,144,80]))
    episodes=[]
    for p in range(0x471734,0x4717b0,4):
        off=struct.unpack_from('<I',original,p)[0]+192
        if not 0x2f3430<=off<0x2f3794 or any(int(x['original_file_offset'],16)==off for x in episodes):continue
        s=original[off:original.index(0,off)].decode('utf8')
        if not any(ord(c)>127 for c in s):continue
        episodes.append(dict(original_file_offset=hex(off),pointer_file_offset=hex(p),source=s,
                             target='',status='needs_context',installed=False))
    # Include all 30 even if table range changes; references are reported only
    # when present, never guessed from sequential row numbering.
    found={int(x['original_file_offset'],16) for x in episodes}
    p=0x2f3430
    while p<0x2f3794:
        end=original.index(0,p);raw=original[p:end]
        if raw.startswith(b'EP') and any(c>=128 for c in raw) and p not in found:
            episodes.append(dict(original_file_offset=hex(p),source=raw.decode('utf8'),target='',status='needs_context',installed=False))
        p=end+1
    episodes.sort(key=lambda x:int(x['original_file_offset'],16))
    if len(episodes)!=30:raise ValueError('Episode title inventory not exactly 30')
    old_payload_offset,old_rel_offset=ph[2][1],ph[3][1]
    new_payload=align(len(patch),64);patch.extend(bytes(new_payload-len(patch)));patch.extend(payload)
    new_rel=align(len(patch),16);patch.extend(bytes(new_rel-len(patch)));patch.extend(rel)
    for section in sections:
        if section[1]==0x700000a0:section[4]=new_rel+(section[4]-old_rel_offset)
        elif section[3]==START and section[4]==old_payload_offset:section[4]=new_payload;section[5]=len(payload)
    newsh=align(len(patch),4);patch.extend(bytes(newsh-len(patch)))
    for section in sections:patch.extend(struct.pack('<10I',*section))
    ph[2][1]=new_payload;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=new_rel
    for n,header in enumerate(ph):struct.pack_into('<8I',patch,phoff+32*n,*header)
    struct.pack_into('<I',patch,32,newsh)
    assert payload[:len(prefix)]==prefix and patch[new_rel:new_rel+len(rel)]==rel
    assert patch[0x2f3430:0x2f37c0]==original[0x2f3430:0x2f37c0]
    # All original content outside header and explicitly audited mutations stays.
    allowed=set(range(28,36))
    allowed.update(range(phoff+64,phoff+128))
    for c in changes:allowed.update(range(int(c['file_offset'],16),int(c['file_offset'],16)+len(bytes.fromhex(c['replacement_hex']))))
    assert all(a==b or n in allowed for n,(a,b) in enumerate(zip(original,patch)))
    rollback=bytearray(patch[:len(original)])
    rollback[28:36]=original[28:36]
    rollback[phoff+64:phoff+128]=original[phoff+64:phoff+128]
    for c in changes:
        p=int(c['file_offset'],16);old=bytes.fromhex(c['expected_hex'])
        rollback[p:p+len(old)]=old
    assert bytes(rollback)==original
    loaded_checks=[]
    from compact_vwf_patch import loaded
    for base in (0x08804000,0x08900000,0x08fff000):
        loaded_new,records,_=loaded(bytes(patch),base)
        loaded_old,_,_=loaded(original,base)
        changed_sites={int(c['rva'],16) for c in changes}
        untouched=0
        for off,flags in records:
            segment=(flags>>8)&255
            if segment==0 and off in changed_sites:continue
            assert loaded_old[segment][off:off+4]==loaded_new[segment][off:off+4]
            untouched+=1
        for label in labels:
            wanted=base+int(label['payload_rva'],16)
            for p in label['pointer_file_offsets']:
                off=int(p,16);assert struct.unpack_from('<I',loaded_new[0],off-192)[0]==wanted
            for high,low in label['address_pairs']:
                hi,lo=struct.unpack_from('<I',loaded_new[0],int(high,16))[0],struct.unpack_from('<I',loaded_new[0],int(low,16))[0]
                addr=(hi&65535)*65536+struct.unpack('<h',struct.pack('<H',lo&65535))[0]
                assert addr==wanted
        for icon in icons:
            assert struct.unpack_from('<I',loaded_new[0],int(icon['pointer_file_offset'],16)-192)[0]==base+int(icon['payload_rva'],16)
        loaded_checks.append(dict(base=hex(base),pointer_words=16,address_pairs=1,untouched_relocation_words=untouched,passed=True))
    report=copy.deepcopy(inherited)
    report.update(version='0.1.15',status='dry_save_ui_proposal_runtime_unverified',runtime_verified=False,
                  input_version='0.1.14',input_sha256=SHA,output_sha256=sha(patch),output_elf_sha256=sha(patch),
                  elf_bytes=len(patch),payload_bytes=len(payload),payload_growth=len(payload)-len(prefix),
                  module_growth_bytes=len(payload),added_relocations=0,total_relocations=len(rel)//8,
                  inherited_payload_preserved=True,inherited_payload_sha256=sha(prefix),
                  relocation_prefix_unchanged=True,relocation_table_sha256=sha(rel))
    report['save_ui_patch']=dict(labels=labels,icons=icons,changes=changes,episode_titles=episodes,
                               episode_clear=dict(original_file_offset='0x2f3794',target='Episode Clear',installed=False),
                               font_file=str(FONT),font_sha256=sha(FONT.read_bytes()),
                               caption_raster_scale=4,no_runtime_hooks_added=True,
                               relocated_address_checks=loaded_checks,reversible_original_sha256=sha(rollback),
                               native_utility_font_used=True,original_strings_preserved=True,
                               original_pngs_preserved=relocate_icons,
                               icon_storage_strategy='appended' if relocate_icons else 'original_allocation',
                               compaction_bytes_retained=125184,
                               extra_loaded_bytes_vs_014=len(payload)-len(prefix),
                               limitation='Preview only; episode titles not translated/installed. Save selector wrapping, limited-edition applicability and image upload lifetime require QA.')
    return bytes(patch),report,previews


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--preview',action='store_true',help='Write ignored report and PNG proposals only, never executable')
    p.add_argument('--relocate-icons',action='store_true',help='Compare full append cost; default preserves original PNG allocations')
    p.add_argument('--write',action='store_true',help='Write only ignored reversible candidate after external review')
    a=p.parse_args();data,report,previews=build(a.relocate_icons)
    print(json.dumps(dict(input_sha256=SHA,output_elf_sha256=sha(data),elf_bytes=len(data),
                         payload_bytes=report['payload_bytes'],payload_growth=report['payload_growth'],
                         added_relocations=0,labels=report['save_ui_patch']['labels'],
                         icons=report['save_ui_patch']['icons'],episode_title_count=30),ensure_ascii=True,indent=2))
    stem=str(PREFIX)+('_appended_rgb' if a.relocate_icons else '_rgb')
    if a.preview:
        paths=[Path(stem+'_proposal.en.json'),Path(stem+'_icons.png')]
        if any(x.exists() for x in paths):raise ValueError('Refusing to overwrite proposal snapshot')
        sheet=Image.new('RGBA',(288,384),(40,40,40,255));draw=ImageDraw.Draw(sheet)
        for n,(name,(source,encoded,image)) in enumerate(previews.items()):
            sheet.paste(Image.open(io.BytesIO(source)),(0,n*96));sheet.paste(image,(144,n*96))
            draw.text((0,n*96+80),name+' original / English',fill='white')
        paths[0].write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf8')
        sheet.save(paths[1]);print('Ignored proposals written; no executable or build assets written.')
    if a.write:
        if a.relocate_icons:raise ValueError('Full append candidate not approved for writer')
        dest=Path(stem+'_EBOOT.BIN');rp=Path(stem+'_candidate.en.json')
        if dest.exists() or rp.exists():raise ValueError('Refusing to overwrite candidate')
        report['status']='written_save_ui_candidate_runtime_unverified'
        dest.write_bytes(data);rp.write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf8')
        if sha(dest.read_bytes())!=report['output_elf_sha256']:raise ValueError('Candidate readback hash differs')
        print('Ignored candidate written; no frozen asset or ISO changed.')
    elif not a.preview:print('DRY RUN: no output files written; candidate exists only in memory.')


if __name__=='__main__':main()
