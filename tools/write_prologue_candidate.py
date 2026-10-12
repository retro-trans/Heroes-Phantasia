"""Guarded, default-dry standalone PMF preparation; never edits an original or archive.

The reviewed RAM candidate is reconstructed before an explicit fresh-output write.
This is not native playback approval or a claim of whole-movie text absence.
"""
import argparse,json,re,shutil
from pathlib import Path
from prepare_prologue_anchor_trial import adaptive_trial,dependencies
from prepare_prologue_overlays import MOVIE,QUEUE,FONT,sha
from movie_preparation_runtime import fingerprint

def inspect(review,expected_review,expected_candidate,output):
    if not __debug__:raise RuntimeError('Optimized Python is forbidden.')
    raw=review.read_bytes()
    if sha(raw)!=expected_review:raise ValueError('Reviewed report hash changed.')
    r=json.loads(raw)
    if r.get('candidate_sha256')!=expected_candidate:raise ValueError('Candidate hash differs from reviewed candidate.')
    if r.get('status')!='anchor_span_ram_candidate_runtime_unverified':raise ValueError('Rejected or unexpected candidate status.')
    if not r.get('candidate_generated') or r.get('failed_spans'):raise ValueError('No fitting candidate.')
    t=r.get('full_pc_timing',{})
    if t.get('frame_count')!=6425 or t.get('differences')!=0 or t.get('decode_errors'):raise ValueError('PC timing/decode failed.')
    for k in ('all_native_timestamp_first_aud_associations_exact','all_native_timestamp_first_slice_associations_exact',
              'original_header_epmap_scr_audio_and_pes_headers_exact','all_nonmutable_bytes_exact'):
        if r.get(k) is not True:raise ValueError('Missing proof: '+k)
    if dependencies()!=r.get('input_dependencies_sha256'):raise ValueError('Preparation dependency changed.')
    if fingerprint()!=r.get('preparation_runtime'):raise ValueError('Python/raster/codec runtime changed.')
    if sha(MOVIE.read_bytes())!=r['source_sha256'] or sha(QUEUE.read_bytes())!=r['target_queue_sha256']:
        raise ValueError('Source or target snapshot changed.')
    if r['candidate_bytes']!=MOVIE.stat().st_size:raise ValueError('Unexpected movie size.')
    out=output.resolve();out.relative_to(Path('work/output').resolve())
    if not re.search(r'0\.\d+\.\d+',str(out)):raise ValueError('Output must identify a build version.')
    if out.exists() or out.with_suffix(out.suffix+'.en.json').exists() or out==MOVIE.resolve():raise ValueError('Output and sidecar must be fresh.')
    image_files=sorted(review.parent.glob('*.png'))
    if len(image_files)<8:raise ValueError('Incomplete actual-decode review sheets.')
    ffmpeg=Path(shutil.which('ffmpeg') or '')
    if not ffmpeg.is_file():raise ValueError('FFmpeg unavailable.')
    bindings=dict(r['input_dependencies_sha256'])
    for p in (FONT,Path('tools/prepare_title_logo_proposal.py'),ffmpeg,Path(__file__)):
        bindings[str(p)]=sha(p.read_bytes())
    return dict(schema_version=1,status='guarded_standalone_movie_write_plan_runtime_unverified',
        source_path=str(MOVIE),source_sha256=r['source_sha256'],review_path=str(review),review_sha256=expected_review,
        candidate_sha256=expected_candidate,candidate_bytes=r['candidate_bytes'],output=str(out),
        target_queue_sha256=r['target_queue_sha256'],dependencies_sha256=bindings,
        review_images_sha256={str(p):sha(p.read_bytes()) for p in image_files},
        preparation_runtime=r['preparation_runtime'],full_pc_timing=t,archive_integration=dict(asset='PSP_GAME/USRDIR/MOVIE/HPMOVE03.PMF',
            strategy='Separate reviewed append-retarget ISO replacement; no CPK entry and no ISO mutation by this tool.',
            original_bytes=MOVIE.stat().st_size,expected_original_sha256=r['source_sha256']),
        intentional_black_backplates=True,native_playback_verified=False,whole_movie_japanese_absence_verified=False,
        native_assets_written=False,release_authorized=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review',type=Path,required=True);p.add_argument('--expected-review-sha256',required=True)
    p.add_argument('--expected-candidate-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--rejection-report',type=Path,help='Optional fresh work/ui JSON if reconstruction fails')
    p.add_argument('--write',action='store_true');a=p.parse_args()
    plan=inspect(a.review,a.expected_review_sha256,a.expected_candidate_sha256,a.output)
    if a.rejection_report:
        a.rejection_report.resolve().relative_to(Path('work/ui').resolve())
        if a.rejection_report.exists():raise ValueError('Rejection report must be fresh.')
    if a.write:
        candidate,r,_=adaptive_trial(return_candidate=True)
        if candidate is None or sha(candidate)!=plan['candidate_sha256'] or r['full_pc_timing']!=plan['full_pc_timing']:
            diagnostic=dict(status='candidate_reconstruction_rejected_no_movie_written',
                expected_sha256=plan['candidate_sha256'],actual_sha256=sha(candidate) if candidate is not None else None,
                actual_timing=r.get('full_pc_timing'),expected_timing=plan['full_pc_timing'],
                actual_encoder_variants=r.get('encoder_variants'),actual_replacement_es_sha256=r.get('replacement_es_sha256'),
                actual_runtime=fingerprint(),expected_runtime=plan['preparation_runtime'],
                dependencies_sha256=dependencies())
            print(json.dumps(diagnostic,indent=2))
            if a.rejection_report:
                a.rejection_report.parent.mkdir(parents=True,exist_ok=True)
                with a.rejection_report.open('x',encoding='utf8') as f:f.write(json.dumps(diagnostic,indent=2)+'\n')
            raise ValueError('Reconstructed candidate differs from reviewed bytes/timing.')
        if inspect(a.review,a.expected_review_sha256,a.expected_candidate_sha256,a.output)!=plan:
            raise ValueError('Inputs changed during reconstruction.')
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('xb') as f:f.write(candidate)
        if sha(a.output.read_bytes())!=plan['candidate_sha256']:raise ValueError('Output readback differs.')
        plan['status']='standalone_movie_written_runtime_unverified';plan['native_assets_written']=True
        sidecar=a.output.with_suffix(a.output.suffix+'.en.json')
        with sidecar.open('x',encoding='utf8') as f:f.write(json.dumps(plan,indent=2)+'\n')
    print(json.dumps(plan,indent=2))

if __name__=='__main__':main()
