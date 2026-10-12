"""Read-only, narrowly scoped validation for one reviewed prologue ISO input."""
import hashlib,json,struct
from pathlib import Path
from build_menu_patch import ISO,record_for

ASSET='PSP_GAME/USRDIR/MOVIE/HPMOVE03.PMF'
ORIGINAL_SHA='252985cb74c0fa117c2f8cc48bb31e932a5ac671b14c3a18d5af2bc0d2b104c1'
def digest(data):return hashlib.sha256(data).hexdigest()

def validated_input(movie,proof,expected_proof_sha256,expected_movie_sha256):
    """Return an existing build_local input tuple and source-bound manifest coverage.

    Call before ISO append planning. build_local's existing original-span and
    embedded extraction checks then apply to this input too. No writes here.
    """
    if not __debug__:raise RuntimeError('Optimized Python is forbidden.')
    movie,proof=Path(movie),Path(proof)
    raw=proof.read_bytes()
    if digest(raw)!=expected_proof_sha256:raise ValueError('Movie proof changed.')
    p=json.loads(raw)
    if p.get('status')!='standalone_movie_written_runtime_unverified':raise ValueError('Movie is not a verified standalone output.')
    if p.get('candidate_sha256')!=expected_movie_sha256 or p.get('source_sha256')!=ORIGINAL_SHA:
        raise ValueError('Movie/source hash is not reviewed.')
    if p.get('archive_integration',{}).get('asset')!=ASSET:raise ValueError('Only the reviewed prologue is allowed.')
    timing=p.get('full_pc_timing',{})
    if timing.get('frame_count')!=6425 or timing.get('differences')!=0 or timing.get('decode_errors'):
        raise ValueError('Movie timing proof failed.')
    data=movie.read_bytes()
    if digest(data)!=expected_movie_sha256 or len(data)!=p['candidate_bytes'] or data[:4]!=b'PSMF':
        raise ValueError('Movie input differs.')
    rec,sector,size=record_for(ISO,ASSET)
    with ISO.open('rb') as f:
        f.seek(rec);r=f.read(34)
        if struct.unpack_from('>I',r,6)[0]!=sector or struct.unpack_from('>I',r,14)[0]!=size:
            raise ValueError('Original ISO directory endian fields disagree.')
        f.seek(sector*2048);native=f.read(size)
    if size!=len(data) or digest(native)!=ORIGINAL_SHA:raise ValueError('Original ISO movie differs.')
    review=Path(p['review_path'])
    if digest(review.read_bytes())!=p['review_sha256']:raise ValueError('Reviewed candidate report changed.')
    r=json.loads(review.read_bytes())
    if r.get('candidate_sha256')!=expected_movie_sha256:raise ValueError('Candidate proof mismatch.')
    for k in ('all_nonmutable_bytes_exact','original_header_epmap_scr_audio_and_pes_headers_exact',
              'all_native_timestamp_first_aud_associations_exact','all_native_timestamp_first_slice_associations_exact'):
        if r.get(k) is not True:raise ValueError('Missing protected-field proof: '+k)
    coverage=dict(asset=ASSET,primary_caption_rows=17,superseding_staggered_fields=10,moving_sign=1,
        complete_english_wording_prepared=True,reviewed_pc_decoded_samples=len(r['selected_pc_decoded_frames']),
        full_pc_timing=timing,candidate_sha256=expected_movie_sha256,source_sha256=ORIGINAL_SHA,
        standalone_proof_path=str(proof),standalone_proof_sha256=expected_proof_sha256,
        reviewed_candidate_report=str(review),reviewed_candidate_report_sha256=p['review_sha256'],installed_in_iso=False,
        native_playback_verified=False,whole_movie_japanese_absence_verified=False,
        intentional_backplates=True,other_movies_installed=0)
    return (ASSET,movie,expected_movie_sha256,len(data)),coverage
