import argparse,copy,json,math
from pathlib import Path
import dialogue_layout_guard as g
import prepare_dialogue_guard_055 as old
from rebuild_dialogue import parse,rebuild
from field_ui_patch import notation
from strip_jp import export
from append_cpk import main as append_main
BASE=Path('work/output/0.1.58-title-credit-vwf-4x-candidate')
OUT=Path('work/output/0.1.59-name-dialogue-assets')
UI=Path('work/ui/dialogue/0.1.59')

def accepts(r,pages):
    if sum(len(p['line_advances'])for p in pages)>32 or any(len(bytes.fromhex(p['body_hex']))>1024 for p in pages):return False
    if g.fallback_fit(r['shape'],pages):return True
    return all(g.ray_fit(r['shape'],k[1:3],h,len(p['line_advances'])) or g.fallback_fit(r['shape'],pages,h) for p in pages for k in r['position_keys'] if k[1:3] not in ((0.,0.),[0.,0.]) for h in g.parent_halves(pages))

def reflow(text,r,widths):
    advance,accept=old.advance,old.accepts
    try:
        old.advance=lambda ts,w:sum(g.token_advance(t,w,True)for t in ts)
        old.accepts=accepts
        # Every literal uses the native advance across the whole owner when
        # even one row contains a runtime name and rejects the VWF pass.
        return old.reflow(text,r,[13 if n>=32 else 0 for n in range(len(widths))])
    finally:old.advance,old.accepts=advance,accept

def build():
    from build_local import sha as file_sha
    m=json.loads((BASE/'manifest.en.json').read_bytes())
    if file_sha(BASE/'HP.CPK')!=m['dialogue_cpk_sha256'] or file_sha(BASE/'EBOOT.BIN')!=m['setup_patch']['output_sha256']:raise ValueError('Frozen .58 input differs')
    limits=m['setup_patch']['default_name_storage']['osk_character_limits']
    if [limits[x]for x in ('female_surname','female_given_name','title','other')]!=list(g.NAME_LIMITS.values()):raise ValueError('Reviewed saved-name limits differ')
    audit=g.audit(BASE/'HP.CPK',BASE/'EBOOT.BIN');selected={}
    for r in audit['records']:
        if r['status']=='overflow':selected.setdefault(r['resource'],[]).append(r)
    widths=g.widths_from(BASE/'EBOOT.BIN');assets={};records=[];blocked=[];queue=[]
    for name,raw in g.resources(BASE/'HP.CPK'):
        if name not in selected:continue
        p=parse(name,raw);by_offset={};replacements={}
        for r in selected[name]:
            n=r['reference_index'];off=p['refs'][n][1];text=p['spans'][off][0]
            try:new,details=reflow(text,r,widths)
            except ValueError as ex:blocked.append(dict(resource=name,reference_index=n,reason=str(ex)));continue
            if off in by_offset and by_offset[off]!=new:raise ValueError('Shared owner needs common layout: '+name)
            by_offset[off]=new
            records.append(dict(resource=name,reference_index=n,shape=r['shape'],old_parent_width=r['parent_maximum_width'],measurement_policy=r['measurement_policy'],old_english=notation(text),new_english=notation(new),**details,custom_names_and_control_order_exact=True,authored_tail_and_tracks_exact=True,natural_playback_verified=False))
            queue.append(dict(id=f'name_guard_059_{Path(name).stem}_{n}',file=name,category='name_substitution_dialogue_layout',target=notation(new),status='translated',notes='Whole-owner native width fallback and saved-name capacity bounds; substitutions, ruby and authored speaker anchor preserved.'))
        for n,(_,off)in enumerate(p['refs']):
            if off in by_offset:replacements[n]=by_offset[off]
        if not replacements:continue
        changed,np=rebuild(name,raw,replacements)
        if raw[p['head'][0]:p['start']]!=changed[np['head'][0]:np['start']] or raw[p['end']:]!=changed[np['end']:]:raise ValueError('Authored tracks/suffix changed')
        for n,(_,off)in enumerate(p['refs']):
            if n not in replacements and p['spans'][off][0]!=np['spans'][np['refs'][n][1]][0]:raise ValueError('Unselected text differs')
        assets[name]=changed
    after=g.audit(BASE/'HP.CPK',BASE/'EBOOT.BIN',assets)
    return m,assets,records,audit,after,blocked,dict(schema_version=1,language='en',rows=queue)

def main():
    a=argparse.ArgumentParser();a.add_argument('--write',action='store_true');opts=a.parse_args();m,assets,records,before,after,blocked,queue=build()
    print(json.dumps(dict(version='0.1.59',before=before['counts'],after=after['counts'],resources=len(assets),reflows=len(records),extra_pages=sum(r['extra_pages']for r in records),blocked=blocked),indent=2))
    if not opts.write:return
    # The inherited exception set already contains these unchanged layouts.
    # Some atomic maximum-length names cannot fit the authored native style.
    # Retain those exact inputs explicitly as risks, never call them fitted.
    if after['counts']['overflow']!=len(blocked):raise ValueError('Unexpected unresolved layout')
    if OUT.exists():raise ValueError('Fresh output required')
    OUT.mkdir(parents=True);UI.mkdir(parents=True,exist_ok=True)
    for name,raw in assets.items():
        p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    report=copy.deepcopy(m['setup_patch']);exe=(BASE/'EBOOT.BIN').read_bytes();(OUT/'EBOOT.BIN').write_bytes(exe)
    proof=dict(version='0.1.59',source_version='0.1.58',records=records,selected_assets=[dict(resource=n,sha256=g.sha(b),bytes=len(b))for n,b in assets.items()],before_counts=before['counts'],after_counts=after['counts'],retained_maximum_name_risks=blocked,name_selector_limits={k.decode():v for k,v in g.NAME_LIMITS.items()},measurement='Native 13px layout fallback across all rows when a 01 name is present; whole-owner minimum/maximum bounds and every 13px parent width tested.',font_and_geometry_code_exact=True,loaded_growth_bytes=0,natural_playback_verified=False)
    report.update(version='0.1.59',input_version='0.1.58',input_sha256=g.sha(exe),output_sha256=g.sha(exe),output_elf_sha256=g.sha(exe));report['name_dialogue_059']=proof
    (OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');(UI/'preparation.en.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    # Only inputs already explicitly unverified in .58 may stay excepted.
    baseline=json.loads(Path('work/ui/dialogue/0.1.58/layout_exceptions.en.json').read_bytes());known={g.exception_key(v)for v in baseline['records']}
    unknown=[{k:r.get(k)for k in ('resource','reference_index','text_sha256','geometry_sha256','reason')}for r in after['records'] if r['status']=='unverified']
    if any(g.exception_key(v)not in known for v in unknown):raise ValueError('New unknown layouts need review')
    prior={(v['resource'],v['reference_index'],v['text_sha256'],v['geometry_sha256'])for v in baseline['records']}
    risks=[{k:r.get(k)for k in ('resource','reference_index','text_sha256','geometry_sha256','parent_maximum_width','measurement_policy')} for r in after['records'] if r['status']=='overflow']
    if any((v['resource'],v['reference_index'],v['text_sha256'],v['geometry_sha256'])not in prior for v in risks):raise ValueError('New maximum-name risk cannot inherit an exception')
    (UI/'layout_exceptions.en.json').write_text(json.dumps(dict(version='0.1.59',name_selector_limits=proof['name_selector_limits'],runtime_contract=g.runtime_contract(BASE/'EBOOT.BIN'),scope='Only unchanged previously excepted inputs may remain unverified. Maximum-name risks are explicitly unsafe at some permitted name lengths; none is certified fitted.',records=unknown,retained_maximum_name_risks=risks),indent=2)+'\n')
    p=Path('work/translation/en/name_dialogue_059.json');p.write_text(json.dumps(queue,indent=2)+'\n');p.with_suffix('.en.json').write_text(json.dumps(export(queue),indent=2)+'\n')
    import sys
    sys.argv=['append','--archive',str(BASE/'HP.CPK'),'--expected-sha256',m['dialogue_cpk_sha256'],'--version','0.1.59','--output',str(OUT/'HP.CPK'),'--write']
    for name in assets:sys.argv+=['--replace',name+'='+str(OUT/name)]
    append_main()
if __name__=='__main__':main()
