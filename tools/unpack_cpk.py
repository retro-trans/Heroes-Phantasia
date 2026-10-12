"""Read-only CPK inspection and opt-in extraction (CRI @UTF + CRILAYLA).

Format reference: https://github.com/esperknight/CriPakTools/blob/master/CriPakTools/CPK.cs
No third-party dependency; original archive is never changed.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import ctypes
import shutil
import subprocess
import tempfile
import atexit


NATIVE_SOURCE = r'''
#include <stdint.h>
#include <stddef.h>
typedef struct { const uint8_t *p; int64_t pos; unsigned pool, left; int error; } Bits;
static unsigned bits(Bits *b, unsigned n) {
    unsigned result=0;
    while(n) {
        if(!b->left) { if(b->pos<16) { b->error=1; return 0; } b->pool=b->p[b->pos--]; b->left=8; }
        unsigned take=n<b->left?n:b->left;
        result=(result<<take)|((b->pool>>(b->left-take))&((1u<<take)-1));
        b->left-=take; n-=take;
    }
    return result;
}
static uint32_t le32(const uint8_t *p) { return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
__declspec(dllexport) int decode(const uint8_t *in, size_t n, uint8_t *out, size_t expected) {
    if(n<272) return 1;
    uint32_t size=le32(in+8), off=le32(in+12);
    if((uint64_t)size+256!=expected || (uint64_t)off+272>n) return 2;
    for(unsigned i=0;i<256;i++) out[i]=in[off+16+i];
    Bits b={in,(int64_t)off+15,0,0,0};
    int64_t dst=(int64_t)expected-1;
    while(dst>=256) {
        if(!bits(&b,1)) out[dst--]=(uint8_t)bits(&b,8);
        else {
            int64_t src=dst+bits(&b,13)+3;
            uint64_t length=3;
            unsigned widths[4]={2,3,5,8}, chunk=0, level;
            for(level=0;level<4;level++) {
                chunk=bits(&b,widths[level]); length+=chunk;
                if(chunk!=((1u<<widths[level])-1)) break;
            }
            if(level==4) do { chunk=bits(&b,8); length+=chunk; } while(chunk==255 && !b.error);
            if(src>=(int64_t)expected || length>(uint64_t)(dst-255)) return 3;
            while(length--) out[dst--]=out[src--];
        }
        if(b.error) return 4;
    }
    return 0;
}
'''


def native_decoder():
    """Optional local GCC acceleration; compilation stays in a temporary folder."""
    compiler = shutil.which('gcc')
    if not compiler:
        raise RuntimeError('--native requires GCC on PATH')
    if struct.calcsize('P') != 8:
        raise RuntimeError('--native requires 64-bit Python to match local GCC')
    temp = tempfile.TemporaryDirectory(prefix='heroes_cpk_')
    source = Path(temp.name) / 'decode.c'
    library = Path(temp.name) / 'decode.dll'
    source.write_text(NATIVE_SOURCE, encoding='ascii')
    subprocess.run([compiler, '-shared', '-O3', str(source), '-o', str(library)], check=True, capture_output=True)
    dll = ctypes.CDLL(str(library))
    dll.decode.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    dll.decode.restype = ctypes.c_int
    def decode(data, expected):
        output = ctypes.create_string_buffer(expected)
        error = dll.decode(data, len(data), output, expected)
        if error:
            raise ValueError('Invalid CRILAYLA stream (native error %d)' % error)
        return output.raw
    # Keep the DLL and temporary directory alive until the process finishes.
    decode.resources = (temp, dll)
    def cleanup():
        import _ctypes
        _ctypes.FreeLibrary(dll._handle)
        dll._handle = 0
        temp.cleanup()
    atexit.register(cleanup)
    return decode


def utf(data):
    if data[:4] != b'@UTF':
        key = 0x655f
        decoded = bytearray()
        for byte in data:
            decoded.append(byte ^ (key & 255))
            key = (key * 0x4115) & 0xffffffff
        data = bytes(decoded)
    if data[:4] != b'@UTF':
        raise ValueError('Invalid @UTF signature')
    size, rows_off, strings_off, blobs_off, name_off, cols, width, count = struct.unpack_from('>IIIIIHHI', data, 4)
    if size + 8 > len(data):
        raise ValueError('Truncated @UTF')
    rows_off += 8
    strings_off += 8
    blobs_off += 8
    def string(offset):
        start = strings_off + offset
        end = data.index(b'\0', start)
        return data[start:end].decode('utf-8', errors='strict')
    formats = {0:'B', 1:'b', 2:'H', 3:'h', 4:'I', 5:'i', 6:'Q', 7:'q', 8:'f', 9:'d', 10:'I', 11:'II'}
    def value(kind, pos):
        fmt = '>' + formats[kind]
        vals = struct.unpack_from(fmt, data, pos)
        item = vals[0]
        if kind == 10:
            item = string(item)
        elif kind == 11:
            item = data[blobs_off + vals[0]:blobs_off + vals[0] + vals[1]]
        return item, pos + struct.calcsize(fmt)
    columns = []
    pos = 32
    for _ in range(cols):
        flag, offset = struct.unpack_from('>BI', data, pos)
        pos += 5
        storage, kind = flag & 0xf0, flag & 0x0f
        default = None
        if storage == 0x30:
            default, pos = value(kind, pos)
        elif storage not in (0x10, 0x50):
            raise ValueError('Unknown @UTF storage flag %02x' % flag)
        columns.append((string(offset), storage, kind, default))
    result = []
    for row in range(count):
        pos = rows_off + row * width
        item = {}
        for name, storage, kind, default in columns:
            val = default
            if storage == 0x50:
                val, pos = value(kind, pos)
            item[name] = val
        if pos > rows_off + (row + 1) * width:
            raise ValueError('Row exceeds @UTF row width')
        result.append(item)
    return string(name_off), result


def packet(stream, offset, magic):
    stream.seek(offset)
    header = stream.read(16)
    if header[:4] != magic:
        raise ValueError('Bad packet signature at %x' % offset)
    size = struct.unpack_from('<Q', header, 8)[0]
    if size > 64 * 1024 * 1024:
        raise ValueError('Unreasonable metadata size')
    data = stream.read(size)
    if len(data) != size:
        raise ValueError('Truncated metadata packet')
    return utf(data)


def crilayla(data, expected):
    size, header_offset = struct.unpack_from('<II', data, 8)
    if size + 256 != expected or header_offset + 272 > len(data):
        raise ValueError('Invalid CRILAYLA sizes')
    out = bytearray(expected)
    out[:256] = data[header_offset + 16:header_offset + 272]
    pos, pool, remaining = header_offset + 15, 0, 0
    def bits(count):
        nonlocal pos, pool, remaining
        result = 0
        while count:
            if not remaining:
                if pos < 16:
                    raise ValueError('Truncated CRILAYLA bit stream')
                pool, remaining = data[pos], 8
                pos -= 1
            take = min(count, remaining)
            result = (result << take) | ((pool >> (remaining - take)) & ((1 << take) - 1))
            remaining -= take
            count -= take
        return result
    dst = expected - 1
    while dst >= 256:
        if not bits(1):
            out[dst] = bits(8)
            dst -= 1
            continue
        src = dst + bits(13) + 3
        length = 3
        for width in (2, 3, 5, 8):
            chunk = bits(width)
            length += chunk
            if chunk != (1 << width) - 1:
                break
        else:
            while True:
                chunk = bits(8)
                length += chunk
                if chunk != 255:
                    break
        if src >= expected or dst - length + 1 < 256:
            raise ValueError('Invalid CRILAYLA backreference')
        distance = src - dst
        if length <= distance:
            out[dst - length + 1:dst + 1] = out[src - length + 1:src + 1]
        else:
            pattern = bytes(out[dst + 1:src + 1])
            out[dst - length + 1:dst + 1] = (pattern * ((length + distance - 1) // distance))[-length:]
        dst -= length
    return bytes(out)


def inventory(path):
    with path.open('rb') as stream:
        _, rows = packet(stream, 0, b'CPK ')
        header = rows[0]
        toc_offset = header.get('TocOffset')
        if toc_offset is None:
            raise ValueError('Archive has no named TOC; ITOC-only archives not supported')
        _, rows = packet(stream, toc_offset, b'TOC ')
        base = min(toc_offset, header['ContentOffset'])
        entries = []
        seen = set()
        for row in rows:
            name = '/'.join(part for part in (row.get('DirName'), row['FileName']) if part)
            relative = PurePosixPath(name.replace('\\', '/'))
            if relative.is_absolute() or '..' in relative.parts or ':' in name:
                raise ValueError('Unsafe entry path: %s' % name)
            name = str(relative)
            if name.casefold() in seen:
                raise ValueError('Duplicate entry path: %s' % name)
            seen.add(name.casefold())
            offset = base + row['FileOffset']
            size = row['FileSize']
            if offset < 0 or offset + size > path.stat().st_size:
                raise ValueError('Entry exceeds archive: %s' % name)
            stream.seek(offset)
            prefix = stream.read(min(size, 16))
            entries.append(dict(path=name, offset=offset, stored_size=size,
                                extract_size=row.get('ExtractSize') or size,
                                compression='CRILAYLA' if prefix.startswith(b'CRILAYLA') else 'none',
                                magic_hex=prefix.hex(), id=row.get('ID')))
        if header['Files'] != len(entries):
            raise ValueError('CPK header file count disagrees with TOC')
        return header, entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, default=Path('work/source/cpk'))
    parser.add_argument('--inventory', type=Path, default=Path('work/source/cpk_inventory.json'))
    parser.add_argument('--extract', action='store_true', help='Opt in to filesystem writes; otherwise dry run')
    parser.add_argument('--resume', action='store_true', help='Verify existing output sizes and continue extraction')
    parser.add_argument('--native', action='store_true', help='Use optional GCC acceleration (Windows)')
    args = parser.parse_args()
    header, entries = inventory(args.archive)
    summary = dict(files=len(entries), stored_bytes=sum(e['stored_size'] for e in entries),
                   extracted_bytes=sum(e['extract_size'] for e in entries),
                   compression=dict(collections.Counter(e['compression'] for e in entries)),
                   extensions=dict(collections.Counter(Path(e['path']).suffix.lower() for e in entries)))
    print(json.dumps(summary, indent=2))
    print('Sample entries:')
    for entry in entries[:12]:
        print(json.dumps(entry))
    if not args.extract:
        print('DRY RUN: no data written. Use --extract after checking the sample.')
        return
    decoder = native_decoder() if args.native else crilayla
    root = args.output.resolve()
    with args.archive.open('rb') as stream:
        for entry in entries:
            target = (root / entry['path']).resolve()
            if root not in target.parents:
                raise ValueError('Entry escapes extraction directory')
            if target.exists():
                if not args.resume:
                    raise FileExistsError('Refusing to overwrite %s' % target)
                # Re-decode and compare, so resume cannot silently accept stale data.
            stream.seek(entry['offset'])
            data = stream.read(entry['stored_size'])
            if entry['compression'] == 'CRILAYLA':
                data = decoder(data, entry['extract_size'])
            if len(data) != entry['extract_size']:
                raise ValueError('Unknown compression or size mismatch: %s' % entry['path'])
            entry['sha256'] = hashlib.sha256(data).hexdigest()
            entry['extracted_magic_hex'] = data[:16].hex()
            if target.exists():
                if target.read_bytes() != data:
                    raise ValueError('Existing output differs: %s' % target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    args.inventory.parent.mkdir(parents=True, exist_ok=True)
    args.inventory.write_text(json.dumps(dict(archive=str(args.archive), header=header,
                                             summary=summary, entries=entries), indent=2), encoding='utf-8')
    print('Extracted %d files to %s' % (len(entries), root))


if __name__ == '__main__':
    main()
