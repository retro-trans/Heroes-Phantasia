"""Audit installed dialogue using whole-container widths and settled geometry.

The native measurement owner keeps the maximum over ALL pages. A successful
ray fit is a static prediction, not a natural-playback or animation proof.
Unsupported cases are explicitly fingerprinted, never silently called safe.
"""
import argparse, hashlib, json, math, struct
from functools import lru_cache
from pathlib import Path
from bubble_metrics import load_templates, centered_interval
from dialogue_tokens import tokenize_bytes
from executable_text_patch import Elf
from rebuild_dialogue import parse
from unpack_cpk import inventory, crilayla

ROOT = Path(__file__).resolve().parents[1]
EXCEPTIONS = ROOT / 'work/ui/dialogue/0.1.60/layout_exceptions.en.json'
PREFIXES = ('phase/bin/', 'fld/talk/', 'btl/res/', 'btl/skit/')
# Native selector offsets 37E4/37EE/3800/381A are the saved surname,
# given-name, epithet and other-name buffers (NUL excluded). Native width
# uses 13 units per character when a 01 substitution rejects the VWF pass.
NAME_LIMITS = {b'0': 9, b'1': 17, b'2': 25, b'3': 15}

def token_advance(t, widths, native=False):
    if t.ruby: return 0
    if t.kind == 'latin': return 13 if native else widths[t.code]
    if t.kind == 'control' and t.code == 1: return 13*NAME_LIMITS[t.argument]
    return 0

def sha(data): return hashlib.sha256(data).hexdigest()

@lru_cache(None)
def templates(): return load_templates()

@lru_cache(None)
def geometry():
    from english_bubble_layout_v10 import native_corners, descriptors
    return native_corners(), descriptors()

def widths_from(executable):
    e = Elf(Path(executable).read_bytes())
    return struct.unpack_from('<131I', e.data, e.file_offset(0x2e4000))

def runtime_contract(executable):
    e=Elf(Path(executable).read_bytes())
    spans=[(0x2e4000,524),(0x16fa8f0,1064),(0x16fad20,1732),
           (0x2e43c0,3648),(0x2e5200,1580),(0x2e7460,912),
           (616800,140),(0xee300,4),(0xe4ec4,0x158),(0xe50cc,0x110),
           (0x45e2c8,152*0x1ec),(0x2e6ed0,128),
           (0xeaf00,0x144),(0x2e8910,216),(616940,128)]
    spans.extend((rva,4) for rva in (0xe4ebc,0xe4ed8,0xece3c,0xe4e68,0xe4e6c))
    return [dict(rva=rva,bytes=n,sha256=sha(e.data[e.file_offset(rva):e.file_offset(rva)+n])) for rva,n in spans]

def resources(archive):
    _, rows = inventory(archive)
    with Path(archive).open('rb') as stream:
        for row in rows:
            name = row['path']
            if not name.startswith(PREFIXES) or not name.endswith('.bin'): continue
            stream.seek(row['offset']); raw = stream.read(row['stored_size'])
            if row['compression'] == 'CRILAYLA': raw = crilayla(raw, row['extract_size'])
            yield name, raw

def layer(name, raw, p, index):
    base = p['head'][0]; h = struct.unpack_from('<16I', raw, base); first = 0
    for group, (_, count, _) in enumerate(p['desc']):
        if first <= index < first + count: break
        first += count
    key = p['refs'][index][0]
    _, lo, _, _ = struct.unpack_from('<4I', raw, base+h[12]+group*16)
    row = struct.unpack_from('<21I', raw, base+h[14]+lo+key*84)
    return base+h[15]+row[0], row

def measured_pages(body, widths):
    native = any(t.kind == 'control' and t.code == 1 for t in tokenize_bytes(body,True))
    pages = []
    for page in body.split(b'\x10'):
        tokens = tokenize_bytes(page, True); lines = [0]; minimum = [0]
        for t in tokens:
            if t.kind == 'latin' and not t.ruby:
                v=token_advance(t,widths,native);lines[-1]+=v;minimum[-1]+=v
            elif t.kind == 'control' and t.code == 1: lines[-1] += token_advance(t,widths,native)
            elif t.kind == 'control' and t.code == 0x11: lines.append(0);minimum.append(0)
            elif t.code == 0x0e: break
        pages.append(dict(body_hex=page.hex(), line_advances=lines,minimum_line_advances=minimum,native_name_fallback=native))
    return pages

def parent_halves(pages):
    maximum=max(v for p in pages for v in p['line_advances'])
    if not any(p.get('native_name_fallback') for p in pages): return (maximum/2,)
    minimum=max(v for p in pages for v in p['minimum_line_advances'])
    return tuple(v/2 for v in range(minimum,maximum+1,13))

def fallback_fit(shape, pages, parent_half=None):
    """Check the native white interior with the owner's shared left origin."""
    if parent_half is None:
        return all(fallback_fit(shape,pages,half) for half in parent_halves(pages))
    t = templates()[shape]; half = parent_half
    for p in pages:
        for n, advance in enumerate(p['line_advances']):
            top = t['text_offset'][1]+n*22; bottom = top+16
            samples = {top+.0001, bottom-.0001}
            samples.update(y+e for _, y in t['banks'][0] for e in (-.0001,.0001) if top < y+e < bottom)
            for y in samples:
                interval = centered_interval(t['banks'][0], y)
                # At this parent width no row can exceed twice its halfwidth.
                right=-half+min(advance,2*half)
                if interval is None or -half < interval[0]+1 or right > interval[1]-1: return False
    return True

def clip(lo, hi, p, v, a, b):
    if abs(v) < 1e-5: return (lo, hi) if a <= p <= b else (2,1)
    ka,kb = sorted(((a-p)/v, (b-p)/v)); return max(lo,ka),min(hi,kb)

def ray_fit(shape, position, parent_half, line_count):
    """Mirror v10 edge clipping, including the whole owner's maximum width."""
    t = templates()[shape]; family = (shape-3)%10
    if shape < 3 or family >= 8 or t['count'] != 10: return False
    if not 1 <= line_count <= 7: return False
    corners, desc = geometry(); c = corners[(shape-3)//10]
    native_family=(shape-3)//10
    cuts=desc[608+native_family*16:624+native_family*16]
    pad = desc[848+native_family]/2
    half = parent_half+pad
    if half > 230.5: return False
    top,bottom = struct.unpack_from('<bb',desc,shape*4+1)
    top/=2;bottom/=2
    required = 36+(line_count-1)*22
    bottom=min(bottom,252-position[1])
    top=bottom-required if line_count>=3 else min(top,bottom-required)
    top=max(top,36-position[1]);bottom=max(bottom,top+required)
    height=bottom-top
    topcut,botcut=[v/2 for v in desc[864+native_family*2:866+native_family*2]]
    # The .60 pre-fit helper prevents the bevels from crossing, including
    # the 1.5px white inset and integer raster rounding. Both routes use it.
    height=max(height,max(cuts[3]+cuts[5],cuts[13]+cuts[11])/2+4)
    tip = t['outline'][family+1]
    vx,vy = [(t['outline'][family][a]+t['outline'][family+2][a])/2-tip[a] for a in (0,1)]
    px,py = position[0]+tip[0],position[1]+tip[1]
    for reach,retry in ((12,1),(3,.25)):
        if abs(vy) < 1e-5: continue
        lo,hi = clip(max(retry,reach/abs(vy)),1024,py,vy,36 if vy>0 else 36+height,252-height if vy>0 else 252)
        li,ri = (14,0) if vy>0 else (8,6)
        lo,hi = clip(lo,hi,px,vx,19+cuts[li]/2,461-cuts[ri]/2)
        if lo<=hi: return True
    height = max(height,topcut+botcut)
    for k in (1,.5):
        lo,hi = clip(k,1024,px,vx,9.5 if vx>0 else 9.5+2*half,470.5-2*half if vx>0 else 470.5)
        lo,hi = clip(lo,hi,py,vy,37.5+topcut,250.5-botcut)
        if lo<=hi: return True
    return False

def inspect(name, raw, p, index, widths):
    text = p['spans'][p['refs'][index][1]][0]
    if b'\x0e' not in text: return None
    body = text.split(b'\x0e',1)[1]
    try: tokens = tokenize_bytes(body, True)
    except ValueError: return None
    if not any(t.kind == 'latin' and not t.ruby for t in tokens): return None
    item = dict(resource=name, reference_index=index, text_sha256=sha(text))
    try:
        ch,l = layer(name,raw,p,index)
        shapes = [struct.unpack_from('<fHH',raw,ch+l[10]+8*k) for k in range(l[9])]
        positions = [struct.unpack_from('<4fI',raw,ch+l[14]+20*k) for k in range(l[13])]
        item['geometry_sha256'] = sha(struct.pack('<21I',*l)+raw[ch+l[10]:ch+l[10]+8*l[9]]+raw[ch+l[14]:ch+l[14]+20*l[13]])
        if l[5] != 3 or not shapes or not positions: raise ValueError('Non-bubble or missing geometry tracks')
        item.update(shape=shapes[-1][1],position=list(positions[-1][1:3]),shape_keys=shapes,position_keys=positions)
        if not 0<=item['shape']<len(templates()): raise ValueError('Unknown template')
        if name in ('phase/bin/p101010.bin','phase/bin/p101011.bin') and index==6:
            # The installed leaf overrides this ONE reviewed lip endpoint at
            # its exact final pose. Changing its text would disable the guard.
            # Earlier animation poses are not covered by that landmark proof.
            if body!=b'Who will accompany you?\x12\x0e' or item['shape']!=8 or item['position']!=[369.,99.]:
                raise ValueError('Reviewed Serish line changed; lip landmark guard requires renewed review')
            raise ValueError('Reviewed Serish lip override; intermediate animation poses unverified')
        if any(t.kind not in ('latin','control','ruby_open','ruby_close') or t.kind=='control' and t.code not in (1,0x10,0x11,0x12,0x0e,5,0x16,0x17,0x1a) for t in tokens):
            raise ValueError('Dynamic names, native glyphs or unsupported controls')
        if any(t.kind=='control' and t.code==1 and t.argument not in NAME_LIMITS for t in tokens): raise ValueError('Unreviewed name selector')
        # The .51 resident scanner accepts span digits 1..9 and a nonempty
        # printable ASCII reading, retaining a strict 1024-byte probe bound.
        for n,t in enumerate(tokens):
            if t.kind!='ruby_open': continue
            closing=next(v.offset for v in tokens[n+1:] if v.kind=='ruby_close')
            reading=body[t.offset+2:closing]
            if t.argument not in tuple(bytes([v]) for v in range(49,58)) or not reading or any(v<32 or v>126 for v in reading):
                raise ValueError('Ruby reading not accepted by native geometry scanner')
        if any(t.code==0x1a and t.argument!=b'5' for t in tokens): raise ValueError('Nondefault alignment control')
        if any(v[1]!=item['shape'] for v in shapes): raise ValueError('Changing shape track')
        settled = [v for v in positions if v[1:3] != (0.,0.)]
        # These are authored position keys, NOT the runtime uniform-scale
        # channel. The final uint32 is not evidence of unit scale. Model the
        # settled XY only; runtime scale/rotation remain explicit assumptions.
        if not settled or any(not all(math.isfinite(x) for x in v[:4]) for v in settled): raise ValueError('Missing or nonfinite settled placement')
        pages = measured_pages(body,widths); item['pages']=pages
        parent_half = max(v for page in pages for v in page['line_advances'])/2
        item['parent_maximum_width']=parent_half*2
        minimum=max(v for page in pages for v in page['minimum_line_advances'])/2
        item['parent_minimum_width']=minimum*2
        names=any(page['native_name_fallback'] for page in pages)
        item['measurement_policy']='native_13px_with_bounded_names' if names else 'installed_vwf'
        halves=parent_halves(pages)
        if sum(len(v['line_advances']) for v in pages)>32: raise ValueError('Native owner exceeds 32-row geometry bound')
        if any(len(bytes.fromhex(v['body_hex']))>1024 for v in pages): raise ValueError('Native page scanner exceeds 1024-byte bound')
        native = fallback_fit(item['shape'],pages)
        failures=[]
        for pi,page in enumerate(pages):
            for key in settled:
                failed=[half for half in halves if not ray_fit(item['shape'],key[1:3],half,len(page['line_advances'])) and not fallback_fit(item['shape'],pages,half)]
                if failed: failures.append(dict(page=pi,position=list(key[1:3]),failed_parent_widths=[half*2 for half in failed]))
        item.update(status='overflow' if failures else 'fit',fallback_white_interior_fit=native,failures=failures)
    except (ValueError,IndexError,struct.error) as ex:
        item.update(status='unverified',reason=str(ex))
    return item

def audit(archive, executable, overlays=None):
    widths=widths_from(executable); records=[]; totals=0; count=0
    for name, raw in resources(archive):
        if overlays and name in overlays: raw=overlays[name]
        try: p=parse(name,raw)
        except ValueError: continue
        count+=1; totals+=len(p['refs'])
        for n in range(len(p['refs'])):
            item=inspect(name,raw,p,n,widths)
            if item: records.append(item)
    return dict(schema_version=1,resources_examined=count,indexed_references=totals,english_body_references=len(records),
        counts={k:sum(r['status']==k for r in records) for k in ('fit','overflow','unverified')},records=records,
        scope='All indexed phase, field, battle result and battle skit containers; shared whole-block width, every settled XY key, authored template or v10 ray clipping under zero rotation and unit runtime scale. Animated intermediate frames, transforms and natural playback are unverified.',full_game_visually_verified=False)

def exception_key(r): return (r['resource'],r['reference_index'],r['text_sha256'],r.get('geometry_sha256'),r['reason'])

def enforce(archive, executable, exception_path=EXCEPTIONS):
    exceptions=json.loads(Path(exception_path).read_text(encoding='utf8'))
    if exceptions.get('name_selector_limits')!={k.decode():v for k,v in NAME_LIMITS.items()}:
        raise ValueError('Dialogue layout guard: reviewed name measurement policy differs')
    if exceptions['runtime_contract']!=runtime_contract(executable):
        raise ValueError('Dialogue layout guard: font widths or native geometry changed; update and verify the model before building')
    proof=audit(archive,executable)
    allowed={exception_key(r) for r in exceptions['records']}
    risk_key=lambda r:tuple(r.get(k)for k in ('resource','reference_index','text_sha256','geometry_sha256','parent_maximum_width','measurement_policy'))
    retained={risk_key(r)for r in exceptions.get('retained_maximum_name_risks',[])}
    failures=[r for r in proof['records'] if r['status']=='overflow' and risk_key(r)not in retained or r['status']=='unverified' and exception_key(r) not in allowed]
    if failures:
        raise ValueError('Dialogue layout guard rejected '+str(len(failures))+' references: '+json.dumps([{k:r.get(k) for k in ('resource','reference_index','status','parent_maximum_width','reason','failures')} for r in failures[:8]]))
    return {k:v for k,v in proof.items() if k!='records'} | dict(guard_passed=True,exception_fingerprints_sha256=sha(Path(exception_path).read_bytes()),unchanged_unverified_references=proof['counts']['unverified'],retained_maximum_name_risks=proof['counts']['overflow'],all_layouts_verified=False)

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--archive',type=Path,required=True);a.add_argument('--executable',type=Path,required=True);a.add_argument('--output',type=Path);a.add_argument('--enforce',action='store_true');opts=a.parse_args()
    proof=enforce(opts.archive,opts.executable) if opts.enforce else audit(opts.archive,opts.executable)
    if opts.output: opts.output.parent.mkdir(parents=True,exist_ok=True);opts.output.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in proof.items() if k!='records'},indent=2))

if __name__=='__main__': main()
