"""Dry-only gallery/list/glyph integration planner. No asset or archive writer.

Returns original-guarded in-memory replacements for the proven CP932 formats.
Local-u16 atlas labels are audited but blocked until their renderer/atlas has
an explicit English contract. ASCII codepoints must never masquerade as IDs.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct

import append_cpk
import decode_glyph_tables
import extract_tables
import rebuild_gallery
from build_translation_archive import MemoryAsset
from dialogue_tokens import validate_controls
from extract_corpus import controls
from rebuild_dialogue import encode_target, PUNCTUATION, NATIVE_FALLBACK, format_placeholders, TOKENS

ORIGINAL_SYMBOLS = frozenset('\u25cb\uff5e\u3008\u3009')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def targets(root):
    result, snapshots = {}, []
    for path in sorted(root.glob('*.json')):
        if path.name.endswith('.en.json'):
            continue
        raw = path.read_bytes()
        snapshots.append({'path': str(path), 'sha256': sha(raw)})
        for row in json.loads(raw).get('rows', []):
            if row['id'] in result:
                raise ValueError('Duplicate working translation ID: ' + row['id'])
            result[row['id']] = row
    return result, snapshots


def encoded(row, target, policy, charset='', symbols=False):
    if row['source'] != target['source']:
        raise ValueError('Working source differs from verified occurrence')
    if not target.get('target'):
        raise ValueError('Unfilled translation: ' + target['id'])
    if not symbols:
        return encode_target(target['target'], row['source'], **policy)
    source,text=row['source'],target['target']
    validate_controls(source,text)
    if format_placeholders(source)!=format_placeholders(text,source):raise ValueError('Format placeholders differ')
    retained=sorted(set(text)&ORIGINAL_SYMBOLS)
    for char in retained:
        if text.count(char)!=source.count(char) or char not in charset:
            raise ValueError('Original symbol count/charset guard failed')
    # Validate the established repertoire/control policy independently, without
    # weakening the shared encoder. Only the explicitly listed visible symbols
    # are removed for this check, after exact original count validation above.
    plain_source=''.join(c for c in source if c not in retained)
    plain_target=''.join(c for c in text if c not in retained)
    _,mapped=encode_target(plain_target,plain_source,**policy)
    if policy['map_punctuation']:
        for a,b in PUNCTUATION.items():text=text.replace(a,b)
    out=bytearray();cursor=0
    def chunk(plain):
        for char in plain:
            if 32<=ord(char)<=126:out.append(ord(char))
            elif policy['vwf_latin'] and char=='\u00e8':out.append(128)
            elif char in retained or (policy['native_fallback'] and char in NATIVE_FALLBACK):out.extend(char.encode('cp932'))
            else:raise ValueError('Unsupported character after original-symbol validation')
    for token in TOKENS.finditer(text):
        chunk(text[cursor:token.start()]);out.append(int(token.group()[1:3],16));cursor=token.end()
    chunk(text[cursor:])
    for char in retained:
        mapped.append({'codepoint':f'U+{ord(char):04X}','original_cp932':char.encode('cp932').hex(),'count':text.count(char),'original_count':source.count(char),'native_charset_index':charset.index(char),'slot_mapping_runtime_verified':False,'policy':'source-preserved symbol in original charset'})
    return bytes(out),mapped


def header(raw):
    width = struct.unpack_from('<I', raw)[0]
    if width not in (32, 48):
        raise ValueError('Unreviewed list header width')
    return list(struct.unpack_from('<' + str(width // 4) + 'I', raw))


def verify_inputs(args, report):
    """Fresh-input gate for a future caller-owned archive writer."""
    for item in report['target_inputs']:
        if sha(Path(item['path']).read_bytes()) != item['sha256']:
            raise ValueError('Working translation changed after dry plan')
    if report.get('dictionary_layout'):
        ref=report['dictionary_layout']['reference']
        for path,key in [(ref['font_report'],'font_dry_report_sha256'),(ref['geometry_proof'],'geometry_proof_sha256')]:
            if sha(Path(path).read_bytes())!=ref[key]:raise ValueError('Dictionary font/geometry evidence changed')
        for path,expected in ref['code_input_sha256'].items():
            if sha(Path(path).read_bytes())!=expected:raise ValueError('Dictionary preparation code changed')
        for item in report['dictionary_layout'].get('long_capacity',{}).get('input_snapshots',[]):
            if sha(Path(item['path']).read_bytes())!=item['sha256']:raise ValueError('Dictionary long-capacity evidence changed')
    for path,key in [(args.inventory,'original_inventory_sha256'),
                     (args.table_inventory,'table_inventory_sha256'),
                     (args.glyph_seeds,'glyph_seed_sha256'),
                     (args.occurrences,'occurrences_sha256')]:
        if sha(path.read_bytes()) != report[key]:
            raise ValueError('Source evidence changed after dry plan')
    for asset in report['assets']:
        if sha((args.source_root/asset['resource']).read_bytes()) != asset['original_sha256']:
            raise ValueError('Original extracted asset changed after dry plan')
    glyph=report['glyph_asset']
    if sha((args.source_root/glyph['resource']).read_bytes()) != glyph['original_sha256']:
        raise ValueError('Original glyph asset changed after dry plan')
    if args.archive and append_cpk.sha(args.archive) != args.expected_sha256:
        raise ValueError('Current archive changed after dry plan')


def relocate_sections(original, replacements):
    """Move whole downstream sections, including metadata/font/charset banks.

    LimitedBattle header[4] is BOTH enemy-list end and map-metadata start.
    Consequently changing only an end pointer or appending text is unsafe.
    All reviewed header offsets are remapped through the same splice ledger.
    """
    h = header(original)
    segments = sorted(replacements)
    cursor, result, ledger = 0, bytearray(), []
    for start, end, new in segments:
        if not cursor <= start < end <= len(original):
            raise ValueError('Overlapping/out-of-range list sections')
        result.extend(original[cursor:start])
        newstart = len(result)
        result.extend(new)
        ledger.append((start, end, newstart, len(result)))
        cursor = end
    result.extend(original[cursor:])

    def mapped(offset):
        delta = 0
        for start, end, newstart, newend in ledger:
            if start < offset < end:
                raise ValueError('Header points inside replaced text section')
            if offset >= end:
                delta += (newend-newstart)-(end-start)
        return offset + delta

    allowed = set()
    for i, offset in enumerate(h[1:], 1):
        if offset:
            if not h[0] <= offset <= len(original):
                raise ValueError('Unreviewed header offset')
            value = mapped(offset)
            struct.pack_into('<I', result, i*4, value)
            if value != offset:
                allowed.update(range(i*4, i*4+4))
    # Every nontext byte is retained in original order, modulo header offsets.
    oldcursor = newcursor = 0
    for start, end, newstart, newend in ledger + [(len(original), len(original), len(result), len(result))]:
        oldchunk, newchunk = original[oldcursor:start], result[newcursor:newstart]
        if len(oldchunk) != len(newchunk):
            raise ValueError('Nontext segment size differs')
        if any(a != b and oldcursor+i not in allowed
               for i, (a, b) in enumerate(zip(oldchunk, newchunk))):
            raise ValueError('Nontext metadata/font/charset/suffix bytes changed')
        oldcursor, newcursor = end, newend
    return bytes(result), ledger


def lists(original, specs, rows, replacements):
    h = header(original)
    sections = []
    for _, meta_index, text_index, category in specs:
        start, end = h[text_index], h[text_index+1]
        count = struct.unpack_from('<I', original, h[meta_index])[0]
        selected = sorted((r for r in rows if r['category'] == category), key=lambda r:r['row_index'])
        if [r['row_index'] for r in selected] != list(range(count)):
            raise ValueError('List occurrence indices/count disagree')
        cursor, blob = start, bytearray()
        for row in selected:
            raw = original[row['offset']:row['offset']+row['byte_length']]
            if row['offset'] != cursor or sha(raw)[:20] != row['id']:
                raise ValueError('List occurrence hash or contiguous offset differs')
            cursor += len(raw)
            blob.extend(replacements.get((category,row['row_index']), raw))
        padding = original[cursor:end]
        if any(padding):
            raise ValueError('Unknown nonzero list suffix')
        blob.extend(padding)
        if replacements:
            blob.extend(bytes((-len(blob)) % 16))
        sections.append((start,end,bytes(blob)))
    rebuilt, ledger = relocate_sections(original, sections)
    newh = header(rebuilt)
    for _, meta_index, text_index, category in specs:
        start,end = newh[text_index],newh[text_index+1]
        text = rebuilt[start:end].rstrip(b'\0')
        if not text.endswith(b'\x0e'):
            raise ValueError('Rebuilt list terminal changed')
        items = text[:-1].split(b'\x11\r\n')
        selected = sorted((r for r in rows if r['category']==category),key=lambda r:r['row_index'])
        if len(items)!=len(selected):
            raise ValueError('List separator/count changed')
        for i,(item,row) in enumerate(zip(items,selected)):
            suffix=bytes.fromhex(row['structure']['separator_hex'])
            if item+suffix != replacements.get((category,i),original[row['offset']:row['offset']+row['byte_length']]):
                raise ValueError('Rebuilt list occurrence differs')
        if rebuilt[newh[meta_index]:newh[meta_index]+4] != original[h[meta_index]:h[meta_index]+4]:
            raise ValueError('List metadata count changed')
    return rebuilt,ledger


def indexed(original, replacements):
    h=header(original);start,end=h[2:4]
    if end!=len(original):
        raise ValueError('Unexpected indexed-table suffix')
    offsets=struct.unpack_from('<256I',original,start);blob=start+1024
    if offsets[0]!=0 or list(offsets)!=sorted(set(offsets)):
        raise ValueError('Indexed references are not strictly monotonic')
    chunks=[];new_offsets=[];out=bytearray()
    for i,off in enumerate(offsets):
        stop=offsets[i+1] if i<255 else end-blob
        full=original[blob+off:blob+stop];raw=full.rstrip(b'\0')
        if not raw.endswith(b'\x0e') or b'\0' in raw:
            raise ValueError('Bad indexed record termination')
        new_offsets.append(len(out));new=replacements.get(i,raw)
        if not new.endswith(b'\x0e') or b'\0' in new:
            raise ValueError('Replacement indexed termination differs')
        out.extend(new);out.extend(full[len(raw):]);chunks.append((raw,new))
    if replacements:out.extend(bytes((-(blob+len(out)))%16))
    rebuilt=bytearray(original[:start]);rebuilt.extend(struct.pack('<256I',*new_offsets));rebuilt.extend(out)
    struct.pack_into('<I',rebuilt,12,len(rebuilt))
    if rebuilt[16:start]!=original[16:start] or rebuilt[:12]!=original[:12]:
        raise ValueError('Indexed font/charset/prefix changed')
    for i,off in enumerate(new_offsets):
        stop=new_offsets[i+1] if i<255 else len(rebuilt)-blob
        if rebuilt[blob+off:blob+stop].rstrip(b'\0')!=chunks[i][1]:
            raise ValueError('Indexed reparse differs')
    return bytes(rebuilt)


def build(args):
    queue,snapshots=targets(args.targets)
    invraw=args.inventory.read_bytes();inv=json.loads(invraw)
    originals={e['path']:e for e in inv['entries']}
    policy=dict(map_punctuation=args.ascii_punctuation,vwf_latin=args.vwf_latin,native_fallback=args.native_fallback)
    reports,assets,failures=[],[],[]
    dictionary_layout=None
    if getattr(args,'long_dictionary_wraps',False) and not getattr(args,'dictionary_wrap',False):
        raise ValueError('Long dictionary wraps require the measured dictionary wrap policy')
    if getattr(args,'dictionary_wrap',False):
        import dictionary_wrap
        dictionary_widths,dictionary_reference=dictionary_wrap.reference()
        dictionary_layout={'reference':dictionary_reference,'prepared':[],'held':[],
                           'unmeasured_routes_not_wrapped':True}
        if getattr(args,'long_dictionary_wraps',False):
            import dictionary_capacity_guard
            dictionary_layout['long_capacity']=dictionary_capacity_guard.reference()
            dictionary_layout['long_capacity']['input_snapshots'].append(dict(
                path='tools/dictionary_capacity_guard.py',sha256=sha(Path('tools/dictionary_capacity_guard.py').read_bytes())))
    table_rows,sections=extract_tables.extract(args.source_root)
    table_snapshot=args.table_inventory.read_bytes()
    if json.loads(table_snapshot)['rows'] != table_rows:
        raise ValueError('Re-extracted table occurrences differ from saved inventory')
    byfile=collections.defaultdict(list)
    for row in table_rows:byfile[row['file']].append(row)
    occurrences=json.loads(args.occurrences.read_text(encoding='utf8'))
    gallery=collections.defaultdict(list)
    for o in occurrences:
        if o['file'].startswith('menu/Gallery/'):gallery[o['file']].append(o)

    def original(name):
        path=(args.source_root/name).resolve()
        if not path.is_relative_to(args.source_root.resolve()):raise ValueError('Path escape')
        data=path.read_bytes();e=originals[name]
        if len(data)!=e['extract_size'] or sha(data)!=e['sha256']:raise ValueError('Original asset inventory SHA/size differs')
        return data

    for name in sorted(set(byfile)|set(gallery)):
        try:
            raw=original(name);entries=[]
            if name in gallery:
                old=rebuild_gallery.parse(name,raw);assert rebuild_gallery.rebuild(name,raw,old['text'])[0]==raw
                oo=gallery[name]
                if len(oo)!=1 or oo[0]['row_index']!=0 or oo[0]['offset']!=old['prose_start'] or oo[0]['byte_length']!=len(old['text']):raise ValueError('Gallery occurrence bounds differ')
                identity=sha(old['text'])[:20]
                if oo[0]['translation_id']!=identity:raise ValueError('Gallery occurrence ID differs')
                row={'id':identity,'source':controls(old['text'].decode('cp932'))}
                enc,mapping=encoded(row,queue[identity],policy,old['charset'],args.native_original_symbols)
                layout=None
                if dictionary_layout is not None and name.startswith('menu/Gallery/dic/'):
                    try:
                        wrapped,layout=dictionary_wrap.wrap(enc,row['source'],queue[identity]['target'],dictionary_widths)
                        layout['wrap_installed']=layout['within_observed_15_physical_line_scroll_range']
                        if not layout['wrap_installed'] and dictionary_layout.get('long_capacity'):
                            entry=int(name.removeprefix('menu/Gallery/dic/GgHelp').removesuffix('.bin'))
                            if dictionary_capacity_guard.LONG_ROWS.get(entry)!=identity or layout['physical_lines']>42:
                                raise ValueError('Long dictionary record exceeds reviewed static scope')
                            layout.update(wrap_installed=True,static_capacity_supported=True,
                                          allocation_bytes=layout['physical_lines']*232,
                                          reachable_scroll_first_rows=list(range(max(1,layout['physical_lines']-6))))
                        if layout['wrap_installed']:enc=wrapped
                        else:layout['raw_full_target_retained_due_to_unproved_scroll_capacity']=True
                        dictionary_layout['prepared'].append({'resource':name,'id':identity,**layout})
                    except ValueError as error:
                        # Retain full raw wording, explicitly distinguish the
                        # one native-symbol entry from prepared Latin wraps.
                        if name!='menu/Gallery/dic/GgHelp133.bin':raise
                        dictionary_layout['held'].append({'resource':name,'id':identity,'reason':str(error),'raw_target_retained':True,'native_symbol_extent_measured':False})
                rebuilt,new=rebuild_gallery.rebuild(name,raw,enc)
                entries=[{'id':identity,'row_index':0,'original_sha256':sha(old['text']),'encoded_sha256':sha(enc),'mapping':mapping}]
                if layout is not None:entries[0]['dictionary_layout']=layout
                kind='gallery_prose'
            else:
                rr=byfile[name];replacement={}
                indexed_format=name in dict(extract_tables.INDEXED_TABLES)
                specs=[s for s in extract_tables.TABLES if s[0]==name]
                if indexed_format:assert indexed(raw,{})==raw
                else:assert lists(raw,specs,rr,{})[0]==raw
                for row in rr:
                    hh=header(raw)
                    if indexed_format:font_end,text_start=hh[1],hh[2]
                    else:
                        spec=next(s for s in specs if s[3]==row['category']);ti=spec[2];font_end,text_start=hh[ti-1],hh[ti]
                    charset=raw[font_end:text_start].rstrip(b'\0').decode('cp932')
                    enc,mapping=encoded(row,queue[row['id']],policy,charset,args.native_original_symbols)
                    key=row['row_index'] if indexed_format else (row['category'],row['row_index'])
                    replacement[key]=enc
                    entries.append({'id':row['id'],'row_index':row['row_index'],'category':row['category'],'original_sha256':sha(raw[row['offset']:row['offset']+row['byte_length']]),'encoded_sha256':sha(enc),'mapping':mapping})
                rebuilt=indexed(raw,replacement) if indexed_format else lists(raw,specs,rr,replacement)[0]
                kind='indexed_table' if indexed_format else 'separated_list'
            reports.append({'resource':name,'kind':kind,'original_sha256':sha(raw),'rebuilt_sha256':sha(rebuilt),'original_bytes':len(raw),'rebuilt_bytes':len(rebuilt),'identity_roundtrip':True,'original_inventory_guard':True,'all_occurrences_verified':True,'nontext_bytes_preserved':True,'rows':entries,'runtime_verified':False})
            assets.append((name,MemoryAsset(name,rebuilt)))
        except (ValueError,KeyError,UnicodeError,AssertionError,struct.error) as error:
            failures.append({'resource':name,'reason':str(error)})

    # Re-derive the reviewed map from its actual source and seed witnesses.
    seeds=json.loads(args.glyph_seeds.read_text(encoding='utf8'));name=seeds['file'];raw=original(name)
    glyph_rows=decode_glyph_tables.table(raw);mapping,witnesses=decode_glyph_tables.decode(glyph_rows,seeds)
    inverse={v:k for k,v in mapping.items()};glyph_reports=[]
    for row in glyph_rows:
        if row['unresolved_glyphs']:raise ValueError('Unresolved original glyph')
        encoded_original=b''.join(struct.pack('<H',inverse[ch]) for ch in row['source'])
        encoded_original+=bytes(row['byte_length']-len(encoded_original))
        if raw[row['offset']:row['offset']+row['byte_length']]!=encoded_original:raise ValueError('Glyph identity roundtrip differs')
        identity=sha(('glyph-index:'+row['source']).encode('utf8'))[:20];target=queue[identity]
        if target['source']!=row['source']:raise ValueError('Glyph queue source differs')
        expected={'row_index':row['row_index'],'offset':row['offset'],'reference_offset':row['reference_offset'],'byte_length':row['byte_length'],'role':row['role']}
        if expected not in target['occurrences']:raise ValueError('Glyph occurrence metadata differs')
        validate_controls(row['source'],target['target'])
        glyph_reports.append({'id':identity,'row_index':row['row_index'],'source_bytes_sha256':sha(encoded_original),'drafted':bool(target['target']),'missing_native_characters':[f'U+{ord(c):04X}' for c in sorted(set(target['target'])-set(inverse))],'status':'blocked_renderer_atlas_contract'})
    report={'schema_version':1,'version':args.version,'status':'dry_extended_plan_runtime_unverified','runtime_verified':False,'full_game_translation_complete':False,'policy':dict(policy,native_original_symbols=args.native_original_symbols),'target_inputs':snapshots,'original_inventory_sha256':sha(invraw),'table_inventory_sha256':sha(table_snapshot),'glyph_seed_sha256':sha(args.glyph_seeds.read_bytes()),'occurrences_sha256':sha(args.occurrences.read_bytes()),'assets':reports,'failures':failures,'gallery_resources':len(gallery),'gallery_unique_rows':len({o['translation_id'] for oo in gallery.values() for o in oo}),'table_occurrences':len(table_rows),'table_unique_rows':len({r['id'] for r in table_rows}),'glyph_asset':{'resource':name,'original_sha256':sha(raw),'identity_roundtrips':len(glyph_rows),'native_glyphs':len(mapping),'unique_rows':len({r['id'] for r in glyph_reports}),'rows':glyph_reports,'replacement_planned':False,'reason':'u16 values are local native atlas IDs. Printable ASCII is not a compatible encoding; an English atlas/renderer contract is required.'},'safe_replacements':len(assets),'limitations':['Gallery and table fonts remain original; ASCII renderer, cursor, measurement, native symbols and layout require separate per-path QA.','No automatic wrapping added; targets and controls are never shortened.','Glyph labels are audited but not falsely counted installed.','Planner sources are original validated extraction. When appended onto a current CPK, untouched current CPL/cache/resource changes are retained; selected gallery/table text is replaced from the full current target.','Human scene review is not inferred from structural checks.','No archive/data writer exists in this tool.']}
    if dictionary_layout is not None:
        if len(dictionary_layout['prepared'])!=134 or len(dictionary_layout['held'])!=1:
            raise ValueError('Dictionary wrap scope changed from reviewed134+1')
        dictionary_layout['prepared_resources']=len(dictionary_layout['prepared'])
        dictionary_layout['held_resources']=len(dictionary_layout['held'])
        dictionary_layout['physical_line_distribution']=dict(collections.Counter(x['physical_lines'] for x in dictionary_layout['prepared']))
        dictionary_layout['beyond_observed_15_line_scroll_resources']=[x['resource'] for x in dictionary_layout['prepared'] if not x['within_observed_15_physical_line_scroll_range']]
        dictionary_layout['wrapped_resources']=sum(x['wrap_installed'] for x in dictionary_layout['prepared'])
        dictionary_layout['prepared_but_deferred_wrap_resources']=len(dictionary_layout['prepared'])-dictionary_layout['wrapped_resources']
        report['dictionary_layout']=dictionary_layout
        report['limitations']=[x for x in report['limitations'] if not x.startswith('No automatic wrapping')]
        report['limitations'].append('Dictionary-only soft spaces become11 controls at proven330px/45glyph limits; original controls and wording are reversible. More than15physical lines exceeds saved scroll QA and needs separate validation; other gallery routes stay unwrapped.')
    if args.archive:
        if not args.expected_sha256:raise ValueError('Explicit archive SHA required')
        plan=append_cpk.plan(args.archive,assets,args.expected_sha256)
        hh,ee,patches,appended,end=plan
        report['archive_plan']={'input':str(args.archive),'input_sha256':args.expected_sha256,'original_bytes':args.archive.stat().st_size,'output_bytes':end,'replacements':len(appended),'shared_extents_preserved':True,'selected_toc_only':True,'unselected_current_assets_preserved':True,'alignment':2048}
    verify_inputs(args,report)
    return report,assets


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--targets',type=Path,default=Path('work/translation/en'))
    p.add_argument('--source-root',type=Path,default=Path('work/source/cpk'))
    p.add_argument('--inventory',type=Path,default=Path('work/source/cpk_inventory.json'))
    p.add_argument('--table-inventory',type=Path,default=Path('work/source/table_strings.json'))
    p.add_argument('--occurrences',type=Path,default=Path('work/source/text_occurrences.json'))
    p.add_argument('--glyph-seeds',type=Path,default=Path('work/source/font_audit/glyph_seeds.json'))
    p.add_argument('--version',default='0.1.16')
    p.add_argument('--ascii-punctuation',action='store_true');p.add_argument('--vwf-latin',action='store_true');p.add_argument('--native-fallback',action='store_true')
    p.add_argument('--native-original-symbols',action='store_true',help='Preserve only approved original symbols with exact source counts and original charset membership')
    p.add_argument('--dictionary-wrap',action='store_true',help='Prepare only measured dictionary-route330px/45glyph soft breaks')
    p.add_argument('--long-dictionary-wraps',action='store_true',help='Include eight statically proved longer records; runtime allocation/scroll QA remains required')
    p.add_argument('--archive',type=Path);p.add_argument('--expected-sha256')
    p.add_argument('--details',action='store_true')
    args=p.parse_args();report,assets=build(args)
    public=report if args.details else {k:v for k,v in report.items() if k not in ('target_inputs','assets','glyph_asset','dictionary_layout')}
    if not args.details:
        if report.get('dictionary_layout'):
            public['dictionary_layout_summary']={k:v for k,v in report['dictionary_layout'].items() if k not in ('reference','prepared','held')}
        public['asset_sample']=[{k:v for k,v in a.items() if k!='rows'} for a in report['assets'][:2]];public['glyph_summary']={k:v for k,v in report['glyph_asset'].items() if k!='rows'}
        public['row_sample']=[r for a in report['assets'][:2] for r in a['rows'][:2]]
    print(json.dumps(public,ensure_ascii=True,indent=2));print('DRY RUN: no files written.')


if __name__=='__main__':main()
