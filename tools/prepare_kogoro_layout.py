"""Reflow the reported Kogoro record in both variants; dry-run then write."""
import argparse,json,struct
from pathlib import Path
from unpack_cpk import inventory
from rebuild_dialogue import parse,rebuild,encode_target
from dialogue_tokens import tokenize_bytes,validate_controls
from executable_text_patch import Elf
from prepare_english_bubbles import SOURCE,sha
from english_word_wrap import wrap_body

BASE=Path('work/output/0.1.32-title-credit-vwf-4x-candidate/HP.CPK')
QUEUE=Path('work/translation/en/batch_0014.json')
OUT=Path('work/output/0.1.33-kogoro-layout-assets')
ID='44ee2e2ade329840340c'
OLD="{1C}Kogoro{0E}If you're in HOLY,{11}then you must be an {05}050{16}03Alter user{16}01,{11}too!{12}{0E}"
TARGET="{1C}Kogoro{0E}If you're in HOLY,{11}then you must be an{11}{05}050{16}03Alter user{16}01, too!{12}{0E}"

def build():
    queue=json.loads(QUEUE.read_text(encoding='utf8'));row=next(r for r in queue['rows']if r['id']==ID)
    # Reflow intentionally moves only the line-break markers across styling.
    # Validate every other marker and argument in its original order.
    validate_controls(row['source'].replace('{11}',''),TARGET.replace('{11}',''))
    if row['target']not in (OLD,TARGET):raise ValueError('Selected working translation changed')
    old=encode_target(OLD,row['source'],True,True,True)[0]
    target=encode_target(TARGET,TARGET,True,True,True)[0]
    visible=lambda raw:b''.join(t.data for t in tokenize_bytes(raw,True)if t.kind=='latin'and t.code!=32)
    if visible(old)!=visible(target):raise ValueError('Spoken words or punctuation changed')
    blob=SOURCE.read_bytes();meta=json.loads(SOURCE.with_name('executable.en.json').read_text());e=Elf(blob)
    widths=struct.unpack('<131I',blob[e.file_offset(meta['body_integer_lut_rva'],524):][:524])
    body=target.split(b'\x0e',1)[1];tokens=tokenize_bytes(body,True);advances=[0]
    for t in tokens:
        if t.kind=='latin':advances[-1]+=widths[t.code]
        elif t.code==0x11:advances.append(0)
    if advances!=[111,132,95]or max(advances)>180:raise ValueError('Reviewed native line advances differ')
    automatic=wrap_body(old.split(b'\x0e',1)[1],widths)
    if not automatic['supported']:raise ValueError('Generic token-aware wrapping rejects selected body')
    _,entries=inventory(BASE);entries={r['path']:r for r in entries};assets={};rows=[]
    for name in ('phase/bin/p101040.bin','phase/bin/p101041.bin'):
        r=entries[name]
        if r['compression']!='none':raise ValueError('Expected current raw phase')
        with BASE.open('rb')as f:f.seek(r['offset']);raw=f.read(r['stored_size'])
        p=parse(name,raw)
        if p['spans'][p['refs'][12][1]][0]!=old:raise ValueError('Current selected record differs')
        changed,new=rebuild(name,raw,{12:target});assets[name]=changed
        for n,ref in enumerate(p['refs']):
            if n!=12 and p['spans'][ref[1]][0]!=new['spans'][new['refs'][n][1]][0]:raise ValueError('Unselected record changed')
        rows.append(dict(resource=name,reference_index=12,reference_count=len(p['refs']),source_sha256=sha(raw),
            output_sha256=sha(changed),all_other_records_exact=True,event_data_and_suffix_preserved=True))
    return queue,assets,dict(version='0.1.33',record_id=ID,old_target=OLD,target=TARGET,
        line_advances_px=advances,all_words_and_non_boundary_controls_preserved=True,highlight_and_timing_preserved=True,
        resources=rows,automatic_wrap_proposal_pages=automatic['pages'],
        layout_choice='Reviewed three-line phrase boundaries retain the opening clause and highlighted Alter user phrase.',natural_scene_verified=False)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');a=ap.parse_args()
    q,assets,p=build();print(json.dumps(p,indent=2))
    if not a.write:print('DRY RUN');return
    if OUT.exists():raise ValueError('Fresh output required')
    OUT.mkdir(parents=True)
    for name,raw in assets.items():(OUT/Path(name).name).write_bytes(raw)
    (OUT/'layout.en.json').write_text(json.dumps(p,indent=2)+'\n',encoding='utf8')
    row=next(r for r in q['rows']if r['id']==ID);row['target']=TARGET
    row['notes']='0.1.33: reviewed three-line English layout; unchanged words, color span, timing argument and page boundaries. Custom polygon/native instruction checks are separate from natural scene QA.'
    QUEUE.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for name,raw in assets.items():
        if (OUT/Path(name).name).read_bytes()!=raw:raise ValueError('Phase write/readback differs')
if __name__=='__main__':main()
