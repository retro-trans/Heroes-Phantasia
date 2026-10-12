"""Bounded read-only capture of an owned crashed PPSSPP process; dry by default."""
import argparse, ctypes, hashlib, json, pathlib, re, struct
from ctypes import wintypes
from executable_text_patch import Elf

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--read',action='store_true')
    p.add_argument('--output',type=pathlib.Path)
    a=p.parse_args()
    exe=pathlib.Path('work/source/setup_runtime_019/emulator/PPSSPPWindows64.exe').resolve()
    original=pathlib.Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf').read_bytes()
    if hashlib.sha256(original).hexdigest()!='03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1':
        raise ValueError('Original native instruction source changed')
    log=pathlib.Path('work/source/runtime_017_allocator/runtime.log').read_bytes()
    pairs=re.findall(rb'Bad memory access detected and ignored: ([0-9a-f]{8}) \(([0-9A-Fa-f]{16})\)',log)
    bases={int(host,16)-int(psp,16) for psp,host in pairs[-12:]}
    if len(bases)!=1:raise ValueError('Fault log does not establish one host mapping base')
    base=bases.pop()
    spans=[('actor_animation',0x08D8E610,128),('actor',0x08D8E5FC,128),
           ('resource_table_pointer',0x08B2D5FC,4),('stack',0x09FFF510,256)]
    plan=dict(pid=42940,expected_executable=str(exe),mapping_base=hex(base),
              spans=spans,guard_rva='0xdd7c8',guard_bytes=4,memory_writes=False,
              process_rights='PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION')
    print(json.dumps(plan,indent=2))
    if not a.read:print('DRY RUN: process untouched');return
    if not a.output or a.output.exists():raise ValueError('Fresh output required')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    k.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    h=k.OpenProcess(0x1010,False,42940)
    if not h:raise ctypes.WinError(ctypes.get_last_error())
    def read(psp,size):
        if not 0x08800000<=psp<psp+size<=0x0A000000 or size>256:raise ValueError('Read escaped approved PSP RAM bounds')
        buf=ctypes.create_string_buffer(size);got=ctypes.c_size_t()
        if not k.ReadProcessMemory(h,base+psp,buf,size,ctypes.byref(got)) or got.value!=size:
            raise ctypes.WinError(ctypes.get_last_error())
        return buf.raw
    try:
        name=ctypes.create_unicode_buffer(32768);n=wintypes.DWORD(len(name))
        if not k.QueryFullProcessImageNameW(h,0,name,ctypes.byref(n)):raise ctypes.WinError(ctypes.get_last_error())
        if pathlib.Path(name.value).resolve()!=exe:raise ValueError('Owned process executable differs')
        expected=struct.pack('<I',Elf(original).word(0xDD7C8))
        actual=read(0x08804000+0xDD7C8,4)
        if actual!=expected:raise ValueError('Native module mapping guard failed: '+actual.hex()+' vs '+expected.hex())
        rows=[]
        for label,psp,size in spans:
            raw=read(psp,size);rows.append(dict(label=label,address=hex(psp),bytes=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()))
        actor_animation=bytes.fromhex(rows[0]['bytes']);resource=struct.unpack_from('<I',actor_animation)[0]
        actor=bytes.fromhex(rows[1]['bytes']);index=struct.unpack_from('<I',actor,8)[0]
        table=struct.unpack('<I',bytes.fromhex(rows[2]['bytes']))[0]
        if index<8 and 0x08800000<=table<0x0A000000-8*48:
            slot=table+index*48;raw=read(slot,48)
            rows.append(dict(label='selected_resource_slot',index=index,address=hex(slot),bytes=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()))
        if 0x08800000<=resource<0x0A000000-128:
            raw=read(resource,128);rows.append(dict(label='actor_resource',address=hex(resource),bytes=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()))
        report=dict(plan,native_mapping_guard=actual.hex(),actor_resource=hex(resource),reads=rows,
                    log_sha256=hashlib.sha256(log).hexdigest(),register_writes=False,input_sent=False)
        a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        print(json.dumps(report,indent=2))
    finally:k.CloseHandle(h)

if __name__=='__main__':main()
