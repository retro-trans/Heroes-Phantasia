"""Prepare scoped .34 English reflows; dry-run first, guarded fresh writes only."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from dialogue_tokens import tokenize_bytes, validate_controls
from english_word_wrap import wrap_body
from executable_text_patch import Elf
from rebuild_dialogue import encode_target, parse, rebuild
from strip_jp import export
from unpack_cpk import inventory

BASE = Path('work/output/0.1.33-title-credit-vwf-4x-candidate')
OUT = Path('work/output/0.1.34-bubble-reflow-assets')
QUEUES = [Path('work/translation/en/batch_0001.json'), Path('work/translation/en/batch_0014.json')]
SELECTED = {'fld/talk/f101070.bin': [0], 'phase/bin/p101040.bin': [17, 24, 26],
            'phase/bin/p101041.bin': [17, 24, 26]}
PREFIXES = {0: b'\x1cCougar\x0eYou know, when our guests',
            17: b'\x1cCougar\x0eTo people like you',
            24: b'\x1c\x011\x0eHe doesn', 26: b'\x1cMitch\x0eOh, right!'}
OLD = {
    'ca3430cfd18ef7ab18cf': "{1C}Cougar{0E}You know, when our guests{11}wander around wherever they please...{12}{10}it puts us in a bit of a bind.{12}{0E}",
    'b331396d073d4ed3a01b': "{1C}Cougar{0E}To people like you{11}who've come from the mainland,{11}Alter users must seem downright exotic.{12}{0E}",
    'eb46eed6a4c5a53fc90e': "{1C}{01}1{0E}He doesn't seem to belong to HOLY or {05}077{16}03HOLD{16}01,{11}though.{12}{0E}",
    '7f3b0fd42cb9831eb5c2': "{1C}{01}1{0E}He doesn't look like a HOLY or {05}077{16}03HOLD{16}01{11}employee, though.{12}{0E}",
    '225ab7278d22cda9e94e': "{1C}Mitch{0E}Oh, right! I saw him in an article{11}about a reception at the Yanbaru{11}Nature Conservation Center.{12}{0E}",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def proof_hash(proof):
    return sha(json.dumps(proof, sort_keys=True, separators=(',', ':')).encode())


def notation(raw):
    return ''.join(t.data.decode('ascii') if t.kind == 'latin' else
                   '{%02X}' % t.code + t.data[1:].decode('ascii')
                   for t in tokenize_bytes(raw, True))


def signature(raw):
    return [t.data for t in tokenize_bytes(raw, True)
            if t.kind == 'control' and t.code != 0x11]


def prose(raw):
    return b''.join(t.data for t in tokenize_bytes(raw, True)
                    if t.kind == 'latin' and t.code != 32)


def build():
    meta = json.loads((BASE / 'manifest.en.json').read_text())
    executable = (BASE / 'EBOOT.BIN').read_bytes()
    if meta['version'] != '0.1.33' or sha(executable) != meta['output_elf_sha256']:
        raise ValueError('Frozen .33 executable identity differs')
    elf = Elf(executable)
    at = elf.file_offset(meta['body_integer_lut_rva'], 524)
    lut = executable[at:at + 524]
    if sha(lut) != meta['body_integer_lut_sha256']:
        raise ValueError('Body width table identity differs')
    widths = struct.unpack('<131I', lut)
    queue_raw = {path: path.read_bytes() for path in QUEUES}
    queues = {path: json.loads(raw.decode('utf-8-sig')) for path, raw in queue_raw.items()}
    candidates = []
    for path, queue in queues.items():
        for row in queue['rows']:
            if row['id'] in OLD:
                frozen = OLD[row['id']]
                candidates.append((path, row, encode_target(frozen, frozen, True, True, True)[0]))
    archive = BASE / 'HP.CPK'
    _, entries = inventory(archive)
    entries = {r['path']: r for r in entries}
    assets, records, resources, changed_queues = {}, [], [], set()
    with archive.open('rb') as stream:
        for name, selected in SELECTED.items():
            entry = entries[name]
            if entry['compression'] != 'none':
                raise ValueError('Expected raw installed phase/field record')
            stream.seek(entry['offset']); raw = stream.read(entry['stored_size'])
            parsed = parse(name, raw); replacements = {}
            for index in selected:
                old = parsed['spans'][parsed['refs'][index][1]][0]
                if not old.startswith(PREFIXES[index]):
                    raise ValueError('Selected installed record differs')
                matches = [(p, row) for p, row, encoded in candidates if encoded == old]
                if len(matches) != 1:
                    raise ValueError('Installed record has no unique working translation')
                path, row = matches[0]
                prefix, body = old.split(b'\x0e', 1)
                wrapped = wrap_body(body, widths, maximum=180, max_lines=4)
                record = dict(resource=name, reference_index=index, record_id=row['id'],
                              old_target=notation(old), supported=wrapped['supported'])
                if not wrapped['supported']:
                    record.update(changed=False, reason=wrapped['reason'])
                    if 'required_lines' in wrapped: record['required_lines'] = wrapped['required_lines']
                    records.append(record); continue
                target = prefix + b'\x0e' + wrapped['data']
                if signature(old) != signature(target) or prose(old) != prose(target):
                    raise ValueError('Proposal changed words or non-line controls')
                target_text = notation(target)
                if row['target'] not in (OLD[row['id']], target_text):
                    raise ValueError('Working translation is neither the frozen old target nor the reviewed proposal')
                validate_controls(row['source'].replace('{11}', ''), target_text.replace('{11}', ''))
                if encode_target(target_text, target_text, True, True, True)[0] != target:
                    raise ValueError('Proposal token notation does not round trip')
                record.update(changed=target != old, target=target_text, pages=wrapped['pages'],
                              words_and_non_line_controls_preserved=True)
                records.append(record)
                if target != old:
                    replacements[index] = target
                    row['target'] = target_text
                    if '0.1.34: scoped English wrap' not in row.get('notes', ''):
                        row['notes'] = row.get('notes', '') + ' 0.1.34: scoped English wrap at word boundaries, maximum 180px and four lines per page; words and non-line controls preserved. Natural scene QA pending.'
                    changed_queues.add(path)
            changed, after = rebuild(name, raw, replacements)
            for index, ref in enumerate(parsed['refs']):
                if index not in replacements and parsed['spans'][ref[1]][0] != after['spans'][after['refs'][index][1]][0]:
                    raise ValueError('Unselected installed text changed')
            if raw[parsed['end']:] != changed[after['end']:]:
                raise ValueError('Nontext suffix changed')
            if replacements: assets[name] = changed
            resources.append(dict(resource=name, source_sha256=sha(raw), output_sha256=sha(changed),
                                  changed_references=sorted(replacements), all_other_records_exact=True,
                                  nontext_suffix_exact=True))
    # Export validates English-only committed copies before any guarded write.
    queue_updates = {path: queues[path] for path in changed_queues}
    exports = {str(path): sha((json.dumps(export(queue), ensure_ascii=False, indent=2)+'\n').encode())
               for path, queue in queue_updates.items()}
    proof = dict(version='0.1.34', source_version='0.1.33', source_executable_sha256=sha(executable),
                 body_width_table_sha256=sha(lut), source_archive_manifest_sha256=meta['dialogue_cpk_sha256'],
                 maximum_advance=180, maximum_lines=4, records=records, resources=resources,
                 queue_input_sha256={str(p): sha(r) for p, r in queue_raw.items()},
                 english_export_sha256=exports, protected_references=[16, 23, 27],
                 natural_scene_verified=False, archive_and_iso_not_modified=True)
    saved = OUT / 'reflows.en.json'
    if saved.exists():
        written = json.loads(saved.read_text(encoding='utf-8'))
        # Preserve the actual prewrite input identity after queues contain the
        # reviewed proposal. All independently recomputed proof fields must match.
        proof['queue_input_sha256'] = written['queue_input_sha256']
        if proof != written:
            raise ValueError('Recomputed preparation differs from the written reviewed proof')
    return queue_updates, assets, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--expected-sha256')
    args = parser.parse_args()
    queues, assets, proof = build(); digest = proof_hash(proof)
    print(json.dumps(proof, indent=2)); print('Reviewed proof SHA256:', digest)
    if not args.write:
        print('DRY RUN'); return
    if args.expected_sha256 != digest or OUT.exists():
        raise ValueError('Reviewed dry-run proof hash and fresh output folder required')
    for path, queue in queues.items():
        if sha(path.read_bytes()) != proof['queue_input_sha256'][str(path)]:
            raise ValueError('Working translation changed after proposal')
    OUT.mkdir(parents=True)
    for name, raw in assets.items():
        destination = OUT / Path(name).name; destination.write_bytes(raw)
        if destination.read_bytes() != raw: raise ValueError('Prepared asset readback differs')
    (OUT / 'reflows.en.json').write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    for path, queue in queues.items():
        path.write_text(json.dumps(queue, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        path.with_name(path.stem+'.en.json').write_text(json.dumps(export(queue), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
