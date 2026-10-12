"""Pure tracked facade-sign pixel proposal; no native movie writes."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from prepare_prologue_overlays import MOVIE,SHA,QUEUE,SOURCE,sha,raster

def prepare():
    assert sha(MOVIE.read_bytes())==SHA
    q=QUEUE.read_bytes();src=json.loads(SOURCE.read_bytes())['rows'][11]
    target=next(x['target'] for x in json.loads(q)['rows'] if x['id']==src['id'])
    lo,hi,anchor=3601,4230,3750;box=(202,68,391,110)
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf',f'select=between(n\\,{lo}\\,{hi})','-fps_mode','vfr','-an','-pix_fmt','gray','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==(hi-lo+1)*130560
    frames=np.frombuffer(p.stdout,np.uint8).reshape(hi-lo+1,272,480);ref=frames[anchor-lo]
    ys,xs=np.mgrid[box[1]+2:box[3]-2,box[0]+2:box[2]-2];ys=ys.flatten();xs=xs.flatten()
    hp=ref[ys,xs].astype(float)-(ref[ys-2,xs].astype(float)+ref[ys+2,xs]+ref[ys,xs-2]+ref[ys,xs+2])/4
    strong=np.flatnonzero((hp>12)&(ref[ys,xs]>100));assert len(strong)>20
    pick=strong[np.linspace(0,len(strong)-1,min(128,len(strong))).astype(int)];ys=ys[pick];xs=xs[pick];hp=hp[pick]
    tracks={anchor:dict(frame=anchor,offset=[0,0],score=1.0,box=list(box))}
    for sequence in (range(anchor+1,hi+1),range(anchor-1,lo-1,-1)):
        ox=oy=0
        for n in sequence:
            dy,dx=np.mgrid[max(-100,oy-3):min(220,oy+3)+1,max(-20,ox-2):min(20,ox+2)+1]
            dy=dy.flatten();dx=dx.flatten();yy=ys[None,:]+dy[:,None];xx=xs[None,:]+dx[:,None]
            valid=(yy>=2)&(yy<270)&(xx>=2)&(xx<478)
            legal=valid.sum(axis=1)>=32
            if not legal.any():break
            valid=valid[legal];yy=yy[legal].clip(2,269);xx=xx[legal].clip(2,477);dy=dy[legal];dx=dx[legal];g=frames[n-lo]
            v=g[yy,xx].astype(float)-(g[yy-2,xx].astype(float)+g[yy+2,xx]+g[yy,xx-2]+g[yy,xx+2])/4
            scores=np.sum(v*hp*valid,axis=1)/np.sum(hp*hp*valid,axis=1);i=int(np.argmax(scores));ox=int(dx[i]);oy=int(dy[i])
            tracks[n]=dict(frame=n,offset=[ox,oy],score=round(float(scores[i]),6),retained_sample_points=int(valid[i].sum()),box=[box[0]+ox,box[1]+oy,box[2]+ox,box[3]+oy])
    selected=[n for n in (3601,3610,3620,3630,3650,3750,3950,4100,4150,4180,4200,4220) if n in tracks]
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select='+ '+'.join('eq(n\\,%d)'%n for n in selected),'-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==len(selected)*391680
    sheet=Image.new('RGB',(960,294*len(selected)),(25,25,25));draw=ImageDraw.Draw(sheet)
    for i,n in enumerate(selected):
        original=Image.frombytes('RGB',(480,272),p.stdout[i*391680:(i+1)*391680]);new=original.copy();b=tracks[n]['box']
        panel,layout=raster(target,b,12);new.paste(panel,b)
        sheet.paste(original,(0,i*294+22));sheet.paste(new,(480,i*294+22));draw.text((3,i*294+3),f"Frame {n}, score {tracks[n]['score']:.3f}, candidate offset {tracks[n]['offset']}",fill='white')
    report=dict(schema_version=1,status='moving_facade_sign_track_and_pixel_dry_proposal_not_approved',source_movie_sha256=SHA,target_queue_sha256=sha(q),
        logical_target=target,shared_caption_id=src['id'],additional_diegetic_occurrence=True,frames_numerically_inspected=hi-lo+1,
        anchor_frame=anchor,anchor_box=list(box),tracks=[tracks[n] for n in sorted(tracks)],review_frames=selected,
        policy='Intentional moving black rectangular plate replaces facade lettering; no recovery of original canopy and no perspective-warp claim.',
        limitations=['Tracking confidence alone is not complete source-footprint proof. Every selected boundary requires pixel review.',
            'Partial clipped tracking excludes offscreen points and requires at least32 native samples; the intended plate is clipped by the viewport. Low confidence remains review-only.',
            'Exact occurrence start/end and native fades remain unverified.'],movie_assets_written=False,runtime_verified=False,whole_movie_english=False)
    return report,sheet

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--output',default='work/ui/media/prologue_facade_sign_proposal_v3');a=p.parse_args();r,s=prepare()
    print(json.dumps({k:v for k,v in r.items() if k!='tracks'},indent=2));print(json.dumps([x for x in r['tracks'] if x['frame'] in r['review_frames']],indent=2))
    if a.write:
        dest=Path(a.output).resolve();dest.relative_to(Path('work/ui').resolve());assert not dest.exists();dest.mkdir(parents=True)
        s.save(dest/'native_proposed_contact.png');(dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
