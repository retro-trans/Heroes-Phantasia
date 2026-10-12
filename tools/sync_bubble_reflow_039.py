"""Keep the scoped English mainland reflow and Japanese-free export together."""
import argparse,json
from pathlib import Path
from prepare_bubble_order_039 import build
from strip_jp import export
from prepare_field_bubble_039 import build as field_build
def text(raw):return ''.join('{%02X}'%v if v<32 else chr(v)for v in raw.encode('ascii'))
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args()
    p=Path('work/translation/en/batch_0014.json');queue=json.loads(p.read_text(encoding='utf8'))
    reflow=build()[1]['records'][0]['reflow'];old=text(reflow['old_english']);new=text(reflow['new_english'])
    row=next(r for r in queue['rows']if r['target']in (old,new));row['target']=new
    note=' 0.1.39: six-line mainland explanation to retain the original Japanese tail ray; words and nonline controls preserved.'
    if note not in row['notes']:row['notes']+=note
    clean=export(queue);print(json.dumps(dict(version='0.1.39',id=row['id'],target=new,visible_lines=6,words_and_nonline_controls_exact=True),indent=2))
    if not a.write:print('DRY RUN');return
    p.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    p.with_suffix('.en.json').write_text(json.dumps(clean,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    p=Path('work/translation/en/batch_0001.json');queue=json.loads(p.read_text(encoding='utf8'));field=field_build()[1]
    old=text(field['old_english']);new=text(field['new_english']);row=next(r for r in queue['rows']if r['id']=='ca3430cfd18ef7ab18cf')
    if row['target']not in (old,new):raise ValueError('Field logical translation differs')
    row['target']=new;note=' 0.1.39: both pages rewrapped to preserve the original Japanese tail ray; wording and nonline controls retained.'
    if note not in row['notes']:row['notes']+=note
    clean=export(queue);p.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8');p.with_suffix('.en.json').write_text(json.dumps(clean,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
