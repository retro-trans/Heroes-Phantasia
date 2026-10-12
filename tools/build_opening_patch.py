"""Build a local 0.1.2 opening-dialogue/VWF ISO; preview by default."""
import argparse,hashlib,json,pathlib,shutil,struct
from build_menu_patch import build,record_for,align,ISO

ROOT=pathlib.Path('work/output/0.1.2-opening-vwf-4x-candidate')
CPK=pathlib.Path('work/output/0.1.1-dialogue-candidate/HP.CPK')
CPK_SHA='b0273345bfe8b7b67a85510b5d3f25a7fe6723bf9b9f5ef7362410df7f89c9df'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--iso',action='store_true');p.add_argument('--speaker-labels',action='store_true');p.add_argument('--bubble-layout',action='store_true');p.add_argument('--compact-font',action='store_true');p.add_argument('--association-fix',action='store_true');a=p.parse_args()
    if a.association_fix:a.compact_font=True
    if a.compact_font:a.bubble_layout=True
    if a.bubble_layout:a.speaker_labels=True
    output_root=pathlib.Path('work/output/0.1.6-opening-vwf-4x-candidate') if a.association_fix else pathlib.Path('work/output/0.1.5-opening-vwf-4x-candidate') if a.compact_font else pathlib.Path('work/output/0.1.4-opening-vwf-4x-candidate') if a.bubble_layout else pathlib.Path('work/output/0.1.3-opening-vwf-4x-candidate') if a.speaker_labels else ROOT
    data,info=build(full_4x=True,dialogue=True,speaker_labels=a.speaker_labels,bubble_layout=a.bubble_layout,compact_font=a.compact_font,association_fix=a.association_fix)
    digest=hashlib.sha256()
    with CPK.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):digest.update(block)
    if digest.hexdigest()!=CPK_SHA:raise ValueError('Selected dialogue CPK changed')
    records={path:record_for(ISO,path) for path in ('PSP_GAME/SYSDIR/EBOOT.BIN','PSP_GAME/USRDIR/HP.CPK')}
    info.update(dialogue_cpk_sha256=CPK_SHA,dialogue_cpk_bytes=CPK.stat().st_size,
        selected_dialogue_rows=[1],translated_game_complete=False,iso_replacements=records)
    print(json.dumps(info,indent=2))
    if not a.write:print('DRY RUN: no output written.');return
    if output_root.exists():raise ValueError('Use a fresh output directory; do not overwrite candidate builds')
    output_root.mkdir(parents=True);(output_root/'EBOOT.BIN').write_bytes(data)
    if a.iso:
        dest=output_root/f"Heroes-Phantasia-{info['version']}-opening-vwf-4x-candidate.iso";shutil.copyfile(ISO,dest)
        with dest.open('r+b') as f:
            for target,source in (('PSP_GAME/SYSDIR/EBOOT.BIN',data),('PSP_GAME/USRDIR/HP.CPK',CPK)):
                end=align(f.seek(0,2),2048);f.write(bytes(end-f.tell()))
                if isinstance(source,bytes):f.write(source);length=len(source)
                else:
                    with source.open('rb') as src:shutil.copyfileobj(src,f,8*1024*1024)
                    length=source.stat().st_size
                final=align(f.tell(),2048);f.write(bytes(final-f.tell()))
                rec,_,_=records[target];f.seek(rec+2);f.write(struct.pack('<I',end//2048)+struct.pack('>I',end//2048))
                f.seek(rec+10);f.write(struct.pack('<I',length)+struct.pack('>I',length))
            f.seek(16*2048+80);f.write(struct.pack('<I',final//2048)+struct.pack('>I',final//2048))
        info['iso_bytes']=final;info['iso_path']=str(dest)
    (output_root/'manifest.en.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf8')
    print('Wrote local candidate; runtime validation pending.')

if __name__=='__main__':main()
