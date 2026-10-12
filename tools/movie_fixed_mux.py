"""Pure fixed-mux AVC replacement feasibility; never writes PMF/native assets."""
import argparse
import bisect
import collections
import hashlib
import json
import re
import struct
from pathlib import Path
from inspect_psmf_structure import EXPECTED, pts

START_CODE=re.compile(b'\x00\x00\x01')

def access_units(video):
    nals=[]
    for match in START_CODE.finditer(video):
        start=match.start()
        if start and video[start-1]==0:start-=1
        nals.append((start,match.end(),video[match.end()]&31))
    starts=[start for start,header,kind in nals if kind==9]
    assert starts and starts[0]==0,'Explicit leading AUD required'
    per_unit=[[] for _ in starts]
    for position,header,kind in nals:
        per_unit[bisect.bisect_right(starts,position)-1].append(kind)
    result=[]
    for (start,end),types in zip(zip(starts,starts[1:]+[len(video)]),per_unit):
        assert sum(t in (1,5) for t in types)==1,'Require one slice/picture per AUD'
        result.append(dict(start=start,end=end,bytes=end-start,idr=5 in types,nal_types=types))
    return result

def source(number):
    path=Path('work/source/media_audit')/f'PSP_GAME_USRDIR_MOVIE_HPMOVE{number:02}.PMF'
    data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==EXPECTED[number]
    stream=struct.unpack_from('>I',data,8)[0];offset=stream;video=bytearray();payloads=[];nav=[];timestamp_records=[]
    immutable=hashlib.sha256();audio=hashlib.sha256();nav_raw=hashlib.sha256()
    while offset<len(data):
        assert data[offset:offset+3]==b'\0\0\1';code=data[offset+3]
        end=offset+14+(data[offset+13]&7) if code==0xba else offset+6+struct.unpack_from('>H',data,offset+4)[0]
        assert offset<end<=len(data)
        if code==0xe0:
            start=offset+9+data[offset+8]
            payloads.append(dict(file_start=start,file_end=end,es_start=len(video),es_end=len(video)+end-start))
            immutable.update(data[offset:start])
            if data[offset+7]&128:
                timestamp_records.append(dict(es_offset=len(video),pts=pts(data[offset+9:offset+14]),
                    dts=pts(data[offset+14:offset+19]) if data[offset+7]&64 else None))
            video.extend(data[start:end])
        else:
            immutable.update(data[offset:end])
            if code==0xbd:audio.update(data[offset:end])
            if code==0xbf:
                body=data[offset+6:end];assert body[:2]==b'\x01\xe0'
                count=struct.unpack_from('>H',body,16)[0];assert len(body)==18+count*4
                nav_raw.update(data[offset:end])
                for index in range(count):
                    word=struct.unpack_from('>I',body,18+index*4)[0]
                    assert word&0xffff0000==0x00800000
                    nav.append(word&65535)
        offset=end
    units=access_units(video)
    assert nav==[x['bytes'] for x in units],'Every private navigation AU length must agree'
    return data,bytes(video),payloads,units,dict(movie=number,file=path.as_posix(),source_sha256=EXPECTED[number],
        frames=len(units),idr_frame_indexes=[i for i,x in enumerate(units) if x['idr']],
        elementary_bytes=len(video),elementary_sha256=hashlib.sha256(video).hexdigest(),
        navigation_au_count=len(nav),all_navigation_au_lengths_match_aud=True,
        navigation_pes_sha256=nav_raw.hexdigest(),audio_pes_sha256=audio.hexdigest(),
        immutable_packet_fields_sha256=immutable.hexdigest(),pes_timestamp_records=timestamp_records,
        smallest_original_au=min(nav),largest_original_au=max(nav))

def filler(size):
    if size<5:return b'\0'*size # Annex-B trailing_zero_8bits, before next AUD.
    return b'\0\0\1\x0c'+b'\xff'*(size-5)+b'\x80'

def prepare(number,replacement=None,prefix=False,timing_transplant=False,compact_clock=False):
    data,video,payloads,units,report=source(number)
    report.update(status='fixed_mux_original_navigation_audit',native_assets_written=False,runtime_verified=False,
        constraints=['Exact AUD offsets, picture order and IDR schedule required, not just GOP byte totals.',
            'All original audio/PES headers/private navigation/SCR/PSMF/EP-map bytes retained.',
            'Per-frame fit cannot be assumed; quality/readability and real PSP decoder acceptance remain independent requirements.'],
        sources=['https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavcodec/h264_parser.c',
                 'https://www.itu.int/rec/T-REC-H.264-202408-I/en',
                 'https://raw.githubusercontent.com/jpcsp/jpcsp/master/src/jpcsp/HLE/modules/sceMpeg.java'])
    # Byte-exact identity round trip through discontiguous MPEG payload extents.
    identity=bytearray(data)
    for payload in payloads:identity[payload['file_start']:payload['file_end']]=video[payload['es_start']:payload['es_end']]
    assert identity==data;report['identity_roundtrip_exact']=True
    if replacement is None:return None,report
    changed=replacement if isinstance(replacement,bytes) else Path(replacement).read_bytes();new=access_units(changed)
    assert len(new)==len(units) or prefix and len(new)<len(units)
    assert [i for i,x in enumerate(new) if x['idr']]==[i for i,x in enumerate(units[:len(new)]) if x['idr']]
    if len(new)<len(units):
        from movie_avc_timing import nals
        next_unit=units[len(new)]
        next_types=[kind for kind,raw,payload in nals(video[next_unit['start']:next_unit['end']])]
        assert next_unit['idr'] and 7 in next_types and 8 in next_types,'Retained native continuation must reset references and native SPS/PPS'
        report['native_prefix_continuation']=dict(frame=len(new),idr=True,sps_pps_present=True)
    if timing_transplant:
        from movie_avc_timing import transplant
        if len(new)<len(units):assert prefix and units[len(new)]['idr'],'Prefix must end at retained native IDR'
        changed,timing=transplant(video,changed,units[:len(new)],new,compact_clock)
        new=access_units(changed);report['timing_transplant']=timing
    failures=[dict(frame=i,original_capacity=old['bytes'],replacement_bytes=item['bytes'],excess=item['bytes']-old['bytes'])
              for i,(old,item) in enumerate(zip(units,new)) if item['bytes']>old['bytes']]
    report.update(status='fixed_mux_fit_rejected' if failures else 'fixed_mux_fit_static_candidate',
        replacement_sha256=hashlib.sha256(changed).hexdigest(),replacement_frames=len(new),prefix_experiment=prefix,
        overflowing_frames=len(failures),first_failures=failures[:24],maximum_excess=max([x['excess'] for x in failures] or [0]),
        all_au_starts_unchanged=False,candidate_generated=False)
    if failures:return None,report
    if len(new)<len(units) and not units[len(new)]['idr']:
        report['prefix_splice_rejected']='Next retained native frame is not IDR; reference continuity is not proven.'
        return None,report
    exact=bytearray(video)
    for old,item in zip(units,new):
        exact[old['start']:old['end']]=changed[item['start']:item['end']]+filler(old['bytes']-item['bytes'])
    assert len(exact)==len(video)
    parsed=access_units(exact)
    assert [x['start'] for x in parsed]==[x['start'] for x in units]
    assert [x['idr'] for x in parsed]==[x['idr'] for x in units]
    candidate=bytearray(data)
    for payload in payloads:candidate[payload['file_start']:payload['file_end']]=exact[payload['es_start']:payload['es_end']]
    # Masking only video payloads proves every other original byte retained.
    masked=bytearray(candidate)
    for payload in payloads:masked[payload['file_start']:payload['file_end']]=data[payload['file_start']:payload['file_end']]
    assert masked==data
    report.update(candidate_generated=True,all_au_starts_unchanged=True,all_non_video_payload_bytes_exact=True,
        candidate_sha256=hashlib.sha256(candidate).hexdigest(),candidate_bytes=len(candidate))
    return bytes(candidate),report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--movie',type=int,choices=(3,9),default=3)
    p.add_argument('--replacement',type=Path);p.add_argument('--prefix-experiment',action='store_true')
    p.add_argument('--timing-transplant',action='store_true')
    p.add_argument('--compact-clock',action='store_true')
    p.add_argument('--report',type=Path);a=p.parse_args();assert not a.compact_clock or a.timing_transplant
    candidate,r=prepare(a.movie,a.replacement,a.prefix_experiment,a.timing_transplant,a.compact_clock)
    print(json.dumps({k:v for k,v in r.items() if k not in ('pes_timestamp_records','idr_frame_indexes')},indent=2))
    if a.report:
        assert not a.report.exists();a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
