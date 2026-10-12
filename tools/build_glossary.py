"""Consolidate researched glossary sources, checking spelling conflicts first."""
import argparse, json, pathlib

def canonical_key(entry, entries):
    # Identical short names can belong to different franchise entities.
    # Explicit context plus different categories/franchises prevents an
    # accidental character/companion merge (for example, the two Julias).
    matches=[e for e in entries if (e['ja'],e['en'])==(entry['ja'],entry['en'])]
    distinct=(len({e.get('franchise') for e in matches})>1 and
              len({e.get('category') for e in matches})>1 and
              any(e.get('context_required') for e in matches))
    return (entry['ja'],entry['en'],entry.get('franchise'),entry.get('category')) if distinct else (entry['ja'],entry['en'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    root=pathlib.Path('work/glossary');merged={};spellings={};sources=[];records=0;all_entries=[]
    for path in sorted(root.glob('*.en.json')):
        if path.name=='glossary.en.json':continue
        sources.append(str(path));data=json.loads(path.read_text(encoding='utf-8'))
        entries=data.get('entries',data.get('terms'))
        if entries is None:raise ValueError('Missing glossary entries or terms: '+str(path))
        all_entries.extend(entries)
    for entry in all_entries:
        records+=1;ja=entry['ja'];en=entry['en']
        for previous in spellings.get(ja,[]):
            if previous['en']==en:continue
            distinct_context=(entry.get('franchise') and previous.get('franchise')
                and entry['franchise']!=previous['franchise']
                and entry.get('category')!=previous.get('category')
                and (entry.get('context_required') or previous.get('context_required')))
            if not distinct_context:raise ValueError('Conflicting English spellings for glossary key; review source records')
        spellings.setdefault(ja,[]).append(entry);key=canonical_key(entry,all_entries)
        if key not in merged:merged[key]=dict(entry);continue
        item=merged[key]
        for field,value in entry.items():
            if field in ('sources','aliases'):
                item[field]=list(dict.fromkeys(item.get(field,[])+value))
            elif field not in item or item[field] in (None,'unknown',''):
                item[field]=value
        item.setdefault('contributor_ids',[item['id']])
        item['contributor_ids'].append(entry['id'])
    entries=list(merged.values())
    homographs=[{'choices':sorted({v['en'] for v in values}),
                 'entities':[{'id':v['id'],'franchise':v.get('franchise'),'category':v.get('category')} for v in values]}
                for values in spellings.values() if len({canonical_key(v,all_entries) for v in values})>1]
    for item in entries:
        if len({canonical_key(v,all_entries) for v in spellings[item['ja']]})>1:item['context_required']=True
    if len({x['id'] for x in entries})!=len(entries):raise ValueError('Duplicate canonical IDs')
    print(json.dumps({'source_files':len(sources),'source_records':records,'canonical_entries':len(entries),
        'spelling_conflicts':0,'context_dependent_homographs':homographs,'sample':[{'id':x['id'],'en':x['en']} for x in entries[:5]]},indent=2))
    if not a.write:print('DRY RUN: no file written.');return
    dest=root/'glossary.en.json'
    dest.write_text(json.dumps({'schema_version':1,'version':'0.1.0','language':'en',
        'source_files':sources,'source_records':records,'canonical_entries':len(entries),
        'policy':'Source-backed names take precedence; provisional names and unknown traits remain marked.',
        'entries':entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
