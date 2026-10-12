"""Decode validated dialogue tables and gallery prose; dry-run before --write.

No texture bytes or sorted font character maps are counted as dialogue.
English translations are keyed by exact source bytes and shared by occurrences.
"""
import argparse, collections, hashlib, json, pathlib, re, struct
from unpack_cpk import inventory, crilayla

JP = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uff66-\uff9d]')
PREFIXES = ('phase/bin/', 'fld/talk/', 'menu/Gallery/prof/',
            'menu/Gallery/dic/', 'menu/Gallery/kno/', 'menu/Gallery/tb/',
            'menu/Gallery/qm/', 'menu/Gallery/qs/', 'menu/Gallery/tf/', 'menu/Gallery/tm/',
            'btl/res/', 'btl/skit/')

def u32(data, off): return struct.unpack_from('<I',data,off)[0]

def controls(text):
    return ''.join('{'+f'{ord(c):02X}'+'}' if ord(c)<32 else c for c in text)

def decode_file(name, data):
    head=struct.unpack_from('<8I',data)
    battle=name.startswith(('btl/res/','btl/skit/'))
    if battle:
        width=head[0]
        if not 32<=width<=640 or width%16 or width>len(data):
            raise ValueError('Unknown battle container header')
        head=struct.unpack_from('<'+str(width//4)+'I',data)
    elif head[0]!=32: raise ValueError('Unknown container header')
    if name.startswith(('phase/bin/','fld/talk/')) or battle:
        if battle:
            candidates=[]
            for start,end in zip(head,head[1:]):
                if not width<=start<end<=len(data) or end-start<16: continue
                zero,n,w1,w2=struct.unpack_from('<4I',data,start)
                if zero==0 and w1==16 and w2==16 and n<=10000:
                    candidates.append((start,end))
            if len(candidates)!=1:
                raise ValueError('Expected one validated battle dialogue section, found '+str(len(candidates)))
            start,end=candidates[0]
        else:
            start,end=head[1:3]
        if not 32<=start<end<=len(data): raise ValueError('Invalid dialogue section')
        zero,n,w1,w2=struct.unpack_from('<4I',data,start)
        if zero or w1!=16 or w2!=16 or n>10000: raise ValueError('Unknown dialogue table')
        desc=[struct.unpack_from('<3I',data,start+16+12*i) for i in range(n)]
        count=sum(x[1] for x in desc)
        refs_start=start+16+12*n
        blob=refs_start+8*count
        if blob>end: raise ValueError('Table exceeds section')
        refs=[struct.unpack_from('<2I',data,refs_start+8*i) for i in range(count)]
        offsets=[x[1] for x in refs]
        if offsets!=sorted(offsets) or any(o>=end-blob for o in offsets):
            raise ValueError('Nonmonotonic/out-of-range text references')
        for i,(ref_id,off) in enumerate(refs):
            stop=offsets[i+1] if i+1<count else end-blob
            raw=data[blob+off:blob+stop].rstrip(b'\0')
            text=raw.decode('cp932',errors='strict')
            if '\0' in text: raise ValueError('Embedded null in text row')
            if JP.search(text):
                yield i,blob+off,raw,text,{'reference_id':ref_id,
                    'reference_offset':refs_start+8*i+4,'blob_offset':blob,'section_offset':start}
    else:
        start,end=head[2:4]
        if not 32<=start<end<=len(data): raise ValueError('Invalid gallery prose section')
        raw=data[start:end].rstrip(b'\0')
        text=raw.decode('cp932',errors='strict')
        if '\0' in text: raise ValueError('Embedded null in gallery prose')
        if JP.search(text): yield 0,start,raw,text,{'header_offset':8}

def category(name):
    if name.startswith('btl/res/'): return 'battle_dialogue'
    if name.startswith('btl/skit/'): return 'battle_skits'
    if name.startswith('phase/'): return 'story_dialogue'
    if name.startswith('fld/'): return 'field_dialogue'
    return {'prof':'character_profiles','dic':'dictionary','kno':'world_lore','tb':'tutorials',
            'qm':'main_quest_objectives','qs':'side_quests','tf':'field_tutorials','tm':'menu_tutorials'}[name.split('/')[2]]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=pathlib.Path,default=pathlib.Path('work/source/PSP_GAME/USRDIR/HP.CPK'))
    p.add_argument('--write',action='store_true')
    p.add_argument('--limit',type=int,default=0,help='Inspect only this many resource entries')
    a=p.parse_args()
    _,entries=inventory(a.archive)
    chosen=[x for x in entries if x['path'].startswith(PREFIXES)]
    if a.limit: chosen=chosen[:a.limit]
    unique={}; occurrences=[]; errors=[]; by_category=collections.Counter(); characters=collections.Counter()
    with a.archive.open('rb') as stream:
        for e in chosen:
            name=e['path']; local=pathlib.Path('work/source/cpk')/name
            if local.exists() and local.stat().st_size==e['extract_size']: data=local.read_bytes()
            else:
                stream.seek(e['offset']);data=stream.read(e['stored_size'])
                if e['compression']=='CRILAYLA': data=crilayla(data,e['extract_size'])
            try:
                decoded=list(decode_file(name,data))
                for row_index,offset,raw,text,structure in decoded:
                    cat=category(name); key=hashlib.sha256(raw).hexdigest()[:20]
                    source=controls(text)
                    occurrence={'id':name+f':{row_index:04d}','translation_id':key,
                        'file':name,'row_index':row_index,'offset':offset,'byte_length':len(raw),
                        'category':cat,'structure':structure}
                    occurrences.append(occurrence);by_category[cat]+=1;characters[cat]+=len(JP.findall(text))
                    if key not in unique:
                        unique[key]={'id':key,'file':name,'offset':offset,'byte_length':len(raw),
                            'encoding':'cp932','category':cat,'source':source,'target':'','status':'untranslated',
                            'occurrences':[]}
                    unique[key]['occurrences'].append(occurrence['id'])
            except (ValueError,UnicodeDecodeError,struct.error) as error:
                errors.append({'file':name,'reason':str(error)})
    rows=list(unique.values())
    summary={'version':'0.1.0','scope':'Validated CPK dialogue tables and gallery prose only',
        'resource_files_examined':len(chosen),'resource_files_with_text':len(set(x['file'] for x in occurrences)),
        'occurrence_rows':len(occurrences),'unique_translation_rows':len(rows),
        'japanese_characters_occurrences':sum(characters.values()),
        'japanese_characters_unique':sum(len(JP.findall(x['source'])) for x in rows),
        'by_category_occurrences':dict(by_category),'by_category_unique':dict(collections.Counter(x['category'] for x in rows)),
        'by_category_japanese_characters':dict(characters),'unresolved_selected_resources':len(errors),
        'unresolved':errors,'excluded':'Other CPK formats, executable text, image text, movies and install archive; audit separately.'}
    print(json.dumps({**summary,'unresolved':errors[:8]},indent=2))
    print('Sample rows:',json.dumps(rows[:3],ensure_ascii=False,indent=2))
    if not a.write:
        print('DRY RUN: no files written. Inspect sample before --write.');return
    root=pathlib.Path('work/source');root.mkdir(parents=True,exist_ok=True)
    (root/'text_inventory.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (root/'text_occurrences.json').write_text(json.dumps(occurrences,indent=2)+'\n',encoding='utf-8')
    dest=pathlib.Path('work/translation/en');dest.mkdir(parents=True,exist_ok=True)
    # Preserve previous targets by stable source hash when extraction is rerun.
    prior={}; prior_order={}
    for old in sorted(dest.glob('batch_*.json')):
        if old.name.endswith('.en.json'): continue
        for row in json.loads(old.read_text(encoding='utf-8'))['rows']:
            prior_order[row['id']]=len(prior_order)
            prior[row['id']]=row
    # New categories append to the existing queue rather than shifting active slices.
    rows.sort(key=lambda row:prior_order.get(row['id'],len(prior_order)))
    for i in range(0,len(rows),80):
        batch=rows[i:i+80]
        for row in batch:
            if row['id'] in prior:
                row.update({k:v for k,v in prior[row['id']].items() if k in ('target','status','notes','context','decisions')})
        path=dest/f'batch_{i//80+1:04d}.json'
        path.write_text(json.dumps({'schema_version':1,'language':'en','rows':batch},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Wrote',len(rows),'unique rows in',(len(rows)+79)//80,'batches')

if __name__=='__main__': main()
