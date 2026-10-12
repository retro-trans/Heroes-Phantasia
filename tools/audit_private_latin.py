"""Read-only source collision/repertoire proof for the candidate accent codec."""
import hashlib,json
from pathlib import Path
from dialogue_tokens import text_bytes
from private_latin import CHAR_BYTES, cases


def audit():
    path=Path('work/source/text_occurrences.json');occ=json.loads(path.read_text())
    seen=set();cache={};collisions=[];byte_count=0
    for row in occ:
        key=(row['file'],row['offset'],row['byte_length'])
        if key in seen:continue
        seen.add(key)
        if key[0] not in cache:cache[key[0]]=(Path('work/source/cpk')/key[0]).read_bytes()
        blob=cache[key[0]][key[1]:key[1]+key[2]]
        if len(blob)!=key[2]:raise ValueError('Source occurrence extends outside file')
        byte_count+=len(blob)
        for name,value in [('DEL',b'\x7f'),('private_a',b'\xf0\x40'),('private_e',b'\xf0\x41')]:
            if value in blob:collisions.append(dict(file=key[0],offset=key[1],kind=name))
    from extract_cpl_text import extract
    cpl=extract();supplemental=0;cpl_rows=0;exe_sources=0;repertoire={}
    def extra_source(row):
        nonlocal byte_count,supplemental
        key=(row['file'],row['offset'],row['byte_length'])
        if key in seen:return
        path=Path('work/source/cpk')/key[0]
        if not path.is_file():return
        seen.add(key);supplemental+=1
        if key[0]not in cache:cache[key[0]]=path.read_bytes()
        blob=cache[key[0]][key[1]:key[1]+key[2]]
        if len(blob)!=key[2]:raise ValueError('Supplemental source range outside file')
        byte_count+=len(blob)
        for name,value in [('DEL',b'\x7f'),('private_a',b'\xf0\x40'),('private_e',b'\xf0\x41')]:
            if value in blob:collisions.append(dict(file=key[0],offset=key[1],kind=name))
    for row in cpl['rows']:extra_source(row);cpl_rows+=1
    for p in sorted(Path('work/translation/en').glob('*.json')):
        if p.name.endswith('.en.json'):continue
        for row in json.loads(p.read_text(encoding='utf-8')).get('rows',[]):
            if not p.name.startswith('batch_') and not row.get('category','').startswith('executable'):
                if all(k in row for k in ('file','offset','byte_length')):extra_source(row)
            if row.get('category','').startswith('executable'):
                exe_sources+=1;blob=text_bytes(row['source'],signature_only=True)
                for name,value in [('DEL',b'\x7f'),('private_a',b'\xf0\x40'),('private_e',b'\xf0\x41')]:
                    if value in blob:collisions.append(dict(file=str(p),id=row['id'],kind=name))
            for c in row.get('target',''):
                if ord(c)>126:repertoire[c]=repertoire.get(c,0)+1
    private_collisions=[x for x in collisions if x['kind']!='DEL']
    if private_collisions:raise ValueError(f'PUA codec collides with {len(private_collisions)} source records: {private_collisions}')
    return dict(dry_only=True,source_occurrences_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                unique_source_ranges=len(seen),source_files=len(cache),source_bytes=byte_count,
                executable_source_rows=exe_sources,collisions=collisions,
                cpl_source_files=len(cpl['files']),cpl_name_rows=cpl_rows,supplemental_unique_ranges=supplemental,
                target_nonascii_repertoire={f'U+{ord(c):04X}':n for c,n in sorted(repertoire.items())},
                proposed_codec={f'U+{ord(c):04X}':b.hex() for c,b in CHAR_BYTES.items()},
                codec_cases=cases(),scope='All indexed original text ranges and executable source queue strings; not arbitrary binary/nonindexed formatter output.',
                runtime_verified=False)


if __name__=='__main__':print(json.dumps(audit(),indent=2))
