"""Inventory original CPL byte-string name blocks; dry by default.

Name-index0 has a proven HUD selector. Later entries remain candidate action
labels until their consumers are established. No asset modification occurs.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct


def sha(raw):return hashlib.sha256(raw).hexdigest()


def extract():
    root=Path('work/source/cpk');inventory=json.loads(Path('work/source/cpk_inventory.json').read_text(encoding='utf8'))
    originals={e['path']:e for e in inventory['entries']};rows=[];files=[]
    for path in sorted((root/'btl/cpl').glob('*.bin')):
        name=path.relative_to(root).as_posix();raw=path.read_bytes();expected=originals[name]
        if sha(raw)!=expected['sha256'] or len(raw)!=expected['extract_size']:raise ValueError('Original source SHA/size differs')
        h=struct.unpack_from('<12I',raw);start,end=h[1:3]
        if not 48<=start<end<=len(raw):raise ValueError('Unknown CPL name bounds')
        body=raw[start:end];trimmed=body.rstrip(b'\0')
        if not trimmed:raise ValueError('Empty CPL name block')
        entries=trimmed.split(b'\0');cursor=start
        for i,entry in enumerate(entries):
            source=entry.decode('cp932',errors='strict')
            if not source or any(ord(c)<32 for c in source):raise ValueError('Unexpected CPL text/control')
            terminated=entry+b'\0'
            if raw[cursor:cursor+len(terminated)]!=terminated:raise ValueError('CPL occurrence bounds differ')
            rows.append({'id':'cpl_'+sha(terminated)[:20],'file':name,'row_index':i,'offset':cursor,'byte_length':len(terminated),'encoding':'cp932-nul','source':source,'category':'battle_entity_name' if i==0 else 'battle_action_label_candidate','original_bytes_sha256':sha(terminated),'structure':{'name_pointer_field':4,'name_section_start':start,'name_section_end':end,'selector':'0x978d8 index0 via0xb06bc' if i==0 else 'unproved'},'target':'','status':'untranslated'})
            cursor+=len(terminated)
        if any(raw[cursor:end]):raise ValueError('Nonzero CPL block suffix')
        files.append({'resource':name,'sha256':sha(raw),'bytes':len(raw),'name_start':start,'name_end':end,'references':len(entries),'padding_bytes':end-cursor,'identity_reparse_passed':True})
    groups=collections.OrderedDict()
    # Place the proven display-name slice first; deduplicate strings shared
    # between name0 and later entries without double-counting their identity.
    for row in sorted(rows,key=lambda r:(r['row_index']!=0,r['file'],r['row_index'])):
        if row['id'] not in groups:
            groups[row['id']]={**row,'occurrences':[]}
        groups[row['id']]['occurrences'].append({k:row[k] for k in ['file','row_index','offset','byte_length','original_bytes_sha256','structure']})
    queue=list(groups.values());first_ids={r['id'] for r in rows if r['row_index']==0};later_ids={r['id'] for r in rows if r['row_index']>0}
    return {'schema_version':1,'files':files,'occurrences':rows,'rows':queue,'summary':{'files':len(files),'occurrences':len(rows),'unique_rows':len(queue),'name0_unique':len(first_ids),'later_unique':len(later_ids),'name0_later_overlap':len(first_ids&later_ids),'name0_proven_selector':True,'later_selector_proven':False,'runtime_verified':False}}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args();d=extract()
    print(json.dumps(d['summary'],indent=2));print('SAMPLE',json.dumps([{k:v for k,v in r.items() if k not in ['source','occurrences']} for r in d['rows'][:3]],indent=2))
    if not a.write:print('DRY RUN: no files written.');return
    destination=Path('work/source/cpl_text_inventory.json')
    if destination.exists():raise ValueError('Fresh inventory required')
    targets=Path('work/translation/en');paths=[targets/f'cpl_{i//80+1:04}.json' for i in range(0,len(d['rows']),80)]
    if any(path.exists() for path in paths):raise ValueError('Fresh CPL queue required')
    destination.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for i,path in zip(range(0,len(d['rows']),80),paths):
        path.write_text(json.dumps({'schema_version':1,'language':'en','rows':d['rows'][i:i+80]},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Wrote original evidence and',len(paths),'ignored working batches; no asset changes.')


if __name__=='__main__':main()
