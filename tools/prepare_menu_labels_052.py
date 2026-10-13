"""Fit and install shared Brave/Equip labels and their typed name lists.

No loaded memory grows. Text uses selected source strings and retired strings
whose original relocation owners all point elsewhere. Bitmap UVs stay intact.
"""
import argparse,copy,json,struct
from pathlib import Path
from PIL import Image
from executable_text_patch import Elf,ORIGINAL,ORIGINAL_SHA,reference_index,encoded_text
from native_menu_install_plan import cstring
from prepare_bubble_scenes_036 import read,sha
from prepare_relocation_019 import coverage,section_load
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from field_ui_patch import notation
from inspect_font_assets import texture,unswizzle
from title_stamp import swizzle
from prepare_battle_labels_045 import lettering
from strip_jp import export

BASE=Path('work/output/0.1.51-title-credit-vwf-4x-candidate')
OUT=Path('work/output/0.1.52-menu-label-assets')
UI=Path('work/ui/menu/0.1.52')
INPUT_SHA='cee7f5479f2e4b69ab554240dbc9736a7b84d090f21a08f88d91aa82ff218aa7'
CPK_SHA='dea945b90d3bc20d010ad27037dc9e23db58e2c55aff8d206d1f0f11ef5741bd'
LABELS={18:'Switch Item',26:'Front',27:'Back',92:'Unequip',143:'None',148:'Item',162:'Accessories'}
HELP={21:'Set normal moves.{0E}',22:'Set special moves.{0E}',31:'Unequip.{0E}'}
ASSETS={'resident/ALLResidentNML.bin':(0x4ddf0,'650af937d12e808c4d52fbfd32a182c8c0e79a050a3ba2c1e7586c866831c892'),
        'resident/ALLResidentLIM.bin':(0x71bd0,'dd115f955b1086eab77fab9e28d8aef38bae314f765f793649c6f81b0a023f69')}
# Slots are the shared native atlas cells; compact stat abbreviations retain
# the game's meanings, with a complete English legend in the review document.
CELLS=[(str(n),[n*32,64,32,16],text,13)for n,text in enumerate(['ATK','DEF','Charm','Link','Power','ACC','Hits','Crit'])]
CELLS += [('observe',[0,80,32,16],'OBS',13),('dodge',[32,80,32,16],'Dodge',12),
 ('normal',[56,144,32,16],'Normal',12),('special',[88,144,32,16],'Special',12),('accessory',[120,144,48,16],'Accessory',12),
 ('menu',[0,160,40,16],'Menu',13),('radar_atk',[40,176,24,16],'ATK',12),('radar_def',[64,176,24,16],'DEF',12),
 ('radar_charm',[40,192,24,16],'CHR',12),('radar_link',[64,192,24,16],'Link',12),
 ('none',[168,184,32,16],'None',12),('hp_mod',[104,256,40,16],'HP MOD',12),('owned',[168,256,40,16],'Owned',12),
 ('overcharge',[0,272,72,16],'Overcharge',12),('pp_cost',[104,272,40,16],'PP Cost',12),
 ('assist',[144,272,64,16],'Assist Effect',12),('max_chain',[0,288,72,16],'Max Chain',12),
 ('users',[72,288,48,16],'Users',13),('foe',[120,288,32,16],'Foe',13),('ally',[152,288,32,16],'Ally',13),
 ('field_effect',[184,288,48,16],'Field FX',12),('front',[232,288,24,16],'Front',11),('back',[232,304,24,16],'Back',12)]

def bitmap(name,data):
    offset,expected=ASSETS[name]
    if sha(data)!=expected:raise ValueError('Frozen atlas changed: '+name)
    t=texture(data,offset);w,h=t['width'],t['height'];assert (w,h)==(256,336)
    palette=[tuple(t['palette'][n:n+4])for n in range(0,1024,4)]
    raw=unswizzle(t['pixels'],w,h);pixels=bytearray(raw);allowed=set();entries=[]
    before=Image.frombytes('RGBA',(w,h),b''.join(bytes(palette[v])for v in raw))
    for key,rect,text,size in CELLS:
        x,y,cw,ch=rect;canvas,size,boxes=lettering([text],cw,ch,size,shadow=True)
        # Preserve legibility against both light portraits and dark panels.
        # An opaque one-pixel outline surrounds every white ink pixel.
        ink=[(xx,yy)for yy in range(ch)for xx in range(cw)if canvas.getpixel((xx,yy))==(255,255,255,255)]
        for xx,yy in ink:
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    if 0<=xx+dx<cw and 0<=yy+dy<ch and canvas.getpixel((xx+dx,yy+dy))[3]==0:canvas.putpixel((xx+dx,yy+dy),(0,0,0,255))
        if key.startswith('radar_'):
            canvas=Image.frombytes('RGBA',canvas.size,bytes(v for c in canvas.get_flattened_data()for v in ((175,175,175,c[3])if c[:3]==(255,255,255)else c)))
        colors={c:min(range(256),key=lambda k:sum((a-b)**2 for a,b in zip(c,palette[k])))for c in set(canvas.get_flattened_data())}
        for yy in range(ch):
            for xx in range(cw):
                at=(y+yy)*w+x+xx
                if at in allowed:raise ValueError('Selected atlas cells overlap')
                allowed.add(at);pixels[at]=colors[canvas.getpixel((xx,yy))]
        entries.append(dict(id=key,target=text,rectangle=rect,font_native_pixels=size,text_boxes=boxes))
    if any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(raw,pixels))):raise ValueError('Other atlas pixels changed')
    result=bytearray(data);p=t['pixel_offset'];result[p:p+len(pixels)]=swizzle(pixels,w,h)
    if result[:p]!=data[:p]or result[p+len(pixels):]!=data[p+len(pixels):]:raise ValueError('Palette, group UV or other assets changed')
    if unswizzle(texture(result,offset)['pixels'],w,h)!=pixels:raise ValueError('Atlas roundtrip differs')
    after=Image.frombytes('RGBA',(w,h),b''.join(bytes(palette[v])for v in pixels))
    return bytes(result),dict(resource=name,input_sha256=sha(data),output_sha256=sha(result),texture_offset=offset,cells=entries,palette_and_all_native_group_bytes_exact=True,outside_cells_exact=True,natural_display_verified=False),before,after

def prepare():
    incoming=(BASE/'EBOOT.BIN').read_bytes();before=json.loads((BASE/'manifest.en.json').read_bytes())['setup_patch']
    original=ORIGINAL.read_bytes()
    if sha(incoming)!=INPUT_SHA or sha(original)!=ORIGINAL_SHA:raise ValueError('Frozen executable changed')
    e,o=Elf(incoming),Elf(original);refs,_=reference_index(o)
    font=authoritative_font_metadata(incoming,before);png=validate_native_png_metadata(incoming,before)
    rows=[x for x in json.loads(Path('work/translation/en/menu_names_052.json').read_bytes())['rows']if x.get('table')in(4,5)];rows=copy.deepcopy(rows)
    if len(rows)!=130 or len({(x['table'],x['index'])for x in rows})!=130:raise ValueError('Complete 99-move/31-location queue required')
    for table,start,labels in [(0,0x94760,LABELS),(1,0x95450,HELP)]:
        for index,target in labels.items():
            slot=start+4*index;src=o.word(slot)
            rows.append(dict(id=f'menu_052_{table}_{index}',table=table,index=index,slot=slot,rva=src,source=notation(cstring(o,src)[:-1]),target=target,canonical_target=target,category='menu_label',status='translated'))
    selected={x['slot'] for x in rows if e.word(x['slot'])==x['rva']}
    entries=[];ranges=[]
    def owners(start,n):return [r for r in refs if start<=r['address']<start+n]
    def reclaimable(start,raw,selected_slots):
        if cstring(e,start)!=raw:return False
        own=owners(start,len(raw))
        return bool(own)and all(r['address']==start and r['kind']=='R_MIPS_32'and all(s in selected_slots or e.word(s)!=start for s in r['sites'])for r in own)
    for row in rows:
        slot,src=row['slot'],row['rva'];old=cstring(o,src)
        starts={0:0x94760,1:0x95450,4:0x962e0,5:0x96ac0}
        if slot!=starts[row['table']]+4*row['index']or o.word(slot)!=src or notation(old[:-1])!=row['source']:raise ValueError('Original source/slot identity differs')
        if e.word(slot)!=src:
            if row['table']==5 and row['index']==0 and notation(cstring(e,e.word(slot))[:-1])==row['target']:continue
            raise ValueError('Selected source already changed: '+str(row))
        if not reclaimable(src,old,selected):raise ValueError('Source has an unreviewed owner')
        match=[r for r in refs if r['address']==src and r['kind']=='R_MIPS_32'and slot in r['sites']]
        if len(match)!=1 or e.relocs[match[0]['relocation_ordinals'][0]]!=(slot,2):raise ValueError('Typed owner changed')
        ranges.append((src,src+len(old)))
        entries.append(dict(row,source_sha256=sha(old),relocation_ordinal=match[0]['relocation_ordinals'][0]))
    retired=[]
    for table,start,count in [(0,0x94760,234),(1,0x95450,75)]:
        for index in range(count):
            src=o.word(start+4*index);old=cstring(o,src)
            if e.word(start+4*index)==src or not reclaimable(src,old,set()):continue
            ranges.append((src,src+len(old)));retired.append(dict(table=table,index=index,rva=src,bytes=len(old),sha256=sha(old)))
    merged=[]
    for a,b in sorted(set(ranges)):
        if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
        else:merged.append([a,b])
    # Every current R32 pointer into a pool must be a selected pointer. The
    # original reference inventory additionally excludes HI/LO/interior owners.
    for site,flags in e.relocs:
        if flags&15==2 and not flags>>8&255 and site not in selected:
            ptr=e.word(site)
            if any(a<=ptr<b for a,b in merged):raise ValueError('Active pointer enters reclaimed pool')
    result=bytearray(incoming);allowed=set();mask=set();dedup={};free=copy.deepcopy(merged)
    def install(rva,raw):
        at=e.file_offset(rva,len(raw));result[at:at+len(raw)]=raw;allowed.update(range(at,at+len(raw)));mask.update(range(rva,rva+len(raw)))
    for a,b in merged:install(a,bytes(b-a))
    floats=struct.unpack_from('<131f',incoming,e.file_offset(before['float_width_lut_rva']))
    for row in sorted(entries,key=lambda r:len(r['target']),reverse=True):
        raw=encoded_text(row['target'].replace('è','\x80'),'latin1')+b'\0'
        if raw not in dedup:
            candidates=[(b-a,n)for n,(a,b)in enumerate(free)if b-a>=len(raw)]
            if not candidates:raise ValueError('Reviewed source pool cannot fit complete targets')
            _,n=min(candidates);rva=free[n][0];free[n][0]+=len(raw);install(rva,raw);dedup[raw]=rva
        row['target_rva']=dedup[raw];install(row['slot'],struct.pack('<I',dedup[raw]))
        row['line_widths_px']=[sum(floats[c]for c in line if 32<=c<=128)for line in raw[:-1].split(b'\x11')]
        if row['table']in(4,5)and max(row['line_widths_px'])>(200 if row['table']==4 else 208):raise ValueError('Name exceeds reviewed menu width: '+row['target'])
    aliases=[]
    for item in before['scoped_executable_ui']['strings']:
        if not item['target'].endswith(' Bond Stone'):continue
        full=item['target'];target=full.removesuffix(' Stone');rva=item['payload_rva'];n=item['payload_bytes']
        old=encoded_text(full,item['encoding'])+b'\0'
        if len(old)!=n or incoming[e.file_offset(rva,n):][:n]!=old:raise ValueError('Frozen accessory name allocation differs')
        raw=encoded_text(target,item['encoding'])+b'\0';install(rva,raw+bytes(n-len(raw)))
        width=sum(floats[ord(c)]for c in target)
        if width>103:raise ValueError('Accessory display alias still clips')
        alias=dict(id='menu_052_alias_'+item['id'],category='accessory_display_name',source=full,target=target,canonical_target=full,target_rva=rva,allocated_bytes=n,native_width_px=width,available_width_px=103,status='translated',notes='Omit the item-type word Stone in the compact UI name. Full canonical name is retained in the original translation/glossary; item identity, icon, effects and storage IDs are unchanged.')
        aliases.append(alias);rows.append(alias)
    out=bytes(result);oe=Elf(out);coverage(out)
    if oe.ph!=e.ph or oe.relocs!=e.relocs or any(a!=b and n not in allowed for n,(a,b)in enumerate(zip(incoming,out))):raise ValueError('Unselected ELF bytes changed')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base);b,_,skipped,_=section_load(out,base)
        if skipped or a[1:]!=b[1:] or any(v!=w and n not in mask for n,(v,w)in enumerate(zip(a[0],b[0]))):raise ValueError('Unselected loaded memory changed')
        for row in entries:
            if struct.unpack_from('<I',b[0],row['slot'])[0]!=base+row['target_rva']:raise ValueError('Loaded typed pointer differs')
        models.append(dict(base=base,selected_pointers=len(entries),outside_mask_exact=True))
    report=copy.deepcopy(before);report.update(version='0.1.52',input_version='0.1.51',input_sha256=INPUT_SHA,output_elf_sha256=sha(out),output_sha256=sha(out),runtime_verified=False)
    for alias in aliases:
        item=next(x for x in report['scoped_executable_ui']['strings']if 'menu_052_alias_'+x['id']==alias['id'])
        item.update(canonical_target=item['target'],target=alias['target'],payload_sha256=sha(out[e.file_offset(item['payload_rva'],item['payload_bytes']):][:item['payload_bytes']]),display_alias_052=True)
    report['menu_labels_052']=dict(entries=entries,accessory_aliases=aliases,reclaimed_retired_strings=retired,pool_ranges=merged,remaining_pool_ranges=free,loader_models=models,loaded_growth_bytes=0,new_relocations=0,natural_display_verified=False)
    if authoritative_font_metadata(out,report)!=font or validate_native_png_metadata(out,report)!=png:raise ValueError('Font or PNG contract changed')
    resources=read(BASE/'HP.CPK',list(ASSETS));assets={};proofs=[];previews=[]
    for name,data in resources.items():
        new,proof,oldim,newim=bitmap(name,data);assets[name]=new;proofs.append(proof);previews.append((Path(name).stem,oldim,newim))
    report['menu_labels_052']['bitmap_assets']=proofs
    return out,report,assets,dict(schema_version=1,language='en',rows=rows),previews

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--expected-sha256');a=p.parse_args()
    data,report,assets,queue,previews=prepare();scope=report['menu_labels_052']
    print(json.dumps(dict(version='0.1.52',sha256=sha(data),typed_entries=len(scope['entries']),bitmap_labels=len(CELLS),loader_models=scope['loader_models'],remaining_pool_bytes=sum(b-a for a,b in scope['remaining_pool_ranges'])),indent=2))
    if not a.write:return
    if a.expected_sha256!=sha(data)or OUT.exists():raise ValueError('Reviewed hash and fresh asset destination required')
    OUT.mkdir(parents=True);UI.mkdir(parents=True,exist_ok=True)
    (OUT/'EBOOT.BIN').write_bytes(data);(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    for name,raw in assets.items():
        dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        if dest.read_bytes()!=raw:raise ValueError('Asset readback differs')
    for name,before,after in previews:before.save(UI/(name+'_before.png'));after.save(UI/(name+'_after.png'))
    qp=Path('work/translation/en/menu_names_052.json');qp.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8');qp.with_name('menu_names_052.en.json').write_text(json.dumps(export(queue),indent=2)+'\n',encoding='utf8')
    (UI/'preparation.en.json').write_text(json.dumps(scope,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
