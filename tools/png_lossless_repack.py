"""Pure lossless PNG filter search; returns bytes without writing assets."""
import hashlib,io,struct,zlib
from PIL import Image

def chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)

def repack(data,beam_width=4):
    if data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('PNG signature differs')
    chunks=[];offset=8
    while offset<len(data):
        size=struct.unpack_from('>I',data,offset)[0];kind=data[offset+4:offset+8];body=data[offset+8:offset+8+size]
        if offset+12+size>len(data)or zlib.crc32(kind+body)&0xffffffff!=struct.unpack_from('>I',data,offset+8+size)[0]:raise ValueError('PNG chunk bounds/CRC differs')
        chunks.append((kind,body));offset+=12+size
        if kind==b'IEND':break
    if offset!=len(data):raise ValueError('PNG trailing bytes excluded from exact source')
    header=chunks[0][1];width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',header)
    if depth!=8 or color!=2 or compression or filtering or interlace:raise ValueError('Expected native noninterlaced8bitRGB')
    image=Image.open(io.BytesIO(data)).convert('RGB');raw=image.tobytes();stride=width*3
    rows=[];previous=bytes(stride)
    def paeth(a,b,c):
        p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
        return a if pa<=pb and pa<=pc else b if pb<=pc else c
    for y in range(height):
        row=raw[y*stride:(y+1)*stride];choices=[]
        for mode in range(5):
            filtered=bytearray([mode])
            for x,value in enumerate(row):
                a=row[x-3]if x>=3 else 0;b=previous[x];c=previous[x-3]if x>=3 else 0
                predictor=(0,a,b,(a+b)//2,paeth(a,b,c))[mode]
                filtered.append((value-predictor)&255)
            choices.append(bytes(filtered))
        rows.append(choices);previous=row
    candidates=[('original',data)]
    def png(filtered):
        encoded=zlib.compress(filtered,9);out=bytearray(data[:8]);inserted=False
        for kind,body in chunks:
            if kind==b'IDAT':
                if not inserted:out.extend(chunk(kind,encoded));inserted=True
            else:out.extend(chunk(kind,body))
        return bytes(out)
    for mode in range(5):candidates.append((f'uniform_filter{mode}',png(b''.join(row[mode]for row in rows))))
    candidates.append(('minimum_signed_filter_sum',png(b''.join(min(row,key=lambda v:sum(min(x,256-x)for x in v[1:]))for row in rows))))
    beam=[(zlib.compressobj(9),b'',b'')]
    for row in rows:
        next_beam=[]
        for state,prefix,filtered in beam:
            for choice in row:
                current=state.copy();emitted=prefix+current.compress(choice);score=len(emitted)+len(current.copy().flush())
                next_beam.append((score,current,emitted,filtered+choice))
        next_beam.sort(key=lambda v:(v[0],v[3]));beam=[(s,p,f)for _,s,p,f in next_beam[:beam_width]]
    for n,(_,_,filtered)in enumerate(beam):candidates.append((f'bounded_filter_beam{beam_width}_{n}',png(filtered)))
    name,result=min(candidates,key=lambda v:(len(v[1]),v[0]));decoded=Image.open(io.BytesIO(result)).convert('RGB').tobytes()
    if decoded!=raw:raise ValueError('Lossless pixel identity failed')
    rgba=Image.open(io.BytesIO(data)).convert('RGBA').tobytes()
    if Image.open(io.BytesIO(result)).convert('RGBA').tobytes()!=rgba:raise ValueError('RGBA pixel identity failed')
    return result,dict(strategy=name,input_bytes=len(data),output_bytes=len(result),recovered_bytes=len(data)-len(result),rgb_pixel_sha256=hashlib.sha256(raw).hexdigest(),rgba_pixel_sha256=hashlib.sha256(rgba).hexdigest(),all_pixels_identical=True,candidate_sizes={n:len(v)for n,v in candidates})
