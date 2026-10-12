"""Queue runtime-observed main-menu and protagonist labels; dry-run before --write."""
import argparse,json,pathlib

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    data=pathlib.Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf').read_bytes()
    dest=pathlib.Path('work/translation/en/menu_ui_0001.json')
    existing={r['id']:r for r in json.loads(dest.read_text(encoding='utf8'))['rows']} if dest.exists() else {}
    start=0x94f43;rows=[]
    for en in ['New Game','Load','Options','Gallery','Data Install']:
        end=data.index(0,start);raw=data[start:end];ident=f'exe_{start:08x}_cp932'
        rows.append(existing.get(ident,dict(id=ident,file='PSP_GAME/SYSDIR/EBOOT.decrypted.elf',offset=start,
            byte_length=len(raw),encoding='cp932',category='executable_menu_ui',source=raw.decode('cp932'),
            target=en,status='draft',context='Main menu, observed at native resolution after pressing Start.',
            decisions='Full menu label translated; runtime source observed, English glyph rendering/insertion still pending.',
            notes='Local display source verified; translation is not runtime verified. Relocate string and pointer rather than squeeze into original slot.')))
        start=end+1
    for row in rows:
        row['decisions']='Full label relocated into a new loaded section; cold-boot menu rendering verified with 4x source VWF.'
        row['notes']='Five-label cold-boot evidence is recorded separately; draft status retained pending broader build QA.'
    for offset,en in ((0x94fba,'Male'),(0x94fbf,'Female')):
        end=data.index(0,offset);raw=data[offset:end];ident=f'exe_{offset:08x}_cp932'
        if raw.decode('cp932')!=('男性' if en=='Male' else '女性'):raise ValueError('Observed gender label changed')
        rows.append(existing.get(ident,dict(id=ident,file='PSP_GAME/SYSDIR/EBOOT.decrypted.elf',offset=offset,
            byte_length=len(raw),encoding='cp932',category='executable_menu_ui',source=raw.decode('cp932'),
            target=en,status='draft',context='Protagonist selection; original label observed in candidate_new_game screenshots.',
            decisions='Full UI label; gender directly displayed by the source, not inferred from a character name.',
            notes='Observed source; English insertion/layout not yet tested. Relocate rather than use source slot as byte budget.')))
    custom=[(0x94f80,'性別選択','Select Gender'),(0x94f89,'苗字変更','Change Last Name'),
        (0x94f92,'名前変更','Change First Name'),(0x94f9b,'異名変更','Change Nickname'),
        (0x954d9,'ボイス再生','Play Voice'),(0x94fa4,'デフォルトに戻す','Restore Defaults'),
        (0x94fb5,'決定','Done')]
    for offset,ja,en in custom:
        end=data.index(0,offset);raw=data[offset:end];ident=f'exe_{offset:08x}_cp932'
        if raw.decode('cp932')!=ja:raise ValueError('Observed customization label changed')
        rows.append(existing.get(ident,dict(id=ident,file='PSP_GAME/SYSDIR/EBOOT.decrypted.elf',offset=offset,
            byte_length=len(raw),encoding='cp932',category='executable_menu_ui',source=ja,
            target=en,status='draft',context='Female protagonist customization screen; observed in candidate_protagonist_confirm.png.',
            decisions=('Full UI action label. Nickname refers to the customizable epithet displayed below the name and gender; wording remains a draft.' if offset==0x94f9b else 'Full UI action label; surname and given-name actions are distinguished by adjacent menu entries.'),
            notes='Observed Japanese source; English insertion, menu width and runtime font path not yet tested. Relocate into new storage.')))
    print(json.dumps({'rows':len(rows),'sample':rows},ensure_ascii=True,indent=2))
    if a.write:dest.write_text(json.dumps(dict(schema_version=1,language='en',rows=rows),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    else:print('DRY RUN: no translation queue written.')

if __name__=='__main__':main()
