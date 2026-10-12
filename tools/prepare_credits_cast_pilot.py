"""Pure bounded English cast-credit samples; no movie or native asset writer."""
import argparse,json,hashlib,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from prepare_title_logo_proposal import FONT
from movie_preparation_runtime import fingerprint

def sha(b):return hashlib.sha256(b).hexdigest()
SOURCE=Path('work/source/media_audit/PSP_GAME_USRDIR_MOVIE_HPMOVE09.PMF')
QUEUES=[Path('work/translation/en/media_0001.json'),Path('work/translation/en/media_0002.json')]
def prepare():
    rows=[r for p in QUEUES for r in json.loads(p.read_bytes())['rows'] if r.get('category')=='movie_cast_credit']
    assert len(rows)==66 and all(r['target'] for r in rows)
    selected=rows[:12]
    # Human-read native glyph extents at the exact decoded frames, not 2fps indexes.
    plans={180:dict(headings=[(73,92,'Heroes Phantasia',18),(131,148,'Cast',14),(163,180,'Sorcerous Stabber Orphen',14)],
                    rows=list(zip(range(4),[184,201,219,237]))),
           300:dict(headings=[(0,16,'Sorcerous Stabber Orphen',14),(107,124,'Rune Soldier',14)],
                    rows=list(zip(range(12),[21,39,57,74,129,147,165,183,201,219,237,255])))}
    p=subprocess.run(['ffmpeg','-v','error','-i',str(SOURCE),'-vf','select=eq(n\\,180)+eq(n\\,300)',
        '-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==2*391680
    sheet=Image.new('RGB',(960,588));draw=ImageDraw.Draw(sheet);ledger=[]
    for k,(frame,plan) in enumerate(plans.items()):
        native=Image.frombytes('RGB',(480,272),p.stdout[k*391680:(k+1)*391680]);out=native.copy();boxes=[]
        def render(y,Y,text,size,pair=False):
            box=[20,max(0,y-1),460,min(272,Y+1)];boxes.append(box)
            panel=Image.new('RGB',((box[2]-box[0])*4,(box[3]-box[1])*4));d=ImageDraw.Draw(panel)
            font=ImageFont.truetype(str(FONT),size*4)
            parts=text.split('\n') if pair else [text]
            assert len(parts)==(2 if pair else 1)
            for i,t in enumerate(parts):
                width=d.textlength(t,font=font);available=(212 if i==0 else 208)*4 if pair else 440*4
                assert width<=available,(t,width,available)
                x=(212*4-width) if pair and i==0 else 232*4 if pair else (440*4-width)/2
                d.text((x,0),t,font=font,fill='white',anchor='lt')
            out.paste(panel.resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS),box)
            ledger.append(dict(frame=frame,box=box,target=text,font_px=size,pair_columns=pair))
        for y,Y,text,size in plan['headings']:render(y,Y,text,size)
        for index,y in plan['rows']:render(y,y+13,selected[index]['target'],12,True)
        # Exact nonselected pixel identity is meaningful only for these samples.
        masked=out.copy()
        for box in boxes:masked.paste(native.crop(box),box)
        assert masked.tobytes()==native.tobytes()
        sheet.paste(native,(0,k*294+22));sheet.paste(out,(480,k*294+22))
        draw.text((2,k*294),f'Native frame {frame}',fill='white');draw.text((482,k*294),'Bounded English intended sample',fill='white')
    report=dict(status='credits_cast_static_pixel_pilot_timing_unverified',movie=9,source_sha256=sha(SOURCE.read_bytes()),
        queue_sha256={str(q):sha(q.read_bytes()) for q in QUEUES},selected_pair_ids=[r['id'] for r in selected],
        unique_cast_pairs=12,sampled_frames=[180,300],placements=ledger,
        native_black_backplate_intent=True,all_outside_selected_boxes_exact=True,preparation_runtime=fingerprint(),
        no_native_frame_timing_claim=True,scroll_tracking_verified=False,whole_movie_text_absence_verified=False,
        staff_unresolved_names_not_replaced=True,native_assets_written=False)
    return report,sheet

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-review',action='store_true');p.add_argument('--output',type=Path,default=Path('work/ui/media/credits_cast_pixel_pilot'))
    a=p.parse_args();r,s=prepare();print(json.dumps(r,indent=2))
    if a.write_review:
        a.output.resolve().relative_to(Path('work/ui').resolve());assert not a.output.exists();a.output.mkdir(parents=True)
        (a.output/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');s.save(a.output/'native_intended.png')
