"""Bounded native custom-polygon tests in an isolated debugger; dry first.

Temporary-code mode is preparation evidence, not installed ISO validation.
All borrowed memory, manager state, registers and temporary code are restored.
"""
import argparse,json,struct,math,time,array
from PIL import Image
from pathlib import Path
from ppsspp_debug import Debugger
from live_vwf import gpr,registers,restore_registers,write
from executable_text_patch import Elf
from prepare_relocation_019 import section_load
from prepare_english_bubbles_v10 import build,SOURCE,CORE,CORE_BYTES,REGION,REGION_BYTES,DORMANT,DORMANT_BYTES,sha
from bubble_metrics import load_templates,TEMPLATE_BASE,TEMPLATE_STRIDE
from english_bubble_layout_v10 import native_corners
from rebuild_dialogue import parse
from dialogue_tokens import tokenize_bytes
from audit_bubble_scenes_035 import build as reported_scenes
from prepare_bubble_scenes_036 import build as current_scenes
from audit_bubble_slopes_038 import build as slope_scenes
from audit_bubble_rays_039 import build as airport_scenes
from prepare_bubble_order_039 import build as ordered_scenes
from prepare_field_bubble_039 import build as field_scene
from prepare_bubble_reflow_040 import build as elevator_reflow,record as scene_record
from prepare_bubble_reflow_041 import build as construction_reflow
from prepare_bubble_reflow_042 import build as kogoro_reflow
from bubble_metrics import centered_interval

def reflows():
    """Read historical prepared binaries, without reinterpreting current queues."""
    root=Path('work/output/0.1.34-bubble-reflow-assets')
    proof=json.loads((root/'reflows.en.json').read_text())
    assets={r['resource']:(root/Path(r['resource']).name).read_bytes()for r in proof['resources']if r['changed_references']}
    return {},assets,proof

def area(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def signed(poly):return sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(poly,poly[1:]+poly[:1]))
def fan_check(poly,hub,label,tolerance=0.01):
    parts=[area(hub,a,b)for a,b in zip(poly,poly[1:]+poly[:1])]
    if abs(sum(abs(v)for v in parts)-abs(signed(poly)))>tolerance:
        raise ValueError(label+': fan fill escapes or overlaps the contour '+str(dict(points=poly,hub=hub,parts=parts,error=sum(abs(v)for v in parts)-abs(signed(poly)))))
    return abs(signed(poly))/2

def definitions():
    cases=[]
    for t in load_templates():
        family=(t['template_id']-3)%10
        if family<8 and t['count']==10:
            lines=t['template_id']//10%4+1
            cases.append((f"standard_{t['template_id']}",t['template_id'],240.,140.,b'\x11'.join([b'A']*lines)+b'\x12\x0e\0',lines,80.,1.,0.,True))
    cases.extend([
      ('kogoro',118,125.,104.,b"If you're in HOLY,\x11then you must be an\x11\x05050\x1603Alter user\x1601, too!\x12\x0e\0",3,66.,1.,0.,True),
      ('serish',8,369.,99.,b'Who will accompany you?\x12\x0e\0',1,82.5,1.,0.,True),
      ('top_clamp',118,125.,40.,b'A\x11B\x11C\x11D\x12\x0e\0',4,80.,1.,0.,True),
      ('right_clamp',118,465.,140.,b'A\x12\x0e\0',1,80.,1.,0.,True),
      ('left_clamp',4,15.,140.,b'A\x12\x0e\0',1,80.,1.,0.,True),
      # Neither original ray can reach a long socket edge of this58px body
      # inside the safe viewport. Preserve native geometry instead of turning
      # the tail toward an unrelated edge or altering the offscreen anchor.
      ('speaker_left_offscreen',75,-40.,65.,b'A\x12\x0e\0',1,80.,1.,0.,False),
      ('speaker_right_offscreen',75,520.,65.,b'A\x12\x0e\0',1,80.,1.,0.,False),
      ('hideo',118,125.,104.,b'Hideo\x0f2Hideo\x0f\x12\x0e\0',1,30.,1.,0.,True),
      ('private_pairs',118,125.,104.,b'A\xf0\x40\xf0\x41\x12\x0e\0',1,30.,1.,0.,True),
      ('mode_controls',118,125.,104.,b'\x1a5\x172A\x12\x0e\0',1,30.,1.,0.,True),
      ('animated',118,125.,104.,b'A\x12\x0e\0',1,30.,.5,0.,False),
      ('rotated',118,125.,104.,b'A\x12\x0e\0',1,30.,1.,1.,False),
      ('native_text',118,125.,104.,b'\x82\xa0\x12\x0e\0',1,30.,1.,0.,False),
      ('malformed_color',118,125.,104.,b'A\x16X1\x12\x0e\0',1,30.,1.,0.,False),
      ('malformed_delay',118,125.,104.,b'A\x050X0\x12\x0e\0',1,30.,1.,0.,False),
      ('name_substitution',118,125.,104.,b'A\x01'+b'0\x12\x0e\0',1,30.,1.,0.,True),
      ('invalid_name_selector',118,125.,104.,b'A\x01'+b'4\x12\x0e\0',1,30.,1.,0.,False),
      ('malformed_name',118,125.,104.,b'A\x01'+b'X\x12\x0e\0',1,30.,1.,0.,False),
      ('other_ruby',118,125.,104.,b'A\x0f1A\x0f\x12\x0e\0',1,30.,1.,0.,False),
      ('star',1,125.,104.,b'A\x12\x0e\0',1,30.,1.,0.,False),
      ('too_wide',118,125.,104.,b'A\x12\x0e\0',1,240.,1.,0.,False),
    ])
    _,assets,_=reflows();assets.update(ordered_scenes()[0]);assets.update(elevator_reflow()[0])
    elf=Elf(SOURCE.read_bytes());widths=struct.unpack('<131I',SOURCE.read_bytes()[elf.file_offset(0x2e4000):][:524])
    for rec in reported_scenes()['records']:
        resource=rec['resource'];raw=assets[resource]
        p=parse(resource,raw);body=p['spans'][p['refs'][rec['reference_index']][1]][0].split(b'\x0e',1)[1]
        advances=[0];first_page=body.split(b'\x10',1)[0];lines=first_page.count(b'\x11')+1
        for token in tokenize_bytes(body,True):
            if token.kind=='latin':advances[-1]+=widths[token.code]
            elif token.code in (0x10,0x11):advances.append(0)
            elif token.code==0x0e:break
        x,y=rec['position'];cases.append((f'reported_{Path(resource).stem}_{rec["reference_index"]}',rec['shape'],x,y,first_page+b'\0',lines,max(advances)/2,1.,0.,True))
    for mode in (0,1,2,3,4):
        cases.append(('alignment_'+str(mode),118,125.,104.,b'A\x12\x0e\0',1,30.,1.,0.,False))
    cases.append(('alignment_mixed',118,125.,104.,b'A\x11B\x12\x0e\0',2,30.,1.,0.,False))
    audit=json.loads(Path('work/ui/dialogue/0.1.34/scene_audit.en.json').read_text())
    for rec in audit['records']:
        resource=rec['resource'];index=rec['reference_index'];bubble=rec['bubble']
        if resource not in assets or index not in (17,24,26,27):continue
        parsed=parse(resource,assets[resource]);raw=parsed['spans'][parsed['refs'][index][1]][0].split(b'\x0e',1)[1]
        advances=[0]
        for token in tokenize_bytes(raw,True):
            if token.kind=='latin':advances[-1]+=widths[token.code]
            elif token.code==0x11:advances.append(0)
            elif token.code==0x0e:break
        shape=bubble['shape_keys'][-1][1];_,x,y,_,_=bubble['position'][-1]
        cases.append((f'scene_{Path(resource).stem}_{index}',shape,x,y,raw+b'\0',len(advances),max(advances)/2,1.,0.,True))
    cases.extend([
        ('later_page',118,125.,104.,b'Visible English.\x12\x0e\0',1,45.,1.,0.,True),
        ('later_unsupported',118,125.,104.,b'\x82\xa0\x12\x0e\0',1,30.,1.,0.,False),
        ('bad_array_header',118,125.,104.,b'A\x12\x0e\0',1,30.,1.,0.,False),
    ])
    field=field_scene()[1]
    for page,body in enumerate(field['new_english'].encode('ascii').split(b'\x0e',1)[1].split(b'\x10')):
        advances=field['page_line_advances'][page]
        cases.append(('field_cougar'if page==0 else 'field_cougar_later',75,165.,65.,body+b'\0',len(advances),max(advances)/2,1.,0.,True))
    for lines in (5,6,7,8):
        cases.append((f'extended_{lines}',118,240.,100.,b'\x11'.join([b'A']*lines)+b'\x12\x0e\0',lines,40.,1.,0.,lines<8))
    for rec in current_scenes()[1]['records']:
        cases.append((f'current_{Path(rec["resource"]).stem}_{rec["reference_index"]}',rec['shape'],*rec['position'],
            bytes.fromhex(rec['body_hex'])+b'\0',rec['visible_lines'],rec['halfwidth'],1.,0.,True))
        if rec['native_name_width']:
            cases.append((f'default_names_{Path(rec["resource"]).stem}',rec['shape'],*rec['position'],
                bytes.fromhex(rec['body_hex'])+b'\0',3,91.,1.,0.,True))
    for rec in slope_scenes()['records']:
        cases.append((f'gratitude_{Path(rec["resource"]).stem}',rec['shape'],*rec['position'],
            bytes.fromhex(rec['body_hex'])+b'\0',rec['visible_lines'],rec['halfwidth'],1.,0.,True))
    for rec in airport_scenes():
        for page,raw in enumerate(bytes.fromhex(rec['body_hex']).split(b'\x10')):
            advances=[0]
            for token in tokenize_bytes(raw,True):
                if token.kind=='latin':advances[-1]+=widths[token.code]
                elif token.code==0x11:advances.append(0)
                elif token.code==0x0e:break
            cases.append((f'airport_{Path(rec["resource"]).stem}_{page}',rec['shape'],*rec['position'],raw+b'\0',len(advances),max(advances)/2,1.,0.,True))
    for rec in elevator_reflow()[1]['fixtures']:
        positions=list(dict.fromkeys(tuple(p[1:3])for p in rec['position_keys']if tuple(p[1:3])!=(0.,0.)))
        for position_index,position in enumerate(positions):
            for page_index,page in enumerate(rec['pages']):
                advances=page['line_advances']
                cases.append((f"elevator_{Path(rec['resource']).stem}_{rec['reference_index']}_{position_index}_{page_index}",
                    rec['shape'],*position,bytes.fromhex(page['body_hex'])+b'\0',len(advances),max(advances)/2,1.,0.,True))
    for rec in construction_reflow()[1]['fixtures']:
        positions=list(dict.fromkeys(tuple(p[1:3])for p in rec['position_keys']if tuple(p[1:3])!=(0.,0.)))
        for position_index,position in enumerate(positions):
            for page_index,page in enumerate(rec['pages']):
                advances=page['line_advances']
                cases.append((f"construction_{Path(rec['resource']).stem}_{rec['reference_index']}_{position_index}_{page_index}",
                    rec['shape'],*position,bytes.fromhex(page['body_hex'])+b'\0',len(advances),max(advances)/2,1.,0.,True))
    # Reported small tails, including the older speech bubble in the same shot.
    from prepare_bubble_scenes_036 import read
    shot_name='phase/bin/p101041.bin'
    shot_raw=read(Path('work/output/0.1.41-title-credit-vwf-4x-candidate/HP.CPK'),[shot_name])[shot_name]
    wanted=[scene_record(shot_name,shot_raw,n,widths)for n in (23,24)]
    wanted+=kogoro_reflow()[1]['fixtures']
    for rec in wanted:
        for page_index,page in enumerate(rec['pages']):
            advances=page['line_advances']
            cases.append((f"outlined_{Path(rec['resource']).stem}_{rec['reference_index']}_{page_index}",rec['shape'],*rec['position'],bytes.fromhex(page['body_hex'])+b'\0',len(advances),max(advances)/2,1.,0.,True))
    return cases

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--port',type=int,default=45388)
    ap.add_argument('--manifest',type=Path,default=Path('work/output/0.1.33-title-credit-vwf-4x-candidate/manifest.en.json'))
    ap.add_argument('--temporary-code',action='store_true');ap.add_argument('--run',action='store_true')
    ap.add_argument('--render-reported',action='store_true',help='Append the reported native bubble draws before GU Finish in this isolated session')
    ap.add_argument('--render-single',action='store_true',help='Render the second reported Cougar shot instead of the two-bubble shot')
    ap.add_argument('--output',type=Path,default=Path('work/ui/dialogue/0.1.42/native_preparation.en.json'));a=ap.parse_args()
    candidate,prep=build();m=json.loads(a.manifest.read_text());defs=definitions();source_corners=native_corners()
    if a.render_single:a.render_reported=True
    if a.render_reported:defs=[r for r in defs if r[0] in (('reported_p101041_4',)if a.render_single else ('reported_p101041_0','reported_p101041_1'))]
    print(json.dumps(dict(candidate_sha256=sha(candidate),loaded_build=m['version'],temporary_code=a.temporary_code,cases=len(defs)),indent=2))
    if not a.run:print('DRY RUN');return
    if a.output.exists():raise ValueError('Fresh native evidence required')
    loaded=(a.manifest.parent/'EBOOT.BIN').read_bytes()
    if sha(loaded)!=m['output_elf_sha256'] or (not a.temporary_code and loaded!=candidate):raise ValueError('Loaded/candidate identity differs')
    d=Debugger(a.port);saved=oldmem=oldmanager=None;start=manager=bp=None;replaced=[]
    try:
        if not d.call('cpu.status').get('stepping'):d.call('cpu.stepping',expect='cpu.stepping')
        saved=registers(d);regs=gpr(saved);base=next(x['address']for x in d.call('hle.module.list')['modules']if x['name']=='hp_proj')
        if a.render_reported:
            saved=None
            d.call('cpu.runUntil',address=base+0x1b6cdc,expect='cpu.stepping')
            saved=registers(d);regs=gpr(saved)
        if a.temporary_code:
            memories,_,_,_=section_load(candidate,base)
            for rva,size,seg in ((CORE,CORE_BYTES,2),(REGION,REGION_BYTES,0),(DORMANT,DORMANT_BYTES,0)):
                old=d.read(base+rva,size);replaced.append((base+rva,old));off=rva-Elf(candidate).ph[seg][2]
                write(d,base+rva,bytes(memories[seg][off:off+size]))
            for rva in (0xe4ebc,0xe4ed8,0xece3c,0xe4e68,0xe4e6c):
                old=d.read(base+rva,4);replaced.append((base+rva,old));write(d,base+rva,bytes(memories[0][rva:rva+4]))
            repair=prep['serish_tail_patch'];rva=repair['repair_rva'];size=repair['repair_bytes']
            old=d.read(base+rva,size);replaced.append((base+rva,old));write(d,base+rva,bytes(memories[0][rva:rva+size]))
        start=regs['sp']-8192;oldmem=d.read(start,8192)
        # Exercise the unmodified native phase layer reader against both
        # reordered headers, verifying whole layer identities and ref keys.
        order_assets,order_proof=ordered_scenes();order_checks=[];fixture=start+5000
        for record in order_proof['records']:
            raw=order_assets[record['resource']];parsed=parse(record['resource'],raw);rb=parsed['head'][0];rh=struct.unpack_from('<16I',raw,rb)
            data=bytearray(416);struct.pack_into('<I',data,0x2c,1);struct.pack_into('<I',data,0x30,64);struct.pack_into('<I',data,0x38,80)
            struct.pack_into('<4I',data,64,4,0,0,0);data[80:]=raw[rb+rh[14]:rb+rh[14]+336];write(d,fixture,data)
            for index in range(4):
                for reg,v in [('a0',fixture),('a1',0),('a2',index),('sp',regs['sp']-1024),('ra',regs['pc']),('pc',base+0xdded4)]:d.call('cpu.setReg',name=reg,value=v)
                d.call('cpu.runUntil',address=regs['pc'],expect='cpu.stepping');rr=gpr(registers(d))
                if rr['v0']!=fixture+80+84*index or d.read(rr['v0'],84)!=bytes(data[80+84*index:80+84*(index+1)]):raise ValueError('Native layer reader changed bubble order')
                restore_registers(d,saved)
            if [key for key,off in parsed['refs'][:2]]!=[3,2]:raise ValueError('Moved speaker text keys differ')
            order_checks.append(dict(resource=record['resource'],native_layer_reader_verified=True,order_back_to_front=['Mitch','Cougar'],text_reference_keys=[3,2],tracks_and_identity_exact=True))
        window=start+128;owner=start+1100;context=start+1400;container=start+1500;source=start+1600;rows=start+2300;temp_sp=regs['sp']-1024
        manager=base+0x166f2c4;oldmanager=d.read(manager,48);bp=base+0xe4e14
        d.call('cpu.breakpoint.add',address=bp);templates=load_templates();cases=[]
        for name,shape,x,y,raw,lines,halfwidth,scale,rotation,supported in defs:
            t=templates[shape];buf=bytearray(0x360)
            struct.pack_into('<3f',buf,0x2d0,x,y,0.);struct.pack_into('<3f',buf,0x2e0,rotation,0.,0.)
            struct.pack_into('<3f',buf,0x2f0,scale,scale,scale)
            struct.pack_into('<4f',buf,0x304,*t['speaker_offset'],*t['text_offset'])
            struct.pack_into('<H',buf,0x318,shape);struct.pack_into('<I',buf,0x31c,0x12345678);struct.pack_into('<I',buf,0x348,owner)
            struct.pack_into('<I',buf,0x300,0xffffffff)
            write(d,window,buf)
            buf=bytearray(0x100);struct.pack_into('<I',buf,0x98,context);struct.pack_into('<I',buf,0xec,2);write(d,owner,buf)
            buf=bytearray(0x40);struct.pack_into('<I',buf,0x30,3);write(d,context,buf)
            first=3 if name.startswith('later_')else 0
            buf=bytearray(0x40);struct.pack_into('<II',buf,8,3,2);struct.pack_into('<4I',buf,0x14,source,lines,lines,first)
            struct.pack_into('<I',buf,4,rows)
            struct.pack_into('<f',buf,0x2c,halfwidth);write(d,container,buf);write(d,source,raw)
            write(d,rows-16,struct.pack('<4I',8*0xe8 if name!='bad_array_header'else 123,0xfffffff7,0,0))
            buf=bytearray(8*0xe8)
            starts=[0]+[n+1 for n,v in enumerate(raw)if v in (0x10,0x11)]
            for row in range(lines):
                alignment=int(name[-1])if name.startswith('alignment_')and name!='alignment_mixed'else (2 if name=='alignment_mixed'and row==1 else -1)
                struct.pack_into('<i',buf,(first+row)*0xe8+0x70,alignment)
                struct.pack_into('<I',buf,(first+row)*0xe8+4,source+starts[row])
            write(d,rows,buf)
            buf=bytearray(oldmanager);struct.pack_into('<I',buf,0,1);struct.pack_into('<II',buf,0x28,1,container);write(d,manager,buf)
            for n,v in [('a0',window),('sp',temp_sp),('pc',base+CORE)]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=bp,expect='cpu.stepping');out=registers(d);actual=gpr(out)
            if actual['pc']!=bp or actual['sp']!=temp_sp-224 or actual['a0']!=window or actual['a1']!=0x12345678:raise ValueError(name+': continuation ABI differs')
            for n,v in regs.items():
                if n not in ('pc','a0','a1','sp')and actual[n]!=v:raise ValueError(name+': GPR clobber '+n)
            for old,now in zip(saved[1:],out[1:]):
                if old['uintValues']!=now['uintValues']:raise ValueError(name+': floating/VFPU ABI differs')
            value=d.read(window,0x360);cx,cy=struct.unpack_from('<2f',value,0x2d0);body=[]
            if (cx,cy)!=(x,y):raise ValueError(name+': authored scene center changed')
            text_cx=struct.unpack_from('<f',value,0x58)[0]
            count=11 if supported else t['count']
            for off in (0,0xf0,0x1e0):body.append([struct.unpack_from('<2f',value,off+n*8)for n in range(count)])
            if supported:
                source_tip=(shape-3)%10+1
                expected=[list(t['outline'][source_tip]) for _ in range(3)]
                if name=='serish':expected=[[243.-x,134.-y]]*3
                tips=[n for n,p in enumerate(body[0])if abs(p[0]+cx-expected[0][0]-x)<1e-4 and abs(p[1]+cy-expected[0][1]-y)<1e-4]
                if len(tips)!=1:raise ValueError(name+': outline tip missing or ambiguous '+str(dict(marker=struct.unpack_from('<I',value,0x5c)[0],points=body[0],expected=expected[0],source_address=source,stack=temp_sp)))
                tip=tips[0]
                # The new base midpoint must stay on the original Japanese
                # reverse ray, including every border bank and a sharp tip.
                native_tip=t['outline'][source_tip]
                ray=[(t['outline'][source_tip-1][a]+t['outline'][source_tip+1][a])/2-native_tip[a]for a in (0,1)]
                for points in body:
                    base_a=points[tip-1];base_b=points[(tip+1)%11];pnt=points[tip];v=[(base_a[n]+base_b[n])/2-pnt[n]for n in (0,1)]
                    if abs(v[0]*ray[1]-v[1]*ray[0])>0.01 or sum(v[n]*ray[n]for n in (0,1))<=0:raise ValueError(name+': original Japanese tail direction changed '+str(dict(actual=v,expected=ray,cross=v[0]*ray[1]-v[1]*ray[0],points=points)))
                base_a=body[0][tip-1];base_b=body[0][(tip+1)%11];pnt=body[0][tip]
                va=[base_a[n]-pnt[n]for n in (0,1)];vb=[base_b[n]-pnt[n]for n in (0,1)]
                reach=abs(area(base_a,base_b,pnt))/math.dist(base_a,base_b)
                base_width=math.dist(base_a,base_b)
                if name.startswith('elevator_p101041_27')and (reach<11.99 or base_width<3.59):raise ValueError(name+': reported tail still too small')
                angle=math.degrees(math.acos(max(-1.,min(1.,sum(va[n]*vb[n]for n in (0,1))/math.hypot(*va)/math.hypot(*vb)))))
                if angle>40:raise ValueError(name+': tail point too broad')
                # Dark outer triangle must enclose the white triangle; sample
                # both white edges away from the deliberately shared sharp tip.
                outer=body[2]
                for basepoint in (body[1][tip-1],body[1][(tip+1)%11]):
                    sample=tuple((basepoint[n]+body[1][tip][n])/2 for n in (0,1))
                    intersections=sum((a[1]>sample[1])!=(b[1]>sample[1]) and sample[0]<a[0]+(sample[1]-a[1])*(b[0]-a[0])/(b[1]-a[1]) for a,b in zip(outer,outer[1:]+outer[:1]))
                    if intersections%2!=1:
                        raise ValueError(name+': white tail escapes dark outline '+str(dict(outer=outer,sample=sample)))
                inner_width=math.dist(body[1][tip-1],body[1][(tip+1)%11])
                outer_width=math.dist(body[2][tip-1],body[2][(tip+1)%11])
                if outer_width-inner_width<2.9:raise ValueError(name+': missing visible tail outline')

                for points,goal in zip(body,expected):
                    vx,vy=points[tip]
                    if abs(vx+cx-goal[0]-x)>1e-4 or abs(vy+cy-goal[1]-y)>1e-4:raise ValueError(name+': tail endpoint moved')
                others=[p for n,p in enumerate(body[0])if n!=tip]
                vx,vy=body[0][tip]
                if min(p[0]for p in others)<=vx<=max(p[0]for p in others)and min(p[1]for p in others)<=vy<=max(p[1]for p in others):raise ValueError(name+': tip enclosed by body')
                for n,(vx,vy)in enumerate(body[0]):
                    if n!=tip and not(8-1e-4<=vx+cx<=472+1e-4 and 36-1e-4<=vy+cy<=252+1e-4):raise ValueError(name+': body outside viewport')
                top=struct.unpack_from('<f',value,0x310)[0]+cy
                left=min(p[0]+cx for n,p in enumerate(body[0])if n!=tip)
                right=max(p[0]+cx for n,p in enumerate(body[0])if n!=tip)
                if text_cx-halfwidth<left+9.5 or text_cx+halfwidth>right-9.5:
                    raise ValueError(name+': centered text width exceeds padded body')
                if not math.isfinite(top)or top<36 or top+(lines-1)*22+16>max(p[1]+cy for n,p in enumerate(body[0])if n!=tip)-8:
                    raise ValueError(f'{name}: text bands exceed padded body top={top} cy={cy} points={body[0]} offsets={struct.unpack_from("<4f",value,0x304)}')
                # Check the actual sloping white interior over every glyph
                # band. A bounding rectangle cannot catch angled-side leaks.
                native_body=[(p[0]+cx-text_cx,p[1]+cy)for n,p in enumerate(body[1])if n not in ((tip-1)%11,tip,(tip+1)%11)]
                corners=[p for n,p in enumerate(body[0])if n not in ((tip-1)%11,tip,(tip+1)%11)]
                original=source_corners[(shape-3)//10]
                if len(corners)!=8:raise ValueError(name+': body corner removed')
                for ca,cb in ((1,2),(5,6)):
                    if abs((corners[ca][0]-corners[cb][0])-(original[ca][0]-original[cb][0]))>1e-4:
                        raise ValueError(name+': original side-corner slope changed')
                for row in range(lines):
                    lo=top+row*22;hi=lo+16
                    samples=[lo+0.001,hi-0.001]+[p[1]for p in native_body if lo<p[1]<hi]
                    for yy in samples:
                        interval=centered_interval(native_body,yy)
                        if interval is None or interval[0]>-halfwidth-2 or interval[1]<halfwidth+2:
                            raise ValueError(name+': text escapes sloping interior '+str(dict(y=yy,interval=interval,halfwidth=halfwidth,body=native_body,text_top=top,lines=lines)))
                if name.startswith(('default_names_','current_p101050_2','current_p101051_2')):
                    if min(p[1]+cy for n,p in enumerate(body[0])if n!=tip)<=expected[0][1]+y:
                        raise ValueError(name+': name introduction flipped above the native anchor')
            else:
                if (cx,cy)!=(x,y)or list(struct.unpack_from('<4f',value,0x304))!=t['speaker_offset']+t['text_offset']:
                    raise ValueError(name+': fallback text offsets differ')
                for points,expected in zip(body,[t['outline'],*t['banks']]):
                    if any(abs(a-b)>1e-4 for pair,goal in zip(points,expected)for a,b in zip(pair,goal)):raise ValueError(name+': fallback geometry differs')
            cases.append(dict(case=name,shape=shape,selected=supported,visible_lines=lines,center=[cx,cy],text_center_x=text_cx,passed=True,
                sloping_text_interior_verified=supported,native_side_corner_deltas_preserved=supported,original_tail_ray_verified=supported,
                tail_angle_deg=angle if supported else None,tail_perpendicular_reach_px=reach if supported else None,tail_base_width_px=base_width if supported else None,tail_dark_outline_verified=supported,tail_inner_base_width_px=inner_width if supported else None,tail_outer_base_width_px=outer_width if supported else None))
            # A second draw with the same native window must be byte-identical.
            for n,v in [('a0',window),('sp',temp_sp),('pc',base+CORE)]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=bp,expect='cpu.stepping')
            if d.read(window,0x360)!=value:raise ValueError(name+': repeated draw drifted')
            cases[-1]['repeat_draw_exact']=True
            # Exercise the installed count hook and its displaced instruction.
            for n,v in [('a0',base+TEMPLATE_BASE+shape*TEMPLATE_STRIDE),('s7',window),('sp',temp_sp),('pc',base+0xe4e68)]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=base+0xe4e70,expect='cpu.stepping');nr=gpr(registers(d))
            if nr['s0']!=count or nr['a0']!=temp_sp:raise ValueError(name+': native draw count/setup differs '+str(dict(actual=nr['s0'],expected=count,a0=nr['a0'],sp=temp_sp,marker=struct.unpack_from('<I',value,0x5c)[0])))
            cases[-1]['native_vertex_count_verified']=True
            # Exercise the native fan hook with the same actual draw count.
            for n,v in [('s0',count),('s7',window),('pc',base+0xe4ebc)]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=base+0xe4ec4,expect='cpu.stepping')
            fr=registers(d)[1]['uintValues'];expected_hub=struct.unpack_from('<2I',value,0xe8)if supported else struct.unpack_from('<2I',value,0x2d0)
            if tuple(fr[12:14])!=expected_hub:raise ValueError(name+': native fan origin differs')
            cases[-1]['native_fan_setup_verified']=True
            # Run the actual native text setup through its final draw-call setup.
            for n,v in [('a0',container),('a1',window),('a2',0xffffffff),('a3',0),('sp',temp_sp),('pc',base+0xece34)]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=base+0xecf24,expect='cpu.stepping')
            tr=gpr(registers(d))
            if tr['a1']!=(math.trunc(text_cx if supported else cx)&0xffffffff):raise ValueError(name+': native text origin differs')
            cases[-1]['native_text_setup_verified']=True
            restore_registers(d,out)
            if supported:
                hub=list(struct.unpack_from('<2f',value,0xe8));world=[[p[0]+cx,p[1]+cy]for p in body[0]]
                fan_check(world,hub,name)
                # E4F68..E4FB8 converts all GE positions by truncation.
                fan_check([[math.trunc(v)for v in p]for p in world],[math.trunc(v)for v in hub],name+' quantized',1e-3)
                cases[-1]['fan_origin']=hub;cases[-1]['fan_fill_matches_contour']=True
                if any(body[n][tip]!=body[0][tip]for n in (1,2)):raise ValueError(name+': split rail endpoint')
                cases[-1]['single_shared_tip']=True
            if name in ('kogoro','serish','top_clamp','field_cougar')or name.startswith(('scene_','reported_','current_','default_names_','gratitude_','airport_','elevator_','construction_','outlined_')):
                cases[-1].update(outline=[list(p)for p in body[0]],fill_banks=[[list(p)for p in bank]for bank in body[1:]],body_text_offset=list(struct.unpack_from('<2f',value,0x30c)))
            if a.render_reported:
                d.call('cpu.breakpoint.remove',address=bp)
                for n,v in [('a0',window),('a1',1),('sp',temp_sp),('ra',regs['pc']),('pc',base+0xe4e0c)]:d.call('cpu.setReg',name=n,value=v)
                d.call('cpu.runUntil',address=regs['pc'],expect='cpu.stepping')
                if gpr(registers(d))['sp']!=temp_sp:raise ValueError('Native full draw stack differs')
                d.call('cpu.breakpoint.add',address=bp)
                cases[-1]['native_full_draw_completed']=True
            restore_registers(d,saved)
        proof=dict(version='0.1.42',loaded_build=m['version'],loaded_iso_sha256=m['iso_sha256'],candidate_sha256=sha(candidate),
            installed_candidate=not a.temporary_code,module_base=base,cases=cases,all_registers_stack_manager_and_temporary_code_restored=True,
            native_instruction_verified=True,native_layer_order=order_checks,natural_story_scene_verified=False,scope='Synthetic associated-window native polygon/ABI and phase layer-reader tests; natural scene rendering remains unverified.')
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
        print(json.dumps(dict(cases=len(cases),all_passed=True,output=str(a.output)),indent=2))
    finally:
        try:
            if bp is not None:d.call('cpu.breakpoint.remove',address=bp)
            if oldmanager is not None:write(d,manager,oldmanager)
            if oldmem is not None:write(d,start,oldmem)
            for addr,raw in reversed(replaced):write(d,addr,raw)
            if saved is not None:
                restore_registers(d,saved)
                display=base+0x29414c if a.render_reported else None
                if display:d.call('cpu.breakpoint.add',address=display)
                try:
                    d.call('cpu.resume',expect='cpu.resume')
                    if display:
                        deadline=time.monotonic()+10
                        while time.monotonic()<deadline:
                            ev=json.loads(d.ws.recv())
                            if ev.get('event')=='cpu.stepping':break
                        r=gpr(registers(d))
                        if r['pc']!=display or r['a1']!=512 or r['a2']!=1:raise ValueError('Unexpected native rendered framebuffer')
                        rgb=bytearray()
                        for v in array.array('H',d.read(r['a0'],512*272*2)):
                            rgb.extend(((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31))
                        target=a.output.with_suffix('.png');Image.frombytes('RGB',(512,272),bytes(rgb)).crop((0,0,480,272)).save(target)
                        target.with_suffix('.capture.en.json').write_text(json.dumps(dict(version='0.1.35',candidate_sha256=sha(candidate),loaded_iso_sha256=m['iso_sha256'],installed_candidate=not a.temporary_code,method='Native bubble draw appended before GU Finish, captured at display import',text_and_portraits_drawn=False,natural_story_scene=False),indent=2)+'\n',encoding='utf8')
                        for frame in range(1,4):
                            d.call('cpu.resume',expect='cpu.resume')
                            deadline=time.monotonic()+10
                            while time.monotonic()<deadline:
                                ev=json.loads(d.ws.recv())
                                if ev.get('event')=='cpu.stepping':break
                            r=gpr(registers(d));rgb=bytearray()
                            if r['pc']!=display:raise ValueError('Unexpected later rendered framebuffer')
                            for v in array.array('H',d.read(r['a0'],512*272*2)):
                                rgb.extend(((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31))
                            Image.frombytes('RGB',(512,272),bytes(rgb)).crop((0,0,480,272)).save(target.with_name(target.stem+f'.frame{frame}.png'))
                finally:
                    if display:
                        d.call('cpu.breakpoint.remove',address=display)
                        if d.call('cpu.status').get('stepping'):d.call('cpu.resume',expect='cpu.resume')
        finally:d.close()
if __name__=='__main__':main()
