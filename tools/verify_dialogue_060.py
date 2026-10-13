"""Read back duplicate-ruby cleanup, name layouts, native widths and ISO assets."""
import json,struct,tempfile
from pathlib import Path
import dialogue_layout_guard as g
from dialogue_tokens import tokenize_bytes
from prepare_dialogue_060 import remove_duplicate_ruby
from prepare_bubble_scenes_036 import read
from rebuild_dialogue import parse
from unpack_cpk import inventory
from inspect_iso import inventory as iso_inventory
from build_local import sha as file_sha
from title_stamp import prepare as title_prepare,RESOURCE
from executable_text_patch import Elf
from dialogue_measure_1a import instruction_cases

ROOT=Path('work/output/0.1.60-title-credit-vwf-4x-candidate')
BASE=Path('work/output/0.1.59-title-credit-vwf-4x-candidate')
ASSETS=Path('work/output/0.1.60-dialogue-assets-final')
UI=Path('work/ui/dialogue/0.1.60')

def main():
    m=json.loads((ROOT/'manifest.en.json').read_bytes());prep=m['setup_patch'];proof=prep['duplicate_ruby_060'];data=(ROOT/'EBOOT.BIN').read_bytes()
    if data!=(ASSETS/'EBOOT.BIN').read_bytes():raise ValueError('Prepared executable differs')
    assets={r['resource']:(ASSETS/r['resource']).read_bytes() for r in proof['selected_assets']}
    installed=read(ROOT/'HP.CPK',list(assets));original=read(BASE/'HP.CPK',list(assets))
    if installed!=assets:raise ValueError('Installed selected assets differ')
    parsed={n:parse(n,b) for n,b in installed.items()};oldparsed={n:parse(n,b) for n,b in original.items()}
    for name,raw in installed.items():
        op,p=oldparsed[name],parsed[name]
        if original[name][op['head'][0]:op['start']]!=raw[p['head'][0]:p['start']] or original[name][op['end']:]!=raw[p['end']:]:raise ValueError('Authored tracks/suffix changed')
    normal=lambda b:b''.join(t.data for t in tokenize_bytes(b,True) if t.kind!='ruby_open' and not t.ruby)
    removed=0;duplicate_left=0
    for r in proof['records']:
        name,n=r['resource'],r['reference_index'];op,p=oldparsed[name],parsed[name]
        old=op['spans'][op['refs'][n][1]][0];new=p['spans'][p['refs'][n][1]][0];expected,spans=remove_duplicate_ruby(old)
        if expected!=new or normal(old)!=normal(new):raise ValueError('Ruby cleanup changed main text or other controls')
        removed+=len(spans)
    if removed!=615:raise ValueError('Unexpected duplicate-reading count')
    for name,raw in g.resources(ROOT/'HP.CPK'):
        try:p=parse(name,raw)
        except ValueError:continue
        for _,off in p['refs']:
            try:_,spans=remove_duplicate_ruby(p['spans'][off][0]);duplicate_left+=len(spans)
            except ValueError:continue
    if duplicate_left:raise ValueError('Duplicate ASCII readings remain')
    for name in ('phase/bin/p101080.bin','phase/bin/p101081.bin'):
        p=parsed[name];text=p['spans'][p['refs'][29][1]][0]
        if b'Ryuho!' not in text or b'\x0f' in text:raise ValueError('Reported Ryuho line differs')
    # Verify the combined .59 name reflows against .58, allowing only the
    # specifically reviewed duplicate-reading removal after rewrapping.
    records=prep['name_dialogue_059']['records'];names=list(dict.fromkeys(r['resource'] for r in records));new_names=read(ROOT/'HP.CPK',names)
    old_names=read(Path('work/output/0.1.58-title-credit-vwf-4x-candidate/HP.CPK'),names)
    widths=g.widths_from(ROOT/'EBOOT.BIN');samples={};modeled_widths=0
    strip=lambda b:bytes(v for v in normal(b) if v not in (32,0x10,0x11,0x12))
    for r in records:
        name,n=r['resource'],r['reference_index'];p=parse(name,new_names[name]);op=parse(name,old_names[name]);text=p['spans'][p['refs'][n][1]][0]
        if strip(text)!=strip(op['spans'][op['refs'][n][1]][0]):raise ValueError('Name reflow altered words or semantic controls')
        if old_names[name][op['head'][0]:op['start']]!=new_names[name][p['head'][0]:p['start']]:raise ValueError('Name scene/tail tracks changed')
        item=g.inspect(name,new_names[name],p,n,widths)
        if item['status']!='fit':raise ValueError('Combined name owner does not fit')
        modeled_widths+=len(g.parent_halves(item['pages']))
        rows=[]
        for page in text.split(b'\x0e',1)[1].split(b'\x0e',1)[0].split(b'\x10'):rows.extend(line+b'\x12' for line in page.split(b'\x12',1)[0].split(b'\x11'))
        samples[tuple(rows)]=(rows,False)
    for selector in range(4):
        name=b'\x01'+str(selector).encode()
        for rows in ([name+b'\x12',b'Plain later page\x12'],[b'Plain earlier page\x12',name+b'\x12']):samples[tuple(rows)]=(rows,False)
    for r in proof['records']:
        p=parsed[r['resource']];text=p['spans'][p['refs'][r['reference_index']][1]][0]
        body=text.split(b'\x0e',1)[1] if b'\x0e' in text else text
        item=g.inspect(r['resource'],installed[r['resource']],p,r['reference_index'],widths)
        if not item or item['status']!='fit':continue
        rows=[]
        for page in body.split(b'\x0e',1)[0].split(b'\x10'):rows.extend(line+b'\x12' for line in page.split(b'\x12',1)[0].split(b'\x11'))
        samples[tuple(rows)]=(rows,item['measurement_policy']=='installed_vwf')
    e=Elf(data);at=e.file_offset(0x16fa8f0);native=bytearray(data[at:at+1064]);struct.pack_into('<II',native,96,0x3c0e0024,0x25ce0000)
    cases=instruction_cases(widths,bytes(native),list(samples.values()));guard=g.enforce(ROOT/'HP.CPK',ROOT/'EBOOT.BIN')
    ledger=json.loads(g.EXCEPTIONS.read_bytes())
    with tempfile.TemporaryDirectory(prefix='dialogue060-') as scratch:
        altered=json.loads(g.EXCEPTIONS.read_bytes());altered['name_selector_limits']['1']=16;path=Path(scratch)/'ledger.en.json';path.write_text(json.dumps(altered))
        try:g.enforce(ROOT/'HP.CPK',ROOT/'EBOOT.BIN',path)
        except ValueError as ex:
            if 'measurement policy differs' not in str(ex):raise
        else:raise ValueError('Name capacity change bypassed guard')
        altered=json.loads(g.EXCEPTIONS.read_bytes());altered['retained_maximum_name_risks'][0]['text_sha256']='0'*64;path.write_text(json.dumps(altered))
        try:g.enforce(ROOT/'HP.CPK',ROOT/'EBOOT.BIN',path)
        except ValueError as ex:
            if 'rejected 1 references' not in str(ex):raise
        else:raise ValueError('Maximum-name risk fingerprint bypassed guard')
        wrong=bytearray(data);wrong[e.file_offset(616940)]^=1;path=Path(scratch)/'wrong.elf';path.write_bytes(wrong)
        try:g.enforce(ROOT/'HP.CPK',path)
        except ValueError as ex:
            if 'native geometry changed' not in str(ex):raise
        else:raise ValueError('Corner helper change bypassed guard')
    _,before=inventory(BASE/'HP.CPK');_,after=inventory(ROOT/'HP.CPK');changed={a['path'] for a,b in zip(before,after) if a!=b}
    if len(before)!=len(after) or changed!=set(assets)|{RESOURCE}:raise ValueError('Unselected archive entries differ')
    title,*_=title_prepare(m['config']);assets[RESOURCE]=title
    if read(ROOT/'HP.CPK',[RESOURCE])[RESOURCE]!=title:raise ValueError('Title version differs')
    entries=iso_inventory(Path(m['iso_path']));exe=next(v for v in entries if v['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');cpk=next(v for v in entries if v['path']=='PSP_GAME/USRDIR/HP.CPK')
    with Path(m['iso_path']).open('rb') as stream:
        stream.seek(exe['offset'])
        if stream.read(exe['size'])!=data:raise ValueError('Nested executable differs')
        for name,raw in assets.items():
            entry=next(v for v in after if v['path']==name);stream.seek(cpk['offset']+entry['offset'])
            if entry['compression']!='none' or stream.read(len(raw))!=raw:raise ValueError('Nested asset differs')
    if file_sha(Path(m['iso_path']))!=m['iso_sha256']:raise ValueError('ISO digest differs')
    result=dict(version='0.1.60',iso_sha256=m['iso_sha256'],archive_sha256=m['dialogue_cpk_sha256'],executable_sha256=g.sha(data),removed_duplicate_readings=removed,ruby_references=len(proof['records']),ruby_resources=len(installed),duplicate_ascii_readings_remaining=duplicate_left,reported_ryuho_both_branches_verified=True,name_reflows_verified=len(records),native_name_parent_width_cases=modeled_widths,native_measurement_unique_owners=len(cases),native_measurement_rows=sum(len(v['line_halfwidths']) for v in cases),whole_owner_width_fallback_verified=True,authored_tracks_and_main_text_exact=True,changed_archive_entries=len(changed),unselected_archive_entries_exact=len(after)-len(changed),all_nested_assets_exact=True,changed_name_capacity_and_risk_fingerprint_rejected=True,changed_corner_helper_rejected=True,layout_guard=guard,natural_scene_playback_verified=False)
    (UI/'validation.en.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
