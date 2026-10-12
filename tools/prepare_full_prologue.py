"""Full English prologue RAM encoder experiment; explicit review output excludes PMF/video assets."""
import argparse,json,subprocess,threading
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from prepare_prologue_overlays import MOVIE,SHA,QUEUE,sha,raster
from movie_fixed_mux import source,prepare as mux,access_units
from movie_fixed_mux_baseline import probe

PLAN=Path('work/ui/media/full_prologue_overlay_plan/proposal.en.json')
LAYERS=Path('work/ui/media/staggered_prologue_layer_plan_v3/proposal.en.json')
SIGN=Path('work/ui/media/prologue_facade_sign_proposal_v3/proposal.en.json')
BOUNDARY_GROUPS={
    'ordinary1_carryover':[195,235,264,265,267,268,295,302,303,360,430,480],
    'ordinary2_onset':[617,618,628,657,658,688],
    'ordinary6_fade':[1957,1970,1981,2010,2100,2141,2171,2180,2190,2220,2230,2240],
    'ordinary14_onset':[4770,4800,4820,4849,4850,4880],
    'ordinary14_paper_tail':[5650,5660,5666,5670,5680,5690,5700,5710,5718],
    'sign_onset':[3600,3601,3610,3620,3630,3650,3700],
    'ordinary9_to10_overlap':[3337,3366,3380,3390,3400,3420,3450,3480,3510]}

def select_expr(frames):
    terms=['eq(n\\,%d)'%n for n in frames]
    while len(terms)>1:terms=['('+terms[i]+'+'+terms[i+1]+')' if i+1<len(terms) else terms[i] for i in range(0,len(terms),2)]
    return terms[0]

def events():
    original=json.loads(PLAN.read_bytes());layered=json.loads(LAYERS.read_bytes());sign=json.loads(SIGN.read_bytes())
    assert all(x.get('target_queue_sha256',x.get('target_queue_sha256'))==sha(QUEUE.read_bytes()) for x in (original,layered,sign))
    result=[]
    for i,x in enumerate(original['entries']):
        if i in (7,11,12,15,16):continue
        a,b=x['timing_candidate']['first_core_frame'],x['timing_candidate']['last_core_frame']
        result.append(dict(key='ordinary_'+str(i),target=x['target'],box=x['box'],ref=x['representative_native_frame'],index=i,
            first=max(0,a-30),last=min(6424,b+30),fade_kind='bounded_linear',core=[a,b]))
    for x in layered['layers']:
        a,b=x['core_frames'];result.append(dict(key=x['key'],target=x['target'],box=x['box'],ref=x['ref'],index=12,
            first=max(0,a-30),last=min(6424,b+30),fade_kind='bounded_linear',core=[a,b],source_box=x['source_box']))
    # Human-inspected native boundary samples supersede contaminated whole-box correlations.
    starts={1:195,2:618,3:972,4:1307,5:1643,6:1957,8:2673,9:3073,10:3380,14:4770}
    for e in result:
        if not e['key'].startswith('ordinary_'):continue
        i=e['index']
        if i in starts:e['first']=starts[i];e['onset_note']='Conservative source-field coverage based on native boundary review; exact authoring onset not claimed.'
        if i==6:e.update(last=2240,core=[2100,2180],end_note='Native black-background luminance confirms full brightness2100..2180, fading2190..2236; matte retained through2240.')
        if i==1:
            _,layout=raster(e['target'],e['box'],1);assert len(layout['lines'])==2
            e['physical_lines']=[dict(target=layout['lines'][0],box=[12,96,468,127],first=195,full=360),
                                 dict(target=layout['lines'][1],box=[12,145,468,177],first=268,full=430)]
            e['gap_matte']=dict(box=[12,127,468,145],first=268)
            e['overlap_note']='First narration line appears while present-day remains; disjoint strips preserve that carryover through267. From268 an opaque gap matte removes tall emphasized native glyphs between strips; both English lines retain their individual fades.'
    first=result[0];assert first['key']=='ordinary_0'
    first.update(first=19,last=302,core=[49,267],fade_kind='native_rule_pilot_bounds',
        fade_note='Restores validated first-caption pilot region19..302 including compression ghosts. Later overlapping caption composites above it.')
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-frames:v','303','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==303*391680
    rgb=np.frombuffer(p.stdout,np.uint8).reshape(303,272,480,3)
    rows={y:rgb[:,y,170:250,:].min(axis=2).astype(float) for y in (131,134,135,137)}
    background=(rows[131]+rows[137])/2
    contrast=np.maximum(np.median(rows[134]-background,axis=1),np.median(rows[135]-background,axis=1))
    first['alpha_trace']=[round(float(max(0,min(1,contrast[n]/157))),6) if n<=267 else 0 for n in range(19,303)]
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select=between(n\\,1957\\,2240)','-fps_mode','vfr','-an','-pix_fmt','gray','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==284*130560
    g=np.frombuffer(p.stdout,np.uint8).reshape(284,272,480)
    values=np.percentile(g[:,116:151,10:470],98,axis=(1,2))
    values=np.array([np.median(values[max(0,i-4):min(len(values),i+5)]) for i in range(len(values))])
    sixth=next(e for e in result if e['key']=='ordinary_6')
    sixth.update(fade_kind='native_black_background_luminance',brightness_normalizer=255,
        alpha_trace=[round(float(max(0,min(1,v/255))),6) for v in values],
        fade_note='Nine-frame median of native black-background ROI98th-percentile intensity; matte bounds include faint boundary remnants.')
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select=between(n\\,3530\\,3599)','-fps_mode','vfr','-an','-pix_fmt','gray','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==70*130560
    g=np.frombuffer(p.stdout,np.uint8).reshape(70,272,480)
    values=np.percentile(g[:,65:199,25:455],99.5,axis=(1,2))
    values=np.array([np.median(values[max(0,i-2):min(len(values),i+3)]) for i in range(len(values))])
    tenth=next(e for e in result if e['key']=='ordinary_10');old=[opacity(tenth,n) for n in range(tenth['first'],3530)]
    full=float(np.median(values[:20]));assert full>200
    tenth.update(last=3599,fade_kind='native_black_background_tail_luminance',
        alpha_trace=old+[round(float(max(0,min(1,v/full))),6) for v in values],
        fade_note='Native black-background tail intensity replaces the excessive English fade; no caption overlay remains at3600.')
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select=between(n\\,5650\\,5718)','-fps_mode','vfr','-an','-pix_fmt','gray','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==69*130560
    g=np.frombuffer(p.stdout,np.uint8).reshape(69,272,480)
    values=np.percentile(g[:,68:224,12:475],75,axis=(1,2));full=float(np.median(values[:10]));assert full>150
    letter=next(e for e in result if e['key']=='ordinary_14')
    letter.update(paper_tail_first=5650,paper_tail_trace=[round(float(max(0,min(1,v/full))),6) for v in values],
        panel_policy='White matte remains white during black-glyph fade-in; after5650 the entire panel follows the measured native paper fade to black.')
    # Ending15's shape score was dark despite native white glyphs. Measure actual black-background foreground.
    selected=list(range(5760,6425));p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select=gte(n\\,5760)','-fps_mode','vfr','-an','-pix_fmt','gray','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==len(selected)*130560
    g=np.frombuffer(p.stdout,np.uint8).reshape(-1,272,480)
    for e in result:
        if not e['key'].startswith('ending_'):continue
        x,y,X,Y=e['source_box'];values=np.percentile(g[:,y:Y,x:X],98,axis=(1,2))
        values=np.array([np.median(values[max(0,i-4):min(len(values),i+5)]) for i in range(len(values))])
        full=float(np.median(values[5940-5760:5990-5760])) if e['key']=='ending_15' else float(np.median(values[6120-5760:6240-5760]))
        assert full>230
        at=e['ref']-5760;a=b=at
        while a and values[a-1]>6:a-=1
        while b<len(values)-1 and values[b+1]>6:b+=1
        e.update(first=5760+a,last=5760+b,fade_kind='native_black_background_luminance',brightness_normalizer=full,
            alpha_trace=[round(float(max(0,min(1,v/full))),6) for v in values[a:b+1]],
            fade_note='Nine-frame median of native ROI98th-percentile intensity, normalized at verified mid-full brightness; decoded visibility threshold6, not authoring timestamps.')
    return result,sign

def opacity(e,n):
    if n<e['first'] or n>e['last']:return 0
    if 'alpha_trace' in e:return e['alpha_trace'][n-e['first']]
    a,b=e['core'];return max(0,min(1,(n-e['first'])/max(1,a-e['first']),(e['last']-n)/max(1,e['last']-b)))

def compose(im,n,entries,sign):
    out=im.copy()
    track=next((x for x in sign['tracks'] if x['frame']==n),None)
    if track is not None:
        panel,_=raster(sign['logical_target'],track['box'],12)
        alpha=max(0,min(1,track['score']/.8)) if track['score']>=.02 else 0
        panel=Image.blend(Image.new('RGB',panel.size),panel,alpha);out.paste(panel,track['box'])
    for e in entries:
        if e['first']<=n<=e['last']:
            if 'physical_lines' in e:
                if n>=e['gap_matte']['first']:
                    box=e['gap_matte']['box'];out.paste(Image.new('RGB',(box[2]-box[0],box[3]-box[1])),box)
                for line in e['physical_lines']:
                    if n<line['first']:continue
                    panel,_=raster(line['target'],line['box'],e['index'])
                    alpha=max(0,min(1,(n-line['first'])/(line['full']-line['first']),(e['last']-n)/30))
                    out.paste(Image.blend(Image.new('RGB',panel.size),panel,alpha),line['box'])
                continue
            panel=e.get('_panel')
            if panel is None:panel,_=raster(e['target'],e['box'],e['index']);e['_panel']=panel
            if e['key']=='ordinary_14':
                alpha=max(0,min(1,(n-e['first'])/max(1,e['core'][0]-e['first'])))
                panel=Image.blend(Image.new('RGB',panel.size,'white'),panel,alpha)
                if n>=e['paper_tail_first']:
                    panel=Image.blend(Image.new('RGB',panel.size),panel,e['paper_tail_trace'][n-e['paper_tail_first']])
            elif opacity(e,n)<1:panel=Image.blend(Image.new('RGB',panel.size),panel,opacity(e,n))
            out.paste(panel,e['box'])
    return out

def prepare(crf=None,qp=None,return_stream=False):
    assert crf is None or qp is None
    assert sha(MOVIE.read_bytes())==SHA
    entries,sign=events();report=dict(schema_version=1,status='full_prologue_fade_and_composite_dry_proposal',source_sha256=SHA,
        target_queue_sha256=sha(QUEUE.read_bytes()),primary_rows=17,composite_events=len(entries),staggered_fields=10,
        additional_diegetic_sign=True,events=entries,
        timing_policy='First caption uses native rule brightness; sixth and ending captions use native black-background brightness. Human-reviewed conservative onset bounds and separate overlapping strips supersede whole-box correlations. Remaining fades are bounded proposals; exact authoring timestamps are not claimed.',
        intentional_backplates=True,whole_movie_japanese_absence_verified=False,native_assets_written=False,runtime_verified=False)
    fs=sorted(set([x['ref'] for x in entries]+[5950,5970,3850,4100,4180]+sum(BOUNDARY_GROUPS.values(),[])))
    report['boundary_groups']=BOUNDARY_GROUPS
    p=subprocess.run(['ffmpeg','-v','error','-i',str(MOVIE),'-vf','select='+select_expr(fs),'-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True)
    assert not p.returncode and not p.stderr and len(p.stdout)==len(fs)*391680
    sheet=Image.new('RGB',(960,len(fs)*294));d=ImageDraw.Draw(sheet)
    for i,n in enumerate(fs):
        im=Image.frombytes('RGB',(480,272),p.stdout[i*391680:(i+1)*391680]);out=compose(im,n,entries,sign)
        sheet.paste(im,(0,i*294+22));sheet.paste(out,(480,i*294+22));d.text((3,i*294+3),f'Frame {n}: native / full English unencoded composite',fill='white')
    candidate=None;mixed=None
    if crf is not None or qp is not None:
        _,native_video,_,native_units,native=source(3);keys=','.join(f'{i*1001/30000:.9f}' for i in native['idr_frame_indexes'])
        rate=['-crf',str(crf)] if qp is None else ['-qp',str(qp)]
        enc=subprocess.Popen(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','rgb24','-video_size','480x272','-framerate','30000/1001','-i','pipe:0','-an','-c:v','libx264','-preset','slow']+rate+['-threads','1','-profile:v','main','-level:v','2.1','-pix_fmt','yuv420p','-bf','0','-refs','1','-g','10000','-keyint_min','1','-sc_threshold','0','-force_key_frames',keys,'-x264-params','aud=1:repeat-headers=1:weightp=0:threads=1:lookahead_threads=1','-bsf:v','filter_units=remove_types=6','-f','h264','pipe:1'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        output=[];errors=[]
        reader=threading.Thread(target=lambda:output.append(enc.stdout.read()));reader.start()
        er=threading.Thread(target=lambda:errors.append(enc.stderr.read()));er.start()
        dec=subprocess.Popen(['ffmpeg','-v','error','-i',str(MOVIE),'-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        n=0
        while True:
            raw=dec.stdout.read(391680)
            if not raw:break
            assert len(raw)==391680
            im=Image.frombytes('RGB',(480,272),raw);enc.stdin.write(compose(im,n,entries,sign).tobytes());n+=1
        assert dec.wait()==0 and not dec.stderr.read() and n==6425
        enc.stdin.close();assert enc.wait()==0;reader.join();er.join();assert not errors[0]
        encoded=output[0]
        from movie_avc_timing import transplant
        transformed,timing=transplant(native_video,encoded,native_units,access_units(encoded),True)
        new_units=access_units(transformed);parts=[];reused=[]
        starts=native['idr_frame_indexes'];signframes={x['frame'] for x in sign['tracks']}
        for a,b in zip(starts,starts[1:]+[6425]):
            active=any(e['first']<b and e['last']>=a for e in entries) or any(a<=n<b for n in signframes)
            if active:parts.append(transformed[new_units[a]['start']:new_units[b-1]['end']])
            else:
                parts.append(native_video[native_units[a]['start']:native_units[b-1]['end']]);reused.append([a,b-1])
        mixed=b''.join(parts);candidate,fit=mux(3,mixed)
        mu=access_units(mixed);overflow=[i for i,(a,b) in enumerate(zip(native_units,mu)) if b['bytes']>a['bytes']]
        gops=[]
        for a,b in zip(starts,starts[1:]+[6425]):
            bad=[i for i in overflow if a<=i<b]
            if bad:gops.append(dict(first=a,last=b-1,failed_frames=len(bad),maximum_excess=max(mu[i]['bytes']-native_units[i]['bytes'] for i in bad)))
        report.update(encoder_crf=crf,encoder_constant_qp=qp,encoder_threads=1,lookahead_threads=1,encoded_frames=n,encoder_bytes=len(encoded),encoder_sha256=sha(encoded),fixed_mux=fit,
            timing_transplant=timing,native_gops_reused_byte_exact=reused,
            overflowing_gops=gops,overflowing_frame_indexes=overflow,
            status='full_prologue_ram_mux_candidate_runtime_unverified' if candidate else 'full_prologue_encode_au_capacity_rejected')
        decoded=subprocess.run(['ffmpeg','-v','error','-f','h264','-i','pipe:0','-vf','select='+select_expr(fs),'-fps_mode','vfr','-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],input=mixed,capture_output=True)
        assert not decoded.returncode and not decoded.stderr and len(decoded.stdout)==len(fs)*391680
        final=Image.new('RGB',(1440,len(fs)*294));final.paste(sheet,(0,0));dd=ImageDraw.Draw(final)
        for i,frame in enumerate(fs):
            final.paste(Image.frombytes('RGB',(480,272),decoded.stdout[i*391680:(i+1)*391680]),(960,i*294+22));dd.text((963,i*294+3),f'Decoded frame {frame}',fill='white')
        sheet=final;report['selected_pc_decoded_frames']=fs
        if candidate:
            original=probe(MOVIE.read_bytes())[0];actual,err=probe(candidate)
            fields=('key_frame','pict_type','pts','pkt_dts','best_effort_timestamp','width','height')
            diff=[i for i,(a,b) in enumerate(zip(original['frames'],actual['frames'])) if any(a.get(k)!=b.get(k) for k in fields)]
            assert len(actual['frames'])==6425 and not err and not diff
            report['full_pc_timing']=dict(frame_count=6425,differences=0,decode_errors=err)
    for e in entries:e.pop('_panel',None)
    return (candidate,report,sheet,mixed) if return_stream else (candidate,report,sheet)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--crf',type=int);p.add_argument('--qp',type=int);p.add_argument('--write-review',action='store_true');p.add_argument('--output',default='work/ui/media/full_prologue_corrected_fades');a=p.parse_args()
    _,r,s=prepare(a.crf,a.qp);print(json.dumps({k:v for k,v in r.items() if k not in ('events','fixed_mux')},indent=2));print(json.dumps([dict(key=e['key'],first=e['first'],last=e['last'],fade=e['fade_kind'],alpha5950=opacity(e,5950)) for e in r['events'][-2:]],indent=2))
    if 'fixed_mux' in r:print(json.dumps({k:v for k,v in r['fixed_mux'].items() if k not in ('pes_timestamp_records','idr_frame_indexes')},indent=2))
    if a.write_review:
        dest=Path(a.output).resolve();dest.relative_to(Path('work/ui').resolve());assert not dest.exists();dest.mkdir(parents=True)
        s.save(dest/'all_native_english_composites.png');(dest/'proposal.en.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
        frames=r.get('selected_pc_decoded_frames',sorted(set([e['ref'] for e in r['events']]+[5950,5970,3850,4100,4180]+sum(BOUNDARY_GROUPS.values(),[]))))
        for key,selected in BOUNDARY_GROUPS.items():
            proof=Image.new('RGB',(s.width,294*len(selected)))
            for j,n in enumerate(selected):
                i=frames.index(n);proof.paste(s.crop((0,i*294,s.width,(i+1)*294)),(0,j*294))
            proof.save(dest/(key+'_native_intended_decoded.png'))
