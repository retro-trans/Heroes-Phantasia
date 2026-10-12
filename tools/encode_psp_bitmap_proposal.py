"""Pure native-format PSP PNG candidates; --write writes only a fresh JSON proposal."""
import argparse
import hashlib
import io
import json
import struct
import zlib
from pathlib import Path
from PIL import Image
from prepare_psp_bitmap_proposal import prepare as pixels

PATHS={'PSP_GAME_PIC0.PNG':'PSP_GAME/PIC0.PNG',
       'PSP_GAME_ICON0.PNG':'PSP_GAME/ICON0.PNG',
       'PSP_GAME_INSDIR_ICON0.PNG':'PSP_GAME/INSDIR/ICON0.PNG'}

def chunks(data):
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    offset=8;result=[]
    while offset<len(data):
        size=struct.unpack_from('>I',data,offset)[0];end=offset+12+size
        assert end<=len(data)
        kind=data[offset+4:offset+8];body=data[offset+8:offset+8+size]
        assert zlib.crc32(kind+body)&0xffffffff==struct.unpack_from('>I',data,end-4)[0]
        result.append((kind,body,data[offset:end]));offset=end
        if kind==b'IEND':break
    assert offset==len(data) and result[-1][0]==b'IEND'
    return result

def chunk(kind,body):
    return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)

def prepare():
    pixel_report,images=pixels();candidates={};entries=[]
    for entry,(name,original,proposal) in zip(pixel_report['entries'],images):
        source=Path(entry['source_path']).read_bytes();native_chunks=chunks(source)
        mode=entry['native_mode'];assert mode in ('RGB','RGBA')
        raster=proposal.convert(mode);width,height=raster.size;stride=width*len(mode)
        raw=raster.tobytes();scanlines=b''.join(b'\x00'+raw[y*stride:(y+1)*stride] for y in range(height))
        compressed=zlib.compress(scanlines,9)
        candidate=source[:8];written=False
        for kind,body,encoded in native_chunks:
            if kind==b'IDAT':
                if not written:candidate+=chunk(b'IDAT',compressed);written=True
            else:candidate+=encoded
        assert written
        final_chunks=chunks(candidate)
        assert [(kind,body) for kind,body,_ in native_chunks if kind!=b'IDAT']==[(kind,body) for kind,body,_ in final_chunks if kind!=b'IDAT']
        assert final_chunks[0]==native_chunks[0]
        decoded=Image.open(io.BytesIO(candidate));decoded.load()
        assert decoded.mode==mode and decoded.size==(width,height)
        assert decoded.convert('RGBA').tobytes()==proposal.tobytes()
        source_rgba=original.tobytes();target_rgba=decoded.convert('RGBA').tobytes()
        regions=[x['source_region'] for x in entry['regions']]
        unchanged=all(source_rgba[(y*width+x)*4:(y*width+x+1)*4]==target_rgba[(y*width+x)*4:(y*width+x+1)*4]
                      for y in range(height) for x in range(width) if not any(a<=x<c and b<=y<d for a,b,c,d in regions))
        assert unchanged
        iso_path=PATHS[name];candidates[iso_path]=candidate
        entries.append(dict(iso_path=iso_path,source_path=entry['source_path'],source_sha256=entry['source_sha256'],
            candidate_sha256=hashlib.sha256(candidate).hexdigest(),source_bytes=len(source),candidate_bytes=len(candidate),
            native_mode=mode,ihdr_bit_depth=entry['ihdr_bit_depth'],ihdr_color_type=entry['ihdr_color_type'],
            dimensions=entry['dimensions'],outside_regions_pixel_exact=unchanged,all_non_idat_chunks_byte_exact=True,
            chunk_order=[k.decode('ascii') for k,_,_ in final_chunks],
            proposed_rgba_sha256=entry['proposed_rgba_sha256'],regions=entry['regions'],
            consumer=('PSP game preview metadata; no original game executable file reference established' if name!='PSP_GAME_INSDIR_ICON0.PNG'
                      else 'Install-data directory metadata icon; original game resource consumer not yet traced'),
            elf_png_tail_allocation=False,cpk_resource=False))
    return candidates,dict(schema_version=1,status='native_png_encoding_static_candidate_runtime_unverified',entries=entries,
        encoding_policy='Original signature/IHDR/ancillary chunks/IEND bytes retained; only IDAT compressed native RGB/RGBA scanlines replaced.',
        integration_policy='Separate ISO metadata files; use guarded ISO directory replacement and preserve original files. Never replace ELF-embedded PNG tail regions by filename similarity.',
        install_data_background='Approved intentional adjacent-row interpolation inside the caption rectangle; original background recovery is not claimed.',
        dependencies=dict(pixel_tool='tools/prepare_psp_bitmap_proposal.py',
            pixel_tool_sha256=hashlib.sha256(Path('tools/prepare_psp_bitmap_proposal.py').read_bytes()).hexdigest(),
            font_sha256=pixel_report['font_sha256']),
        native_png_files_written=False,runtime_verified=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('work/ui/psp_bitmap_proposal/native_encoding.en.json'))
    args=parser.parse_args();candidates,report=prepare()
    print(json.dumps(report,indent=2))
    if args.write:
        assert not args.output.exists(),'Refusing to overwrite evidence'
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
