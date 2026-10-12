"""Prepare a source-bound normal-route playback evidence plan; default dry.

This tool never connects to an emulator and does not turn a plan into proof.
--write saves only a fresh English JSON plan, never native media or an ISO.
"""
import argparse,json,hashlib
from pathlib import Path

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def prepare(manifest):
    raw=manifest.read_bytes();m=json.loads(raw)
    if m['version']!='0.1.23':raise ValueError('This scoped plan is for reviewed23 only.')
    iso=Path(m['iso_path']);movie=m['prologue_movie_translation_coverage']
    if not movie['installed_in_iso']:raise ValueError('Movie is not installed in this manifest.')
    items={r['path']:r for r in m['iso_replacements']}
    names=['PSP_GAME/SYSDIR/EBOOT.BIN','PSP_GAME/USRDIR/HP.CPK','PSP_GAME/USRDIR/MOVIE/HPMOVE03.PMF']
    if file_sha(iso)!=m['iso_sha256']:raise ValueError('ISO differs.')
    actual={}
    with iso.open('rb') as f:
        for name in names:
            r=items[name];f.seek(r['offset']);remaining=r['size'];h=hashlib.sha256()
            while remaining:
                b=f.read(min(8*1024*1024,remaining))
                if not b:raise ValueError('Truncated embedded asset.')
                h.update(b);remaining-=len(b)
            actual[name]=h.hexdigest()
            if actual[name]!=r['sha256'] or file_sha(r['source'])!=r['sha256']:
                raise ValueError('Installed/source asset differs: '+name)
    if actual[names[0]]!=m['output_elf_sha256'] or actual[names[1]]!=m['dialogue_cpk_sha256'] or actual[names[2]]!=movie['candidate_sha256']:
        raise ValueError('Manifest coverage disagrees with installed hashes.')
    return dict(schema_version=1,status='normal_route_full_prologue_playback_plan_not_runtime_proof',
        version=m['version'],manifest_path=str(manifest),manifest_sha256=hashlib.sha256(raw).hexdigest(),
        iso_sha256=m['iso_sha256'],embedded_and_local_asset_sha256=actual,
        expected_movie_frames=6425,expected_frame_rate='30000/1001',expected_duration_seconds=6425*1001/30000,
        route_requirements=['Cold boot this exact ISO with the recorded executable/archive/movie hashes.',
            'Navigate using normal controller input; record load confirmation, title/menu and the transition into the prologue.',
            'Do not substitute a desktop preview, save-state injection, patched memory or direct movie launch.',
            'Let the complete prologue play without skipping. Record first and last captions and the return/next game scene.',
            'Record whether original audio was heard continuously, decoder errors/stalls occurred, and normal skip/transition behavior separately.'],
        capture_annotations_required=['fresh PNG path and SHA256','capture tool/manifest binding',
            'native frame format and480x272 dimensions','normal-route sequence number',
            'elapsed playback time or observed movie-frame index; never label an inferred timestamp exact',
            'English text readability, Japanese remnants, clipping and compression artifacts actually observed'],
        representative_checkpoints=['The present day and overlapping first narration.',
            'Native Alters, Orphans, chiropterans and I-Jin captions.',
            'Organization headings and Contractors/Hell\'s Gate overlap.',
            'Moving Sawada International Research sign and staggered agency description.',
            'White investigation request, fade to black, both ending captions and next normal game scene.'],
        coverage_rules=['80 PC-decoded samples are prior static quality evidence, not PSP playback evidence.',
            'A screenshot collection verifies only those captures; full playback is a separately recorded human observation.',
            'No whole-movie Japanese-absence claim without reviewing every relevant native playback state.',
            'Other movies remain uninstalled and outside this proof.'],
        prior_pc_timing=movie['full_pc_timing'],runtime_verified=False,full_playback_observed=False,
        audio_playback_observed=False,whole_movie_japanese_absence_verified=False,native_assets_written=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path);p.add_argument('--write',action='store_true');a=p.parse_args()
    r=prepare(a.manifest);print(json.dumps(r,indent=2))
    if a.write:
        if not a.output:raise ValueError('--write needs a fresh output path.')
        a.output.resolve().relative_to(Path('work/ui').resolve())
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x',encoding='utf8') as f:f.write(json.dumps(r,indent=2)+'\n')
