"""Export English-only translation copies. Dry-run is the default.

Japanese names and UI terms belong in the separately maintained glossary.
Source text never enters the exported translation files.
"""
import argparse, json, pathlib, re

JP = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uff66-\uff9d]')
SAFE_FIELDS = ('id', 'file', 'offset', 'byte_length', 'encoding', 'category',
               'speaker_id', 'target', 'status', 'notes', 'context', 'decisions',
               'source_omission_preserved', 'native_index')

def export(data):
    rows = data if isinstance(data,list) else data['rows']
    clean=[]
    for row in rows:
        item={k:row[k] for k in SAFE_FIELDS if k in row}
        for key,value in item.items():
            if isinstance(value,str) and JP.search(value):
                raise ValueError(f"Japanese remains in {row.get('id')}, field {key}; use English notes/IDs")
        clean.append(item)
    return {'schema_version':1, 'language':'en', 'rows':clean}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('paths',nargs='*',default=[])
    p.add_argument('--write',action='store_true')
    p.add_argument('--filled-only',action='store_true',help='Export only batches containing at least one draft')
    a=p.parse_args()
    paths=[pathlib.Path(x) for x in a.paths] if a.paths else sorted(pathlib.Path('work/translation/en').rglob('*.json'))
    paths=[x for x in paths if not x.name.endswith('.en.json')]
    for path in paths:
        working=json.loads(path.read_text(encoding='utf-8-sig'))
        if a.filled_only and not any(r.get('target') for r in (working if isinstance(working,list) else working['rows'])):
            continue
        data=export(working)
        dest=path.with_name(path.stem+'.en.json')
        print(json.dumps({'input':str(path),'output':str(dest),'rows':len(data['rows']),
                          'translated':sum(bool(x.get('target')) for x in data['rows']),
                          'sample':data['rows'][:2]},ensure_ascii=True))
        if a.write: dest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__': main()
