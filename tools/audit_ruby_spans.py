"""Dry translated-ruby association audit; never modifies drafts or assets.

The original one-digit base count remains protected. A separate association
describes the translated base's actual bytes; a complete Latin word is inferred
only when its spelling agrees with the reading. Canonical multiword bases use
an exact source-base glossary match. Other spans remain unresolved.
"""
import argparse
import collections
import json
from pathlib import Path
import re
from dialogue_tokens import tokenize_text, text_bytes, validate_controls


def spans(text):
    tokens = tokenize_text(text, private_latin=True)
    result = []
    for n, token in enumerate(tokens):
        if token.kind != 'ruby_open':continue
        close = next(x for x in tokens[n+1:] if x.kind == 'ruby_close')
        count = int(token.argument)
        preceding = []
        for prior in reversed(tokens[:n]):
            if prior.kind not in ('latin', 'native') or prior.ruby:break
            preceding.insert(0, prior)
        result.append(dict(open=token, close=close, count=count,
                           preceding=b''.join(x.data for x in preceding),
                           native_base=b''.join(x.data for x in preceding[-count:]) if count else b'',
                           reading=b''.join(x.data for x in tokens[n+1:] if x.offset < close.offset)))
    return result


APPROVED_BASES = {
    ('24ff85058bebf85134e6',0):(b'Great Waves',b''),
    ('8510006d023cc07c9460',0):(b'Minoru',b' Sawada'),
    ('dbc89180f65e2d1cf975',2):(b'Master',b''),
    ('77b49628046d859bee9e',0):(b'chiropterans',b''),
    ('8c48366db1ee866876b3',0):(b'Shield',b''),
    ('278ab288c5e655f0ee2e',0):(b'Tate',b''),
    ('420e582de2e61ba5671a',1):(b'Sisters',b''),
    ('ae37cb7fc3a3691ec660',0):(b'Mimori',b''),
    ('68cd824ce7ee21989bf9',0):(b'Natsumi',b''),
    # Root approval2026-10-11: complete source/target pairs and exact suffixes;
    # association-only, no prose/control/count edits or new scene-read claims.
    ('da5558c572bd9c003b55',0):(b'Sister Chuka',b''),
    ('c5065fd52895909c1d19',0):(b'Young Master',b''),
    ('0a8d7309a68951f80894',0):(b'Young Master',b''),
    ('cad8e9d0afa24f93ad15',0):(b'great wave',b''),
    ('5071861bf077402210bc',0):(b'great wave',b''),
    ('001670e32e4599efadfe',0):(b'great wave',b''),
    ('89bc68a509774ae44dac',0):(b'great wave',b''),
    ('79dd1948672a073b6831',0):(b'great wave',b''),
    ('1649f23b647909014ad0',0):(b'great wave',b''),
    ('f4bdf372eaede4e2dd0c',0):(b'great wave',b''),
    ('0b87f1bb16c64d5011e1',0):(b'great wave',b''),
    ('9a7c889215fc26fe5342',0):(b'Great Waves',b''),
    ('cc370c987f1365f23ca2',0):(b'minus',b''),
    ('4f795b4b3029dee5a561',0):(b'rare book',b''),
    ('f3bc3b47604d5a2f86b0',0):(b'rare book',b''),
}


def audit(target_fixes=None):
    glossary=json.loads(Path('work/glossary/glossary.en.json').read_text(encoding='utf-8'))
    names=collections.defaultdict(set)
    for entry in glossary['entries']:
        if isinstance(entry.get('ja'),str) and isinstance(entry.get('en'),str):
            try:names[entry['ja'].encode('cp932')].add(text_bytes(entry['en'],True))
            except UnicodeEncodeError:pass
    rows=[];counts=collections.Counter()
    for path in sorted(Path('work/translation/en').glob('batch_*.json')):
        if path.name.endswith('.en.json'):continue
        for row in json.loads(path.read_text(encoding='utf-8-sig'))['rows']:
            if not row.get('target') or '{0F}' not in row['source']:continue
            row={**row,'target':(target_fixes or {}).get(row['id'],row['target'])}
            validate_controls(row['source'],row['target'])
            source=spans(row['source']);target=spans(row['target'])
            if len(source)!=len(target):raise ValueError('Ruby pair count changed')
            for index,(old,new) in enumerate(zip(source,target)):
                matches=[]
                for alias in names.get(old['native_base'],()):
                    if new['preceding'].endswith(alias):
                        before=new['preceding'][:-len(alias)] if alias else b''
                        if not before or before[-1:] not in b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz':
                            matches.append(alias)
                if matches:
                    base=max(matches,key=len);decision='exact_source_base_and_canonical_English_suffix'
                else:
                    word=re.search(rb"[A-Za-z\x80]+(?:[-'][A-Za-z\x80]+)*$",new['preceding'])
                    base=word.group() if word else b''
                    if base and base.lower()==new['reading'].lower():
                        decision='complete_preceding_word_agrees_with_reading_provisional'
                    else:base=b'';decision='needs_context'
                gap=b''
                if (row['id'],index) in APPROVED_BASES:
                    base,gap=APPROVED_BASES[row['id'],index]
                    if not new['preceding'].endswith(base+gap):
                        raise ValueError('Approved base no longer matches target suffix')
                    decision='root_reviewed_contextual_association'
                counts[decision]+=1
                item=dict(id=row['id'],file=row['file'],ruby_index=index,
                          original_argument=new['count'],target_open_byte_offset=new['open'].offset,
                          target_reading_bytes=new['reading'].hex(),target_base_bytes=base.hex(),
                          target_base_byte_length=len(base),decision=decision,runtime_verified=False)
                if base:
                    item['target_base_byte_offset']=new['open'].offset-len(base)-len(gap)
                    item['target_gap_bytes']=gap.hex()
                    item['runtime_signature_hex']=(base+gap+new['open'].data+
                                                   new['reading']+new['close'].data).hex()
                rows.append(item)
    return dict(schema_version=1,counts=dict(counts),ruby_spans=len(rows),rows=rows,
                preserves_original_control_arguments=True,source_rewritten=False,
                note='Association candidates need contextual review and runtime positioning QA. Offsets are within each encoded target, not absolute PSP heap addresses.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--all',action='store_true')
    parser.add_argument('--target-fixes',type=Path,help='Ignored proposed target overlay; no queue changes')
    args=parser.parse_args()
    fixes={x['id']:x['target'] for x in json.loads(args.target_fixes.read_text(encoding='utf-8'))['rows']} if args.target_fixes else None
    result=audit(fixes)
    print(json.dumps(result if args.all else {**result,'rows':result['rows'][:8]},indent=2))
    print('DRY RUN: no drafts or assets written.')


if __name__=='__main__':main()
