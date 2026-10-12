"""Bounded read-only HUD trace; explicit --trace, no input or memory writes."""
import argparse,json,time,struct
from pathlib import Path
from ppsspp_debug import Debugger

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trace',action='store_true');p.add_argument('--output',type=Path)
    p.add_argument('--native-blit',action='store_true');a=p.parse_args()
    probes=((0xd7fc,420),) if a.native_blit else ((0xd8e4,420),(0xea45c,120))
    print(f'Plan: {probes}, <=45 seconds; registers/texture header reads only; finally remove owned breakpoints and resume.')
    if not a.trace:print('DRY RUN: emulator untouched.');return
    d=Debugger(45373);owned=[];records=[];deadline=time.monotonic()+45
    try:
        existing=d.call('cpu.breakpoint.list')['breakpoints']
        if existing:raise RuntimeError('Other breakpoints active; trace not started')
        base=next(m['address'] for m in d.call('hle.module.list')['modules'] if m['name']=='hp_proj')
        for site,limit in probes:
            address=base+site;owned.append(address)
            for _ in range(limit):
                if time.monotonic()>=deadline:break
                d.call('cpu.runUntil',address=address,expect='cpu.stepping',timeout=5)
                c=d.call('cpu.getAllRegs')['categories'][0];r=dict(zip(c['registerNames'],c['uintValues']))
                if r['pc']!=address:raise RuntimeError('Different breakpoint stopped trace')
                row=dict(site=hex(site),ra=hex(r['ra']-base),regs={k:r[k] for k in ('a0','a1','a2','a3','t0','t1','t2','t3','sp')})
                if site==0xd8e4:row['source_height']=struct.unpack('<I',d.read(r['sp'],4))[0]
                selected=r['a2']<=40 and (r['t1']<=128 and r['t2']<=32 if site==0xd7fc else r['a3']<=128)
                if selected:
                    try:row['texture_or_font_header']=d.read(r['a0'],32).hex()
                    except Exception:row['header_read']='unavailable'
                records.append(row)
            d.call('cpu.breakpoint.remove',address=address);owned.remove(address)
        result=dict(module_base=hex(base),records=records,emulated_memory_written=False,input_sent=False)
        selected=[x for x in records if x['regs']['a2']<=40 and (x['regs']['t1']<=128 and x['regs']['t2']<=32 if x['site']=='0xd7fc' else x['regs']['a3']<=128)]
        print(json.dumps(dict(total_hits=len(records),selected_hits=len(selected),selected=selected[:30]),indent=2))
        if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
    finally:
        for address in owned:
            try:d.call('cpu.breakpoint.remove',address=address)
            except Exception:pass
        if d.call('cpu.status')['stepping']:d.call('cpu.resume',expect='cpu.resume')
        print('Final breakpoints:',d.call('cpu.breakpoint.list')['breakpoints'])
        d.close()

if __name__=='__main__':main()
