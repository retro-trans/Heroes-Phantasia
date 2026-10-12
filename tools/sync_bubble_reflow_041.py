"""Keep the English construction-company reflow and Japanese-free export together."""
import argparse,json
from pathlib import Path
from prepare_bubble_reflow_041 import build
from strip_jp import export

def text(s):return ''.join('{%02X}'%v if v<32 else chr(v)for v in s.encode('ascii'))
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args()
    p=Path('work/translation/en/batch_0014.json');queue=json.loads(p.read_text(encoding='utf8'))
    rec=build()[1]['records'][0];old,new=text(rec['old_english']),text(rec['new_english'])
    row=next(r for r in queue['rows']if r['id']=='c5299a7bbe51ffe5b085')
    if row['target']not in (old,new):raise ValueError('Logical translation differs')
    row['target']=new;note=' 0.1.41: construction-company pages rewrapped to fit the original Japanese tail ray and preserve every word and nonline control.'
    if note not in row['notes']:row['notes']+=note
    clean=export(queue);print(json.dumps(dict(version='0.1.41',id=row['id'],target=new),indent=2))
    if not a.write:print('DRY RUN');return
    p.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    p.with_suffix('.en.json').write_text(json.dumps(clean,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
