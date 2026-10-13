"""Reflow whole-block overflow risks, preserving authored scene/tail tracks."""
import argparse, copy, json, math, re
from pathlib import Path
import dialogue_layout_guard as guard
from bubble_metrics import usable_half_width
from dialogue_tokens import tokenize_bytes
from field_ui_patch import notation
from rebuild_dialogue import parse, rebuild
from strip_jp import export

BASE=Path('work/output/0.1.53-title-credit-vwf-4x-candidate')
OUT=Path('work/output/0.1.55-dialogue-guard-assets')
UI=Path('work/ui/dialogue/0.1.55')
CPK_SHA='ac1328545a2969bb54e3529c6ab27a33c07bb1ba1feae0e30608013c83778d12'
EXE_SHA='20e295dd2932aa74d42fc2ae2d457b0771408b82a8267c774a79fae48e89ac0b'

def words(plain,widths):
    result=[];word=[]
    for t in tokenize_bytes(plain.replace(b'\x11',b' '),True):
        if t.kind=='latin' and t.code==32 and not t.ruby:
            if word: result.append(word);word=[]
        else: word.append(t)
    if word: result.append(word)
    return result

def advance(ts,widths): return sum(widths[t.code] for t in ts if t.kind=='latin' and not t.ruby)

def wrap_page(page,cap,maxlines,widths,split_words=False):
    if page.count(b'\x12')==1:
        plain,suffix=page.split(b'\x12');pause=b'\x12'
    elif page.count(b'\x12')==0 and b'\x0e' in page:
        plain,tail=page.split(b'\x0e',1);suffix=b'\x0e'+tail;pause=b''
    else: raise ValueError('Unexpected authored page terminator')
    # Native 0E ends the displayed body. Preserve authored trailing bytes
    # (some resources have padding controls/digits) without interpreting them.
    if suffix and not suffix.startswith(b'\x0e'): raise ValueError('Unexpected page suffix')
    ws=words(plain,widths);lines=[[]];used=0;broken=0
    for word in ws:
        width=advance(word,widths)
        if width>cap:
            if not split_words or any(t.kind.startswith('ruby') for t in word): raise ValueError('Long word or ruby needs explicit layout review')
            if lines[-1]: lines.append([]);used=0
            for t in word:
                v=advance([t],widths)
                if used+v>cap and lines[-1]: lines.append([]);used=0;broken+=1
                lines[-1].append(t.data);used+=v
            continue
        sep=widths[32] if lines[-1] else 0
        if used+sep+width>cap and lines[-1]: lines.append([]);used=0;sep=0
        if sep: lines[-1].append(b' ');used+=sep
        lines[-1].extend(t.data for t in word);used+=width
    count=math.ceil(len(lines)/maxlines);size=math.ceil(len(lines)/count)
    chunks=[lines[n:n+size] for n in range(0,len(lines),size)]
    return [b'\x11'.join(b''.join(line) for line in chunk)+(pause if n==len(chunks)-1 else b'\x12')+(suffix if n==len(chunks)-1 else b'') for n,chunk in enumerate(chunks)],len(chunks)-1,broken

def accepts(r, pages):
    if sum(len(p['line_advances']) for p in pages)>32: return False
    if any(len(bytes.fromhex(p['body_hex']))>1024 for p in pages): return False
    parent=max(v for p in pages for v in p['line_advances'])/2
    # Prefer the native fallback for styles that cannot use the fitted contour.
    if guard.fallback_fit(r['shape'],pages): return True
    return all(guard.ray_fit(r['shape'],key[1:3],parent,len(p['line_advances'])) for p in pages for key in r['position_keys'] if key[1:3]!=(0.,0.) and key[1:3]!=[0.,0.])

def reflow(text,r,widths):
    speaker,body=text.split(b'\x0e',1);original=body.split(b'\x10')
    t=guard.templates()[r['shape']];standard=t['count']==10 and r['shape']>=3 and (r['shape']-3)%10<8
    if standard:
        # Breakpoints at contiguous word widths cover each greedy-wrap result.
        caps=set()
        for page in original:
            widths_ws=[advance(w,widths) for w in words(page.split(b'\x12',1)[0],widths)]
            for n in range(len(widths_ws)):
                v=0
                for m in range(n,len(widths_ws)):
                    v+=widths_ws[m]+(widths[32] if m>n else 0)
                    if v>=r['parent_maximum_width']: break
                    caps.add(v)
        trials=[(c,n,False) for c in sorted(caps,reverse=True) for n in range(7,0,-1)]
    else: trials=[]
    # Every style gets a conservative immutable-white-interior escape route.
    trials.extend((int(2*usable_half_width(t,n)-3),n,True) for n in range(3,0,-1) if usable_half_width(t,n)>0)
    for cap,maxlines,split in trials:
        if cap<13: continue
        try:
            packed=[wrap_page(p,cap,maxlines,widths,split) for p in original]
        except ValueError: continue
        newbody=b'\x10'.join(page for pages,_,_ in packed for page in pages)
        pages=guard.measured_pages(newbody,widths)
        if not accepts(r,pages): continue
        new=speaker+b'\x0e'+newbody
        strip=lambda s:bytes(c for c in s if c not in (32,0x10,0x11,0x12))
        if strip(text)!=strip(new): raise ValueError('Glyphs or nonlayout controls changed')
        return new,dict(cap=cap,max_lines=maxlines,extra_pages=sum(x[1] for x in packed),long_word_line_breaks=sum(x[2] for x in packed),page_line_advances=[p['line_advances'] for p in pages],fallback_white_interior_fit=guard.fallback_fit(r['shape'],pages))
    raise ValueError('No word-preserving layout fits within native bounds')

def build():
    from build_local import sha as file_sha
    if file_sha(BASE/'HP.CPK')!=CPK_SHA or file_sha(BASE/'EBOOT.BIN')!=EXE_SHA: raise ValueError('Frozen .53 input differs')
    before=guard.audit(BASE/'HP.CPK',BASE/'EBOOT.BIN');widths=guard.widths_from(BASE/'EBOOT.BIN')
    selected={}
    for r in before['records']:
        if r['status']=='overflow': selected.setdefault(r['resource'],[]).append(r)
    assets={};records=[];blocked=[];queue=[]
    for name,raw in guard.resources(BASE/'HP.CPK'):
        if name not in selected: continue
        p=parse(name,raw);replacements={};by_offset={}
        for r in selected[name]:
            n=r['reference_index'];off=p['refs'][n][1];text=p['spans'][off][0]
            try: new,details=reflow(text,r,widths)
            except ValueError as ex: blocked.append(dict(resource=name,reference_index=n,reason=str(ex)));continue
            if off in by_offset and new!=by_offset[off]: raise ValueError('Shared dialogue has incompatible geometry')
            by_offset[off]=new
            records.append(dict(resource=name,reference_index=n,shape=r['shape'],old_parent_width=r['parent_maximum_width'],old_english=notation(text),new_english=notation(new),**details,words_and_control_order_exact=True,authored_tail_and_tracks_exact=True,natural_playback_verified=False))
            queue.append(dict(id=f'guard_055_{Path(name).stem}_{n}',file=name,category='dialogue_layout',target=notation(new),status='translated',notes='Whole-block width check; original scene/tail tracks preserved.'))
        # Closure: shared strings must fit every associated layer, including
        # layers that passed before. Do not drop existing shared owners.
        for n,(_,off) in enumerate(p['refs']):
            if off in by_offset: replacements[n]=by_offset[off]
        if not replacements: continue
        changed,np=rebuild(name,raw,replacements)
        if raw[p['head'][0]:p['start']]!=changed[np['head'][0]:np['start']] or raw[p['end']:]!=changed[np['end']:]: raise ValueError('Native tracks or suffix changed')
        for n,(_,off) in enumerate(p['refs']):
            if n not in replacements and p['spans'][off][0]!=np['spans'][np['refs'][n][1]][0]: raise ValueError('Unselected dialogue changed')
        assets[name]=changed
    after=guard.audit(BASE/'HP.CPK',BASE/'EBOOT.BIN',assets)
    return assets,records,before,after,blocked,dict(schema_version=1,language='en',rows=queue)

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--write',action='store_true');opts=a.parse_args()
    assets,records,before,after,blocked,queue=build()
    print(json.dumps(dict(version='0.1.55',before=before['counts'],after=after['counts'],reflows=len(records),resources=len(assets),extra_pages=sum(r['extra_pages'] for r in records),blocked=blocked),indent=2))
    if not opts.write: return
    if blocked or after['counts']['overflow']: raise ValueError('Unresolved layout risks block preparation')
    if OUT.exists(): raise ValueError('Fresh preparation directory required')
    OUT.mkdir(parents=True);UI.mkdir(parents=True,exist_ok=True)
    for name,raw in assets.items():
        path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    exe=(BASE/'EBOOT.BIN').read_bytes();(OUT/'EBOOT.BIN').write_bytes(exe)
    report=copy.deepcopy(json.loads((BASE/'manifest.en.json').read_text(encoding='utf8'))['setup_patch'])
    proof=dict(version='0.1.55',input_version='0.1.53',archive_input_sha256=CPK_SHA,executable_exact=True,loaded_growth_bytes=0,records=records,selected_assets=[dict(resource=n,sha256=guard.sha(b),bytes=len(b)) for n,b in assets.items()],before_counts=before['counts'],after_counts=after['counts'],full_game_visually_verified=False)
    report.update(version='0.1.55',input_version='0.1.53',input_sha256=EXE_SHA,output_elf_sha256=EXE_SHA,output_sha256=EXE_SHA,runtime_verified=False);report['dialogue_guard_055']=proof
    (OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    (UI/'preparation.en.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    (UI/'corpus_audit.en.json').write_text(json.dumps({k:v for k,v in after.items() if k!='records'},indent=2)+'\n',encoding='utf8')
    exceptions=[{k:r.get(k) for k in ('resource','reference_index','text_sha256','geometry_sha256','reason')} for r in after['records'] if r['status']=='unverified']
    (UI/'layout_exceptions.en.json').write_text(json.dumps(dict(version='0.1.55',scope='Unchanged fingerprinted inputs only. These cases are not declared safe; changed or new inputs require review.',runtime_contract=guard.runtime_contract(BASE/'EBOOT.BIN'),records=exceptions),indent=2)+'\n',encoding='utf8')
    dest=Path('work/translation/en/dialogue_guard_055.json');dest.write_text(json.dumps(queue,indent=2)+'\n',encoding='utf8');dest.with_suffix('.en.json').write_text(json.dumps(export(queue),indent=2)+'\n',encoding='utf8')

if __name__=='__main__': main()
