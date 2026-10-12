"""Apply a reviewed row-for-row English draft, after a mandatory dry run."""
import argparse, json, pathlib, re
from dialogue_tokens import validate_controls, control_arguments

TOKENS=re.compile(r'\{[0-9A-F]{2}\}')
class _ArgumentCompatibility:
    """Legacy metadata import; validation uses the atomic parser directly."""
    findall = staticmethod(control_arguments)
ARGS = _ArgumentCompatibility()
JP=re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uff66-\uff9d]')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('batch',type=pathlib.Path);p.add_argument('draft',type=pathlib.Path)
    p.add_argument('--write',action='store_true');a=p.parse_args()
    data=json.loads(a.batch.read_text(encoding='utf-8'));draft=json.loads(a.draft.read_text(encoding='utf-8'))
    if len(data['rows'])!=len(draft['targets']):raise ValueError('Row count mismatch')
    for i,(row,target) in enumerate(zip(data['rows'],draft['targets'])):
        try:validate_controls(row['source'],target)
        except ValueError as error:raise ValueError(f'Control mismatch row {i}: {error}') from error
        if JP.search(target):raise ValueError(f'Japanese in target row {i}')
        row.update(target=target,status='draft',context=draft['context'],decisions=draft.get('decisions',{}).get(str(i),'Full English draft; original row and control sequence preserved.'))
    print(json.dumps({'rows':len(data['rows']),'sample':[{k:r[k] for k in ('id','target','decisions')} for r in data['rows'][:4]]},indent=2))
    if a.write:a.batch.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:print('DRY RUN: no changes written.')

if __name__=='__main__':main()
