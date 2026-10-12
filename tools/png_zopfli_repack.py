"""Pure native-RGB IDAT recompression using guarded local official dependency."""
import hashlib,io,struct,sys,zipfile,zlib,functools
from pathlib import Path
from PIL import Image
from png_lossless_repack import repack,chunk

ROOT=Path('work/source/vendor/zopfli-0.4.3')
WHEEL='zopfli-0.4.3-cp310-abi3-win_amd64.whl'
WHEEL_SHA='921c2c9907f4364963848da5ad194b46d68865e07fdb975d04fd09bc42d47357'

def compressor():
    wheel=(ROOT/WHEEL).read_bytes()
    if hashlib.sha256(wheel).hexdigest()!=WHEEL_SHA:raise ValueError('Official dependency wheel hash differs')
    with zipfile.ZipFile(io.BytesIO(wheel))as archive:
        for name in archive.namelist():
            if name.startswith('zopfli/')and not name.endswith('/'):
                if (ROOT/name).read_bytes()!=archive.read(name):raise ValueError('Local dependency unpack differs from wheel')
    sys.path.insert(0,str(ROOT.resolve()))
    import zopfli.zlib
    if not Path(zopfli.zlib.__file__).resolve().is_relative_to(ROOT.resolve()):raise ValueError('Unexpected external compressor import')
    return zopfli.zlib.compress

@functools.lru_cache(maxsize=5)
def optimize(data,iterations=5):
    if iterations not in(5,15):raise ValueError('Bounded iteration choices required')
    prepared,proof=repack(data,beam_width=16);offset=8;chunks=[];filtered=bytearray()
    while offset<len(prepared):
        n=struct.unpack_from('>I',prepared,offset)[0];kind=prepared[offset+4:offset+8];body=prepared[offset+8:offset+8+n];chunks.append((kind,body));offset+=12+n
        if kind==b'IDAT':filtered.extend(body)
    decoded=zlib.decompress(filtered);encoded=compressor()(decoded,numiterations=iterations)
    if zlib.decompress(encoded)!=decoded:raise ValueError('Filtered stream identity differs')
    result=bytearray(prepared[:8]);inserted=False
    for kind,body in chunks:
        if kind==b'IDAT':
            if not inserted:result.extend(chunk(kind,encoded));inserted=True
        else:result.extend(chunk(kind,body))
    result=min((bytes(result),prepared),key=lambda v:len(v))
    original=Image.open(io.BytesIO(data)).convert('RGBA').tobytes()
    if result[24:29]!=data[24:29]or Image.open(io.BytesIO(result)).convert('RGBA').tobytes()!=original:raise ValueError('Native PNG format/pixels differ')
    return result,dict(input_bytes=len(data),beam_bytes=len(prepared),output_bytes=len(result),recovered_bytes=len(data)-len(result),rgba_pixel_sha256=hashlib.sha256(original).hexdigest(),native_color_type=2,all_pixels_identical=True,
        compressor='fonttools/py-zopfli0.4.3, Google Zopfli upstream',dependency_wheel_sha256=WHEEL_SHA,num_iterations=iterations,filter_proof=proof,assets_written=False)
