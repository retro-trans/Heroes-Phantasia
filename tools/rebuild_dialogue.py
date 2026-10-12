"""Rebuild indexed dialogue resources into fresh blobs; dry-run by default.

No CPK/ISO mutation. Printable English uses ASCII bytes and {XX} controls;
non-ASCII is rejected unless an explicit punctuation or VWF Latin policy applies.
--vwf-latin maps the supported accent to the candidate's private single-byte slot.
--native-fallback preserves symbol counts and wide-space padding in CP932;
mixed-font layout still needs runtime testing.
IDs, group membership, unselected rows, and trailing sections are preserved.
Native font/classification/layout hooks are a separate requirement.
"""
import argparse, hashlib, json, pathlib, re, struct
from extract_corpus import controls, decode_file
from apply_targets import TOKENS
from dialogue_tokens import validate_controls
from private_latin import CHAR_BYTES, decode_bytes

PUNCTUATION = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
               '\u2013': '-', '\u2014': '--', '\u2026': '...', '\u00a0': ' '}
# A format conversion must not consume the first letter of an English word
# after a literal percentage, such as "100% damage".
PERCENT = re.compile(r'%(?:\d+\$)?[-+ #0]*\d*(?:\.\d+)?[sdifuxXc]')

def format_placeholders(text, source=None):
    """Preserve printf conversions while recognizing translated fullwidth percentages.

    A prose source such as １００％ is not a printf template. Its English
    `100% damage` must not be mistaken for the otherwise valid `% d` conversion.
    Only percentages present in that original source are masked.
    """
    if source is not None and '％' in source:
        import unicodedata
        percentages=re.findall(r'[0-9０-９]+(?:[.．][0-9０-９]+)?％',source)
        for percentage in percentages:
            literal=unicodedata.normalize('NFKC',percentage)
            text=text.replace(literal, literal[:-1]+'％',1)
    return PERCENT.findall(text)
NATIVE_FALLBACK = frozenset('\u25cb\u00d7\u25b3\u25a1\u2605\u2606\u3000')

def parse(name, data):
    if not name.startswith(('phase/bin/', 'fld/talk/', 'btl/res/', 'btl/skit/')):
        raise ValueError('Only validated indexed dialogue containers are supported')
    width = struct.unpack_from('<I', data)[0]
    if not 32 <= width <= 640 or width % 16 or width > len(data):
        raise ValueError('Invalid container header width')
    head = list(struct.unpack_from('<'+str(width//4)+'I', data))
    if name.startswith(('phase/bin/', 'fld/talk/')):
        start, end = head[1:3]
    else:
        matches = [(s,e) for s,e in zip(head,head[1:])
                   if width <= s < e <= len(data) and e-s >= 16
                   and struct.unpack_from('<4I',data,s)[0::2] == (0,16)
                   and struct.unpack_from('<4I',data,s)[3] == 16]
        if len(matches) != 1: raise ValueError('Ambiguous dialogue section')
        start, end = matches[0]
    if not width <= start < end <= len(data): raise ValueError('Invalid section bounds')
    zero,n,w1,w2 = struct.unpack_from('<4I',data,start)
    if (zero,w1,w2) != (0,16,16) or n > 10000: raise ValueError('Invalid text table')
    desc = [struct.unpack_from('<3I',data,start+16+12*i) for i in range(n)]
    count = sum(d[1] for d in desc); rs = start+16+12*n; blob = rs+8*count
    if blob > end: raise ValueError('References exceed section')
    refs = [struct.unpack_from('<2I',data,rs+8*i) for i in range(count)]
    offsets = [r[1] for r in refs]
    if offsets != sorted(offsets) or any(o >= end-blob for o in offsets):
        raise ValueError('Invalid reference offsets')
    cursor = 0
    for _,size,off in desc:
        if size == 0:
            if off > min(offsets,default=end-blob) and off not in offsets:
                raise ValueError('Unverified empty-group text offset')
            continue
        if cursor+size > count or off != offsets[cursor]:
            raise ValueError('Unverified group-to-text offset relationship')
        cursor += size
    unique = sorted(set(offsets)); spans = {}
    for i,off in enumerate(unique):
        stop = unique[i+1] if i+1 < len(unique) else end-blob
        chunk = data[blob+off:blob+stop]; raw = chunk.rstrip(b'\0')
        text = raw.decode('cp932', errors='strict')
        if '\0' in text: raise ValueError('Embedded null')
        spans[off] = (raw, chunk[len(raw):])
    return {'head':head, 'start':start, 'end':end, 'desc':desc, 'refs':refs,
            'refs_start':rs, 'blob':blob, 'spans':spans}

def encode_target(target, source, map_punctuation=False, vwf_latin=False, native_fallback=False):
    validate_controls(source, target)
    if format_placeholders(source) != format_placeholders(target,source): raise ValueError('Format placeholder changed')
    mapped = []
    if map_punctuation:
        for char,replacement in PUNCTUATION.items():
            if char in target:
                mapped.append({'character':char, 'replacement':replacement, 'count':target.count(char)})
                target = target.replace(char,replacement)
    if vwf_latin:
        for char,encoded in CHAR_BYTES.items():
            if char in target:mapped.append({'character':char,'replacement_bytes':encoded.hex(),'count':target.count(char)})
    if native_fallback:
        for char in sorted(NATIVE_FALLBACK):
            # Stars are visible dialogue symbols and quest bullets. Reject
            # removal as well as addition under the native preservation policy.
            if char in '\u2605\u2606' and target.count(char) != source.count(char):
                raise ValueError('Native fallback character count differs from original')
            if char not in target: continue
            if char == '\u3000':
                # Single separators inside Japanese prose can become English
                # punctuation/ASCII spaces. Preserve multi-space layout runs.
                if target.count(char) > source.count(char) or re.findall('\u3000{2,}', target) != re.findall('\u3000{2,}', source):
                    raise ValueError('Native wide-space padding differs from original')
            elif target.count(char) != source.count(char):
                raise ValueError('Native fallback character count differs from original')
            mapped.append({'codepoint':f'U+{ord(char):04X}', 'preserved_cp932_bytes':char.encode('cp932').hex(),
                           'count':target.count(char), 'original_count':source.count(char), 'runtime_verified':False})

    def encode_plain(plain):
        encoded=bytearray()
        for char in plain:
            if 32 <= ord(char) <= 126: encoded.append(ord(char))
            elif vwf_latin and char in CHAR_BYTES: encoded.extend(CHAR_BYTES[char])
            elif native_fallback and char in NATIVE_FALLBACK: encoded.extend(char.encode('cp932'))
            else: raise ValueError('Non-ASCII target; explicit policy required')
        return bytes(encoded)

    parts = []; pos = 0
    for token in TOKENS.finditer(target):
        plain = target[pos:token.start()]
        parts.append(encode_plain(plain)); code = int(token.group()[1:3],16)
        if not 1 <= code < 32: raise ValueError('Only nonzero low-byte control tokens are supported')
        parts.append(bytes([code])); pos = token.end()
    plain = target[pos:]
    if re.search(r'\{[0-9A-Fa-f]{2}\}', TOKENS.sub('',target)): raise ValueError('Malformed control token')
    parts.append(encode_plain(plain))
    return b''.join(parts), mapped

def rebuild(name, original, replacements):
    old = parse(name, original); changed = {}; new_offsets = {}; blob = bytearray()
    first = min(old['spans'], default=old['end']-old['blob'])
    blob.extend(original[old['blob']:old['blob']+first])
    for index,(_,off) in enumerate(old['refs']):
        if index in replacements:
            if off in changed and changed[off] != replacements[index]: raise ValueError('Conflicting shared text reference')
            changed[off] = replacements[index]
    for index,(_,off) in enumerate(old['refs']):
        if off in changed and index not in replacements:
            raise ValueError('Partial selection of shared text would change an untouched reference')
    for off,(raw,pad) in old['spans'].items():
        new_offsets[off] = len(blob); blob.extend(changed.get(off,raw)); blob.extend(pad)
    delta = len(blob)-(old['end']-old['blob'])
    if replacements:
        # Preserve downstream 32-byte alignment without retaining a byte budget.
        extra = (-delta) % 32; blob.extend(bytes(extra)); delta += extra
    prefix = bytearray(original[:old['blob']])
    for i,(_,_,off) in enumerate(old['desc']):
        struct.pack_into('<I',prefix,old['start']+16+i*12+8,new_offsets.get(off,off))
    for i,(_,off) in enumerate(old['refs']):
        struct.pack_into('<I',prefix,old['refs_start']+i*8+4,new_offsets[off])
    for i,offset in enumerate(old['head']):
        if i and offset >= old['end']:
            if offset > len(original): raise ValueError('Header word is not a verified file offset')
            struct.pack_into('<I',prefix,i*4,offset+delta)
    result = bytes(prefix)+bytes(blob)+original[old['end']:]
    new = parse(name,result)
    assert result[new['end']:] == original[old['end']:]
    assert result[len(old['head'])*4:old['start']] == original[len(old['head'])*4:old['start']]
    assert [d[:2] for d in old['desc']] == [d[:2] for d in new['desc']]
    assert [r[0] for r in old['refs']] == [r[0] for r in new['refs']]
    for index,(_,off) in enumerate(old['refs']):
        newraw = new['spans'][new['refs'][index][1]][0]
        assert newraw == changed.get(off,old['spans'][off][0])
    # Independently invoke the existing extractor on both containers.
    list(decode_file(name,original)); list(decode_file(name,result))
    return result,new

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('resource',help='CPK-relative path, e.g. fld/talk/f101010.bin')
    p.add_argument('targets',type=pathlib.Path,help='English target export with rows/id/target')
    p.add_argument('--source-root',type=pathlib.Path,default=pathlib.Path('work/source/cpk'))
    p.add_argument('--occurrences',type=pathlib.Path,default=pathlib.Path('work/source/text_occurrences.json'))
    p.add_argument('--row-index',type=int,action='append',help='Only these reference indices; repeatable')
    p.add_argument('--ascii-punctuation',action='store_true',help='Explicitly map curly quotes/dashes/ellipsis/NBSP to ASCII')
    p.add_argument('--vwf-latin',action='store_true',help='Encode è/á/é with the explicit candidate private codec; requires matching VWF hooks')
    p.add_argument('--native-fallback',action='store_true',help='Preserve original controller/star symbol counts and wide-space padding as CP932; mixed-font layout remains unverified')
    p.add_argument('--output',type=pathlib.Path,help='Fresh binary output path; never the source')
    p.add_argument('--report',type=pathlib.Path,help='Optional fresh English-only JSON report alongside --write output')
    p.add_argument('--write',action='store_true'); a = p.parse_args()
    root=a.source_root.resolve(); source=(root/a.resource).resolve()
    if not source.is_relative_to(root): raise ValueError('Resource escapes source root')
    original=source.read_bytes(); old=parse(a.resource,original)
    assert rebuild(a.resource,original,{})[0] == original, 'Identity round-trip failed'
    targets={r['id']:r for r in json.loads(a.targets.read_text(encoding='utf-8'))['rows']}
    occurrences=json.loads(a.occurrences.read_text(encoding='utf-8')); replacements={}; audit=[]
    for occ in occurrences:
        if occ['file'] != a.resource: continue
        index=occ['row_index']
        if a.row_index is not None and index not in a.row_index: continue
        row=targets.get(occ['translation_id'])
        if not row or not row.get('target'): continue
        raw=old['spans'][old['refs'][index][1]][0]
        if hashlib.sha256(raw).hexdigest()[:20] != occ['translation_id']: raise ValueError('Occurrence source hash changed')
        if old['blob']+old['refs'][index][1] != occ['offset'] or len(raw) != occ['byte_length']:
            raise ValueError('Occurrence offset/length changed')
        encoded,mapped=encode_target(row['target'],controls(raw.decode('cp932')),a.ascii_punctuation,a.vwf_latin,a.native_fallback)
        replacements[index]=encoded
        audit.append({'row_index':index,'id':row['id'],'old_bytes':len(raw),'new_bytes':len(encoded),
                      'target':controls(decode_bytes(encoded) if a.vwf_latin else encoded.decode('cp932')),'punctuation_mapping':mapped})
    if not replacements: raise ValueError('No matching nonempty English targets')
    if a.row_index is not None and set(a.row_index) != set(replacements):
        raise ValueError('Some explicitly selected rows have no matching English target')
    result,new=rebuild(a.resource,original,replacements)
    for row in audit:
        row['new_offset']=new['blob']+new['refs'][row['row_index']][1]
    report={'resource':a.resource,'original_bytes':len(original),'rebuilt_bytes':len(result),
            'translated_references':len(replacements),'total_references':len(old['refs']), 'translated_row_indices':sorted(replacements),
            'validation':'Identity round-trip, group/ref IDs, all row bytes, suffix, extractor parse, controls/recognized numeric args/placeholders passed',
            'sha256':hashlib.sha256(result).hexdigest(),'sample':audit[:4],
            'renderer_requirement':'ASCII classification, resident glyph routing and dialogue layout hooks remain required'}
    if a.vwf_latin:
        report.update(encoding_policy='ASCII plus private80=è,F040=á,F041=é; requires cp932-pua-f040-f041-v1 matching candidate hooks and bank',
                      accent_glyph_runtime_verified=False)
    if a.native_fallback:
        report.update(native_fallback_policy='Existing controller and star symbols preserve CP932 bytes/counts; wide spaces preserve multi-space padding runs with no added spaces',
                      native_fallback_runtime_verified=False)
    print(json.dumps(report,indent=2,ensure_ascii=True))
    if not a.write: print('DRY RUN: no files written.'); return
    if a.output is None: raise ValueError('--write requires --output to a fresh path')
    output=a.output.resolve()
    if output == source or output.exists() or output.is_relative_to(root): raise ValueError('Output must be fresh and outside source tree')
    report_path=a.report.resolve() if a.report else None
    if report_path and (report_path in (source,output) or report_path.exists() or report_path.is_relative_to(root)):
        raise ValueError('Report must be fresh and outside source tree')
    output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes(result)
    if report_path:
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Wrote fresh rebuilt resource:',output)

if __name__ == '__main__': main()
