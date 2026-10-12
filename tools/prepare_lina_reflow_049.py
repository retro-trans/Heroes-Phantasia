"""Install the native-tested six-line Lina reflow; dry before guarded writing."""
import argparse,copy,json
from pathlib import Path
from prepare_bubble_scenes_036 import read,sha
from rebuild_dialogue import parse,rebuild
from dialogue_tokens import tokenize_bytes
from strip_jp import export

BASE=Path('work/output/0.1.48-title-credit-vwf-4x-candidate')
OUT=Path('work/output/0.1.49-dialogue-command-assets')
EXE_SHA='5b2fc12a78052c40aa1d499976680b566d2f43ce508ac9d3a58853f814ce3c2f'

def notation(b):return ''.join('{%02X}'%c if c<32 else chr(c)for c in b)

def build():
    m=json.loads((BASE/'manifest.en.json').read_text());e=(BASE/'EBOOT.BIN').read_bytes()
    if sha(e)!=EXE_SHA:raise ValueError('Reviewed command/ruby executable differs')
    proof=json.loads(Path('work/ui/dialogue/0.1.48/lina_six_line_proposal.en.json').read_text())
    if proof['candidate_sha256']!=EXE_SHA or proof['loaded_iso_sha256']!=m['iso_sha256']or len(proof['cases'])!=1 or not proof['cases'][0]['passed']:raise ValueError('Native six-line preparation proof differs')
    oldrows=m['setup_patch']['dialogue_commands_048']['reflows'];assets={};records=[]
    new=b'\x1cLina\x0eAll right, descendant\x11of the hero\x0f2hero\x0f!\x11Now that this\x11beautiful genius\x11sorceress is here,\x11your troubles are over!\x12\x0e'
    for name,raw in read(BASE/'HP.CPK',[r['resource']for r in oldrows]).items():
        p=parse(name,raw);old=p['spans'][p['refs'][0][1]][0]
        expected=next(r['new_english'].encode('ascii')for r in oldrows if r['resource']==name)
        if old!=expected or old.replace(b'\x11',b' ')!=new.replace(b'\x11',b' '):raise ValueError('English words changed')
        signature=lambda s:[(t.kind,t.code,t.argument)for t in tokenize_bytes(s,True)if t.kind!='latin'and t.code!=17]
        if signature(old)!=signature(new):raise ValueError('Nonline controls changed')
        changed,np=rebuild(name,raw,{0:new})
        if raw[p['head'][0]:p['start']]!=changed[np['head'][0]:np['start']]or raw[p['end']:]!=changed[np['end']:]:raise ValueError('Authored tracks changed')
        if any(p['spans'][off][0]!=np['spans'][np['refs'][ix][1]][0]for ix,(_,off)in enumerate(p['refs'])if ix):raise ValueError('Other rows changed')
        assets[name]=changed;records.append(dict(resource=name,reference_index=0,new_english=new.decode('ascii'),old_english=old.decode('ascii'),line_advances=[133,75,86,105,113,146],input_sha256=sha(raw),output_sha256=sha(changed),words_and_nonline_controls_exact=True,authored_tracks_and_other_rows_exact=True))
    report=copy.deepcopy(m['setup_patch']);report.update(version='0.1.49',input_version='0.1.48',input_sha256=EXE_SHA,runtime_verified=False,status='dialogue_commands_native_prepared_candidate')
    report['lina_reflow_049']=dict(records=records,native_preparation_proof='work/ui/dialogue/0.1.48/lina_six_line_proposal.en.json',natural_gameplay_verified=False)
    report['dialogue_commands_048']['reflows_superseded_by']='lina_reflow_049'
    q=Path('work/translation/en/batch_0017.json');queue=json.loads(q.read_text(encoding='utf8'));row=next(r for r in queue['rows']if r['id']=='cb478b9706bf7e3387f8')
    if row['target']not in (notation(oldrows[0]['new_english'].encode('ascii')),notation(new)):raise ValueError('Logical translation differs')
    row['target']=notation(new);row['notes']+=' 0.1.49: Six-line reflow replaces the rejected four-line candidate. Native polygon, sloping interior, preserved tail ray/endpoint and repeat-draw tests pass in isolated preparation; natural scene playback remains unverified.'
    return e,report,assets,queue

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--write',action='store_true');ap.add_argument('--expected-sha256');a=ap.parse_args();e,report,assets,queue=build()
    print(json.dumps(dict(version='0.1.49',executable_sha256=sha(e),reflows=report['lina_reflow_049']['records']),indent=2))
    if not a.write:print('DRY RUN');return
    if a.expected_sha256!=sha(e)or OUT.exists():raise ValueError('Reviewed digest and fresh folder required')
    clean=export(queue);OUT.mkdir(parents=True);(OUT/'EBOOT.BIN').write_bytes(e);(OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,raw in assets.items():
        dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    q=Path('work/translation/en/batch_0017.json');q.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8');q.with_suffix('.en.json').write_text(json.dumps(clean,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
