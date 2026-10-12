"""Apply selected English drafts by stable ID. Preview first; --write opts in."""
import argparse, json, pathlib, re
from apply_targets import JP
from dialogue_tokens import validate_controls

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('draft',type=pathlib.Path)
    p.add_argument('--write',action='store_true');a=p.parse_args()
    draft=json.loads(a.draft.read_text(encoding='utf-8'));wanted={x['id']:x for x in draft['rows']}
    if len(wanted)!=len(draft['rows']):raise ValueError('Duplicate draft IDs')
    found=set();changes=[]
    for path in sorted(pathlib.Path('work/translation/en').glob('*.json')):
        if path.name.endswith('.en.json'):continue
        data=json.loads(path.read_text(encoding='utf-8'));touched=False
        for row in data['rows']:
            if row['id'] not in wanted:continue
            new=wanted[row['id']];target=new['target']
            try:validate_controls(row['source'],target)
            except ValueError as error:raise ValueError('Control mismatch '+row['id']+': '+str(error)) from error
            if JP.search(target):raise ValueError('Japanese in target '+row['id'])
            row.update(target=target,status='draft',context=new.get('context','Player-facing reference/help text, translated as one original record.'),decisions=new.get('decisions','Full meaning retained; control order preserved; layout awaits VWF integration.'))
            if 'source_omission_preserved' in new:
                if not isinstance(new['source_omission_preserved'],bool):raise ValueError('Omission flag must be boolean '+row['id'])
                row['source_omission_preserved']=new['source_omission_preserved']
            print(json.dumps({'file':str(path),'id':row['id'],'target':target},ensure_ascii=False))
            found.add(row['id']);touched=True
        if touched:changes.append((path,data))
    if found!=wanted.keys():raise ValueError('Draft IDs missing from queue: '+str(wanted.keys()-found))
    print('Matched',len(found),'drafts in',len(changes),'files')
    if a.write:
        for path,data in changes:path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:print('DRY RUN: no changes written.')

if __name__=='__main__':main()
