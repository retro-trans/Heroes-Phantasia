"""Append relocated setup strings and scoped Latin drawing hooks; dry-run default."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from build_menu_patch import START, align, reloc, relocate_code
from dialogue_vwf_hooks import Block, address, r, route
from live_vwf import i, j, jal, words

SOURCE = Path('work/output/0.1.8-title-credit-vwf-4x-candidate/EBOOT.BIN')
OUTPUT = Path('work/output/0.1.9-setup-assets')
SHA = '8d310d47f903d2dfdcb86d8ba63ced77b06a1d80aa4590c255b50c26ecdc0bf1'
# File offsets identify immutable original strings; code and pointers use RVAs.
STRINGS = [
 (0x94f80, 'Gender', [0x948e8], []),
 (0x94f89, 'Surname', [0x948ec], []),
 (0x94f92, 'Given Name', [0x948f0], []),
 (0x94f9b, 'Title', [0x948f4], []),
 (0x94fa4, 'Restore Defaults', [0x948f8], []),
 (0x94fb5, 'Confirm', [0x948fc], []),
 (0x94fba, 'Male', [0x94900], []),
 (0x94fbf, 'Female', [0x94904], []),
 (0x954d9, 'Play Voice', [0x94af4], []),
 (0x95021, 'Yes', [0x9493c], []),
 (0x95026, 'No', [0x94940], []),
 (0x2ea868, 'Heroes Phantasia', [], [(0x4bec8,0x4bed8)]),
 (0x2ea890, 'Create system save data.', [], [(0x4becc,0x4bedc)]),
 (0x2ea8b4, 'Are you sure?', [], [(0x4bed0,0x4bee0)]),
 (0x2ea8c8, 'If you do not create system save data,', [], [(0x4bef8,0x4bf08)]),
 (0x2ea8f0, 'Gallery, Options, and other settings cannot be saved.', [], [(0x4befc,0x4bf0c)]),
 (0x2ea924, 'If you do not load system save data,', [], [(0x4bf28,0x4bf38)]),
 (0x2ea950, 'Gallery, Options, and other saved data will not take effect.', [], [(0x4bf2c,0x4bf3c)]),
 (0x2ea750, 'Do you want to start the game anyway?', [], [(0x4bf00,0x4bf10),(0x4bf30,0x4bf40)]),
 (0x2eaafc, 'Watari', [], [(0x4efd8,0x4efe0)]),
 (0x2eab06, 'Eiji', [], [(0x4f0a4,0x4f0ac)]),
 (0x2eab18, 'S.I.R. Ace', [], [(0x4f170,0x4f178)]),
 (0x2eab32, 'Fudo', [], [(0x4efd4,0x4efe4)]),
 (0x2eab3c, 'Shinobu', [], [(0x4f0a0,0x4f0b0)]),
 (0x2eab4e, 'S.I.R. Ace', [], [(0x4f16c,0x4f17c)]),
 (0x2eab68, 'Select Gender', [], [(0x4fae0,0x4faf0)]),
 (0x2eab78, 'Restore the default surname, given name, and title.', [], [(0x4fff0,0x4fffc)]),
 (0x2eabac, 'Are you sure?', [], [(0x4fff4,0x50004),(0x50070,0x50080),(0x500ec,0x500fc)]),
 (0x2eabc4, 'Start the game with these settings.', [], [(0x5006c,0x50078)]),
 (0x2eabe8, 'Discard these settings and return to the title screen.', [], [(0x500e8,0x500f4)]),
 (0x2eb348, 'Watari', [], [(0x8426c,0x84270)]),
 (0x2eb352, 'Eiji', [], [(0x84284,0x84290)]),
 (0x2eb364, 'S.I.R. Ace', [], [(0x84294,0x842a0)]),
 (0x2eb39a, 'Fudo', [], [(0x842ec,0x842f0)]),
 (0x2eb3a4, 'Shinobu', [], [(0x84304,0x84310)]),
 (0x2eb3b6, 'S.I.R. Ace', [], [(0x84314,0x84320)]),
]

def latin(h, code, scratch, fallback):
    h.emit(i(11,code,scratch,32));h.branch(5,scratch,0,fallback)
    h.emit(i(11,code,scratch,129));h.branch(4,scratch,0,fallback)
    h.emit(i(13,0,scratch,127));h.branch(4,code,scratch,fallback)

def classify():
    h=Block();h.emit(i(9,29,29,-16),i(43,29,31,12),i(43,29,6,8),jal(0xe9c64),0)
    h.emit(i(35,29,24,8),i(37,24,24,0));latin(h,24,25,'return')
    h.emit(i(13,0,2,1));h.label('return')
    h.emit(i(35,29,31,12),0x03e00008,i(9,29,29,16));return h.finish()

def advance(lut, header=False):
    h=Block();h.emit(i(9,29,29,-16),i(43,29,24,0),i(43,29,25,4))
    h.emit(i(37,29,24,0x20 if header else 0x14));latin(h,24,25,'native')
    address(h,25,lut);h.emit(r(0,24,24,0,2),r(25,24,25),i(35,25,24,0))
    if header:
        h.emit(i(57,29,0,8),0x44980000,0x46800020,i(49,29,12,16),0x46006300,i(49,29,0,8))
    else:h.emit(r(17,24,17))
    h.branch(4,0,0,'done');h.label('native')
    if header:h.emit(i(49,29,12,16),0x46146300)
    else:h.emit(i(9,17,17,13))
    h.label('done');h.emit(i(35,29,24,0),i(35,29,25,4),j(0x4fcb0 if header else 0x92db0),i(9,29,29,16))
    return h.finish()

def length(lut):
    # Existing layout multiplies strlen/2 by13. Return the rounded VWF width
    # in these native units only for entirely printable Latin strings.
    h=Block();h.emit(r(4,0,8),i(13,0,9,0));address(h,12,lut)
    h.label('loop');h.emit(i(36,8,10,0));h.branch(4,10,0,'end')
    latin(h,10,11,'native');h.emit(r(0,10,11,0,2),r(12,11,11),i(35,11,11,0),r(9,11,9),i(9,8,8,1))
    h.branch(4,0,0,'loop');h.label('end')
    h.emit(i(9,9,9,12),i(13,0,10,13),r(9,10,0,0x1b),0x00001012,r(0,2,2,0,1),0x03e00008,0)
    h.label('native');h.emit(j(0x128b64),0);return h.finish()

def input_bound():
    h=Block();h.emit(r(20,0,4));h.branch(4,30,0,'empty')
    h.emit(r(30,23,24,0x2b));h.branch(4,24,0,'reject')
    h.emit(j(0x51128),0);h.label('empty');h.emit(j(0x511f4),0)
    h.label('reject');h.emit(i(13,0,17,1),j(0x511f4),0);return h.finish()

def cleared_temp():
    h=Block();h.emit(i(9,29,29,-32),i(43,29,31,28),i(43,29,4,24),jal(0x1a2e10),0,i(43,29,2,20))
    h.branch(4,2,0,'return');h.emit(r(2,0,4),r(0,0,5),i(35,29,6,24),jal(0x1288a4),0)
    h.label('return');h.emit(i(35,29,2,20),i(35,29,31,28),0x03e00008,i(9,29,29,32));return h.finish()

def build():
    original=SOURCE.read_bytes()
    if hashlib.sha256(original).hexdigest()!=SHA:raise ValueError('Input is not the preserved 0.1.8 executable')
    phoff,shoff=struct.unpack_from('<II',original,28)
    phnum,shnum=struct.unpack_from('<H',original,44)[0],struct.unpack_from('<H',original,48)[0]
    if phnum!=4:raise ValueError('Unexpected segment count')
    ph=[list(struct.unpack_from('<8I',original,phoff+n*32)) for n in range(phnum)]
    sections=[list(struct.unpack_from('<10I',original,shoff+n*40)) for n in range(shnum)]
    if ph[2][2]!=START or ph[3][0]!=0x700000a0:raise ValueError('Unexpected payload or relocation segment')
    oldpayload=original[ph[2][1]:ph[2][1]+ph[2][4]];payload=bytearray(oldpayload)
    oldrel=original[ph[3][1]:ph[3][1]+ph[3][4]]
    sites={struct.unpack_from('<II',oldrel,n) for n in range(0,len(oldrel),8)}
    patch=bytearray(original);entries=[];additions=[];changes=[]
    def replace(site,data,expected):
        if original[site+192:site+192+len(expected)]!=expected:raise ValueError(f'Changed site {site:x}')
        patch[site+192:site+192+len(data)]=data
        changes.append(dict(rva=hex(site),expected_hex=expected.hex(),replacement_hex=data.hex()))
    for off,text,pointers,pairs in STRINGS:
        raw=original[off:original.index(b'\0',off)]
        raw.decode('cp932')
        if any(v<32 for v in raw):raise ValueError('Unexpected control in setup text')
        while len(payload)%4:payload.append(0)
        addr=START+len(payload);payload.extend(text.encode('ascii')+b'\0')
        for site in pointers:
            if (site,2) not in sites:raise ValueError('Pointer relocation missing')
            replace(site,struct.pack('<I',addr),struct.pack('<I',off-192))
        for high,low in pairs:
            hi,lo=struct.unpack_from('<I',original,high+192)[0],struct.unpack_from('<I',original,low+192)[0]
            if hi>>26!=15 or lo>>26!=9 or (((hi&65535)<<16)+struct.unpack('<h',struct.pack('<H',lo&65535))[0])&0xffffffff!=off-192:
                raise ValueError(f'Address pair changed {high:x}/{low:x}')
            if (high,5) not in sites or (low,6) not in sites:raise ValueError('HI/LO relocation missing')
            replace(high,words([(hi&0xffff0000)|(((addr+0x8000)>>16)&65535)]),words([hi]))
            replace(low,words([(lo&0xffff0000)|(addr&65535)]),words([lo]))
        entries.append(dict(original_file_offset=hex(off),target=text,payload_rva=hex(addr),pointer_rvas=list(map(hex,pointers)),address_pairs=[[hex(a),hex(b)] for a,b in pairs]))
    while len(payload)%4:payload.append(0)
    lut=START+len(payload);payload.extend(words([round(v) for v in struct.unpack_from('<129f',oldpayload,0x800)]))
    hookmap={}
    for name,code in [('classify',classify()),('route',route(0xea900)),('header_advance',advance(lut,True)),('prompt_advance',advance(lut)),('prompt_length',length(lut)),('name_input_bound',input_bound()),('name_cleared_temp',cleared_temp())]:
        while len(payload)%16:payload.append(0)
        off=len(payload);hookmap[name]=START+off;payload.extend(code);additions.extend(relocate_code(payload,off,len(code)))
    for site,name,target in [(0x4fc48,'classify',0xe9c64),(0x92dc0,'classify',0xe9c64),(0x4fca0,'route',0xea900),(0x92e08,'route',0xea900),(0x510fc,'name_cleared_temp',0x1a2e10),*[(s,'prompt_length',0x128b64) for s in (0x9320c,0x93218,0x93224,0x93230)]]:
        if (site,4) not in sites:raise ValueError('Call relocation missing')
        replace(site,words([jal(hookmap[name])]),words([jal(target)]))
    for site,name,expected in [(0x4fca8,'header_advance',words([i(49,29,12,0),0x46146300])),(0x92e10,'prompt_advance',words([0x1000ffe7,i(9,17,17,13)])),(0x51120,'name_input_bound',words([i(4,30,0,52),r(20,0,4,0x25)]))]:
        if any(off==site and ((flags>>8)&255)==0 for off,flags in sites):raise ValueError('Unexpected relocation at inline hook')
        replace(site,words([j(hookmap[name]),0]),expected);additions.append(reloc(site,4,0))
    # Persistent CP932 storage and dispatch retain original capacities. UTF16
    # buffers double; the independent CP932 scratch allocation also doubles and
    # is cleared because the unchanged validator scans two bytes per character.
    for site,reg,cap in [(0x502ec,4,10),(0x502f8,4,18),(0x50304,4,26),(0x4ea34,6,10),(0x4ea54,5,10),(0x4ea70,6,18),(0x4ea90,5,18),(0x4eaac,6,26),(0x4eacc,5,26)]:
        replace(site,words([i(13,0,reg,cap*2)]),words([i(13,0,reg,cap)]))
    for site,source,dest in [(0x51100,23,4),(0x5110c,23,4),(0x51130,23,6),(0x5120c,23,6),(0x51258,23,6),(0x51260,23,5)]:
        replace(site,words([r(0,source,dest,0,1)]),words([r(source,0,dest,0x25)]))
    # Copying the UTF16 destination uses twice the cap, without changing s7.
    # The original slt at these sites is needed: inject doubled bound through
    # a small inline block and return to its original branch with the result.
    for site in (0x51214,0x51234):
        off=align(len(payload),16);payload.extend(bytes(off-len(payload)))
        # Branch delay slots must remain the native instructions: relocate the
        # branch itself to the block, with its original delay and target.
        branch=struct.unpack_from('<I',original,site+4+192)[0]
        delay=struct.unpack_from('<I',original,site+8+192)[0]
        target=site+8+struct.unpack('<h',struct.pack('<H',branch&65535))[0]*4
        h=Block();h.emit(r(0,23,24,0,1),r(4,24,5,0x2a))
        if branch>>26==20:
            h.branch(5,5,0,'fallthrough');h.emit(delay,j(target),0)
        elif branch>>26==5:
            h.branch(5,5,0,'taken');h.code[-1]=delay
            h.emit(j(site+12),0);h.label('taken');h.emit(j(target),0)
        else:raise ValueError('Unexpected name copy branch')
        if branch>>26==20:h.label('fallthrough');h.emit(j(site+12),0)
        actual=h.finish();payload.extend(actual)
        additions.extend(relocate_code(payload,off,len(actual)))
        replace(site,words([j(START+off),0]),original[site+192:site+200])
        additions.append(reloc(site,4,0));hookmap[f'name_copy_bound_{site:x}']=START+off
    for site,cap in [(0x512b4,10),(0x5130c,18),(0x51364,26)]:replace(site,words([i(11,2,4,cap)]),words([i(11,2,4,cap+1)]))
    payload_file=align(len(patch),64);patch.extend(bytes(payload_file-len(patch)));patch.extend(payload)
    rel_file=align(len(patch),16);patch.extend(bytes(rel_file-len(patch)));patch.extend(oldrel+b''.join(additions))
    for s in sections:
        if s[1]==0x700000a0:s[4]=rel_file+(s[4]-ph[3][1])
        elif s[3]==START and s[4]==ph[2][1]:s[4]=payload_file;s[5]=len(payload)
    payload_section=next(n for n,s in enumerate(sections) if s[3]==START and s[4]==payload_file)
    sections.append([0,0x700000a0,0,0,rel_file+len(oldrel),len(additions)*8,0,payload_section,4,8])
    newsh=align(len(patch),4);patch.extend(bytes(newsh-len(patch)))
    for s in sections:patch.extend(struct.pack('<10I',*s))
    ph[2][1]=payload_file;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=rel_file;ph[3][4]=len(oldrel)+len(additions)*8
    for n,p in enumerate(ph):struct.pack_into('<8I',patch,phoff+n*32,*p)
    struct.pack_into('<I',patch,32,newsh);struct.pack_into('<H',patch,48,len(sections))
    spans=sorted((s[4],s[4]+s[5]) for s in sections if s[1]==0x700000a0)
    assert spans[0][0]==rel_file and spans[-1][1]==rel_file+ph[3][4] and all(a[1]==b[0] for a,b in zip(spans,spans[1:]))
    assert payload[:len(oldpayload)]==oldpayload
    for e in entries:
        off=int(e['original_file_offset'],16);end=original.index(b'\0',off)+1
        assert patch[off:end]==original[off:end]
    digest=hashlib.sha256(patch).hexdigest()
    return bytes(patch),dict(version='0.1.9',status='setup_candidate_runtime_unverified',runtime_verified=False,input_sha256=SHA,output_sha256=digest,output_elf_sha256=digest,elf_bytes=len(patch),payload_bytes=len(payload),strings=entries,hooks={n:hex(v) for n,v in hookmap.items()},changed_rvas=changes,added_relocations=len(additions),old_payload_preserved=True,old_payload_sha256=hashlib.sha256(oldpayload).hexdigest(),old_relocations_preserved=True,old_relocations_sha256=hashlib.sha256(oldrel).hexdigest(),payload_growth=len(payload)-len(oldpayload),default_name_storage=dict(cp932_bytes=dict(surname=10,given_name=18,title=26),utf16_bytes=dict(surname=20,given_name=36,title=52),custom_validator_preserved=True,nul_included_in_capacity=True),limitations=['Name editor Latin OSK round-trip and cancellation require runtime verification.','Prompt centering rounds to native 13px layout units; runtime layout QA required.','Shared menu labels and confirmation draw path also affect other users of those labels/functions.'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    data,report=build();print(json.dumps(report,indent=2))
    if not a.write:print('DRY RUN: no output written.');return
    OUTPUT.mkdir(parents=True,exist_ok=True)
    for name,content in [('EBOOT.BIN',data),('setup_patch.en.json',(json.dumps(report,indent=2)+'\n').encode())]:
        dest=OUTPUT/name
        if dest.exists():raise ValueError(f'Refusing to overwrite {dest}')
        dest.write_bytes(content)

if __name__=='__main__':main()
