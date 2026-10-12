"""Pure first-caption303-frame GOP pilot; optional writes only fresh review JSON/PNGs."""
import argparse,hashlib,json,statistics,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from prepare_movie_caption_pilot import prepare as pixels,MOVIE,BOX,ID
from movie_fixed_mux import source,prepare as mux
from movie_fixed_mux_baseline import probe

def sha(d):return hashlib.sha256(d).hexdigest()

def run(cmd,data=None):
    p=subprocess.run(cmd,input=data,capture_output=True)
    assert p.returncode==0 and not p.stderr,p.stderr.decode(errors='replace')
    return p.stdout

def prepare(crf=28,refined_rule=False):
    proposal,reference,english=pixels();original,video,_,units,base=source(3)
    frames=303;assert units[frames]['idr']
    raw=run(['ffmpeg','-v','error','-i',str(MOVIE),'-frames:v',str(frames),'-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'])
    assert len(raw)==frames*480*272*3
    modified=bytearray(raw);alpha=[];crop_rows=[]
    # Median rule contrast rejects colored sparks and local background gradients better than2fps OCR timing.
    for n in range(frames):
        d=raw[n*480*272*3:(n+1)*480*272*3]
        def grey(x,y):return min(d[(y*480+x)*3:(y*480+x)*3+3])
        contrast=statistics.median(grey(x,134)-(grey(x,131)+grey(x,137))/2 for x in range(170,250))
        if refined_rule:
            contrast=max(contrast,statistics.median(grey(x,135)-(grey(x,131)+grey(x,137))/2 for x in range(170,250)))
        first,normal=(19,157) if refined_rule else (22,113)
        opacity=round(max(0,min(255,contrast/normal*255))) if first<=n<=267 else 0
        alpha.append(opacity)
        if n<first:continue
        frame=Image.frombytes('RGB',(480,272),d)
        frame.paste((0,0,0),BOX)
        # Blend approved English foreground against black, preserving its measured native fade strength.
        patch=english.crop(BOX)
        if opacity<255:patch=Image.blend(Image.new('RGB',patch.size),patch,opacity/255)
        frame.paste(patch,BOX);new=frame.tobytes()
        assert all(a==b for y in range(272) for a,b in [(d[y*1440:(y+1)*1440],new[y*1440:(y+1)*1440])] if y<BOX[1] or y>=BOX[3])
        for y in range(BOX[1],BOX[3]):
            assert d[y*1440:y*1440+BOX[0]*3]==new[y*1440:y*1440+BOX[0]*3]
            assert d[y*1440+BOX[2]*3:(y+1)*1440]==new[y*1440+BOX[2]*3:(y+1)*1440]
        modified[n*480*272*3:(n+1)*480*272*3]=new
    keys=','.join(f'{i*1001/30000:.9f}' for i in base['idr_frame_indexes'] if i<frames)
    assert 18<=crf<=40
    encoded=run(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','rgb24','-video_size','480x272','-framerate','30000/1001','-i','pipe:0','-an','-frames:v',str(frames),'-c:v','libx264','-preset','slow','-crf',str(crf),'-profile:v','main','-level:v','2.1','-pix_fmt','yuv420p','-bf','0','-refs','1','-g','10000','-keyint_min','1','-sc_threshold','0','-force_key_frames',keys,'-x264-params','aud=1:repeat-headers=1:weightp=0','-bsf:v','filter_units=remove_types=6','-f','h264','pipe:1'],bytes(modified))
    candidate,report=mux(3,encoded,prefix=True,timing_transplant=True,compact_clock=True)
    report.update(schema_version=1,row_id=ID,logical_target=proposal['target'],pilot_frames=frames,
        translated_pixel_scope='Only first caption region of first303 frames; every later native frame retained.',
        preencode_outside_region_rgb_exact=True,intended_frame90_rgb_sha256=sha(modified[90*480*272*3:91*480*272*3]),
        encoder_h264_sha256=sha(encoded),encoder_h264_bytes=len(encoded),encoder_crf=crf,native_assets_written=False,
        source_caption_timing_approved=False,fade_proposal=dict(first_frame=first,last_frame=267,
            native_rule_refinement=refined_rule,alpha_8bit_trace=alpha,
            method='Maximum median contrast across both native rule rows normalized to157; first positive median atframe19.' if refined_rule else 'Native horizontal-rule median contrast normalized to113; outside proposed fade interval English alpha0.',
            caveat='This decoded visibility proposal needs boundary-frame review; compression residue does not reveal an authoring event timestamp.'),
        backplate_policy=f'Black replacement rectangle remains fromframe{first} through302 to remove source compression ghosts; this intentionally removes background inside the approved box.',
        runtime_verified=False,whole_movie_english=False)
    if candidate:
        old,_=probe(original);new,errors=probe(candidate);keys=('key_frame','pict_type','pts','pkt_dts','best_effort_timestamp','width','height')
        differences=[i for i,(a,b) in enumerate(zip(old['frames'],new['frames'])) if any(a.get(k)!=b.get(k) for k in keys)]
        report['full_pc_timing']=dict(frames=len(new['frames']),difference_count=len(differences),first_differences=differences[:8],errors=errors)
        assert len(new['frames'])==len(old['frames'])==6425 and not errors and not differences
    decoded=run(['ffmpeg','-v','error','-f','h264','-i','pipe:0','-vf','select=eq(n\\,90)','-frames:v','1','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],encoded)
    assert len(decoded)==480*272*3
    actual=Image.frombytes('RGB',(480,272),decoded);report['decoded_h264_frame90_rgb_sha256']=sha(decoded)
    selected=[18,19,20,21,22,23,24,25,260,263,264,265,266,267,268,269,270,274,276]
    boundary=Image.new('RGB',(600,len(selected)*62),(30,30,30));draw=ImageDraw.Draw(boundary)
    for i,n in enumerate(selected):
        im=Image.frombytes('RGB',(480,272),raw[n*480*272*3:(n+1)*480*272*3]).crop(BOX)
        boosted=im.point(lambda x:min(255,x*8))
        boundary.paste(im.resize((300,48),Image.Resampling.NEAREST),(0,i*62+14))
        boundary.paste(boosted.resize((300,48),Image.Resampling.NEAREST),(300,i*62+14))
        draw.text((3,i*62),f'Frame{n}: native / diagnostic8x brightness',fill='white')
    report['boundary_frames_reviewed_automatically']=selected
    return candidate,report,reference,english,actual,boundary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--crf',type=int,default=28);p.add_argument('--native-rule-v2',action='store_true');a=p.parse_args()
    _,r,source,intended,decoded,boundary=prepare(a.crf,a.native_rule_v2)
    print(json.dumps({k:v for k,v in r.items() if k not in ('pes_timestamp_records','idr_frame_indexes','fade_proposal')},indent=2))
    if a.write:
        dest=Path(f'work/ui/media/first_caption_encoded_pilot_crf{a.crf}'+('_rule_v2' if a.native_rule_v2 else ''));assert not dest.exists();dest.mkdir(parents=True)
        boundary.save(dest/'boundary_comparison.png');decoded.save(dest/'decoded_frame90.png')
        comparison=Image.new('RGB',(1440,272));comparison.paste(source,(0,0));comparison.paste(intended,(480,0));comparison.paste(decoded,(960,0));comparison.save(dest/'source_intended_decoded.png')
        (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
