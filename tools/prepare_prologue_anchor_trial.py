"""Pure English prologue anchor-span mux/PC-timing trial; review-only outputs."""
import argparse,json,subprocess
from pathlib import Path
from prepare_full_prologue import prepare,BOUNDARY_GROUPS,select_expr
from movie_anchor_mux import prepare as anchor_mux
from movie_fixed_mux import source,access_units
from movie_fixed_mux_baseline import probe
from prepare_prologue_overlays import MOVIE,sha
from PIL import Image,ImageDraw
from movie_preparation_runtime import fingerprint

def dependencies():
    paths=['tools/movie_preparation_runtime.py','tools/prepare_prologue_anchor_trial.py','tools/prepare_full_prologue.py','tools/movie_anchor_mux.py',
        'tools/movie_fixed_mux.py','tools/movie_avc_timing.py','tools/movie_fixed_mux_baseline.py','tools/prepare_prologue_overlays.py',
        'work/ui/media/full_prologue_overlay_plan/proposal.en.json',
        'work/ui/media/staggered_prologue_layer_plan_v3/proposal.en.json',
        'work/ui/media/prologue_facade_sign_proposal_v3/proposal.en.json',
        'tools/prepare_title_logo_proposal.py','work/source/ppsspp/assets/Roboto_Condensed-Regular.ttf']
    return {p:sha(Path(p).read_bytes()) for p in paths}

def trial(crf=28,recompute_bf_endpoints=False):
    _,r,s,stream=prepare(crf=crf,return_stream=True)
    preserved=[(a,b+1) for a,b in r['native_gops_reused_byte_exact']]
    candidate,report=anchor_mux(stream,preserve_native_gops=preserved,recompute_bf_endpoints=recompute_bf_endpoints)
    report.update(encoder_crf=crf,encoder_sha256=r['encoder_sha256'],target_queue_sha256=r['target_queue_sha256'],
        events=r['events'],selected_pc_decoded_frames=r['selected_pc_decoded_frames'],boundary_groups=BOUNDARY_GROUPS,
        whole_movie_japanese_absence_verified=False,review_images='Native / intended / decoded replacement VCL; anchor padding does not change VCL.')
    if candidate:
        original=probe(MOVIE.read_bytes())[0];actual,err=probe(candidate)
        fields=('key_frame','pict_type','pts','pkt_dts','best_effort_timestamp','width','height')
        differences=[i for i,(a,b) in enumerate(zip(original['frames'],actual['frames'])) if any(a.get(k)!=b.get(k) for k in fields)]
        report['full_pc_timing']=dict(frame_count=len(actual['frames']),differences=len(differences),first_difference_indexes=differences[:24],decode_errors=err)
        assert len(actual['frames'])==6425 and not err and not differences
        report['pc_timing_verified']=True
    return report,s

def adaptive_trial(return_candidate=False):
    if not __debug__:raise RuntimeError('Optimized Python is forbidden: structural assertions are required.')
    bound=dependencies()
    runtime=fingerprint()
    _,r28,s,stream28=prepare(crf=28,return_stream=True)
    _,initial=anchor_mux(stream28,recompute_bf_endpoints=True)
    _,r35,_,stream35=prepare(crf=35,return_stream=True)
    original,_,_,units,native=source(3);streams={28:stream28,35:stream35}
    parsed={q:access_units(stream) for q,stream in streams.items()}
    starts=native['idr_frame_indexes'];blocks=[];ledger=[]
    for a,b in zip(starts,starts[1:]+[6425]):
        q=35 if any(a<=x['first']<b for x in initial['failed_spans']) else 28
        u=parsed[q];blocks.append(streams[q][u[a]['start']:u[b-1]['end']])
        ledger.append(dict(first=a,last=b-1,encoder_crf=q))
    mixed=b''.join(blocks);preserved=[(a,b+1) for a,b in r28['native_gops_reused_byte_exact']]
    candidate,report=anchor_mux(mixed,preserve_native_gops=preserved,recompute_bf_endpoints=True)
    report.update(quality_policy='CRF28 preferred; only whole GOPs intersecting rejected28 anchor spans use35. No severeQP variants.',
        encoder_variants=[dict(crf=28,encoder_sha256=r28['encoder_sha256']),dict(crf=35,encoder_sha256=r35['encoder_sha256'])],
        crf28_failed_spans=initial['failed_spans'],whole_gop_ledger=ledger,
        frames_at_crf28=sum(x['last']-x['first']+1 for x in ledger if x['encoder_crf']==28),
        frames_at_crf35=sum(x['last']-x['first']+1 for x in ledger if x['encoder_crf']==35),
        target_queue_sha256=r28['target_queue_sha256'],events=r28['events'],boundary_groups=BOUNDARY_GROUPS,
        whole_movie_japanese_absence_verified=False,selected_pc_decoded_frames=r28['selected_pc_decoded_frames'])
    if candidate:
        old,_=probe(original);new,err=probe(candidate);fields=('key_frame','pict_type','pts','pkt_dts','best_effort_timestamp','width','height')
        differences=[i for i,(a,b) in enumerate(zip(old['frames'],new['frames'])) if any(a.get(k)!=b.get(k) for k in fields)]
        report['full_pc_timing']=dict(frame_count=len(new['frames']),differences=len(differences),decode_errors=err,
            first_differences=[dict(frame=i,original=old['frames'][i],candidate=new['frames'][i]) for i in differences[:12]])
        if len(new['frames'])!=6425 or err or differences:
            report['status']='anchor_hybrid_pc_timing_rejected'
            report['review_images']='CRF28 individual trial only; rejected RAM hybrid is not shown.'
            return report,s
        fs=report['selected_pc_decoded_frames']
        p=subprocess.run(['ffmpeg','-v','error','-i','pipe:0','-vf','select='+select_expr(fs),'-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],input=candidate,capture_output=True)
        assert not p.returncode and not p.stderr and len(p.stdout)==len(fs)*391680
        d=ImageDraw.Draw(s)
        for i,n in enumerate(fs):
            s.paste(Image.frombytes('RGB',(480,272),p.stdout[i*391680:(i+1)*391680]),(960,i*294+22))
            d.rectangle((960,i*294,1440,i*294+21),fill='black');d.text((963,i*294+3),'RAM mux decoded frame '+str(n),fill='white')
        report['review_images']='Native / intended / actual RAM candidate decoded frames.'
    assert dependencies()==bound
    assert fingerprint()==runtime
    report['input_dependencies_sha256']=bound
    report['preparation_runtime']=runtime
    return (candidate,report,s) if return_candidate else (report,s)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--crf',type=int,default=28);p.add_argument('--adaptive',action='store_true');p.add_argument('--recompute-bf-endpoints',action='store_true');p.add_argument('--write-review',action='store_true');p.add_argument('--output',default='work/ui/media/full_prologue_anchor_crf28');args=p.parse_args()
    r,s=adaptive_trial() if args.adaptive else trial(args.crf,args.recompute_bf_endpoints);print(json.dumps({k:v for k,v in r.items() if k not in ('events','selected_pc_decoded_frames','boundary_groups','whole_gop_ledger')},indent=2))
    if args.write_review:
        dest=Path(args.output).resolve();dest.relative_to(Path('work/ui').resolve());assert not dest.exists();dest.mkdir(parents=True)
        (dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');s.save(dest/'all_native_intended_decoded.png')
        fs=r['selected_pc_decoded_frames']
        for key,frames in BOUNDARY_GROUPS.items():
            out=Image.new('RGB',(s.width,294*len(frames)))
            for j,n in enumerate(frames):
                i=fs.index(n);out.paste(s.crop((0,i*294,s.width,(i+1)*294)),(0,j*294))
            out.save(dest/(key+'_native_intended_decoded.png'))
