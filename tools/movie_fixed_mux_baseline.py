"""Pure whole-IDR-GOP compression baseline and full PC timing/decode audit, no PMF writes."""
import argparse, collections, hashlib, json, subprocess
from pathlib import Path
from movie_fixed_mux import source, access_units, prepare as fixed
from movie_avc_timing import transplant, nals, sps

DIR=Path('work/source/media_audit/fixed_mux_experiment')
VARIANTS={3:['p03_crf28_full.h264','p03_crf28_zone40_full.h264',
    'p03_main28_gop40_timing_full.h264','p03_main28_two_gop38_full.h264',
    'p03_main28_aq0_gop40_full.h264','p03_main28_gop48_timing_full.h264'],
    9:['p09_crf28_full.h264','p09_crf28_zonegop40_full.h264',
    'p09_main28_gop40_timing_full.h264','p09_main28_aq0_gop40_full.h264',
    'p09_main28_gop48_timing_full.h264']}

def sha(data):return hashlib.sha256(data).hexdigest()

def probe(data):
    p=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_streams',
        '-show_entries','frame=key_frame,pict_type,pts,pkt_dts,best_effort_timestamp,width,height:stream=profile,level,width,height,has_b_frames,refs,pix_fmt,time_base',
        '-of','json','pipe:0'],input=data,capture_output=True)
    if p.returncode:raise ValueError(p.stderr.decode(errors='replace'))
    return json.loads(p.stdout),p.stderr.decode(errors='replace')

def prepare(number,decode=False):
    original,video,_,units,base=source(number);variants=[];files=[]
    for name in VARIANTS[number]:
        raw=(DIR/name).read_bytes();au=access_units(raw)
        assert len(au)==len(units) and [i for i,x in enumerate(au) if x['idr']]==base['idr_frame_indexes']
        transformed,_=transplant(video,raw,units,au,True)
        variants.append((name,raw,au,access_units(transformed)))
        files.append(dict(path=(DIR/name).as_posix(),sha256=sha(raw),bytes=len(raw)))
    if number==3:
        name='p03_gop1927_cqp44.h264';raw=(DIR/name).read_bytes();au=access_units(raw)
        sub=video[units[1927]['start']:units[1985]['end']];ou=access_units(sub)
        assert len(au)==59 and [i for i,x in enumerate(au) if x['idr']]==[0]
        transformed,_=transplant(sub,raw,ou,au,True)
        variants.append((name,raw,au,access_units(transformed)))
        files.append(dict(path=(DIR/name).as_posix(),sha256=sha(raw),bytes=len(raw)))
    output=bytearray();ledger=[];starts=base['idr_frame_indexes']+[len(units)]
    for start,end in zip(starts,starts[1:]):
        for name,raw,au,measured in variants:
            local=name=='p03_gop1927_cqp44.h264'
            if local and (start,end)!=(1927,1986):continue
            a,b=(0,59) if local else (start,end)
            if any(x['bytes']>y['bytes'] for x,y in zip(measured[a:b],units[start:end])):continue
            selected=raw[au[a]['start']:au[b-1]['end']]
            kinds=[k for k,_,_ in nals(selected[:au[a]['bytes']])]
            assert 7 in kinds and 8 in kinds,'Selected IDR must carry its actual SPS/PPS'
            _,_,fields=sps(next(p for k,r,p in nals(selected[:au[a]['bytes']]) if k==7))
            assert fields['profile']==77 and fields['max_num_ref_frames']==1
            output.extend(selected);ledger.append(dict(first_frame=start,last_frame=end-1,source=name));break
        else:raise ValueError('No fitted complete IDR GOP at '+str(start))
    candidate,report=fixed(number,bytes(output),timing_transplant=True,compact_clock=True)
    assert candidate is not None and report['overflowing_frames']==0
    report.update(status='fixed_mux_compression_baseline_static_only',encoder_inputs=files,
        whole_idr_gop_ledger=ledger,assembled_encoder_sha256=sha(output),
        selected_gop_counts=dict(collections.Counter(x['source'] for x in ledger)),
        translated_pixels_installed=False,native_psp_decode_verified=False,pc_decode_verified=False,
        optional_clock_encoded_bytes_saved_per_frame=5,
        notes=['GOPs selected in ordered preference, keeping the original CRF28 baseline wherever it fits.',
            'A standalone CQP44 GOP is required for prologue frames1927..1985; its actual SPS/PPS is retained.' if number==3 else 'Only two credits GOPs require tested encoder variants; no standalone prologue CQP44 GOP is used.',
            'No PMF file is saved. Candidate exists only in memory; PC validation does not prove PSP compatibility or caption quality.'])
    # Full AU AUD bytes agree, not merely counts/IDR positions.
    # The output raw encoder timeline has the same I/P AUD primary_pic_type bytes.
    output_units=access_units(output)
    assert [next(p for k,r,p in nals(output[x['start']:x['end']]) if k==9) for x in output_units]==[
        next(p for k,r,p in nals(video[x['start']:x['end']]) if k==9) for x in units]
    report['all_aud_primary_picture_types_exact']=True
    if decode:
        old,old_errors=probe(original);new,new_errors=probe(candidate)
        comparisons=len(old['frames']);assert comparisons==len(units)==len(new['frames'])
        keys=('key_frame','pict_type','pts','pkt_dts','best_effort_timestamp','width','height')
        old_core=[{k:a.get(k) for k in keys} for a in old['frames']]
        new_core=[{k:a.get(k) for k in keys} for a in new['frames']]
        differences=[dict(frame=i,original=a,replacement=b) for i,(a,b) in enumerate(zip(old_core,new_core)) if a!=b]
        report['pc_decode']=dict(frame_count=comparisons,exact_frame_timing_picture_metadata=not differences,
            first_metadata_differences=differences[:4],difference_count=len(differences),
            original_stream=old['streams'],candidate_stream=new['streams'],
            original_decoder_errors=old_errors,candidate_decoder_errors=new_errors,
            original_timing_sha256=sha(json.dumps(old_core,separators=(',',':')).encode()),
            candidate_timing_sha256=sha(json.dumps(new_core,separators=(',',':')).encode()),
            optional_smpte_clock_side_data_original_frames=sum('side_data_list' in a for a in old['frames']),
            optional_smpte_clock_side_data_candidate_frames=sum('side_data_list' in a for a in new['frames']),
            fields='key_frame,pict_type,PTS,DTS,best_effort_timestamp,width,height')
        report['pc_decode_verified']=not new_errors and not differences
        if not report['pc_decode_verified']:report['status']='fixed_mux_baseline_pc_timeline_or_decode_rejected'
    return candidate,report

def quality(candidate,report):
    p=subprocess.run(['ffmpeg','-v','info','-i',report['file'],'-i','pipe:0','-filter_complex',
        '[0:v]setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]psnr','-an','-f','null','-'],
        input=candidate,capture_output=True)
    assert p.returncode==0
    lines=[line for line in p.stderr.decode(errors='replace').splitlines() if 'PSNR y:' in line]
    assert len(lines)==1
    return dict(metric='Full-movie decoded YUV PSNR against native original',summary=lines[0].split('PSNR ')[1],
        translated_caption_quality_verified=False,notes='A mean quality metric cannot establish subtitle readability; selected low-quality GOP images and native decoder acceptance still require human review.')

def previews(candidate,report,destination):
    from PIL import Image,ImageDraw
    frames=sorted(set([0,report['idr_frame_indexes'][-1],report['frames']-1]+([1927,1985] if report['movie']==3 else [6972,7031])))
    select='+'.join('eq(n\\,%d)'%x for x in frames)
    decoded=[]
    for data in (Path(report['file']).read_bytes(),candidate):
        p=subprocess.run(['ffmpeg','-v','error','-i','pipe:0','-vf','select='+select,'-fps_mode','vfr',
            '-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],input=data,capture_output=True)
        assert p.returncode==0 and not p.stderr and len(p.stdout)==len(frames)*480*272*3
        decoded.append(p.stdout)
    sheet=Image.new('RGB',(960,len(frames)*292),(35,35,35));draw=ImageDraw.Draw(sheet)
    for i,frame in enumerate(frames):
        for side in range(2):
            start=i*480*272*3;im=Image.frombytes('RGB',(480,272),decoded[side][start:start+480*272*3])
            sheet.paste(im,(side*480,i*292+20));draw.text((side*480+4,i*292+3),('Native original' if side==0 else 'Compressed baseline')+' frame '+str(frame),fill='white')
    assert not destination.exists();destination.parent.mkdir(parents=True,exist_ok=True);sheet.save(destination)
    return dict(path=destination.as_posix(),sha256=sha(destination.read_bytes()),selected_frames=frames,
        scope='First frame, last IDR, last frame and selected constrained GOP endpoints, decoded on PC; not PSP playback.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--movie',type=int,choices=(3,9),default=3)
    p.add_argument('--decode',action='store_true');p.add_argument('--quality',action='store_true');p.add_argument('--report',type=Path);p.add_argument('--preview',type=Path);a=p.parse_args()
    candidate,r=prepare(a.movie,a.decode)
    if a.quality:r['compression_quality']=quality(candidate,r)
    print(json.dumps({k:v for k,v in r.items() if k not in ('pes_timestamp_records','idr_frame_indexes','whole_idr_gop_ledger','encoder_inputs')},indent=2))
    if a.preview:r['pixel_review']=previews(candidate,r,a.preview)
    if a.report:
        assert not a.report.exists();a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
