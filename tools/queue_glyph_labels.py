"""Queue reviewed glyph-index labels with stable IDs; default dry-run."""
import argparse,collections,hashlib,json,pathlib

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    data=json.loads(pathlib.Path('work/source/font_audit/sys_tbl_names.json').read_text(encoding='utf8'))
    if not data['summary'].get('round_trip_verified') or data['summary']['unresolved_glyphs']:
        raise ValueError('Glyph inventory requires reviewed exact round trips')
    root=pathlib.Path('work/translation/en');dest=root/'glyph_labels_0001.json'
    existing={r['id']:r for r in json.loads(dest.read_text(encoding='utf8'))['rows']} if dest.exists() else {}
    groups=collections.OrderedDict()
    for row in data['rows']:groups.setdefault(row['source'],[]).append(row)
    gloss=json.loads(pathlib.Path('work/glossary/glossary.en.json').read_text(encoding='utf8'))['entries']
    names={g['ja']:g['en'] for g in gloss}
    for g in gloss:
        for alias in g.get('aliases',[]):
            if any('\u3040'<=c<='\u9fff' for c in alias):names.setdefault(alias,g['en'])
    rows=[]
    for source,occ in groups.items():
        first=occ[0];ident=hashlib.sha256(('glyph-index:'+source).encode('utf8')).hexdigest()[:20]
        if ident in existing:rows.append(existing[ident]);continue
        target=names.get(source,'')
        rows.append(dict(id=ident,file='btl/sys_tbl.bin',offset=first['offset'],
            byte_length=first['byte_length'],encoding='local-glyph-id-u16le',category='battle_name_labels',
            source=source,target=target,status='draft' if target else 'untranslated',
            occurrences=[dict(row_index=r['row_index'],offset=r['offset'],reference_offset=r['reference_offset'],byte_length=r['byte_length'],role=r['role']) for r in occ],
            context='Battle/system name table; some tail records may be debug labels. Runtime visibility unverified.',
            decisions='Exact glossary term applied; native glyph map verified by byte round trip.' if target else 'Requires glossary match or reviewed translation.',
            notes='Relocate English glyph stream and rebuild atlas; do not overwrite existing byte slots.'))
    print(json.dumps(dict(rows=len(rows),occurrences=len(data['rows']),glossary_drafts=sum(bool(r['target']) for r in rows),sample=rows[:4]),ensure_ascii=True,indent=2))
    if a.write:dest.write_text(json.dumps(dict(schema_version=1,language='en',rows=rows),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    else:print('DRY RUN: no queue written.')

if __name__=='__main__':main()
