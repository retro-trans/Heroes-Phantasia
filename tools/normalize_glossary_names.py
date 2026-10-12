"""Apply reviewed glossary spelling changes to English fields only; dry-run default."""
import argparse,copy,hashlib,json,pathlib,re
from dialogue_tokens import validate_controls

SOURCE_RULES=(
    ('風華',r'\bFuka\b','Fuuka'),
    ('ミレル',r'\bMirelle\b','Merrill'),
    ('{1C}命{0E}',r'\bInochi\b','Mikoto'),
    ('アンゴル族',r"Angol people's","Angolans'"),
    ('アンゴル族',r'Angol people','Angolans'),
    ('アルター結晶体',r'\bthe Crystallized Alter\b','The Crystal'),
    ('アルター結晶体',r'\bCrystallized Alter\b','The Crystal'),
    ('おまもり',r'\bCharms\b','Amulets'),
    ('おまもり',r'\bCharm\b','Amulet'),
)
def digest(raw):return hashlib.sha256(raw).hexdigest()

RULES=(('Adroas','Adloaz'),
       ('Cinq Fleches Pharmacy','Cinq Flèches Pharmaceutical'),
       ('Highly-advanced Materialising Equipment','Highly-advanced Materializing Equipment'),
       ('Joji Nakata','Jouji Nakata'),
       ('Akino Watanabe','Akeno Watanabe'),
       ('Tama Maruta','Mari Maruta'),
       ('Makiko Omoto','Makiko Ohmoto'),
       ('Narumi Iwasaki','Masami Iwasaki'),
       ('Cinq Fleches Pharmaceutical','Cinq Flèches Pharmaceutical'),
       ('Cinq Fleches','Cinq Flèches'),
       ('Space Detective','Space Deputy'),
       ('ＮＰ３２２８','NP3228'),
       ('mI6','MI6'),
       ('race called the chijin','race known as dwarves'),
       ('Chijin have','Dwarves have'),
       ('a chijin','a dwarf'),
       ('chijin have','dwarves have'))

EXPANSION_NOTES=(
    ('Official Sunrise English expansion Highly-advanced Materializing Equipment',
     'Project glossary expansion Highly-advanced Materializing Equipment (franchise-wiki spelling)'),
    ('Official glossary Highly-advanced Materializing Equipment overrides source Latin spelling Materializing; nomenclature discrepancy recorded under wiki/official-source precedence.',
     'Project glossary uses Materializing, matching the source and franchise wiki; this supersedes the earlier official-based Materialising spelling.'),
    ('the official Highly-advanced Materializing Equipment expansion. Preserve official spelling',
     'the project Highly-advanced Materializing Equipment expansion. Preserve franchise-wiki spelling'),
)

NP_DECISIONS={
    'ffc7634da542dcb896a7':'Player-facing prisoner designation rendered as NP3228 in ASCII; identifier letters/digits preserved, not a runtime substitution or control argument.',
    '4bd12adbb753c9ea75ee':'Prisoner designation NP3228 uses ASCII presentation with identical value; Mitch recognizes it as the alarm announcement number. Full recognition clause retained.',
    '702de10578c8e2107191':'Player-facing NP3228 rendered in ASCII without changing identifier value; deliberate number-only vocative retained.',
    'b47b35991a88ff54ff95':'Restore you want to know; direct-address prisoner designation NP3228 uses ASCII with identical value, no runtime argument change.',
    '4d3760c756d07e653962':"Player-facing NP3228 uses ASCII with identical identifier value; simultaneous arrival remains Asuka's accusation, not translator confirmation.",
}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write',action='store_true')
    p.add_argument('--preview-path',type=pathlib.Path)
    p.add_argument('--approved-preview',type=pathlib.Path)
    p.add_argument('--snapshot-dir',type=pathlib.Path)
    a=p.parse_args()
    changes=[];pending=[];inputs={}
    paths=list(pathlib.Path('work/translation/en').glob('*.json'))+list(pathlib.Path('work/glossary').glob('*.en.json'))
    for path in paths:
        if path.name=='glossary.en.json' or path.name.endswith('.en.json') and 'translation' in path.parts:continue
        raw=path.read_bytes();inputs[str(path)]=digest(raw)
        data=json.loads(raw.decode('utf8'));before=copy.deepcopy(data);modified=False
        for row in data.get('rows',data.get('entries',[])):
            normalize_np='ＮＰ３２２８' in (row.get('target') or '')
            for field in ('target','en','role','decisions'):
                old=row.get(field)
                if not isinstance(old,str):continue
                new=old
                for source,target in RULES:new=new.replace(source,target)
                if field=='target' and 'Materialising' in new and ('HiME' in row.get('source','') or 'ＨｉＭＥ' in row.get('source','') or 'Ｍａｔｅｒｉａｌｉｚｉｎｇ' in row.get('source','')):
                    # Line controls may split the named expansion; leave historical
                    # spelling discussion in decision metadata untouched.
                    new=re.sub(r'\bMaterialising\b','Materializing',new)
                if field=='target' and 'ボルカン' in row.get('source',''):
                    new=re.sub(r'\bVulcan\b','Volkan',new)
                if field=='target':
                    for marker,pattern,replacement in SOURCE_RULES:
                        if marker in row.get('source',''):
                            if marker=='おまもり' and '魅力' in row['source']:
                                raise ValueError('Mixed Amulet/Charm source needs individual review: '+row['id'])
                            new=re.sub(pattern,replacement,new)
                    source=row.get('source','')
                    # Exact labels preserve shortened names in dialogue.
                    if source=='魔術師ギルド':new="Magicians' Guild"
                    if source=='ＣＩＡの荒法師':new="CIA's Warrior Monk"
                    if source=='盗賊殺し':new="Robbers' Killer"
                    if source=='英雄度' and new=='Heroism':new='Heroic Score'
                    if new!=old:validate_controls(source,new)
                if field=='decisions':
                    for source,target in EXPANSION_NOTES:new=new.replace(source,target)
                if field in ('target','role'):new=re.sub(r'\bHaji\b','Hagi',new)
                if field=='decisions' and normalize_np and row['id'] in NP_DECISIONS:
                    new=NP_DECISIONS[row['id']]
                if new!=old:
                    row[field]=new;modified=True
                    changes.append(dict(file=str(path),id=row['id'],field=field,before=old,after=new))
        if modified:
            for original,updated in zip(before.get('rows',before.get('entries',[])),data.get('rows',data.get('entries',[]))):
                for key in set(original)|set(updated):
                    if key not in ('target','en','role','decisions') and original.get(key)!=updated.get(key):
                        raise ValueError('Protected metadata changed: '+str(path))
            pending.append((path,raw,data))
    preview={'input_sha256':inputs,'changes':changes}
    print(json.dumps({'changes':len(changes),'sample':changes[:6]},ensure_ascii=True,indent=2))
    if a.write:
        if not a.approved_preview or not a.snapshot_dir:
            raise ValueError('Writer requires reviewed full preview and fresh snapshot directory')
        if json.loads(a.approved_preview.read_text(encoding='utf8'))!=preview:
            raise ValueError('Preview or input files changed; review a fresh dry run')
        if a.snapshot_dir.exists():raise ValueError('Snapshot directory must be fresh')
        for path,raw,data in pending:
            if digest(path.read_bytes())!=inputs[str(path)]:raise ValueError('Input changed: '+str(path))
        a.snapshot_dir.mkdir(parents=True)
        for path,raw,data in pending:
            snapshot=a.snapshot_dir/path.parent.name/path.name
            snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(raw)
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    elif a.preview_path:
        a.preview_path.parent.mkdir(parents=True,exist_ok=True)
        a.preview_path.write_text(json.dumps(preview,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print('Full dry preview saved: '+str(a.preview_path))
    else:print('DRY RUN: no changes written.')

if __name__=='__main__':main()
