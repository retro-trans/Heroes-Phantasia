"""Bounded Latin ruby and command UI repair; dry first, hash-guarded writer."""
import argparse, copy, json, struct
from pathlib import Path
from executable_text_patch import Elf, ORIGINAL, reference_index
from native_menu_install_plan import cstring
from dialogue_vwf_hooks import Block
from live_vwf import i
from dialogue_measure_1a import measure_1a, instruction_cases
import dialogue_measure as dm
import english_bubble_layout_v10 as eb
from build_menu_patch import relocate_code
from prepare_relocation_019 import section_load, coverage
from prepare_bubble_scenes_036 import read, sha
from rebuild_dialogue import parse, rebuild
from dialogue_tokens import tokenize_bytes
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata

BASE = Path('work/output/0.1.47-title-credit-vwf-4x-candidate')
OUT = Path('work/output/0.1.48-dialogue-command-assets')
INPUT_SHA = '0e01d17e2578234eea09e32b996bb06edd91a67048963874ab5d0a1e3d1efa13'


def capture(generator, module):
    saved, found = module.Block, []
    class Capture(Block):
        def finish(self):
            result = super().finish(); found.append(self.labels.copy()); return result
    try:
        module.Block = Capture; result = generator()
    finally: module.Block = saved
    return result, found[0]


def ruby_chunk(labels, end_label, resume, pointer, counter, char, tmp):
    """Keep the original block extent and external branches/relocations fixed.

    Span digit2 remains required. A nonempty printable ASCII reading is skipped
    for body measurement only. Controls/native glyphs and missing closers reject.
    Every probe stays strictly inside the inherited1024-byte bound.
    """
    start, end = labels['hideo_reading'], labels[end_label]
    h = Block(); h.labels.update({k: labels[k]-start for k in ('return', resume)})
    h.emit(i(11,counter,tmp,1022)); h.branch(4,tmp,0,'return')
    h.emit(i(36,pointer,char,1),i(13,0,tmp,50)); h.branch(5,char,tmp,'return')
    h.emit(i(36,pointer,char,2),i(9,char,tmp,-32),i(11,tmp,tmp,95)); h.branch(4,tmp,0,'return')
    h.emit(i(9,pointer,pointer,2),i(9,counter,counter,2))
    h.label('reading'); h.emit(i(11,counter,tmp,1024)); h.branch(4,tmp,0,'return')
    h.emit(i(36,pointer,char,0),i(9,pointer,pointer,1),i(9,counter,counter,1),i(13,0,tmp,15))
    h.branch(4,char,tmp,resume)
    h.emit(i(9,char,tmp,-32),i(11,tmp,tmp,95)); h.branch(4,tmp,0,'return')
    h.branch(4,0,0,'reading')
    code = h.finish()
    if len(code) > (end-start)*4: raise ValueError('Ruby code exceeds reviewed block')
    return start*4, code+bytes((end-start)*4-len(code))


def scanner_cases(code, labels):
    from font_vram_hooks import instruction_model
    from live_vwf import j
    model=instruction_model(); b=model['B']; patched=bytearray(code)
    struct.pack_into('<II',patched,0,j(b+labels['byte']*4),0)
    for label, dest in [('return',0xeadbe00),('validated',0xeadbe20)]:
        struct.pack_into('<II',patched,labels[label]*4,j(dest),0)
    samples=[(b'hero\x0f2hero\x0f!\x12\x0e',True),
        (b'Hideo\x0f2Hideo\x0f\x12\x0e',True),
        (b'A\x0f2Other\x0f\x12\x0e',True),
        (b'A\x0f2\x0f\x12\x0e',False),(b'A\x0fXhero\x0f\0',False),
        (b'A\x0f2he\x11ro\x0f\0',False),(b'A\x0f2hero\0',False),
        (b'A\x0f2\x83\x41\x0f\0',False),
        (b'A'*1016+b'\x0f2hero\x0f\0',True),
        (b'A'*1017+b'\x0f2hero\x0f\0',False)]
    result=[]
    for raw, supported in samples:
        regs=[0]*32; regs[5]=0x220000; regs[10]=1; regs[29]=0x250000
        mem={0x220000+n:v for n,v in enumerate(raw)}
        # Primary scanner's one-row descriptor and end counter.
        mem.update({0x250000+n:0 for n in range(128)})
        mem.update({0x250000+76+n:v for n,v in enumerate(struct.pack('<I',1))})
        pc, out, reads=model['execute'](bytes(patched),regs,mem)
        if pc != (0xeadbe20 if supported else 0xeadbe00): raise ValueError('Scanner result differs')
        probes=[a for a in reads if 0x220000<=a<0x221000]
        if max(probes,default=0)>0x220000+min(len(raw)-1,1023): raise ValueError('Out-of-bound scanner')
        result.append(dict(bytes=len(raw),supported=supported,passed=True))
    return result


def build():
    incoming=(BASE/'EBOOT.BIN').read_bytes(); before=json.loads((BASE/'manifest.en.json').read_text())['setup_patch']
    if sha(incoming)!=INPUT_SHA: raise ValueError('Frozen47 executable changed')
    e=Elf(incoming); result=bytearray(incoming); allowed=set(); masks=[set(),set(),set()]; changes=[]
    def install(rva, data, name):
        off=e.file_offset(rva,len(data)); result[off:off+len(data)]=data
        allowed.update(range(off,off+len(data)))
        segment=next(n for n,p in enumerate(e.ph[:3])if p[2]<=rva<p[2]+p[4])
        masks[segment].update(range(rva-e.ph[segment][2],rva-e.ph[segment][2]+len(data)))
        changes.append(dict(name=name,rva=rva,bytes=len(data),before_sha256=sha(incoming[off:off+len(data)]),after_sha256=sha(data)))
    layout=before['english_bubble_layout']
    measured, ml=capture(lambda:measure_1a(before['body_integer_lut_rva'],True),dm)
    primary, pl=capture(lambda:eb.primary(layout['body_helper_rva'],layout['descriptor_rva'],layout['main_rva'],layout['epilogue_rva']),eb)
    main=primary[0]
    samples=[([b'hero\x0f2hero\x0f!\x12'],True),([b'Hideo\x0f2Hideo\x0f\x12'],True),
        ([b'A\x0f2Other\x0f\x12'],True),([b'A\x0f2\x0f\x12'],False),
        ([b'A\x0fXhero\x0f\x12'],False),([b'A\x0f2hero\0'],False),
        ([b'A\x0f2he\x11ro\x0f\x12'],False),([b'A\x0f2\x83\x41\x0f\x12'],False),
        ([b'A'*1017+b'\x0f2hero\x0f\x12'],True),([b'A'*1018+b'\x0f2hero\x0f\x12'],False)]
    new_codes=[]
    for name,code,labels,rva,end,resume,regs in [
        ('measurement',measured,ml,before['font_hooks']['measurement'],'endline','char',(11,25,13,15)),
        ('geometry_scanner',main,pl,layout['main_rva'],'row_end','byte',(5,6,7,24))]:
        old=bytearray(code); relocate_code(old,0,len(old))
        f=e.file_offset(rva,len(old))
        if incoming[f:f+len(old)]!=old:raise ValueError('Inherited generator differs: '+name)
        offset, chunk=ruby_chunk(labels,end,resume,*regs)
        if any(rva+offset<=e.ph[(flags>>8)&255][2]+site<rva+offset+len(chunk)for site,flags in e.relocs):raise ValueError('Ruby block owns a relocation')
        new=bytearray(code); new[offset:offset+len(chunk)]=chunk
        installed=bytearray(new); relocate_code(installed,0,len(installed))
        if installed[:offset]!=old[:offset]or installed[offset+len(chunk):]!=old[offset+len(chunk):]:raise ValueError('Unselected hook code changed')
        install(rva+offset,chunk,name); new_codes.append(bytes(new))
    widths=struct.unpack_from('<131I',incoming,e.file_offset(before['body_integer_lut_rva']))
    test_measure=bytearray(measure_1a(0x240000,True))
    offset,chunk=ruby_chunk(ml,'endline','char',11,25,13,15);test_measure[offset:offset+len(chunk)]=chunk
    cases=instruction_cases(widths,bytes(test_measure),samples)+instruction_cases(widths,bytes(test_measure))
    scanners=scanner_cases(new_codes[1],pl)
    # Only unconsumed spans of the previously audited retired storage are reused.
    retired=before['field_labels_047']; free=[(r['start'],r['end'])for r in retired['retired_menu_regions']]
    free.append((retired['retired_notification_bank']['rva'],retired['retired_notification_bank']['rva']+retired['retired_notification_bank']['bytes']))
    for p in retired['placements']:
        start,end=p['rva'],p['rva']+p['bytes']; reduced=[]
        for a,b in free:
            if b<=start or end<=a:reduced.append((a,b));continue
            if a<start:reduced.append((a,start))
            if end<b:reduced.append((end,b))
        free=reduced
    refs,_=reference_index(e)
    if any(a<=r['address']<b for r in refs for a,b in free):raise ValueError('Unused storage has a live typed owner')
    targets={55:'Commands',56:'Breakthrough',57:'Declare Victory',58:'End Turn',59:'Force a Breakthrough',60:'Skip',61:'Allies',62:'Enemies'}
    original=Elf(ORIGINAL.read_bytes()); labels=[]
    for index,target in sorted(targets.items(),key=lambda q:len(q[1]),reverse=True):
        slot=0x94760+index*4; source=original.word(slot)
        if e.word(slot)!=source:raise ValueError('Selected menu slot already modified')
        owners=[r for r in refs if source<=r['address']<source+len(cstring(e,source))]
        if len(owners)!=1 or owners[0]['sites']!=[slot]or owners[0]['kind']!='R_MIPS_32':raise ValueError('Unproved label ownership')
        data=target.encode('ascii')+b'\0'
        for k,(a,b)in sorted(enumerate(free),key=lambda q:q[1][1]-q[1][0]):
            if len(data)<=b-a:
                free[k]=(a+len(data),b); install(a,data,'command_'+str(index)); install(slot,struct.pack('<I',a),'menu_pointer_'+str(index)); break
        else:raise ValueError('No reviewed retired storage fits label')
        labels.append(dict(native_index=index,pointer_slot=slot,source_rva=source,target_rva=a,target=target,source_sha256=sha(cstring(original,source)),typed_relocation_ordinal=owners[0]['relocation_ordinals'][0]))
    # Wider R Commands plate: extend left, keeping its right edge/gauge fixed.
    words={0xb555c:(0x26f50130,0x26f50118),0xb55a4:(0x26f70141,0x26f70129),
        0xb55cc:(0x2a240009,0x2a24000c),0xb5624:(0x2a24000a,0x2a24000d),
        # Two adjacent command cards: x200..328 and336..472, gap8.
        0xb5c08:(0x340500e8,0x340500c8),0xb5c0c:(0x3407000d,0x34070010),
        0xb5c3c:(0x340500ea,0x340500ca),0xb5cc4:(0x34060108,0x340600e8),
        0xb5c60:(0x3406013d,0x34060135),
        0xb5d8c:(0x34050158,0x34050150),0xb5d90:(0x3407000d,0x34070011),
        0xb5dc0:(0x3405015a,0x34050152),0xb5e48:(0x34060178,0x34060170),
        0xb5de4:(0x340601ad,0x340601c5),
        # The shared mode2/3 plate has exactly two native callers. Extend
        # left96px and move its R icon/text with it, retaining right edge472.
        0xb56d8:(0x26770188,0x26770128),0xb5748:(0x2666019b,0x2666013b),
        0xb579c:(0x2666019b,0x2666013b),0xb5830:(0x34050188,0x34050128),
        0xb3d00:(0x26330048,0x263300a8),0xb3d2c:(0x2aa40008,0x2aa40014),
        0xb3da4:(0x2aa40008,0x2aa40014)}
    calls=[e.ph[0][2]+n-e.ph[0][1]for n in range(e.ph[0][1],e.ph[0][1]+e.ph[0][4],4)
        if struct.unpack_from('<I',incoming,n)[0]==0x0c000000|(0xb3cac>>2)]
    if calls!=[0xb5704,0xb580c]:raise ValueError('Command mode plate has another caller')
    for site,(old,new)in words.items():
        if e.word(site)!=old:raise ValueError('Native UI instruction changed at '+hex(site))
        install(site,struct.pack('<I',new),'command_layout')
    data=bytes(result); out=Elf(data); coverage(data)
    if out.ph!=e.ph or out.relocs!=e.relocs:raise ValueError('Loaded spans/relocations changed')
    if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,data))):raise ValueError('Unselected bytes changed')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base); b,_,skipped,_=section_load(data,base)
        if skipped or any(len(x)!=len(y)or any(v!=w and n not in masks[s]for n,(v,w)in enumerate(zip(x,y)))for s,(x,y)in enumerate(zip(a,b))):raise ValueError('Unselected loaded memory differs')
        for row in labels:
            if struct.unpack_from('<I',b[0],row['pointer_slot'])[0]!=base+row['target_rva']:raise ValueError('Loaded label pointer differs')
        models.append(dict(base=base,loaded_growth_bytes=0,unselected_memory_exact=True))
    report=copy.deepcopy(before); report.update(version='0.1.48',input_version='0.1.47',input_sha256=INPUT_SHA,output_elf_sha256=sha(data),output_sha256=sha(data),elf_bytes=len(data),runtime_verified=False)
    for key in ('main','primary','body_helper'):
        if key=='main':report['english_bubble_layout'][key+'_sha256']=sha(data[out.file_offset(layout[key+'_rva']):][:layout[key+'_bytes']])
    report['font_native_tail_loaded_extension_sha256']=sha(data[e.ph[2][1]:e.ph[2][1]+e.ph[2][4]])
    report['english_bubble_layout']['accepted_controls']=[s if s!='exact Hideo reading'else 'nonempty printable ASCII reading with preserved span digit2'for s in layout['accepted_controls']]
    for chunk in report['native_tail_compaction']['chunks']:
        f=chunk['file_offset']; n=chunk['bytes']
        if data[f:f+n]!=incoming[f:f+n]:chunk['output_sha256']=sha(data[f:f+n]);chunk['current_proof_scope']='Bounded Latin ruby scanner repair; all bytes outside selected block retained.'
    report['dialogue_commands_048']=dict(labels=labels,changes=changes,measurement_cases=cases,scanner_cases=scanners,loader_models=models,loaded_growth_bytes=0,remaining_retired_bytes=sum(b-a for a,b in free),ruby_scope='Nonempty printable ASCII reading, preserved span digit2,1024-byte probe bound.',tail_geometry_and_scene_tracks_exact=True,natural_gameplay_verified=False)
    advances=struct.unpack_from('<131f',incoming,e.file_offset(before['float_width_lut_rva']))
    fits=[dict(text=text,text_x=x,text_advance=sum(advances[ord(c)]for c in text),card_left=left,card_right=right)
        for text,x,left,right in [('Commands',297,280,384),('Breakthrough',232,200,328),('Declare Victory',368,336,472),('End Turn',308,288,392),('Force a Breakthrough',315,296,472),('Skip',315,296,472)]]
    if any(f['text_x']+f['text_advance']>f['card_right']-2 for f in fits):raise ValueError('Full command label exceeds card')
    report['dialogue_commands_048']['command_layout_models']=fits
    authoritative_font_metadata(data,report)
    if validate_native_png_metadata(data,report)!=validate_native_png_metadata(incoming,before):raise ValueError('Font/image contract changed')
    assets={}; reflows=[]
    names=['phase/bin/p101110.bin','phase/bin/p101111.bin']
    for name,raw in read(BASE/'HP.CPK',names).items():
        p=parse(name,raw); old=p['spans'][p['refs'][0][1]][0]
        expected=b'\x1cLina\x0eAll right, descendant of the hero\x0f2hero\x0f!\x11Now that this beautiful genius sorceress is here,\x11your troubles are over!\x12\x0e'
        if old!=expected:raise ValueError('Reported Lina row changed')
        new=b'\x1cLina\x0eAll right, descendant of the hero\x0f2hero\x0f!\x11Now that this beautiful genius\x11sorceress is here,\x11your troubles are over!\x12\x0e'
        signature=lambda s:[(t.kind,t.code,t.argument)for t in tokenize_bytes(s,True)if t.kind!='latin'and t.code!=17]
        if signature(old)!=signature(new)or old.replace(b'\x11',b' ')!=new.replace(b'\x11',b' '):raise ValueError('Dialogue words or controls changed')
        changed,np=rebuild(name,raw,{0:new})
        if raw[p['head'][0]:p['start']]!=changed[np['head'][0]:np['start']]or raw[p['end']:]!=changed[np['end']:]:raise ValueError('Authored tracks changed')
        if any(p['spans'][off][0]!=np['spans'][np['refs'][ix][1]][0]for ix,(_,off)in enumerate(p['refs'])if ix):raise ValueError('Other rows changed')
        lines=[]
        for line in new.split(b'\x0e',1)[1].split(b'\x12')[0].split(b'\x11'):
            lines.append(sum(widths[t.code]for t in tokenize_bytes(line,True)if t.kind=='latin'and not t.ruby))
        if max(lines)>220:raise ValueError('Lina lines exceed reviewed width')
        assets[name]=changed;reflows.append(dict(resource=name,reference_index=0,old_english=old.decode('ascii'),new_english=new.decode('ascii'),line_advances=lines,input_sha256=sha(raw),output_sha256=sha(changed),words_and_nonline_controls_exact=True,authored_tracks_and_other_rows_exact=True))
    report['dialogue_commands_048']['reflows']=reflows
    return data,report,assets


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256');a=ap.parse_args()
    data,report,assets=build(); p=report['dialogue_commands_048']
    print(json.dumps(dict(version='0.1.48',sha256=sha(data),labels=p['labels'],reflows=p['reflows'],measurement_cases=len(p['measurement_cases']),scanner_cases=len(p['scanner_cases']),loaded_growth_bytes=0),indent=2))
    if not a.write:print('DRY RUN');return
    if a.expected_sha256!=sha(data)or OUT.exists():raise ValueError('Reviewed digest and fresh output required')
    OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(data)
    if (OUT/'EBOOT.BIN').read_bytes()!=data:raise ValueError('Executable readback differs')
    (OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,raw in assets.items():
        dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    queue=dict(schema_version=1,language='en',rows=[dict(id='command_048_'+str(r['native_index']),category='battle_command_ui',target=r['target'],status='installed_static_verified',native_index=r['native_index'])for r in p['labels']])
    Path('work/translation/en/dialogue_commands_048.en.json').write_text(json.dumps(queue,indent=2)+'\n')

if __name__=='__main__':main()
