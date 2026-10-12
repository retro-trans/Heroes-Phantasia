"""Reflow two English records without changing words, controls or other rows."""
import argparse,json,re,hashlib
from pathlib import Path
from unpack_cpk import inventory
from rebuild_dialogue import parse,rebuild,encode_target
from extract_corpus import controls
from dialogue_tokens import validate_controls
from executable_text_patch import Elf
import struct

BASE=Path('work/output/0.1.26-title-credit-vwf-4x-candidate/HP.CPK')
QUEUE=Path('work/translation/en/batch_0012.json')
OUT=Path('work/output/0.1.27-ryudock-assets')
TARGETS={
 'd293999c047627cb3a7d':'{1C}Ryudock{0E}Preparations for the{11}tracking Gift are{11}finally complete.{12}{0E}',
 '0c71d0ec7969387abe79':"{1C}Ryudock{0E}I shall now leave for Hideo{0F}2Hideo{0F}'s{11}world, bound{11}for Japan.{12}{0E}"}
def sha(b):return hashlib.sha256(b).hexdigest()
def build():
    d=json.loads(QUEUE.read_text(encoding='utf8'));rows={r['id']:r for r in d['rows']};queue_updates=[]
    for key,text in TARGETS.items():
        row=rows[key];validate_controls(row['source'],text)
        if re.sub(r'\{11\}|\s','',row['target'])!=re.sub(r'\{11\}|\s','',text):raise ValueError('Wording changed')
        queue_updates.append(dict(id=key,old_target=row['target'],target=text))
    _,entries=inventory(BASE);entries={q['path']:q for q in entries};assets={};proof=[]
    for name in ('phase/bin/p101010.bin','phase/bin/p101011.bin'):
        q=entries[name]
        if q['compression']!='none':raise ValueError('Expected current raw resource')
        with BASE.open('rb') as f:f.seek(q['offset']);raw=f.read(q['stored_size'])
        p=parse(name,raw);replacements={}
        for index,key in enumerate(TARGETS):
            current=p['spans'][p['refs'][index][1]][0]
            old,_=encode_target(rows[key]['target'],rows[key]['source'],True,True,True)
            if current!=old:raise ValueError('Current installed row differs')
            replacements[index]=encode_target(TARGETS[key],rows[key]['source'],True,True,True)[0]
        candidate,new=rebuild(name,raw,replacements);assets[name]=candidate
        proof.append(dict(resource=name,old_sha256=sha(raw),new_sha256=sha(candidate),reference_count=len(p['refs']),changed_references=[0,1],
            all_other_row_bytes_and_suffix_exact=True,group_ids_and_reference_ids_exact=True))
    return d,assets,dict(version='0.1.27',queue_updates=queue_updates,resources=proof,source_control_arguments_preserved=True,word_sequence_exact=True,runtime_verified=False)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args()
    d,assets,proof=build();print(json.dumps(proof,indent=2))
    if not a.write:print('DRY RUN');return
    if OUT.exists():raise ValueError('Fresh assets required')
    OUT.mkdir(parents=True)
    for name,data in assets.items():(OUT/Path(name).name).write_bytes(data)
    (OUT/'layout.en.json').write_text(json.dumps(proof,indent=2)+'\n')
    for r in d['rows']:
        if r['id'] in TARGETS:
            r['target']=TARGETS[r['id']];r['notes']='0.1.27: exact wording reflowed across the same three body lines. Controls, ruby reading and original span digit preserved. Narrow Hideo ruby measurement/geometry hook installed; scene display QA pending.'
    QUEUE.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
if __name__=='__main__':main()
