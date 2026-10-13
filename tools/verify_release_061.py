"""Verify .61 Retro Trans routes and GitHub uploaded assets; read-only by default."""
import argparse,json,subprocess,sys
from pathlib import Path
from package_release import sha
from package_release_061 import OUT,UPSTREAM,TARGET_SHA

REPO='retro-trans/Heroes-Phantasia';TAG='v0.1.61';DOC=Path('docs/releases/0.1.61')

def api(path):return json.loads(subprocess.check_output(['gh','api',path],text=True,encoding='utf-8'))

def routes(catalog=None):
    sys.path.insert(0,str(UPSTREAM.resolve()))
    from retro_trans.catalog import Catalog,matches
    m=json.loads((OUT/'BUILD-MANIFEST.json').read_text(encoding='utf-8'))
    data=json.loads((catalog or UPSTREAM/'retro_trans/resources/catalog.json').read_text(encoding='utf-8'))
    if catalog:
        record=next(r for r in data['releases']if r['repo']==REPO and r['tag']==TAG)
        if record['manifest']!=m:raise ValueError('Public manifest differs')
    else:
        data['releases'].append(dict(repo=REPO,tag=TAG,manifest=m,assets={r['patch']:f'https://github.com/{REPO}/releases/download/{TAG}/{r["patch"]}'for r in m['patches']}))
    c=Catalog(data);target=c.nodes[('heroes-phantasia','English','en','0.1.61')];checked=[]
    for row in m['patches']:
        source=c.nodes[('heroes-phantasia','English','en',row['source_version'])]
        if not matches(source,{'sha256':row['source_sha256']},row['source_bytes']):raise ValueError('Source recognition differs')
        plan=c.plan(source,'Latest')
        if plan.target.id!=target.id or len(plan.edges)!=1 or plan.edges[0].asset.sha256!=row['patch_sha256'] or plan.edges[0].asset.size!=row['patch_bytes']:raise ValueError('Automatic route differs')
        if c.plan(source,'0.1.61').target.id!=target.id:raise ValueError('Explicit target differs')
        checked.append(dict(source_version=row['source_version'],patch=row['patch'],one_step=True,patch_integrity_matches=True))
    if not matches(target,{'sha256':TARGET_SHA},m['patches'][0]['target_bytes']) or c.plan(target,'Latest').edges:raise ValueError('Current target no-op differs')
    earlier=c.nodes[('heroes-phantasia','English','en','0.1.45')]
    upgrade=c.plan(earlier,'Latest')
    if upgrade.target.id!=target.id or len(upgrade.edges)!=2:raise ValueError('Published .45 upgrade route differs')
    checked.append(dict(source_version='0.1.45',via_version='0.1.50',two_steps=True,
                        patches=[edge.asset.name for edge in upgrade.edges]))
    if any(matches(n,{'sha256':'0'*64},1415020544)for n in c.nodes.values()):raise ValueError('Unknown image accepted')
    return dict(schema_version=1,repo=REPO,tag=TAG,catalog='public'if catalog else'candidate',catalog_sha256=sha(catalog)if catalog else None,routes=checked,current_version_no_op=True,unknown_hash_rejected=True,source_commit=m['source_commit'])

def publication(require_public):
    if api('user')['login']!='binhlt0402':raise ValueError('Unexpected account')
    release=next(r for r in api(f'repos/{REPO}/releases?per_page=100')if r['tag_name']==TAG)
    if release['author']['login']!='binhlt0402' or release['prerelease'] or require_public and release['draft']:raise ValueError('Release state/author differs')
    expected={p.name:p for p in OUT.iterdir()if p.is_file()};assets={x['name']:x for x in release['assets']}
    if set(expected)!=set(assets) or len(expected)!=5:raise ValueError('Asset set differs')
    checked=[]
    for name,path in expected.items():
        row=assets[name];digest=sha(path)
        if row['size']!=path.stat().st_size or row['state']!='uploaded' or row.get('digest')!='sha256:'+digest:raise ValueError('Uploaded asset integrity differs: '+name)
        checked.append(dict(name=name,bytes=row['size'],sha256=digest,url=row['browser_download_url']))
    m=json.loads((OUT/'BUILD-MANIFEST.json').read_text(encoding='utf-8'))
    if api(f'repos/{REPO}/commits/'+m['source_commit'])['sha']!=m['source_commit']:raise ValueError('Public source commit missing')
    if require_public:
        ref=api(f'repos/{REPO}/git/ref/tags/{TAG}')
        if ref['object']['type']!='commit' or ref['object']['sha']!=m['source_commit']:raise ValueError('Tag commit differs')
    return dict(schema_version=1,repo=REPO,tag=TAG,release_url=release['html_url'],release_id=release['id'],author='binhlt0402',draft=release['draft'],source_commit=m['source_commit'],public_source_commit_verified=True,tag_source_commit_verified=require_public,all_uploaded_asset_hashes_and_sizes_match=True,assets=checked)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--catalog',type=Path);ap.add_argument('--publication',action='store_true');ap.add_argument('--require-public',action='store_true');ap.add_argument('--write',action='store_true');a=ap.parse_args()
    result=publication(a.require_public)if a.publication else routes(a.catalog)
    print(json.dumps(result,indent=2))
    if not a.write:print('DRY RUN');return
    name=('publication'if a.require_public else'draft-assets')if a.publication else('public-catalog-routes'if a.catalog else'candidate-routes')
    dest=DOC/(name+'.en.json')
    if dest.exists():raise ValueError('Fresh evidence required')
    DOC.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
