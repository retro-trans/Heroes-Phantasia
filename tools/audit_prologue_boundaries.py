"""Pure ordinary-caption temporal boundary comparisons; saves reviews only."""
import argparse,json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from prepare_full_prologue import events,compose,MOVIE,sha,QUEUE

def prepare():
    es,sign=events();ordinary=[e for e in es if e['key'].startswith('ordinary_')]
    fs=sorted(set(max(0,min(6424,n)) for e in ordinary for n in (e['first']-30,e['first']-1,e['first'],e['last'],e['last']+1,e['last']+30)))
    def balanced(v):
        if len(v)==1:return 'eq(n\\,%d)'%v[0]
        k=len(v)//2;return '('+balanced(v[:k])+'+'+balanced(v[k:])+')'
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select='+balanced(fs),'-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==len(fs)*391680
    images={n:Image.frombytes('RGB',(480,272),p.stdout[i*391680:(i+1)*391680]) for i,n in enumerate(fs)};sheets=[];rows=[]
    for e in ordinary:
        selected=[max(0,min(6424,n)) for n in (e['first']-30,e['first']-1,e['first'],e['last'],e['last']+1,e['last']+30)]
        b=e['box'];height=b[3]-b[1];sheet=Image.new('RGB',(960,(height+24)*6));d=ImageDraw.Draw(sheet)
        for i,n in enumerate(selected):
            old=images[n];new=compose(old,n,es,sign);sheet.paste(old.crop(b),(0,i*(height+24)+24));sheet.paste(new.crop(b),(480,i*(height+24)+24))
            d.text((3,i*(height+24)+3),f'{n} source / complete composite crop',fill='white')
        sheets.append((e['key'],sheet));rows.append(dict(key=e['key'],frames=selected,box=b,source_ghost_absence_verified=False))
    for e in es:e.pop('_panel',None)
    return dict(schema_version=1,status='ordinary_caption_boundary_pixel_review_pending',target_queue_sha256=sha(QUEUE.read_bytes()),rows=rows,
        first_caption_restored_native_pilot_bounds=[19,302],native_assets_written=False,whole_movie_english=False),sheets

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-review',action='store_true');a=p.parse_args();r,s=prepare();print(json.dumps(r,indent=2))
    if a.write_review:
        dest=Path('work/ui/media/ordinary_prologue_boundary_audit');assert not dest.exists();dest.mkdir(parents=True)
        for key,im in s:im.save(dest/(key+'.png'))
        (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
