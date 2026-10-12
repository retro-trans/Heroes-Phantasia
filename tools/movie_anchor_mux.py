"""Pure fixed-pack AVC padding redistribution with native GOP/timestamp anchors.

Only video PES payloads, verified BF01E0 AU-length low words, and optionally
the four independently verified BF AU-end packet-offset words may change.
No native asset writer is provided. Native decoder acceptance remains unproved.
"""
import bisect,hashlib,struct
from movie_fixed_mux import source,access_units,filler,START_CODE
from movie_avc_timing import nals,sps

def sha(data):return hashlib.sha256(data).hexdigest()

def anchors(units,records):
    starts=[u['start'] for u in units];bounds={0:0,len(units):units[-1]['end']}
    for i,u in enumerate(units):
        if u['idr']:bounds[i]=u['start']
    associations=[];prior_upper={}
    for r in records:
        p=r['es_offset'];i=bisect.bisect_left(starts,p)
        assert i<len(units)
        # Independently corroborate native timestamp association by its known 3003-tick timeline.
        assert r['pts']==90000+i*3003 and r['dts']==86997+i*3003
        bounds[i]=starts[i]
        if i:
            assert starts[i-1]<p<=starts[i]
            prior_upper[i-1]=min(prior_upper.get(i-1,p-1),p-1)
        else:assert p==0
        associations.append(dict(es_offset=p,frame=i,pts=r['pts'],dts=r['dts']))
    return bounds,prior_upper,associations

def navigation_anchors(data,payloads,units,bounds,fix_endpoints=True):
    ends=[p['es_end'] for p in payloads];offset=struct.unpack_from('>I',data,8)[0]
    first=0;blocks=0;comparisons=0
    while offset<len(data):
        code=data[offset+3];end=offset+14+(data[offset+13]&7) if code==0xba else offset+6+struct.unpack_from('>H',data,offset+4)[0]
        if code==0xbf:
            body=data[offset+6:end];assert body[:2]==b'\x01\xe0'
            count=struct.unpack_from('>H',body,16)[0]
            assert count>=4 and len(body)==18+count*4
            assert body[10:14]==b'\0'*4 and struct.unpack_from('>H',body,14)[0]==2+count*4
            for j in range(4):
                at=units[first+j]['end']-1;p=payloads[bisect.bisect_right(ends,at)]
                physical=p['file_start']+at-p['es_start'];expected=physical//2048-offset//2048
                assert struct.unpack_from('>H',body,2+j*2)[0]==expected
                if fix_endpoints:bounds[first+j+1]=units[first+j]['end']
                comparisons+=1
            first+=count;blocks+=1
        offset=end
    assert first==len(units)
    return dict(blocks=blocks,first_four_au_end_pack_offset_comparisons=comparisons,all_original_values_match=True,
        first_four_au_es_ends_fixed=fix_endpoints,remaining_prefix_zero_and_table_byte_count_verified=True)

def prepare(replacement,number=3,preserve_native_gops=(),recompute_bf_endpoints=False):
    data,video,payloads,units,native=source(number)
    new=access_units(replacement);assert len(new)==len(units)
    assert [i for i,u in enumerate(new) if u['idr']]==native['idr_frame_indexes']
    for old,item in zip(units,new):
        native_nals=nals(video[old['start']:old['end']]);replacement_nals=nals(replacement[item['start']:item['end']])
        assert [p for k,_,p in native_nals if k==9]==[p for k,_,p in replacement_nals if k==9],'AUD picture type changed'
        if item['idr'] and replacement[item['start']:item['end']]!=video[old['start']:old['end']]:
            assert any(k==8 for k,_,_ in replacement_nals),'IDR lacks local PPS reset'
            headers=[p for k,_,p in replacement_nals if k==7];assert len(headers)==1
            _,_,fields=sps(headers[0]);assert fields['profile']==77 and fields['max_num_ref_frames']==1
    bounds,upper,associations=anchors(units,native['pes_timestamp_records'])
    def slices(stream):
        return [m.start()-int(m.start()>0 and stream[m.start()-1]==0) for m in START_CODE.finditer(stream) if stream[m.end()]&31 in (1,5)]
    native_slices=slices(video);new_slices=slices(replacement);assert len(native_slices)==len(new_slices)==len(units)
    slice_offsets=[p-u['start'] for p,u in zip(new_slices,new)];lower={};slice_associations=[]
    for r in associations:
        i=r['frame'];p=r['es_offset'];first_slice=bisect.bisect_left(native_slices,p)
        assert first_slice in (i,max(0,i-1))
        slice_associations.append((p,first_slice))
        if i and first_slice==i:upper[i-1]=min(upper[i-1],p-1-slice_offsets[i-1])
        elif i:lower[i-1]=max(lower.get(i-1,0),p-slice_offsets[i-1])
    navigation=navigation_anchors(data,payloads,units,bounds,not recompute_bf_endpoints)
    indexes=sorted(bounds);allocations=[None]*len(units);failures=[]
    for a,b in zip(indexes,indexes[1:]):
        capacity=bounds[b]-bounds[a];sizes=[new[i]['bytes'] for i in range(a,b)]
        ceilings=[65535]*(b-a)
        if b-1 in upper:sizes[-1]=max(sizes[-1],bounds[b]-upper[b-1])
        if b-1 in lower:ceilings[-1]=min(ceilings[-1],bounds[b]-lower[b-1])
        if any(x>limit for x,limit in zip(sizes,ceilings)) or sum(sizes)>capacity:
            failures.append(dict(first=a,last=b-1,original_bytes=capacity,required_bytes=sum(sizes),
                excess=max(0,sum(sizes)-capacity),au_size_exceeds_u16=any(x>65535 for x in sizes)));continue
        slack=capacity-sum(sizes)
        # Retain each native allocation as far as possible, then distribute remaining padding.
        for j,i in enumerate(range(a,b)):
            take=min(slack,max(0,min(ceilings[j],units[i]['bytes'])-sizes[j]));sizes[j]+=take;slack-=take
        for j in range(len(sizes)):
            take=min(slack,ceilings[j]-sizes[j]);sizes[j]+=take;slack-=take
        assert not slack
        allocations[a:b]=sizes
    report=dict(schema_version=1,status='anchor_span_capacity_rejected' if failures else 'anchor_span_ram_candidate_runtime_unverified',
        source_sha256=native['source_sha256'],replacement_es_sha256=sha(replacement),
        frames=len(units),timestamp_associations=len(associations),fixed_anchor_count=len(bounds),
        all_aud_picture_types_exact=True,all_modified_idr_local_sps_pps_verified=True,
        private_navigation=navigation,
        failed_spans=failures,mutable_regions=['E0 video PES payloads','BF01E0 verified AU-size low16 words']+(['BF01E0 four verified AU-end packet offsets'] if recompute_bf_endpoints else []),
        native_assets_written=False,runtime_verified=False,candidate_generated=False,
        limitations=['Timestamp-to-first-AUD association is structurally checked and must also pass full PC decode timing.',
            'Native PSP AVC/ringbuffer/seek behavior remains runtime-unverified.',
            'Picture-offset EP byte is retained with original IDR ordinal, physical start, packet and timestamps; its broader semantics are not inferred.'])
    if failures:return None,report
    rebuilt=bytearray();starts=[]
    for i,(u,size) in enumerate(zip(new,allocations)):
        starts.append(len(rebuilt));rebuilt.extend(replacement[u['start']:u['end']]);rebuilt.extend(filler(size-u['bytes']))
    assert len(rebuilt)==len(video)
    for i,pos in bounds.items():assert (starts[i] if i<len(starts) else len(rebuilt))==pos
    for r in associations:assert bisect.bisect_left(starts,r['es_offset'])==r['frame']
    rebuilt_slices=[start+relative for start,relative in zip(starts,slice_offsets)]
    for p,first_slice in slice_associations:assert bisect.bisect_left(rebuilt_slices,p)==first_slice
    parsed=access_units(rebuilt);assert [u['bytes'] for u in parsed]==allocations
    candidate=bytearray(data)
    for p in payloads:candidate[p['file_start']:p['file_end']]=rebuilt[p['es_start']:p['es_end']]
    # Preserve native unmodified GOP bytes when explicitly requested and allocation allows exact identity.
    for a,b in preserve_native_gops:
        assert units[a]['idr'] and (b==len(units) or units[b]['idr'])
        lo,hi=units[a]['start'],units[b-1]['end']
        assert rebuilt[lo:hi]==video[lo:hi],'Requested native GOP is not byte-exact after redistribution'
    offset=struct.unpack_from('>I',data,8)[0];mutable=[];word_index=0;endpoint_changes=0;payload_ends=[p['es_end'] for p in payloads]
    while offset<len(data):
        code=data[offset+3];end=offset+14+(data[offset+13]&7) if code==0xba else offset+6+struct.unpack_from('>H',data,offset+4)[0]
        if code==0xbf:
            body=data[offset+6:end];assert body[:2]==b'\x01\xe0'
            count=struct.unpack_from('>H',body,16)[0];assert len(body)==18+count*4
            for j in range(4):
                at=parsed[word_index+j]['end']-1;p=payloads[bisect.bisect_right(payload_ends,at)]
                physical=p['file_start']+at-p['es_start'];new_value=physical//2048-offset//2048
                assert 0<=new_value<=65535
                pos=offset+6+2+j*2;old_value=struct.unpack_from('>H',data,pos)[0]
                if recompute_bf_endpoints:
                    struct.pack_into('>H',candidate,pos,new_value);mutable.append((pos,pos+2));endpoint_changes+=new_value!=old_value
                else:assert old_value==new_value,'Preserved BF endpoint no longer maps to its native packet'
            for j in range(count):
                pos=offset+6+18+j*4;word=struct.unpack_from('>I',data,pos)[0]
                assert word==0x00800000+units[word_index]['bytes']
                struct.pack_into('>H',candidate,pos+2,allocations[word_index]);mutable.append((pos+2,pos+4));word_index+=1
        offset=end
    assert word_index==len(units)
    candidate_navigation=navigation_anchors(bytes(candidate),payloads,parsed,{})
    masked=bytearray(candidate)
    for p in payloads:masked[p['file_start']:p['file_end']]=data[p['file_start']:p['file_end']]
    for a,b in mutable:masked[a:b]=data[a:b]
    assert masked==data,'A byte outside verified mutable fields changed'
    if replacement==video:assert candidate==data,'Native identity must be exact'
    report.update(candidate_generated=True,candidate_sha256=sha(candidate),candidate_bytes=len(candidate),
        all_nonmutable_bytes_exact=True,audio_pes_sha256=native['audio_pes_sha256'],
        native_idr_es_offsets_exact=True,all_native_timestamp_first_aud_associations_exact=True,
        all_native_timestamp_first_slice_associations_exact=True,native_first_slice_exceptions=sum(i!=r['frame'] for (_,i),r in zip(slice_associations,associations)),
        bf_navigation_words=len(units),changed_navigation_words=sum(x!=y['bytes'] for x,y in zip(allocations,units)),
        recomputed_bf_endpoints=recompute_bf_endpoints,changed_bf_endpoint_words=endpoint_changes,
        candidate_bf_end_packet_mapping_comparisons=candidate_navigation['first_four_au_end_pack_offset_comparisons'],
        original_header_epmap_scr_audio_and_pes_headers_exact=True,retained_native_gops=list(preserve_native_gops),
        identity_roundtrip_exact=replacement==video)
    return bytes(candidate),report
