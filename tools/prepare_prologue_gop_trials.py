"""RAM-only whole-GOP selection between moderate-quality prologue encoder trials."""
import argparse,json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from prepare_full_prologue import prepare,BOUNDARY_GROUPS,select_expr
from movie_fixed_mux import source,access_units,prepare as mux
from movie_fixed_mux_baseline import probe
from prepare_prologue_overlays import sha,MOVIE

def trial():
    native_pmf,native_video,_,native_units,native=source(3)
    variants=[]
    for mode,value in [('crf',35),('qp',35)]:
        _,report,sheet,stream=prepare(crf=value if mode=='crf' else None,qp=value if mode=='qp' else None,return_stream=True)
        variants.append((mode,report,sheet,stream,access_units(stream)))
    starts=native['idr_frame_indexes'];parts=[];ledger=[]
    for a,b in zip(starts,starts[1:]+[6425]):
        candidates=[]
        for order,(mode,r,_,stream,units) in enumerate(variants):
            excess=[units[i]['bytes']-native_units[i]['bytes'] for i in range(a,b)]
            failures=sum(x>0 for x in excess)
            candidates.append((failures,max(0,max(excess)),order,mode,stream,units))
        # Prefer CRF35 when both entire GOPs fit; never mix interdependent P pictures.
        failures,maximum,_,mode,stream,units=min(candidates,key=lambda x:(x[0],x[1],x[2]))
        block=stream[units[a]['start']:units[b-1]['end']]
        original=native_video[native_units[a]['start']:native_units[b-1]['end']]
        parts.append(block);ledger.append(dict(first=a,last=b-1,selected_mode=mode,failed_frames=failures,
            maximum_excess=maximum,native_byte_exact=block==original))
    mixed=b''.join(parts);candidate,fit=mux(3,mixed)
    units=access_units(mixed);assert len(units)==6425
    fs=variants[0][1]['selected_pc_decoded_frames']
    decoded=subprocess.run(['ffmpeg','-v','error','-f','h264','-i','pipe:0','-vf','select='+select_expr(fs),'-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],input=mixed,capture_output=True)
    assert not decoded.returncode and not decoded.stderr and len(decoded.stdout)==len(fs)*391680
    sheet=variants[0][2].crop((0,0,1440,len(fs)*294));d=ImageDraw.Draw(sheet)
    for i,n in enumerate(fs):
        sheet.paste(Image.frombytes('RGB',(480,272),decoded.stdout[i*391680:(i+1)*391680]),(960,i*294+22))
        d.rectangle((960,i*294,1440,i*294+21),fill='black');d.text((963,i*294+3),'Selected GOP decoded frame '+str(n),fill='white')
    report=dict(schema_version=1,status='ram_candidate_runtime_unverified' if candidate else 'moderate_quality_gop_capacity_rejected',
        source_sha256=sha(native_pmf),target_queue_sha256=variants[0][1]['target_queue_sha256'],
        input_variants=[dict(mode=m,encoder_sha256=r['encoder_sha256'],overflow_frames=len(r['overflowing_frame_indexes'])) for m,r,_,_,_ in variants],
        selected_gops=ledger,fixed_mux=fit,mixed_es_sha256=sha(mixed),
        selected_pc_decoded_frames=fs,boundary_groups=BOUNDARY_GROUPS,whole_movie_japanese_absence_verified=False,
        native_assets_written=False,runtime_verified=False,
        limitations=['Selection is whole-GOP only. Both encoder settings remain35; no severeQP trial is selected.',
            'Native caption overlap9-to10 is not fully preserved: the next plate occludes the previous fading English sentence.',
            'Selected PC frames cannot establish whole-movie absence of Japanese ghosts or native decoder compatibility.'])
    if candidate:
        original=probe(native_pmf)[0];actual,err=probe(candidate)
        fields=('key_frame','pict_type','pts','pkt_dts','best_effort_timestamp','width','height')
        assert not err and len(actual['frames'])==6425
        diff=[i for i,(a,b) in enumerate(zip(original['frames'],actual['frames'])) if any(a.get(k)!=b.get(k) for k in fields)]
        assert not diff;report['full_pc_timing']=dict(frame_count=6425,differences=0,decode_errors=err)
    return report,sheet

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-review',action='store_true');p.add_argument('--output',default='work/ui/media/full_prologue_moderate_gop_trials');args=p.parse_args()
    report,sheet=trial()
    print(json.dumps(dict(status=report['status'],variants=report['input_variants'],failed_gops=[x for x in report['selected_gops'] if x['failed_frames']],candidate_generated=report['fixed_mux']['candidate_generated']),indent=2))
    if args.write_review:
        dest=Path(args.output).resolve();dest.relative_to(Path('work/ui').resolve());assert not dest.exists();dest.mkdir(parents=True)
        (dest/'proposal.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');sheet.save(dest/'all_native_intended_decoded.png')
        fs=report['selected_pc_decoded_frames']
        for key,frames in BOUNDARY_GROUPS.items():
            proof=Image.new('RGB',(1440,len(frames)*294))
            for j,n in enumerate(frames):
                i=fs.index(n);proof.paste(sheet.crop((0,i*294,1440,(i+1)*294)),(0,j*294))
            proof.save(dest/(key+'_native_intended_decoded.png'))
