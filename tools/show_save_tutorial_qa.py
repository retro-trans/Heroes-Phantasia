"""Display the actual Save Points resource in the isolated .29 emulator.

Dry first. --run invokes the reviewed native load/show sequence, independent
of Gallery unlocks. It changes only the disposable test session's UI state.
"""
import argparse,json,time,struct
from pathlib import Path
from ppsspp_debug import Debugger
from live_vwf import registers,gpr,restore_registers

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',action='store_true');a=ap.parse_args()
    print(json.dumps(dict(port=45384,version='0.1.29',resource='menu/Gallery/tf/TfHelp000.bin',
      reviewed_native_sequence=['9352C model getter','93570 load(model,1,0)','93738 readiness','93804 allocate panel','938D4 show resource'],
      scope='Isolated debugger-triggered real resource panel; natural guild event is not exercised.'),indent=2))
    if not a.run:print('DRY RUN');return
    d=Debugger(45384)
    def call(rva,*args):
        saved=None;bp=None
        try:
            saved=registers(d);old=gpr(saved)
            base=next(x['address']for x in d.call('hle.module.list')['modules']if x['name']=='hp_proj')
            # This draw branch cannot execute inside the reviewed load/show
            # functions. Its breakpoint is removed before normal UI resumes.
            bp=base+0x940c8;d.call('cpu.breakpoint.add',address=bp)
            for n,v in zip(('a0','a1','a2','a3'),args):d.call('cpu.setReg',name=n,value=v)
            for n,v in [('sp',old['sp']-1024),('ra',bp),('pc',base+rva)]:d.call('cpu.setReg',name=n,value=v)
            d.call('cpu.runUntil',address=bp,expect='cpu.stepping');out=gpr(registers(d))
            if out['pc']!=bp:raise ValueError('Native RPC did not return')
            return out['v0']
        finally:
            if bp is not None:d.call('cpu.breakpoint.remove',address=bp)
            if saved is not None:restore_registers(d,saved)
    try:
        d.call('cpu.stepping',expect='cpu.stepping')
        model=call(0x9352c);state=struct.unpack('<4I',d.read(model,16))
        if state[3]:raise ValueError('A tutorial resource is already owned by this model')
        call(0x93570,model,1,0)
        for n in range(30):
            ready=call(0x93738,model)
            if ready==1:break
            d.call('cpu.resume',expect='cpu.resume');time.sleep(.3);d.call('cpu.stepping',expect='cpu.stepping')
        else:raise TimeoutError('Native tutorial resource did not become ready')
        call(0x93804);manager=call(0x7ca54);panel=struct.unpack('<I',d.read(manager+0x1c,4))[0]
        if not panel:raise ValueError('Layer3 allocation failed')
        call(0x938d4,model)
        proof=dict(version='0.1.29',model=model,panel=panel,category=1,topic=0,resource='menu/Gallery/tf/TfHelp000.bin',
          native_resource_loader_used=True,borrowed_text_kept_alive=True,debugger_triggered=True,natural_field_event=False)
        Path('work/source/runtime_029/tutorial_rpc.en.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
    finally:d.call('cpu.resume',expect='cpu.resume');d.close()

if __name__=='__main__':main()
