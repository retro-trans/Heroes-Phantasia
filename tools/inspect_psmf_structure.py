"""Read-only PSMF seek/audio audit; --write saves a fresh review JSON, never movies."""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path

SOURCE=Path('work/source/media_audit')
EXPECTED={3:'252985cb74c0fa117c2f8cc48bb31e932a5ac671b14c3a18d5af2bc0d2b104c1',
          9:'4cce1578cad940901409f195f960309aa0aa27a4e30c24d525fdcf7dbd50b83a'}

def pts(data):
    assert len(data)==5 and data[0]&1 and data[2]&1 and data[4]&1
    return ((data[0]>>1)&7)<<30 | data[1]<<22 | (data[2]>>1)<<15 | data[3]<<7 | data[4]>>1

def audit(number):
    path=SOURCE/f'PSP_GAME_USRDIR_MOVIE_HPMOVE{number:02}.PMF'
    data=path.read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha==EXPECTED[number]
    assert data[:8]==b'PSMF0015'
    stream,size=struct.unpack_from('>II',data,8)
    assert stream==2048 and stream+size==len(data) and size%2048==0
    stream_count=struct.unpack_from('>H',data,0x80)[0];assert stream_count==2
    descriptors=[];maps=[]
    for index in range(stream_count):
        pos=0x82+16*index;raw=data[pos:pos+16]
        row=dict(header_offset=pos,raw_hex=raw.hex(),stream_id=raw[0],private_stream_id=raw[1])
        if raw[0]==0xe0:
            offset,count=struct.unpack_from('>II',raw,4)
            assert offset>=0x82+16*stream_count and offset+10*count<=stream
            row.update(width=raw[12]*16,height=raw[13]*16,ep_map_offset=offset,ep_map_entries=count,
                       ep_map_sha256=hashlib.sha256(data[offset:offset+10*count]).hexdigest())
            for i in range(count):
                ep_index,picture_offset,timestamp,packet=struct.unpack_from('>BBII',data,offset+10*i)
                absolute=stream+packet*2048
                assert stream<=absolute<len(data) and data[absolute:absolute+4]==b'\0\0\1\xba'
                pack=data[absolute:absolute+2048];pes=pack.find(b'\0\0\1\xe0')
                assert pes>=0 and pack[pes+7]&128 and pts(pack[pes+9:pes+14])==timestamp
                maps.append(dict(index=i,ep_index=ep_index,picture_offset_opaque=picture_offset,
                                 pts_90khz=timestamp,packet_index=packet,absolute_file_offset=absolute))
            assert all(a['pts_90khz']<b['pts_90khz'] and a['packet_index']<b['packet_index'] for a,b in zip(maps,maps[1:]))
        else:
            assert raw[0]==0xbd and raw[1]==0
            row.update(codec='private ATRAC stream by PPSSPP descriptor interpretation',
                       audio_channels=raw[14],frequency_code=raw[15])
        descriptors.append(row)
    audio=hashlib.sha256();audio_pts=hashlib.sha256();counts=collections.Counter();offset=stream
    audio_count=0;audio_timestamp_count=0;pack_positions=[]
    while offset<len(data):
        assert data[offset:offset+3]==b'\0\0\1'
        code=data[offset+3]
        if code==0xba:
            end=offset+14+(data[offset+13]&7);pack_positions.append(offset)
        elif code==0xb9:end=offset+4
        else:end=offset+6+struct.unpack_from('>H',data,offset+4)[0]
        assert offset<end<=len(data);counts[f'{code:02X}']+=1
        if code==0xbd:
            audio.update(data[offset:end]);audio_count+=1
            assert data[offset+9+data[offset+8]]==0
            if data[offset+7]&128:
                timestamp=pts(data[offset+9:offset+14]);audio_pts.update(struct.pack('>Q',timestamp));audio_timestamp_count+=1
        offset=end
    assert len(pack_positions)==size//2048 and all(p==stream+i*2048 for i,p in enumerate(pack_positions))
    return dict(file=path.as_posix(),sha256=sha,bytes=len(data),header_sha256=hashlib.sha256(data[:stream]).hexdigest(),
        stream_offset=stream,stream_bytes=size,pack_bytes=2048,all_pack_positions_aligned=True,
        descriptors=descriptors,ep_map=maps,all_ep_map_offsets_point_to_pack_with_matching_video_pts=True,
        packet_counts=dict(counts),audio_pes_count=audio_count,audio_pts_count=audio_timestamp_count,
        private_audio_pes_sha256=audio.hexdigest(),ordered_audio_pts_sha256=audio_pts.hexdigest())

def prepare():
    return dict(schema_version=1,status='original_psmf_contract_verified_replacement_mux_not_implemented',
        movies=[audit(n) for n in (3,9)],
        sources=[dict(url='https://raw.githubusercontent.com/hrydgard/ppsspp/master/Core/HLE/scePsmf.cpp',
            evidence='Descriptors at0x82/stride16, countBE16 at0x80; video EP map entries10bytes; seek uses streamOffset+EPOffset*2048.'),
            dict(url='https://raw.githubusercontent.com/hrydgard/ppsspp/master/Core/HW/MpegDemux.cpp',
            evidence='Private streamBD contains audio with channel and PTS, despite video-only ffprobe output.')],
        replacement_requirements=[
            'Re-encode only reviewed video raster at original dimensions/frame timeline; captions and credits scroll require complete frame timing QA.',
            'Copy original private-audio PES bytes and ordered timestamps exactly; do not silently re-encode or discard ATRAC audio.',
            'Rebuild2048-byte program-stream packs with compatible SCR/PTS/DTS, interleaving and buffer signaling; packing is not ordinary concatenation.',
            'Recompute video EP map packet indexes from new mux positions and verify every point against its corresponding video timestamp.',
            'Preserve/recompute descriptor fields and header timing/stream sizes from verified field semantics; picture-offset byte remains opaque and must be preserved only with equivalent GOP or researched before regeneration.',
            'Validate full decode, audio sync, seeking/skipping and next-scene transition on the PSP decoder before installation.'],
        movie_assets_written=False,runtime_replacement_verified=False,all_movie_text_reviewed=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('work/ui/media/psmf_seek_audio_contract.en.json'))
    args=parser.parse_args();report=prepare()
    print(json.dumps(dict(status=report['status'],movies=[dict(file=x['file'],sha256=x['sha256'],
        ep_entries=len(x['ep_map']),audio_pes=x['audio_pes_count'],first_ep=x['ep_map'][0],last_ep=x['ep_map'][-1],
        audio_sha=x['private_audio_pes_sha256']) for x in report['movies']],movie_assets_written=False),indent=2))
    if args.write:
        assert not args.output.exists(),'Refusing to overwrite evidence'
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
