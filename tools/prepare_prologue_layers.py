"""Pure staggered prologue layer review; only explicit review PNG/JSON writes."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from prepare_prologue_overlays import QUEUE,SOURCE,MOVIE,SHA,sha,raster

def prepare():
    assert sha(MOVIE.read_bytes())==SHA
    queue=QUEUE.read_bytes();sources=json.loads(SOURCE.read_bytes())['rows']
    targets={x['id']:x['target'] for x in json.loads(queue)['rows']}
    definitions=targets[sources[12]['id']].split('\n')
    organizations=targets[sources[7]['id']].split('\n')
    assert len(definitions)==len(organizations)==4
    assert definitions[0]==targets[sources[11]['id']]
    layers=[]
    for i,(text,y) in enumerate(zip(organizations,(65,111,157,203))):
        layers.append(dict(key='organization_'+str(i),row_id=sources[7]['id'],target=text,
            source_box=[140,y-12,345,y+12],box=[55,y-16,425,y+16],ref=2532,search=[2100,3000]))
    for i,(text,src,dst) in enumerate(zip(definitions,
        ([177,43,307,65],[65,92,408,115],[100,138,382,161],[64,189,407,236]),
        ([112,35,368,71],[38,82,442,126],[30,132,450,166],[35,173,445,248]))):
        layers.append(dict(key='sir_'+str(i),row_id=sources[12]['id'],target=text,
            source_box=src,box=dst,ref=4376,search=[3700,4500],
            shared_row_ids=[sources[11]['id'],sources[12]['id']] if i==0 else [sources[12]['id']]))
    for i,src,dst in ((15,[116,75,366,144],[60,68,420,149]),(16,[150,174,335,199],[80,166,400,208])):
        layers.append(dict(key='ending_'+str(i),row_id=sources[i]['id'],target=targets[sources[i]['id']],
            source_box=src,box=dst,ref=6249,search=[5800,6424]))
    refs=sorted(set(x['ref'] for x in layers))
    cmd=['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select='+ '+'.join('eq(n\\,%d)'%n for n in refs),'-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1']
    p=subprocess.run(cmd,capture_output=True);assert not p.returncode and not p.stderr
    images={n:Image.frombytes('RGB',(480,272),p.stdout[i*391680:(i+1)*391680]) for i,n in enumerate(refs)}
    fingerprints=[]
    for entry in layers:
        g=np.asarray(images[entry['ref']].convert('L'));x0,y0,x1,y1=entry['source_box']
        ys,xs=np.mgrid[y0:y1,x0:x1];ys=ys.flatten();xs=xs.flatten()
        hp=g[ys,xs].astype(float)-(g[ys-2,xs].astype(float)+g[ys+2,xs]+g[ys,xs-2]+g[ys,xs+2])/4
        # Select bright foreground edges, excluding dark facade/window edges.
        strong=np.flatnonzero((hp>25)&(g[ys,xs]>150));assert len(strong)>20
        pick=strong[np.linspace(0,len(strong)-1,min(128,len(strong))).astype(int)]
        fingerprints.append((ys[pick],xs[pick],hp[pick]))
        panel,layout=raster(entry['target'],entry['box'],12);entry['layout']=layout
        entry['trace']=[]
        entry['native_offset_trace']=[]
    d=subprocess.Popen(['ffmpeg','-v','error','-i',str(MOVIE),'-an','-pix_fmt','gray','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    n=0
    oy,ox=np.mgrid[-12:13,-4:5];oy=oy.flatten();ox=ox.flatten()
    while True:
        raw=d.stdout.read(130560)
        if not raw:break
        assert len(raw)==130560
        g=np.frombuffer(raw,np.uint8).reshape(272,480)
        for entry,(ys,xs,hp) in zip(layers,fingerprints):
            if entry['search'][0]<=n<=entry['search'][1]:
                yy=ys[None,:]+oy[:,None];xx=xs[None,:]+ox[:,None]
                h=g[yy,xx].astype(float)-(g[yy-2,xx].astype(float)+g[yy+2,xx].astype(float)+g[yy,xx-2].astype(float)+g[yy,xx+2].astype(float))/4
                scores=np.sum(h*hp[None,:],axis=1)/np.dot(hp,hp);best=int(np.argmax(scores))
                entry['trace'].append(round(float(scores[best]),6))
                entry['native_offset_trace'].append([int(ox[best]),int(oy[best])])
        n+=1
    assert d.wait()==0 and not d.stderr.read() and n==6425
    for entry in layers:
        lo,hi=entry['search'];v=entry['trace'];at=entry['ref']-lo;left=right=at
        while left and v[left-1]>.12:left-=1
        while right<len(v)-1 and v[right+1]>.12:right+=1
        entry['core_frames']=[lo+left,lo+right]
        entry['boundary_review_frames']=sorted(set(max(lo,min(hi,a+b)) for a in entry['core_frames'] for b in (-30,-10,-1,0,1,10,30)))
        entry['exact_authoring_interval_verified']=False
        entry['trace_origin_frame']=lo
        entry['fade_policy']='Bright-edge shape projection with bounded +/-4px X and +/-12px Y search; normalized luminance proposal, boundary approval pending. Low-opacity offsets may match noise.'
    previews=[]
    for ref in refs:
        original=images[ref];out=original.copy()
        for entry in layers:
            if entry['ref']==ref:
                panel,_=raster(entry['target'],entry['box'],12);out.paste(panel,entry['box'])
        pair=Image.new('RGB',(960,272));pair.paste(original,(0,0));pair.paste(out,(480,0));previews.append((ref,pair))
    report=dict(schema_version=1,status='staggered_field_pixel_and_numeric_timing_proposal',source_movie_sha256=SHA,
        target_queue_sha256=sha(queue),native_frames_numerically_examined=n,layers=layers,
        primary_rows_represented=[sources[i]['id'] for i in (7,11,12,15,16)],
        shared_title_rendered_once=True,full_wording_preserved=True,all_layer_plates_disjoint=True,
        backplate_policy='Intentional separate opaque black plates, not reconstructed source imagery.',
        remaining_signage='Native contact frames show the moving facade sign at least125 to139 seconds; exact per-frame footprint remains unproved. The plates do not establish its removal.',
        movie_assets_written=False,runtime_verified=False,whole_movie_english=False)
    # Geometric proof applies separately within each scene.
    for scene in (layers[:4],layers[4:8],layers[8:]):
        for i,a in enumerate(scene):
            for b in scene[i+1:]:
                x,y,X,Y=a['box'];u,v,U,V=b['box'];assert min(X,U)<=max(x,u) or min(Y,V)<=max(y,v)
    return report,previews

def signage_sheet():
    frames=list(range(3750,4500,30))
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select='+ '+'.join('eq(n\\,%d)'%n for n in frames),'-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==len(frames)*391680
    sheet=Image.new('RGB',(1200,5*154),(25,25,25));draw=ImageDraw.Draw(sheet)
    hashes=[]
    for i,n in enumerate(frames):
        raw=p.stdout[i*391680:(i+1)*391680];im=Image.frombytes('RGB',(480,272),raw)
        x=(i%5)*240;y=(i//5)*154;sheet.paste(im.resize((240,136)),(x,y+18))
        draw.text((x+3,y+2),f'Frame {n} / {n*1001/30000:.3f}s',fill='white')
        hashes.append(dict(frame=n,source_rgb_sha256=sha(raw)))
    return sheet,hashes

def boundaries(report):
    frames=sorted(set(n for entry in report['layers'] for n in entry['boundary_review_frames']))
    def balanced(values):
        if len(values)==1:return 'eq(n\\,%d)'%values[0]
        k=len(values)//2;return '('+balanced(values[:k])+'+'+balanced(values[k:])+')'
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select='+balanced(frames),'-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==len(frames)*391680
    images={n:Image.frombytes('RGB',(480,272),p.stdout[i*391680:(i+1)*391680]) for i,n in enumerate(frames)}
    results=[]
    for entry in report['layers']:
        box=entry['box'];h=box[3]-box[1];step=h+22
        sheet=Image.new('RGB',(840,step*len(entry['boundary_review_frames'])),(25,25,25));draw=ImageDraw.Draw(sheet)
        for i,n in enumerate(entry['boundary_review_frames']):
            # Native visibility crops plus unencoded fade proposal: no guessed exact event timestamps.
            im=images[n];panel,_=raster(entry['target'],box,12)
            opacity=max(0,min(1,entry['trace'][n-entry['trace_origin_frame']]))
            panel=Image.blend(Image.new('RGB',panel.size),panel,opacity)
            sheet.paste(im.crop(box),(0,i*step+22));sheet.paste(panel,(420,i*step+22))
            draw.text((3,i*step+2),f"Frame {n} / native crop | proposed alpha {opacity:.3f}",fill='white')
        results.append((entry['key'],sheet))
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--output',default='work/ui/media/staggered_prologue_layer_plan_v3');a=p.parse_args()
    r,previews=prepare();print(json.dumps([dict(key=x['key'],target=x['target'],layout=x['layout'],core=x['core_frames']) for x in r['layers']],indent=2))
    if a.write:
        dest=Path(a.output).resolve();dest.relative_to(Path('work/ui').resolve());assert not dest.exists();dest.mkdir(parents=True)
        for ref,im in previews:im.save(dest/f'frame{ref}_comparison.png')
        sheet,hashes=signage_sheet();sheet.save(dest/'moving_signage_native_contact.png');r['signage_inspection_frames']=hashes
        for key,sheet in boundaries(r):sheet.save(dest/(key+'_boundaries.png'))
        (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
