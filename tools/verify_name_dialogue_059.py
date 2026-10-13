"""Validate installed name reflows, width fallback, guard and nested ISO bytes."""
import json, struct, tempfile
from pathlib import Path
import dialogue_layout_guard as g
from rebuild_dialogue import parse
from unpack_cpk import inventory
from prepare_bubble_scenes_036 import read
from build_local import sha as file_sha
from inspect_iso import inventory as iso_inventory
from title_stamp import prepare as title_prepare, RESOURCE
from executable_text_patch import Elf
from dialogue_measure_1a import instruction_cases

BASE=Path('work/output/0.1.58-title-credit-vwf-4x-candidate')
ROOT=Path('work/output/0.1.59-title-credit-vwf-4x-candidate')
ASSETS=Path('work/output/0.1.59-name-dialogue-assets')
UI=Path('work/ui/dialogue/0.1.59')

def main():
    manifest=json.loads((ROOT/'manifest.en.json').read_bytes())
    prep=manifest['setup_patch']['name_dialogue_059'];data=(ROOT/'EBOOT.BIN').read_bytes()
    if data!=(BASE/'EBOOT.BIN').read_bytes():raise ValueError('Frozen tested executable changed')
    assets={r['resource']:(ASSETS/r['resource']).read_bytes() for r in prep['selected_assets']}
    original=read(BASE/'HP.CPK',list(assets));installed=read(ROOT/'HP.CPK',list(assets))
    if assets!=installed:raise ValueError('Installed reflows differ')
    parsed={n:parse(n,b) for n,b in installed.items()};oldparsed={n:parse(n,b) for n,b in original.items()}
    for name,raw in installed.items():
        old,p=oldparsed[name],parsed[name]
        if original[name][old['head'][0]:old['start']]!=raw[p['head'][0]:p['start']] or original[name][old['end']:]!=raw[p['end']:]:raise ValueError('Authored scene/tail tracks changed')
    samples={};pages=0;widths=g.widths_from(ROOT/'EBOOT.BIN')
    strip=lambda b:bytes(c for c in b if c not in (32,0x10,0x11,0x12))
    for rec in prep['records']:
        name,n=rec['resource'],rec['reference_index'];p,op=parsed[name],oldparsed[name]
        text=p['spans'][p['refs'][n][1]][0];before=op['spans'][op['refs'][n][1]][0]
        if strip(text)!=strip(before):raise ValueError('Glyph/control order changed')
        r=g.inspect(name,installed[name],p,n,widths)
        if r['status']!='fit' or r['measurement_policy']!='native_13px_with_bounded_names':raise ValueError('Reflow does not fit bounded native widths')
        rows=[]
        for page in text.split(b'\x0e',1)[1].split(b'\x0e',1)[0].split(b'\x10'):
            rows.extend(line+b'\x12' for line in page.split(b'\x12',1)[0].split(b'\x11'));pages+=1
        samples[tuple(rows)]=(rows,False)
    # A name in any row must leave every native row width and the shared
    # owner unchanged, including earlier rows scanned before that name.
    for selector in range(4):
        name=b'\x01'+str(selector).encode()
        for rows in ([name+b'\x12',b'Plain later page\x12'],[b'Plain earlier page\x12',name+b'\x12']):samples[tuple(rows)]=(rows,False)
    e=Elf(data);at=e.file_offset(0x16fa8f0);native=bytearray(data[at:at+1064])
    if struct.unpack_from('<II',native,96)!=(0x3c0e002e,0x25ce4000):raise ValueError('Installed LUT load changed')
    struct.pack_into('<II',native,96,0x3c0e0024,0x25ce0000)
    cases=instruction_cases(widths,bytes(native),list(samples.values()))
    guard=g.enforce(ROOT/'HP.CPK',ROOT/'EBOOT.BIN')
    try:g.enforce(BASE/'HP.CPK',ROOT/'EBOOT.BIN')
    except ValueError as ex:
        if 'rejected 239 references' not in str(ex):raise
    else:raise ValueError('Old named overflows bypass the new gate')
    ledger=json.loads(g.EXCEPTIONS.read_bytes())
    risk_names=list(dict.fromkeys(v['resource'] for v in ledger['retained_maximum_name_risks']))
    old_risks=read(BASE/'HP.CPK',risk_names);new_risks=read(ROOT/'HP.CPK',risk_names)
    for rec in ledger['retained_maximum_name_risks']:
        name,n=rec['resource'],rec['reference_index'];op=parse(name,old_risks[name]);np=parse(name,new_risks[name])
        if op['spans'][op['refs'][n][1]][0]!=np['spans'][np['refs'][n][1]][0]:raise ValueError('Retained risk changed')
    # A reviewed-name capacity change or a new maximum-name fingerprint
    # must not inherit permission from the explicit unchanged-risk ledger.
    with tempfile.TemporaryDirectory(prefix='name-guard-') as scratch:
        altered=json.loads(g.EXCEPTIONS.read_bytes());altered['name_selector_limits']['1']=16
        path=Path(scratch)/'limits.en.json';path.write_text(json.dumps(altered))
        try:g.enforce(ROOT/'HP.CPK',ROOT/'EBOOT.BIN',path)
        except ValueError as ex:
            if 'measurement policy differs' not in str(ex):raise
        else:raise ValueError('Changed capacity bypasses guard')
        altered=json.loads(g.EXCEPTIONS.read_bytes());altered['retained_maximum_name_risks'][0]['text_sha256']='0'*64
        path.write_text(json.dumps(altered))
        try:g.enforce(ROOT/'HP.CPK',ROOT/'EBOOT.BIN',path)
        except ValueError as ex:
            if 'rejected 1 references' not in str(ex):raise
        else:raise ValueError('Risk fingerprint bypasses guard')
    _,before=inventory(BASE/'HP.CPK');_,after=inventory(ROOT/'HP.CPK')
    changed={a['path'] for a,b in zip(before,after) if a!=b}
    if len(before)!=len(after) or changed!=set(assets)|{RESOURCE}:raise ValueError('Unselected archive entries differ')
    title,*_=title_prepare(manifest['config']);assets[RESOURCE]=title
    if read(ROOT/'HP.CPK',[RESOURCE])[RESOURCE]!=title:raise ValueError('Title version differs')
    entries=iso_inventory(Path(manifest['iso_path']))
    exe=next(v for v in entries if v['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');cpk=next(v for v in entries if v['path']=='PSP_GAME/USRDIR/HP.CPK')
    with Path(manifest['iso_path']).open('rb') as stream:
        stream.seek(exe['offset'])
        if stream.read(exe['size'])!=data:raise ValueError('Nested executable differs')
        for name,raw in assets.items():
            entry=next(v for v in after if v['path']==name);stream.seek(cpk['offset']+entry['offset'])
            if entry['compression']!='none' or stream.read(len(raw))!=raw:raise ValueError('Nested asset differs')
    if file_sha(Path(manifest['iso_path']))!=manifest['iso_sha256']:raise ValueError('ISO digest differs')
    proof=dict(version='0.1.59',iso_sha256=manifest['iso_sha256'],archive_sha256=manifest['dialogue_cpk_sha256'],executable_sha256=g.sha(data),executable_exact_to_tested_058=True,reflow_references=len(prep['records']),resources_reflowed=len(installed),pages_in_reflowed_references=pages,native_measurement_unique_owners=len(cases),native_measurement_rows=sum(len(v['line_halfwidths']) for v in cases),whole_owner_name_fallback_verified=True,all_four_name_selectors_first_and_last_rows_verified=True,authored_tracks_and_glyph_control_order_exact=True,changed_archive_entries=len(changed),unselected_archive_entries_exact=len(after)-len(changed),old_named_overflows_rejected=True,changed_name_capacity_rejected=True,changed_risk_fingerprint_rejected=True,retained_maximum_name_risks_unchanged=len(ledger['retained_maximum_name_risks']),all_nested_assets_exact=True,layout_guard=guard,natural_scene_playback_verified=False)
    (UI/'validation.en.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps(proof,indent=2))

if __name__=='__main__':main()
