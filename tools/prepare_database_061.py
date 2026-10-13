"""Fix Gift spacing and install the missing database discovery notice.

Reuse the existing notice helper's owned allocation with a table-driven exact
match loop. Event bytecode, loaded extents, font and bubble geometry stay exact.
"""
import argparse, copy, json, struct, sys
from pathlib import Path
import dialogue_layout_guard as g
from executable_text_patch import Elf, encoded_text
from native_menu_install_plan import cstring
from dialogue_tokens import validate_controls
from dialogue_vwf_hooks import Block, address, r
from live_vwf import i, j
from prepare_field_labels_046 import hook as old_hook, instruction_cases, EVENT, EVENT_SHA
from prepare_english_bubbles_v10 import relocate
from prepare_relocation_019 import sections, section_load, coverage
from build_menu_patch import align
from compact_vwf_patch import loaded
from unpack_cpk import packet, crilayla
from rebuild_dialogue import parse, rebuild
from field_ui_patch import notation
from build_local import authoritative_font_metadata
from save_logo_overlay import validate_native_png_metadata
from strip_jp import export
from append_cpk import main as append_main

BASE = Path('work/output/0.1.60-title-credit-vwf-4x-candidate')
OUT = Path('work/output/0.1.61-database-assets')
UI = Path('work/ui/dialogue/0.1.61')
RESOURCES = ('phase/bin/p101110.bin', 'phase/bin/p101111.bin')
OFFSET = 0x11ca3
TARGET = '{1A}2{01}1 found hidden{11}files in the database!{12}{0E}'
UNLOCK_EVENT = 'fld/event/d99.evt'
UNLOCK_EVENT_SHA = '6b616f2276ab2e610df21b7e1be63d59bce1f90edd9b727e8aeb96f068465e05'
UNLOCK_OFFSET = 0x6787
UNLOCK_TARGET = '{1A}5New Party Menu features{11}have been unlocked.{12}{0E}'
OLD = b'use\x05133\x1603Gift'
NEW = b'use \x05133\x1603Gift'


def read(path,names):
    """Read selected named rows without seeking every unrelated archive entry."""
    with Path(path).open('rb') as stream:
        _,headers=packet(stream,0,b'CPK '); header=headers[0]
        _,rows=packet(stream,header['TocOffset'],b'TOC ')
        if header['Files']!=len(rows): raise ValueError('Archive row count differs')
        base=min(header['TocOffset'],header['ContentOffset']); result={}
        for row in rows:
            name='/'.join(v for v in (row.get('DirName'),row['FileName']) if v)
            if name not in names: continue
            if name in result: raise ValueError('Duplicate selected archive row')
            stream.seek(base+row['FileOffset']); data=stream.read(row['FileSize'])
            if len(data)!=row['FileSize']: raise ValueError('Truncated selected archive row')
            result[name]=crilayla(data,row['ExtractSize']) if data.startswith(b'CRILAYLA') else data
        if set(result)!=set(names): raise ValueError('Missing selected archive row')
        return result


def table_hook(table, continuation):
    h = Block(); h.emit(i(35,20,4,0x14), i(9,29,29,-32))
    regs = (8,9,10,11,12,24)
    for n, reg in enumerate(regs): h.emit(i(43,29,reg,n*4))
    h.branch(4,4,0,'restore'); address(h,12,table)
    h.label('entry'); h.emit(i(35,12,9,0)); h.branch(4,9,0,'restore')
    h.emit(r(4,0,8)); h.label('compare')
    h.emit(i(36,8,10,0), i(36,9,11,0))
    h.branch(5,10,11,'next'); h.branch(4,10,0,'match')
    h.emit(i(9,8,8,1), i(9,9,9,1)); h.branch(4,0,0,'compare')
    h.label('next'); h.emit(i(9,12,12,8)); h.branch(4,0,0,'entry')
    h.label('match'); h.emit(i(35,12,4,4), i(43,20,4,0x14))
    h.label('restore')
    for n,reg in enumerate(regs): h.emit(i(35,29,reg,n*4))
    h.emit(i(9,29,29,32), i(43,20,21,0x24), j(continuation),0)
    return h.finish()


def executable():
    incoming=(BASE/'EBOOT.BIN').read_bytes()
    if g.sha(incoming)!='3dce3495886471a8e81cff59e562311079070795c0f019ab9f0a5ae822cd8eef':
        raise ValueError('Frozen .60 executable differs')
    before=json.loads((BASE/'manifest.en.json').read_bytes())['setup_patch']; e=Elf(incoming)
    scope=before['field_labels_047']; helper=scope['helper_rva']; size=scope['helper_bytes']
    entries=copy.deepcopy(scope['notices']); continuation=scope['episode_hook_continuation_rva']
    prior_code, _=relocate(old_hook(entries,continuation),helper,0,0)
    off=e.file_offset(helper,size)
    if len(prior_code)!=size or incoming[off:off+size]!=prior_code:
        raise ValueError('Existing exact-payload helper differs')
    events=read(BASE/'HP.CPK',[EVENT,UNLOCK_EVENT])
    sources=[cstring(e,v['source_payload_rva']) for v in entries]
    for row,raw in zip(entries,sources):
        if g.sha(raw)!=row['source_payload_sha256']: raise ValueError('Existing notice key differs')
    table=helper+align(len(table_hook(0,continuation)),4)
    cursor=table+(len(entries)+3)*8; additions=[]; payloads=[]
    specs=[('discovery',EVENT,EVENT_SHA,OFFSET,TARGET,[(17+len(' found hidden'))*13,len('files in the database!')*13]),
        ('party_unlock',UNLOCK_EVENT,UNLOCK_EVENT_SHA,UNLOCK_OFFSET,UNLOCK_TARGET,[len('New Party Menu features')*13,len('have been unlocked.')*13])]
    for label,name,event_sha,offset,text,widths in specs:
        event=events[name]
        if g.sha(event)!=event_sha or event[offset-2:offset]!=b'\x07\0': raise ValueError('Frozen event or opcode boundary differs')
        source=event[offset:event.index(0,offset)+1]; target=encoded_text(text,'ascii')+b'\0'
        validate_controls(notation(source[:-1]),text.replace('{11}','') if label=='party_unlock' else text)
        key=cursor; dest=key+len(source); cursor=dest+len(target)
        row=dict(id='field_notice_061_'+label,event=name,event_sha256=event_sha,offsets=[offset],source_payload_rva=key,
            source_payload_bytes=len(source),source_payload_sha256=g.sha(source),target_payload_rva=dest,
            target_payload_bytes=len(target),target=text,available_width_px=440,conservative_line_widths_px=widths)
        if max(widths)>440: raise ValueError('Bounded notice overflows')
        entries.append(row); sources.append(source); additions.append(row); payloads.extend([(key,source),(dest,target)])
    entry=additions[0]
    code, rels=relocate(table_hook(table,continuation),helper,0,0)
    blob=bytearray(size); blob[:len(code)]=code
    for n,row in enumerate(entries):
        struct.pack_into('<II',blob,table-helper+n*8,row['source_payload_rva'],row['target_payload_rva'])
        rels.extend([(table+n*8,2),(table+n*8+4,2)])
    if cursor>helper+size: raise ValueError('Owned helper allocation exhausted')
    for rva,data in payloads: blob[rva-helper:rva-helper+len(data)]=data
    result=bytearray(incoming); result[off:off+size]=blob
    removed={n for n,(site,flags) in enumerate(e.relocs) if flags>>8&255==0 and helper<=site<helper+size}
    if any(n<before['original_relocations'] for n in removed): raise ValueError('Original relocation selected')
    kept=[v for n,v in enumerate(e.relocs) if n not in removed]; newrels=kept+rels
    rp=e.ph[3]; ss=sections(incoming); relfile=align(len(result),16)
    result.extend(bytes(relfile-len(result))); result.extend(b''.join(struct.pack('<II',*v) for v in newrels))
    for s in ss:
        if s[1]!=0x700000a0: continue
        first=(s[4]-rp[1])//8; count=s[5]//8
        s[4]=relfile+(first-sum(n<first for n in removed))*8
        s[5]-=sum(n in removed for n in range(first,first+count))*8
    ss.append([0,0x700000a0,0,0,relfile+len(kept)*8,len(rels)*8,0,1,4,8])
    ph=[list(v) for v in e.ph]; ph[3][1]=relfile; ph[3][4]=len(newrels)*8
    shoff=align(len(result),4); result.extend(bytes(shoff-len(result)))
    result.extend(b''.join(struct.pack('<10I',*s) for s in ss))
    po=struct.unpack_from('<I',incoming,28)[0]; struct.pack_into('<8I',result,po+96,*ph[3])
    struct.pack_into('<I',result,32,shoff); struct.pack_into('<H',result,48,len(ss))
    out=bytes(result); oe=Elf(out); coverage(out)
    allowed=set(range(off,off+size))|set(range(po+96,po+128))|set(range(32,36))|set(range(48,50))
    if any(a!=b and n not in allowed for n,(a,b) in enumerate(zip(incoming,out))):
        raise ValueError('Unselected executable bytes changed')
    if oe.ph[:3]!=e.ph[:3] or oe.relocs[:before['original_relocations']]!=e.relocs[:before['original_relocations']]:
        raise ValueError('Original loaded contract differs')
    episode=cstring(e,before['field_ui_patch']['episode_inline_banner']['source_payload_rva']); models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        a,_,_,_=section_load(incoming,base); z,visited,skipped,_=section_load(out,base)
        independent,_,_=loaded(out,base)
        if skipped or visited!=oe.relocs or independent!=[z[n][:oe.ph[n][4]] for n in range(3)]:
            raise ValueError('Independent relocation loaders differ')
        if a[1:]!=z[1:] or any(x!=y and not helper<=n<helper+size for n,(x,y) in enumerate(zip(a[0],z[0]))):
            raise ValueError('Unselected loaded memory changed')
        mapped=[dict(v,source_payload_rva=base+v['source_payload_rva'],target_payload_rva=base+v['target_payload_rva']) for v in entries]
        # The instruction fixture provides the pointer table as executable data.
        from font_vram_hooks import instruction_model
        original_model=instruction_model
        import prepare_field_labels_046 as tests
        def model_with_table():
            model=original_model(); execute=model['execute']
            def execute_table(c,regs,memory):
                memory.update({base+table+n:value for n,value in enumerate(z[0][table:table+(len(entries)+1)*8])})
                return execute(c,regs,memory)
            model['execute']=execute_table
            return model
        # instruction_cases sets execute.__globals__['B']; the native model's
        # function also needs its own base when wrapped for table fixture data.
        original_model()['execute'].__globals__['B']=base+helper
        tests.instruction_model=model_with_table
        try: checks=instruction_cases(bytes(z[0][helper:helper+len(code)]),base+helper,mapped,sources,base+continuation,episode)
        finally: tests.instruction_model=original_model
        models.append(dict(base=base,loaded_extents_exact=True,outside_allocation_exact=True,instruction_checks=checks))
    report=copy.deepcopy(before)
    report.update(version='0.1.61',input_version='0.1.60',input_sha256=g.sha(incoming),
        output_sha256=g.sha(out),output_elf_sha256=g.sha(out),elf_bytes=len(out),
        total_relocations=len(oe.relocs),runtime_verified=False)
    report['field_labels_047'].update(notices=entries,helper_bytes=len(code),helper_sha256=g.sha(code),
        helper_implementation='table-driven exact complete payload match, 0.1.61',event_occurrences=17)
    next(v for v in report['field_labels_047']['placements'] if v['name']=='field_notice_helper')['sha256']=g.sha(blob)
    report['database_notice_061']=dict(entry=entry,new_notices=additions,helper_rva=helper,helper_bytes=len(code),
        table_rva=table,allocation_bytes=size,allocation_sha256=g.sha(blob),models=models,
        source_event_sha256=EVENT_SHA,event_bytecode_exact=True,loaded_growth_bytes=0,
        font_and_geometry_exact=True,natural_gameplay_verified=False)
    for chunk in report['native_tail_compaction']['chunks']:
        chunk['output_sha256']=g.sha(out[chunk['file_offset']:chunk['file_offset']+chunk['bytes']])
    authoritative_font_metadata(out,report); validate_native_png_metadata(out,report)
    return out,report,entry


def dialogue(executable):
    raws=read(BASE/'HP.CPK',RESOURCES); widths=g.widths_from(executable); assets={}; rows=[]; proof=[]
    for name,raw in raws.items():
        p=parse(name,raw); old=p['spans'][p['refs'][11][1]][0]
        if old.count(OLD)!=1: raise ValueError('Reported Gift token differs')
        new=old.replace(OLD,NEW); changed,np=rebuild(name,raw,{11:new})
        if raw[p['head'][0]:p['start']]!=changed[np['head'][0]:np['start']] or raw[p['end']:]!=changed[np['end']:]:
            raise ValueError('Authored animation or suffix changed')
        for n,(_,at) in enumerate(p['refs']):
            if n!=11 and p['spans'][at][0]!=np['spans'][np['refs'][n][1]][0]: raise ValueError('Other dialogue changed')
        validate_controls(notation(old),notation(new)); fit=g.inspect(name,changed,np,11,widths)
        if fit['status']!='fit': raise ValueError('Gift spacing layout does not fit')
        assets[name]=changed; rows.append(dict(id='spacing_061_'+Path(name).stem,file=name,target=notation(new),
            category='dialogue_spacing',status='translated',notes='Added one space before the highlighted Gift; all words, controls, pages and authored tracks retained.'))
        proof.append(dict(resource=name,reference_index=11,old_sha256=g.sha(old),new_sha256=g.sha(new),
            authored_tracks_exact=True,other_dialogue_exact=True,layout=fit))
    return assets,rows,proof


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--write',action='store_true'); opts=ap.parse_args()
    exe,report,entry=executable()
    if not opts.write: print(json.dumps(report['database_notice_061'],indent=2)); return
    if OUT.exists(): raise ValueError('Fresh output required')
    OUT.mkdir(parents=True); UI.mkdir(parents=True,exist_ok=True); (OUT/'EBOOT.BIN').write_bytes(exe)
    assets,rows,proof=dialogue(OUT/'EBOOT.BIN'); report['gift_spacing_061']=proof
    (OUT/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    for row in report['database_notice_061']['new_notices']:
        rows.append(dict(id=row['id'],file=row['event'],offset=row['offsets'][0],target=row['target'],category='field_notices',
            status='translated',notes='Complete payload remap preserves event commands and semantic controls; English line breaks fit conservative native widths.'))
    queue=Path('work/translation/en/database_061.json'); queue.write_text(json.dumps(dict(rows=rows),indent=2)+'\n',encoding='utf8')
    queue.with_suffix('.en.json').write_text(json.dumps(export(dict(rows=rows)),indent=2)+'\n',encoding='utf8')
    for name,raw in assets.items():
        f=OUT/name; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(raw)
    m=json.loads((BASE/'manifest.en.json').read_bytes()); sys.argv=['append','--archive',str(BASE/'HP.CPK'),
        '--expected-sha256',m['dialogue_cpk_sha256'],'--version','0.1.61','--output',str(OUT/'HP.CPK'),'--write']
    for name in assets: sys.argv+=['--replace',name+'='+str(OUT/name)]
    append_main()
    ledger=json.loads(Path('work/ui/dialogue/0.1.60/layout_exceptions.en.json').read_bytes())
    if ledger['runtime_contract']!=g.runtime_contract(OUT/'EBOOT.BIN'): raise ValueError('Font/geometry contract changed')
    ledger.update(version='0.1.61',scope='Unchanged inherited unsupported and name-layout risks; none is enlarged or modified by this build.')
    (UI/'layout_exceptions.en.json').write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf8')
    (UI/'preparation.en.json').write_text(json.dumps(dict(version='0.1.61',database=report['database_notice_061'],spacing=proof),indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(version='0.1.61',executable_sha256=g.sha(exe),changed_dialogue_resources=2,notice=TARGET),indent=2))


if __name__=='__main__': main()
