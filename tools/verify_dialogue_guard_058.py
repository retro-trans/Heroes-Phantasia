"""Read back every installed reflow, test native width code and build guard."""
import json, struct, tempfile
from pathlib import Path
import dialogue_layout_guard as g
from rebuild_dialogue import parse, rebuild
from unpack_cpk import inventory
from prepare_bubble_scenes_036 import read
from build_local import sha as file_sha
from inspect_iso import inventory as iso_inventory
from title_stamp import prepare as title_prepare, RESOURCE
from executable_text_patch import Elf
from dialogue_measure_1a import instruction_cases

BASE=Path('work/output/0.1.53-title-credit-vwf-4x-candidate')
ROOT=Path('work/output/0.1.58-title-credit-vwf-4x-candidate')
ASSETS=Path('work/output/0.1.55-dialogue-guard-assets')
UI=Path('work/ui/dialogue/0.1.58')

def main():
    manifest=json.loads((ROOT/'manifest.en.json').read_text(encoding='utf8'))
    prep=json.loads((ASSETS/'executable.en.json').read_text(encoding='utf8'))['dialogue_guard_055']
    data=(ROOT/'EBOOT.BIN').read_bytes()
    if data!=Path('work/output/0.1.58-elevator-crash-assets/EBOOT.BIN').read_bytes(): raise ValueError('Prepared executable differs')
    old_data=(BASE/'EBOOT.BIN').read_bytes();old_e=Elf(old_data)
    if data[Elf(data).file_offset(0x16fa8f0):Elf(data).file_offset(0x16fa8f0)+1064]!=old_data[old_e.file_offset(0x16fa8f0):old_e.file_offset(0x16fa8f0)+1064]: raise ValueError('Native width code changed')
    assets={r['resource']:(ASSETS/r['resource']).read_bytes() for r in prep['selected_assets']}
    original=read(BASE/'HP.CPK',list(assets));installed=read(ROOT/'HP.CPK',list(assets))
    if assets!=installed: raise ValueError('Installed assets differ')
    samples={};page_count=0
    for name,raw in installed.items():
        old=parse(name,original[name]);p=parse(name,raw)
        if original[name][old['head'][0]:old['start']]!=raw[p['head'][0]:p['start']] or original[name][old['end']:]!=raw[p['end']:]: raise ValueError('Authored scene/tail tracks changed')
    for rec in prep['records']:
        name,n=rec['resource'],rec['reference_index'];p=parse(name,installed[name]);oldp=parse(name,original[name]);text=p['spans'][p['refs'][n][1]][0];oldtext=oldp['spans'][oldp['refs'][n][1]][0]
        strip=lambda b:bytes(c for c in b if c not in (32,0x10,0x11,0x12))
        if strip(text)!=strip(oldtext): raise ValueError('Glyphs/control order changed')
        # Supply the whole owner's row array to installed measurement code,
        # never separate page cases: the shared maximum is the regression.
        body=text.split(b'\x0e',1)[1].split(b'\x0e',1)[0];rows=[]
        for page in body.split(b'\x10'):
            plain=page.split(b'\x12',1)[0]
            rows.extend(line+b'\x12' for line in plain.split(b'\x11'));page_count+=1
        samples[tuple(rows)]=(rows,True)
    e=Elf(data);at=e.file_offset(0x16fa8f0);native=bytearray(data[at:at+1064])
    if struct.unpack_from('<II',native,24*4)!=(0x3c0e002e,0x25ce4000): raise ValueError('Native LUT address differs')
    struct.pack_into('<II',native,24*4,0x3c0e0024,0x25ce0000)
    widths=g.widths_from(ROOT/'EBOOT.BIN');cases=instruction_cases(widths,bytes(native),list(samples.values()))
    guard=g.enforce(ROOT/'HP.CPK',ROOT/'EBOOT.BIN')
    altered=bytearray(data);altered[e.file_offset(0x45e2c8+12)]^=1
    with tempfile.TemporaryDirectory(prefix='dialogue-guard-') as scratch:
        changed_template=Path(scratch)/'EBOOT.elf';changed_template.write_bytes(altered)
        try:g.enforce(ROOT/'HP.CPK',changed_template)
        except ValueError as ex:
            if 'native geometry changed' not in str(ex):raise
        else:raise ValueError('Changed native template bypasses the build guard')
    old_audit=g.audit(BASE/'HP.CPK',BASE/'EBOOT.BIN')
    if old_audit['counts']['overflow']!=4588: raise ValueError('Original overflow count differs')
    try: g.enforce(BASE/'HP.CPK',ROOT/'EBOOT.BIN')
    except ValueError as ex:
        if 'rejected 4588 references' not in str(ex): raise
    else: raise ValueError('Old overflowing corpus incorrectly passed the gate')
    # A later short page must be rejected when another page increases the
    # shared width. A changed unverified name input cannot use the baseline.
    name='phase/bin/p101050.bin';raw=installed[name];p=parse(name,raw)
    op=parse(name,original[name]);original_zig=op['spans'][op['refs'][30][1]][0]
    modified,mp=rebuild(name,raw,{30:original_zig});r=g.inspect(name,modified,mp,30,widths)
    if r['status']!='overflow' or r['parent_maximum_width']!=290 or not any(v['page']==2 for v in r['failures']): raise ValueError('Whole-block later-page regression not detected')
    exceptions=json.loads(g.EXCEPTIONS.read_text(encoding='utf8'));unknown=next(v for v in exceptions['records'] if 'Dynamic names' in v['reason'])
    unknown_raw=read(ROOT/'HP.CPK',[unknown['resource']])[unknown['resource']];up=parse(unknown['resource'],unknown_raw);n=unknown['reference_index'];text=up['spans'][up['refs'][n][1]][0]
    replacement=text.split(b'\x0e',1)[0]+b'\x0eA '+text.split(b'\x0e',1)[1]
    mutated,ump=rebuild(unknown['resource'],unknown_raw,{n:replacement});item=g.inspect(unknown['resource'],mutated,ump,n,widths)
    if item['status']!='unverified' or g.exception_key(item) in {g.exception_key(v) for v in exceptions['records']}: raise ValueError('Changed unknown input bypasses gate')
    _,before=inventory(BASE/'HP.CPK');_,after=inventory(ROOT/'HP.CPK');changed={a['path'] for a,b in zip(before,after) if a!=b}
    if len(before)!=len(after) or changed!=set(assets)|{RESOURCE}: raise ValueError('Unselected archive row changed')
    title,*_=title_prepare(manifest['config']);assets[RESOURCE]=title
    if read(ROOT/'HP.CPK',[RESOURCE])[RESOURCE]!=title: raise ValueError('Title differs')
    entries=iso_inventory(Path(manifest['iso_path']));exe=next(v for v in entries if v['path']=='PSP_GAME/SYSDIR/EBOOT.BIN');cpk=next(v for v in entries if v['path']=='PSP_GAME/USRDIR/HP.CPK')
    with Path(manifest['iso_path']).open('rb') as stream:
        stream.seek(exe['offset'])
        if stream.read(exe['size'])!=data: raise ValueError('Nested executable differs')
        for name,raw in assets.items():
            entry=next(v for v in after if v['path']==name);stream.seek(cpk['offset']+entry['offset'])
            if entry['compression']!='none' or stream.read(len(raw))!=raw: raise ValueError('Nested archive asset differs')
    if file_sha(Path(manifest['iso_path']))!=manifest['iso_sha256']: raise ValueError('ISO digest differs')
    proof=dict(version='0.1.58',iso_sha256=manifest['iso_sha256'],archive_sha256=manifest['dialogue_cpk_sha256'],executable_sha256=g.sha(data),reflow_references=len(prep['records']),resources_reflowed=len(installed),pages_in_reflowed_references=page_count,native_measurement_unique_owners=len(cases),native_measurement_rows=sum(len(v['line_halfwidths']) for v in cases),all_native_parent_maxima_verified=True,authored_tracks_and_glyphs_exact=True,changed_archive_entries=len(changed),unselected_archive_entries_exact=len(after)-len(changed),old_corpus_rejected=True,later_page_shared_width_regression_rejected=True,changed_unverified_input_rejected=True,changed_native_template_catalog_rejected=True,all_nested_assets_exact=True,layout_guard=guard,natural_scene_playback_verified=False)
    (UI/'validation.en.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8');print(json.dumps(proof,indent=2))

if __name__=='__main__': main()
