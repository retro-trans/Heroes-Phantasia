"""Dry-only original-guarded CPL name-index0 append plan; no asset writer.

Native978D8 walks name strings from header+4; header+8 remains the original
cache start, not a relocated name-end field. Later labels remain byte-exact.
"""
import argparse,json,struct,hashlib
from pathlib import Path
from extract_cpl_text import extract
from build_translation_archive import MemoryAsset
from unpack_cpk import inventory, crilayla
PRIOR_MONSTER_FILES={f'btl/cpl/cpl{x}.bin' for x in ('0001','0002','0197','0198')}

def sha(b):return hashlib.sha256(b).hexdigest()

def rebuild(raw,old,target):
    h=struct.unpack_from('<12I',raw);start,end=h[1:3]
    if not 48<=start<end<=len(raw):raise ValueError('Original CPL bounds invalid')
    if raw[start:start+len(old)+1]!=old+b'\0':raise ValueError('Name-index0 identity differs')
    if target==old:return raw,{'identity_roundtrip':True}
    if not target or len(target)>31 or any(c<32 or c>126 for c in target):raise ValueError('HUD target must be 1..31 printable ASCII bytes')
    block=target+raw[start+len(old):end]
    where=(len(raw)+15)&~15
    out=bytearray(raw);out.extend(bytes(where-len(out)));out.extend(block);struct.pack_into('<I',out,4,where)
    assert out[:4]==raw[:4] and out[8:len(raw)]==raw[8:]
    assert out[where:where+len(target)+1]==target+b'\0'
    assert out[where+len(target):]==raw[start+len(old):end]
    assert struct.unpack_from('<11I',out,8)==struct.unpack_from('<11I',raw,8)
    return bytes(out),{'old_name_pointer':start,'new_name_pointer':where,'new_block_bytes':len(block),'target_bytes':len(target),'header8_original_cache_pointer':end,'only_original_header4_changed':True,'other_strings_padding_cache_fonts_preserved':True,'native_name_walker_has_no_header8_end_check':True,'runtime_verified':False}

def build(archive=None,prior_assets=None,*,resident_names=False):
    evidence=extract(); saved=json.loads(Path('work/source/cpl_text_inventory.json').read_text(encoding='utf8'))
    if evidence!=saved:raise ValueError('Saved CPL evidence differs from freshly verified originals')
    targets={};snaps=[]
    for path in sorted(Path('work/translation/en').glob('cpl_[0-9][0-9][0-9][0-9].json')):
        b=path.read_bytes();snaps.append({'path':str(path),'sha256':sha(b)})
        for row in json.loads(b)['rows']:
            if row['id'] in targets:raise ValueError('Duplicate CPL queue ID')
            targets[row['id']]=row
    if targets.keys()!={r['id'] for r in evidence['rows']}:raise ValueError('CPL queue coverage mismatch')
    for row in evidence['rows']:
        q=targets[row['id']]
        for key in ['source','file','row_index','offset','byte_length','encoding','original_bytes_sha256','structure','occurrences','category']:
            if q[key]!=row[key]:raise ValueError('CPL immutable metadata changed '+key)
    current={e['path']:e for e in inventory(archive)[1]} if archive else None
    stream=archive.open('rb') if archive else None
    plans=[];assets=[]
    prior_by_name={item['resource']:item for item in (prior_assets or [])}
    if prior_assets is not None and (len(prior_by_name)!=len(prior_assets) or set(prior_by_name)!={f['resource'] for f in evidence['files']}):
        raise ValueError('Prior CPL manifest resource scope differs')
    for f in evidence['files']:
        name=f['resource'];occ=[o for o in evidence['occurrences'] if o['file']==name];first=occ[0];q=targets[first['id']]
        if not q['target']:raise ValueError('Unfilled name0 '+first['id'])
        raw=(Path('work/source/cpk')/name).read_bytes();old=first['source'].encode('cp932');target=q['target'].encode('ascii')
        current_sha=None
        if stream:
            entry=current[name];stream.seek(entry['offset']);live=stream.read(entry['stored_size'])
            if live.startswith(b'CRILAYLA'):live=crilayla(live,entry['extract_size'])
            if prior_assets is not None:
                prior=prior_by_name[name]
                if prior['id']!=q['id'] or prior['original_sha256']!=sha(raw):
                    raise ValueError('Prior CPL identity/original differs')
                expected=raw if prior.get('all_original_bytes_restored') is True else rebuild(raw,old,prior['target'].encode('ascii'))[0]
                if sha(expected)!=prior['rebuilt_sha256']:
                    raise ValueError('Prior CPL exact rebuild differs')
            elif name in PRIOR_MONSTER_FILES:
                if old!=bytes.fromhex('838283938358835e815b'):raise ValueError('Prior Monster source differs')
                expected=rebuild(raw,old,b'Monster')[0]
            else:expected=raw
            if live!=expected:raise ValueError('Unexpected current CPL modification '+name)
            current_sha=sha(live)
        identity,_=rebuild(raw,old,old)
        if identity!=raw:raise ValueError('Identity rebuild differs')
        if resident_names:
            out=raw
            proof={'original_native_header_restored':True,'all_original_bytes_restored':True,
                   'resident_hud_name_lookup_required':True,'runtime_verified':False}
        else:out,proof=rebuild(raw,old,target)
        assets.append((name,MemoryAsset(name,out)))
        plans.append({'resource':name,'id':q['id'],'target':q['target'],'original_sha256':sha(raw),'rebuilt_sha256':sha(out),'original_bytes':len(raw),'rebuilt_bytes':len(out),'current_asset_sha256':current_sha,'status':'planned_cpl_name0','original_references':len(occ),'identity_roundtrip':True,**proof})
    if stream:stream.close()
    names={q['id']:q['target'] for q in targets.values() if q['category']=='battle_entity_name'}
    if len(names)!=79:raise ValueError('Expected79 unique HUD name targets')
    target_sha=sha(json.dumps(names,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('utf8'))
    return {'schema_version':1,'status':'dry_original_cpl_restore_resident_name_lookup_required' if resident_names else 'dry_cpl_name0_append_plan','files':len(plans),'name0_unique':79,'name0_occurrences':424,'name0_storage':'resident_hud_lookup' if resident_names else 'appended_cpl_name_block','name0_translations_installed_in_archive':0 if resident_names else 79,'resident_name_targets_sha256':target_sha,'later_labels_installed':0,'later_labels_not_installed':350,'runtime_verified':False,'current_archive_cpl_guard_verified':bool(archive),'known_prior_monster_assets_verified':4 if archive and prior_assets is None else 0,'prior_manifest_cpl_assets_verified':len(prior_by_name) if archive else 0,'target_input_snapshots':snaps,'assets':plans,'limits':['Source original guard and byte preservation are structural evidence, not runtime proof.','Prototype/test labels have unproved gameplay visibility.','Native enemy-count scans require original monotonic CPL section headers; resident mode restores every original byte and requires a separate executable HUD lookup.','Current CPL resources must match exact original-based prior rebuilds, including every original cache byte; no current executable change is implied.']},assets

def main():
    argparse.ArgumentParser(description=__doc__).parse_args();report,_=build()
    print(json.dumps({k:v for k,v in report.items() if k not in ['assets','target_input_snapshots']},indent=2))
    print(json.dumps(report['assets'][:3],indent=2));print('DRY RUN: no files written.')
if __name__=='__main__':main()
