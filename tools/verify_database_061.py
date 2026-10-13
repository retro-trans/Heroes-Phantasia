"""Read back the two dialogue fixes, event remap, title and nested ISO assets."""
import json
from pathlib import Path
from prepare_database_061 import BASE, OUT, UI, RESOURCES, EVENT, EVENT_SHA, OFFSET, TARGET, OLD, NEW, UNLOCK_EVENT, read
from rebuild_dialogue import parse
from unpack_cpk import packet
from inspect_iso import inventory as iso_inventory
from title_stamp import prepare, RESOURCE
from executable_text_patch import Elf, encoded_text
from native_menu_install_plan import cstring
import dialogue_layout_guard as g

ROOT=Path('work/output/0.1.61-title-credit-vwf-4x-candidate')


def toc(path):
    with Path(path).open('rb') as stream:
        _,header=packet(stream,0,b'CPK '); header=header[0]
        _,rows=packet(stream,header['TocOffset'],b'TOC ')
    if header['Files']!=len(rows): raise ValueError('Archive TOC row count differs')
    base=min(header['TocOffset'],header['ContentOffset'])
    return [(('/'.join(v for v in (r.get('DirName'),r['FileName']) if v)),r,base+r['FileOffset']) for r in rows]


def main():
    m=json.loads((ROOT/'manifest.en.json').read_bytes()); exe=(ROOT/'EBOOT.BIN').read_bytes(); e=Elf(exe)
    if exe!=(OUT/'EBOOT.BIN').read_bytes() or g.sha(exe)!=m['output_elf_sha256']: raise ValueError('Installed executable differs')
    selected=read(ROOT/'HP.CPK',[*RESOURCES,EVENT,UNLOCK_EVENT,RESOURCE]); old=read(BASE/'HP.CPK',RESOURCES)
    title,*_=prepare(m['config']); assets={RESOURCE:title}
    for name in RESOURCES:
        if selected[name]!=(OUT/name).read_bytes(): raise ValueError('Installed dialogue differs')
        p=parse(name,old[name]); np=parse(name,selected[name])
        prior=p['spans'][p['refs'][11][1]][0]; current=np['spans'][np['refs'][11][1]][0]
        if current!=prior.replace(OLD,NEW) or OLD in current: raise ValueError('Gift space differs')
        if g.inspect(name,selected[name],np,11,g.widths_from(ROOT/'EBOOT.BIN'))['status']!='fit':
            raise ValueError('Reported bubble layout fails')
        assets[name]=selected[name]
    if g.sha(selected[EVENT])!=EVENT_SHA or selected[RESOURCE]!=title: raise ValueError('Event bytecode or title differs')
    scope=m['setup_patch']['database_notice_061']
    for row in scope['new_notices']:
        event=selected[row['event']]; offset=row['offsets'][0]; source=event[offset:event.index(0,offset)+1]
        if g.sha(event)!=row['event_sha256'] or cstring(e,row['source_payload_rva'])!=source or cstring(e,row['target_payload_rva'])!=encoded_text(row['target'],'ascii')+b'\0':
            raise ValueError('Installed new notice differs')
    before=toc(BASE/'HP.CPK'); after=toc(ROOT/'HP.CPK')
    changed={a[0] for a,b in zip(before,after) if a!=b}
    if len(before)!=len(after) or changed!=set(assets): raise ValueError('Unselected archive entries changed')
    paths=iso_inventory(Path(m['iso_path'])); er=next(v for v in paths if v['path']=='PSP_GAME/SYSDIR/EBOOT.BIN')
    cr=next(v for v in paths if v['path']=='PSP_GAME/USRDIR/HP.CPK')
    with Path(m['iso_path']).open('rb') as stream:
        stream.seek(er['offset'])
        if stream.read(er['size'])!=exe: raise ValueError('Nested executable differs')
        for name,raw in assets.items():
            entry=next(v for v in after if v[0]==name); stream.seek(cr['offset']+entry[2])
            if entry[1]['FileSize']!=len(raw) or stream.read(len(raw))!=raw: raise ValueError('Nested selected asset differs')
    if not m['dialogue_layout_guard']['guard_passed']: raise ValueError('Mandatory full corpus guard did not pass')
    result=dict(version='0.1.61',iso_sha256=m['iso_sha256'],archive_sha256=m['dialogue_cpk_sha256'],
        executable_sha256=g.sha(exe),gift_space_both_branches_verified=True,discovery_notice_installed=True,
        new_notices_verified=[v['id'] for v in scope['new_notices']],
        player_name_selector_preserved=True,event_bytecode_exact=True,changed_archive_entries=len(changed),
        unselected_archive_toc_rows_exact=len(after)-len(changed),all_nested_selected_assets_exact=True,
        whole_iso_digest_checked_by_builder=True,
        layout_guard=m['dialogue_layout_guard'],natural_hq_playthrough_verified=False)
    (UI/'validation.en.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8'); print(json.dumps(result,indent=2))


if __name__=='__main__': main()
