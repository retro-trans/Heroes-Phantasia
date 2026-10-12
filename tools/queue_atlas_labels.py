"""Queue reviewed physical battle labels; no texture or archive writes."""
import argparse,copy,hashlib,json,pathlib

def sha(raw):return hashlib.sha256(raw).hexdigest()
def prepare():
    path=pathlib.Path('work/source/media_audit/battle_atlas_label_proposal.json')
    raw=path.read_bytes();data=json.loads(raw)
    asset=pathlib.Path('work/source/cpk')/data['source_asset']
    if sha(asset.read_bytes())!=data['source_sha256']:raise ValueError('Reviewed original atlas changed')
    if len(data['rows'])!=20 or any(r['uv_owner_verified'] or r['runtime_installed'] for r in data['rows']):
        raise ValueError('Expected twenty reviewed but uninstalled physical labels')
    result=copy.deepcopy(data)
    result.update(language='en',category='bitmap_battle_ui',
                  status='drafted_physical_labels_native_uv_layout_pending',
                  proposal_sha256=sha(raw),headline_counting_scope='Separate physical-label records; overlap with glyph labels remains unresolved.')
    existing=set()
    for queued in pathlib.Path('work/translation/en').glob('*.json'):
        if queued.name.endswith('.en.json'):continue
        existing.update(r['id'] for r in json.loads(queued.read_text(encoding='utf8'))['rows'])
    for row in result['rows']:
        if row['id'] in existing:raise ValueError('Duplicate queue ID: '+row['id'])
        row.update(file=data['source_asset'],category='bitmap_battle_ui',
                   encoding='baked_raster_source_transcription')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true')
    p.add_argument('--approved-sha256');a=p.parse_args()
    data=prepare();raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf8')
    digest=sha(raw);print(json.dumps(dict(rows=data['rows'],candidate_sha256=digest,source_sha256=data['source_sha256']),ensure_ascii=True,indent=2))
    if not a.write:print('DRY RUN: no queue written');return
    if a.approved_sha256!=digest:raise ValueError('Full reviewed dry hash required')
    destination=pathlib.Path('work/translation/en/bitmap_battle_0001.json')
    if destination.exists():raise ValueError('Fresh queue required')
    destination.write_bytes(raw)

if __name__=='__main__':main()
