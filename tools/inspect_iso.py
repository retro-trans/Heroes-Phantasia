"""Read an ISO9660 image without mounting it. Extract only explicitly selected files."""
import argparse, json, pathlib, struct

SECTOR = 2048

def inventory(image):
    files = []
    with open(image, 'rb') as f:
        f.seek(16 * SECTOR)
        pvd = f.read(SECTOR)
        if pvd[1:6] != b'CD001':
            raise ValueError('Not an ISO9660 primary descriptor')
        root = pvd[156:]
        seen = set()
        def walk(extent, size, parent):
            if extent in seen: return
            seen.add(extent)
            f.seek(extent * SECTOR)
            data = f.read(size)
            pos = 0
            while pos < len(data):
                length = data[pos]
                if not length:
                    pos = (pos // SECTOR + 1) * SECTOR
                    continue
                rec = data[pos:pos+length]
                pos += length
                name = rec[33:33+rec[32]]
                if name in (b'\x00', b'\x01'): continue
                name = name.decode('ascii', errors='replace').split(';')[0]
                off, n = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
                path = parent + '/' + name if parent else name
                if rec[25] & 2: walk(off, n, path)
                else: files.append({'path':path, 'offset':off*SECTOR, 'size':n})
        walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '')
    return files

def main():
    p = argparse.ArgumentParser()
    p.add_argument('image')
    p.add_argument('--write', action='store_true')
    p.add_argument('--extract', nargs='*', default=[])
    a = p.parse_args()
    files = inventory(a.image)
    print(json.dumps({'files':len(files), 'largest':sorted(files,key=lambda x:x['size'], reverse=True)[:25]}, indent=2))
    if a.write:
        out = pathlib.Path('work/source')
        out.mkdir(parents=True, exist_ok=True)
        (out/'iso_inventory.json').write_text(json.dumps(files,indent=2),encoding='utf-8')
        with open(a.image,'rb') as f:
            for item in files:
                if item['path'] not in a.extract: continue
                dest = out/item['path']
                dest.parent.mkdir(parents=True,exist_ok=True)
                f.seek(item['offset'])
                with open(dest,'wb') as target:
                    remaining=item['size']
                    while remaining:
                        block=f.read(min(1048576,remaining))
                        if not block: raise EOFError(item['path'])
                        target.write(block)
                        remaining-=len(block)
                print('Extracted',item['path'],item['size'])

if __name__ == '__main__': main()
