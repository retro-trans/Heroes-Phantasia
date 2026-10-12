"""Audit the staged public Git snapshot; read-only unless --write is requested."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path

BANNED={'.iso','.cso','.pbp','.cpk','.bin','.elf','.pmf','.png','.jpg','.jpeg','.ttf','.otf','.zip','.xdelta','.exe','.dll','.ppst','.dmp','.pyc'}
JP=re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uff66-\uff9d]')
TOKEN=re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{30,})\b')

def audit():
    raw=subprocess.check_output(['git','ls-files','--stage','-z'])
    rows=[];errors=[];english_rows=0
    for record in raw.decode('utf8').split('\0'):
        if not record:continue
        meta,name=record.split('\t',1);mode,blob,stage=meta.split();path=Path(name)
        if stage!='0' or mode not in ['100644','100755']:errors.append(name+': unsupported index entry')
        if path.suffix.lower() in BANNED or name.startswith(('work/source/','work/output/','work/local/','incoming/')):
            errors.append(name+': private/game asset staged')
        b=subprocess.check_output(['git','cat-file','blob',blob])
        try:text=b.decode('utf-8-sig')
        except UnicodeDecodeError:errors.append(name+': non-UTF8 source');continue
        if '\0' in text:errors.append(name+': binary content')
        if TOKEN.search(text):errors.append(name+': possible credential')
        if name.startswith('work/translation/'):
            if not name.endswith('.en.json'):errors.append(name+': working translation staged')
            if JP.search(text):errors.append(name+': Japanese remains in English export')
            data=json.loads(text);english_rows+=len(data['rows'])
            if any('source' in row for row in data['rows']):errors.append(name+': Japanese source field staged')
        rows.append(dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    if not rows:errors.append('Git index is empty')
    if errors:raise ValueError('\n'.join(errors))
    return dict(schema_version=1,status='public_source_index_audit_passed',files=len(rows),bytes=sum(r['bytes'] for r in rows),
        english_translation_rows=english_rows,game_assets_dumps_private_inputs_excluded=True,
        English_exports_without_Japanese_or_source_fields=True,credential_pattern_check_passed=True,
        Japanese_names_and_UI_terms_allowed=True,index_entries=rows)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--output',type=Path,default=Path('docs/releases/0.1.45/public-source-audit.en.json'));a=p.parse_args()
    report=audit();print(json.dumps({k:v for k,v in report.items() if k!='index_entries'},indent=2))
    print('Sample staged paths:',[r['path'] for r in report['index_entries'][:8]])
    if a.write:
        dest=a.output
        if dest.exists():raise ValueError('Fresh audit output required')
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    else:print('DRY RUN: no evidence writes.')

if __name__=='__main__':main()
