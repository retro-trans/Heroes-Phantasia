"""Pure first-prologue-caption pixel/timing proposal; no movie or video writes."""
import argparse,hashlib,json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from prepare_title_logo_proposal import FONT

MOVIE=Path('work/source/media_audit/PSP_GAME_USRDIR_MOVIE_HPMOVE03.PMF')
SHA='252985cb74c0fa117c2f8cc48bb31e932a5ac671b14c3a18d5af2bc0d2b104c1'
QUEUE=Path('work/translation/en/media_0001.json')
ID='movie03_4fe3759116982142eebf'
BOX=(165,123,315,147)

def sha(data):return hashlib.sha256(data).hexdigest()

def decode(args):
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE)]+args+['-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True)
    assert p.returncode==0 and not p.stderr
    return p.stdout

def prepare():
    assert sha(MOVIE.read_bytes())==SHA
    queue_raw=QUEUE.read_bytes();rows=json.loads(queue_raw)['rows'];row=next(x for x in rows if x['id']==ID)
    assert row['target']=='The present day.'
    raw=decode(['-vf','select=eq(n\\,90)','-frames:v','1']);assert len(raw)==480*272*3
    original=Image.frombytes('RGB',(480,272),raw);proposed=original.copy()
    # This is an intentional backplate; no claim to reconstruct occluded fire imagery.
    proposed.paste((0,0,0),BOX)
    font=ImageFont.truetype(str(FONT),16*4);bb=font.getbbox(row['target']);mw,mh=math.ceil((bb[2]-bb[0])/4),math.ceil((bb[3]-bb[1])/4)
    assert mw<=BOX[2]-BOX[0]-8 and mh<=BOX[3]-BOX[1]-4
    mask=Image.new('L',(mw*4,mh*4));ImageDraw.Draw(mask).text((-bb[0],-bb[1]),row['target'],font=font,fill=255)
    mask=mask.resize((mw,mh),Image.Resampling.LANCZOS)
    x=BOX[0]+(BOX[2]-BOX[0]-mw)//2;y=BOX[1]+(BOX[3]-BOX[1]-mh)//2
    proposed.paste((255,255,255),(x,y,x+mw,y+mh),mask)
    before=original.tobytes();after=proposed.tobytes()
    assert all(before[p*3:p*3+3]==after[p*3:p*3+3] for p in range(480*272) if not(BOX[0]<=p%480<BOX[2] and BOX[1]<=p//480<BOX[3]))
    # Every decoded frame of the initial500-frame window, not a sampled2fps scan.
    crop=decode(['-frames:v','500','-vf','crop=150:24:165:123']);assert len(crop)==500*150*24*3
    contrast=[]
    for frame in range(500):
        d=crop[frame*10800:(frame+1)*10800]
        means=[sum(min(d[(yy*150+xx)*3:(yy*150+xx)*3+3]) for xx in range(5,85))/80 for yy in (8,11,14)]
        contrast.append(round(means[1]-(means[0]+means[2])/2,6))
    # Numeric evidence only. Compression ghosts/background gradients forbid a false exact event-bound claim.
    report=dict(schema_version=1,status='first_caption_bounded_static_pixel_pilot_timing_pending',
        source_movie=MOVIE.as_posix(),source_sha256=SHA,translation_queue_sha256=sha(queue_raw),row_id=ID,
        target=row['target'],representative_frame=90,frame_pts=90000+90*3003,
        frame_time_seconds=90*1001/30000,viewport=[480,272],replacement_box=list(BOX),
        text_box=[x,y,mw,mh],font_px=16,font_sha256=sha(FONT.read_bytes()),
        original_rgb_sha256=sha(before),proposed_rgb_sha256=sha(after),outside_box_pixels_exact=True,
        source_region_policy='Intentional opaque black backplate replacing the entire horizontal-rule/label extent, not original background recovery.',
        initial_native_frames_analysed=500,line_contrast_trace=contrast,
        candidate_fade_first_decoded_contrast_frame=22,exact_caption_interval_verified=False,
        notes=['First source caption includes a horizontal rule preceding its era label; both are inside the selected region.',
            'Rule contrast rises at frame22. Low-level decoded fade residue and later fire gradients require boundary-frame visual review before exact end/alpha approval.',
            'This is one full-native-resolution frame proposal, not a reencoded movie or whole-movie coverage.',
            'Fixedmux baseline timing passed, but constrained CQP44 prologue GOP1927..1985 failed faint-text visual quality.'],
        encoded_candidate_generated=False,native_assets_written=False,runtime_verified=False)
    return report,original,proposed

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    r,old,new=prepare();print(json.dumps({k:v for k,v in r.items() if k!='line_contrast_trace'},indent=2))
    if a.write:
        dest=Path('work/ui/media/first_caption_pilot');assert not dest.exists();dest.mkdir(parents=True)
        old.save(dest/'original.png');new.save(dest/'proposed.png')
        pair=Image.new('RGB',(960,272));pair.paste(old,(0,0));pair.paste(new,(480,0));pair.save(dest/'comparison.png')
        (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
