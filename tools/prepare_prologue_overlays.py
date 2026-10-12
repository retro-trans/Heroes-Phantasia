"""Full-native-frame primary prologue overlay plan; saves reviews only, never PMF assets."""
import argparse,hashlib,json,math,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from prepare_movie_caption_pilot import MOVIE,SHA
from prepare_title_logo_proposal import FONT

QUEUE=Path('work/translation/en/media_0001.json')
SOURCE=Path('work/source/media_audit/prologue_caption_proposal.json')
BOXES=[(165,123,315,147)]+[(12,90,468,181)]*5+[(10,116,470,151),(65,48,415,220),
    (45,72,455,207),(15,92,465,181),(25,65,455,199),(55,37,425,175),
    (38,39,445,247),(53,119,427,151),(12,68,475,224),(80,67,400,147),(90,70,390,207)]

def sha(d):return hashlib.sha256(d).hexdigest()

def layout(target,box):
    w,h=box[2]-box[0],box[3]-box[1]
    for size in range(16,9,-1):
        f=ImageFont.truetype(str(FONT),size*4);lines=[]
        for paragraph in target.split('\n'):
            current=''
            for word in paragraph.split(' '):
                candidate=(current+' '+word).strip()
                if f.getlength(candidate)>4*(w-16) and current:lines.append(current);current=word
                else:current=candidate
            lines.append(current)
        if any(f.getlength(line)>4*(w-16) for line in lines):continue
        if len(lines)*(size+4)<=h-4:break
    else:raise ValueError('Full wording does not fit bounded plate')
    assert ''.join(target.split())==''.join(''.join(lines).split())
    return f,size,lines

def raster(target,box,index):
    f,size,lines=layout(target,box);w,h=box[2]-box[0],box[3]-box[1]
    background=(245,245,245) if index==14 else (0,0,0)
    foreground=(15,15,15) if index==14 else (255,255,255)
    canvas=Image.new('RGB',(w,h),background);step=size+4;y=(h-len(lines)*step)//2
    masks=[]
    for line in lines:
        bb=f.getbbox(line);mw,mh=math.ceil((bb[2]-bb[0])/4),math.ceil((bb[3]-bb[1])/4)
        mask=Image.new('L',(mw*4,mh*4));ImageDraw.Draw(mask).text((-bb[0],-bb[1]),line,font=f,fill=255)
        mask=mask.resize((mw,mh),Image.Resampling.LANCZOS);x=(w-mw)//2
        yy=y+(step-mh)//2
        canvas.paste(foreground,(x,yy,x+mw,yy+mh),mask);masks.append([x,yy,mw,mh]);y+=step
    return canvas,dict(font_px=size,lines=lines,line_boxes=masks,
        policy='Intentional flat light plate retains letter contrast; not recovered paper texture.' if index==14 else 'Intentional opaque black backplate, not reconstructed original imagery.')

def prepare():
    assert sha(MOVIE.read_bytes())==SHA
    source_raw=SOURCE.read_bytes();queue_raw=QUEUE.read_bytes();sources=json.loads(source_raw)['rows']
    targets={x['id']:x for x in json.loads(queue_raw)['rows']};assert len(sources)==17
    refs=[round(x['nominal_frame_time_seconds']*30000/1001) for x in sources]
    select='+'.join('eq(n\\,%d)'%n for n in refs)
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select='+select,'-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==17*480*272*3
    originals=[];previews=[];entries=[];templates=[]
    for i,(row,box,ref) in enumerate(zip(sources,BOXES,refs)):
        target=targets[row['id']]['target'];assert target
        im=Image.frombytes('RGB',(480,272),p.stdout[i*480*272*3:(i+1)*480*272*3]);originals.append(im)
        panel,l=raster(target,box,i);out=im.copy();out.paste(panel,box);previews.append(out)
        entries.append(dict(id=row['id'],target=target,representative_native_frame=ref,box=list(box),layout=l,
            primary_caption_only=True,exact_interval_verified=False,bounded_region_review_pending=i!=0))
        grey=np.asarray(im.convert('L'));x0,y0,x1,y1=box
        ys,xs=np.mgrid[max(3,y0):min(269,y1),max(3,x0):min(477,x1)];ys=ys.flatten();xs=xs.flatten()
        hp=grey[ys,xs].astype(float)-(grey[ys-2,xs].astype(float)+grey[ys+2,xs]+grey[ys,xs-2]+grey[ys,xs+2])/4
        strong=np.flatnonzero(abs(hp)>12)
        assert len(strong)>20
        chosen=strong[np.linspace(0,len(strong)-1,min(1024,len(strong))).astype(int)]
        templates.append((ys[chosen],xs[chosen],hp[chosen]))
    # Every frame is numerically inspected against caption shape fingerprints, not claimed human views.
    decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(MOVIE),'-an','-pix_fmt','gray','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    traces=[[] for _ in range(17)];frame=0
    while True:
        raw=decoder.stdout.read(480*272)
        if not raw:break
        assert len(raw)==480*272
        g=np.frombuffer(raw,np.uint8).reshape(272,480)
        for i,(ys,xs,refhp) in enumerate(templates):
            hp=g[ys,xs].astype(float)-(g[ys-2,xs].astype(float)+g[ys+2,xs]+g[ys,xs-2]+g[ys,xs+2])/4
            score=float(np.dot(hp,refhp)/np.dot(refhp,refhp))
            traces[i].append(round(score,6))
        frame+=1
    assert decoder.wait()==0 and not decoder.stderr.read() and frame==6425
    for i,entry in enumerate(entries):
        lo=0 if i==0 else refs[i-1];hi=6424 if i==16 else refs[i+1]
        # Seeded component near the human-transcribed representative, followed through low fades.
        values=traces[i];peak=refs[i];assert values[peak]>.5
        left=peak;right=peak
        while left>lo and values[left-1]>.12:left-=1
        while right<hi and values[right+1]>.12:right+=1
        entry['timing_candidate']=dict(first_core_frame=left,last_core_frame=right,
            threshold=.12,first_pts=90000+left*3003,last_pts=90000+right*3003,
            inspection_search_bounds=[max(lo,left-50),min(hi,right+50)],
            caveat='Shape correlation identifies a core candidate, not exact authoring fade timestamps; moving backgrounds and repeated titles require boundary review.')
        entry['native_shape_correlation_trace']=values
    report=dict(schema_version=1,status='all_primary_prologue_overlay_dry_plan_boundaries_pending',source_movie=MOVIE.as_posix(),source_sha256=SHA,
        source_caption_registry_sha256=sha(source_raw),target_queue_sha256=sha(queue_raw),primary_rows=17,
        native_frames_numerically_examined=frame,representative_frames_human_review_required=17,entries=entries,
        font_sha256=sha(FONT.read_bytes()),full_wording_and_paragraph_order_preserved=True,
        additional_occurrences=[dict(text='Sawada International Research',kind='diegetic building signage',
            approximate_seconds=[133,149],geometry='Camera-dependent moving facade; separate source footprint and timing still need validation.',
            represented_in_primary_rows=False,translated_pixel_proposal_pending=True)],
        limitations=['Organization list and SIR definition contain staggered internal line reveals; one block correlation cannot prove each line fade.',
            'The seventeen reviewed primary rows do not establish whole-movie Japanese-text absence.',
            'Source sign occurrences and exact temporal/region bounds must be resolved before installation.'],
        movie_assets_written=False,encoded_candidate_generated=False,runtime_verified=False,whole_movie_english=False)
    return report,originals,previews

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    r,old,new=prepare();print(json.dumps({k:v for k,v in r.items() if k!='entries'},indent=2))
    print(json.dumps([dict(id=x['id'],font=x['layout']['font_px'],lines=x['layout']['lines'],timing=x['timing_candidate']) for x in r['entries']],indent=2))
    if a.write:
        dest=Path('work/ui/media/full_prologue_overlay_plan');assert not dest.exists();dest.mkdir(parents=True)
        for i,(a,b) in enumerate(zip(old,new)):
            pair=Image.new('RGB',(960,272));pair.paste(a,(0,0));pair.paste(b,(480,0));pair.save(dest/f'caption{i:02}_comparison.png')
        (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
