"""Append raw replacements and retarget named CPK rows; dry-run by default.

Writes only a fresh separate archive with --write --output. Unknown aggregate
header counters are preserved, not recomputed. No ISO/emulator access.
"""
import argparse, hashlib, json, pathlib, shutil, struct
from unpack_cpk import inventory, packet, utf

ORIGINAL_SHA = '0f328819199f95f4cf04dd2284d82a4ea405dbba2ef332dbaf09ff1ea3148bdd'
SIZES = {0:1,1:1,2:2,3:2,4:4,5:4,6:8,7:8,8:4,9:8,10:4,11:8}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def table(path,offset,magic):
    with path.open('rb') as f:
        f.seek(offset); header=f.read(16)
        if header[:4]!=magic: raise ValueError('Packet signature changed')
        data=f.read(struct.unpack_from('<Q',header,8)[0])
    if data[:4]!=b'@UTF': raise ValueError('Only verified unencrypted UTF packets supported')
    name,rows=utf(data)
    size,ro,so,bo,no,count,width,nrows=struct.unpack_from('>IIIIIHHI',data,4)
    if nrows!=len(rows): raise ValueError('UTF row count mismatch')
    ro+=8;so+=8;pos=32;rowpos=0;fields={}
    for _ in range(count):
        flag,nm=struct.unpack_from('>BI',data,pos);pos+=5
        key=data[so+nm:data.index(b'\0',so+nm)].decode('utf-8')
        storage=flag&240;kind=flag&15
        if key in fields: raise ValueError('Duplicate UTF column')
        fields[key]={'flag':flag,'relative':rowpos if storage==80 else pos}
        if storage==80: rowpos+=SIZES[kind]
        elif storage==48: pos+=SIZES[kind]
        elif storage!=16: raise ValueError('Unsupported UTF storage')
    if rowpos!=width: raise ValueError('Unexpected UTF row padding/layout')
    return {'data':data,'rows':rows,'fields':fields,'row_offset':ro,'width':width,'offset':offset}

def field(t,row,key,flag):
    col=t['fields'][key]
    if col['flag']!=flag: raise ValueError('UTF column type/storage changed: '+key)
    return t['offset']+16+t['row_offset']+row*t['width']+col['relative']

def plan(archive,replacements,expected_sha):
    if sha(archive)!=expected_sha: raise ValueError('Original archive SHA256 mismatch')
    header,entries=inventory(archive); ht=table(archive,0,b'CPK ');tt=table(archive,header['TocOffset'],b'TOC ')
    if header['Align']!=2048 or archive.stat().st_size%2048: raise ValueError('Archive alignment changed')
    if header['ContentOffset']+header['ContentSize']!=archive.stat().st_size:
        raise ValueError('ContentSize no longer exactly covers original content span')
    for name in ('ItocOffset','EtocOffset','GtocOffset','TocCrc','ItocCrc'):
        if header.get(name) is not None: raise ValueError('Additional metadata requires a separate audit: '+name)
    rows=tt['rows'];byname={q['path']:i for i,q in enumerate(entries)}
    if len(byname)!=len(entries) or len(rows)!=len(entries): raise ValueError('TOC identity mismatch')
    base=min(header['TocOffset'],header['ContentOffset']);end=archive.stat().st_size
    patches={};assets=[];expected=[dict(q) for q in rows]
    for name,path in replacements:
        if name not in byname: raise ValueError('Resource absent: '+name)
        index=byname[name];raw=path.read_bytes()
        if not raw or raw.startswith(b'CRILAYLA'): raise ValueError('Replacement must be nonempty uncompressed bytes')
        if len(raw)>0xffffffff: raise ValueError('Replacement exceeds u32 size')
        end=(end+2047)//2048*2048;start=end;end+=(len(raw)+2047)//2048*2048
        for key,flag,value,fmt in [('FileSize',0x54,len(raw),'>I'),('ExtractSize',0x54,len(raw),'>I'),
                                   ('FileOffset',0x56,start-base,'>Q')]:
            patches[field(tt,index,key,flag)]=struct.pack(fmt,value);expected[index][key]=value
        aliases=[q['path'] for q in entries if q['offset']==entries[index]['offset'] and q['path']!=name]
        assets.append({'resource':name,'input':str(path),'row':index,'offset':start,'bytes':len(raw),
                       'sha256':hashlib.sha256(raw).hexdigest(),'preserved_aliases':aliases,'data':raw})
    patches[field(ht,0,'ContentSize',0x56)]=struct.pack('>Q',end-header['ContentOffset'])
    # Reparse proposed packet edits before any output, comparing every column.
    for t,wanted in [(tt,expected),(ht,[dict(header,ContentSize=end-header['ContentOffset'])])]:
        data=bytearray(t['data'])
        for off,value in patches.items():
            local=off-t['offset']-16
            if 0<=local<len(data): data[local:local+len(value)]=value
        if utf(bytes(data))[1]!=wanted: raise ValueError('Proposed metadata changed an unrelated field')
    return header,entries,patches,assets,end

def verify_original_span(original,output,patches):
    with original.open('rb') as a,output.open('rb') as b:
        pos=0
        while True:
            old=a.read(1024*1024)
            if not old:break
            proposed=bytearray(old)
            for off,value in patches.items():
                lo=max(pos,off);hi=min(pos+len(old),off+len(value))
                if lo<hi: proposed[lo-pos:hi-pos]=value[lo-off:hi-off]
            if b.read(len(old))!=proposed: raise ValueError('Unselected original bytes changed')
            pos+=len(old)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=pathlib.Path,default=pathlib.Path('work/source/PSP_GAME/USRDIR/HP.CPK'))
    p.add_argument('--expected-sha256',default=ORIGINAL_SHA)
    p.add_argument('--version',default='0.1.1',help='Version of the local candidate being prepared')
    p.add_argument('--replace',action='append',required=True,metavar='RESOURCE=RAW_FILE')
    p.add_argument('--output',type=pathlib.Path);p.add_argument('--write',action='store_true');a=p.parse_args()
    replacements=[]
    for value in a.replace:
        name,path=value.split('=',1);replacements.append((name,pathlib.Path(path)))
    if len({n for n,_ in replacements})!=len(replacements): raise ValueError('Duplicate replacement resource')
    header,entries,patches,assets,end=plan(a.archive,replacements,a.expected_sha256.lower())
    public=[{k:v for k,v in asset.items() if k!='data'} for asset in assets]
    report={'version':a.version,'status':'structural_candidate_runtime_untested','original_sha256':a.expected_sha256.lower(),
            'original_bytes':a.archive.stat().st_size,'output_bytes':end,'alignment':2048,'replacements':public,
            'unknown_header_counts':'EnabledPackedSize/EnabledDataSize and other unrelated metadata preserved; their semantics are unverified',
            'validation':'Input hash/schema/alignment; all proposed TOC/header fields independently reparsed'}
    print(json.dumps(report,indent=2))
    if not a.write:print('DRY RUN: no archive or manifest written.');return
    if a.output is None:raise ValueError('--write requires --output')
    output=a.output.resolve();manifest=pathlib.Path(str(output)+'.manifest.en.json')
    if output.exists() or manifest.exists() or output==a.archive.resolve():raise ValueError('Output and manifest must be fresh separate files')
    output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.archive,output)
    with output.open('r+b') as f:
        for off,value in patches.items():f.seek(off);f.write(value)
        for asset in assets:
            f.seek(0,2);f.write(bytes(asset['offset']-f.tell()));f.write(asset['data'])
            f.write(bytes((-f.tell())%2048))
    newheader,newentries=inventory(output);chosen={q['resource']:q for q in assets}
    if newheader!=dict(header,ContentSize=end-header['ContentOffset']):raise ValueError('Written header mismatch')
    for old,new in zip(entries,newentries):
        asset=chosen.get(old['path'])
        if asset is None:
            if old!=new:raise ValueError('Untouched TOC entry changed')
        else:
            if new['offset']!=asset['offset'] or new['stored_size']!=asset['bytes'] or new['extract_size']!=asset['bytes'] or new['compression']!='none':
                raise ValueError('Written replacement metadata mismatch')
            with output.open('rb') as f:
                f.seek(new['offset'])
                if f.read(new['stored_size'])!=asset['data']:raise ValueError('Appended resource byte mismatch')
    verify_original_span(a.archive,output,patches)
    if output.stat().st_size!=end:raise ValueError('Final archive length mismatch')
    report.update(output_sha256=sha(output),validation='Written inventory, appended raw extraction, every untouched original byte and TOC/header field verified')
    manifest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Verified separate candidate:',output)

if __name__=='__main__':main()
