"""Trace bounded actual dialogue/speaker 4x uploads; preview before --write."""
import argparse,hashlib,json,pathlib,struct
from ppsspp_debug import Debugger
from trace_vwf_4x import regs

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build-manifest',type=pathlib.Path,required=True)
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--speaker-only',action='store_true')
    modes.add_argument('--gallery',action='store_true',help='Observe the mode-4 body route; select a translated gallery entry first')
    p.add_argument('--draws',type=int,default=64)
    p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--write',action='store_true');a=p.parse_args()
    maximum=1024 if a.gallery else 128
    if not 1<=a.draws<=maximum:raise ValueError('Trace exceeds its bounded draw limit')
    build=json.loads(a.build_manifest.read_text());exe=(a.build_manifest.parent/'EBOOT.BIN').read_bytes()
    if hashlib.sha256(exe).hexdigest()!=build['output_elf_sha256']:raise ValueError('Candidate changed')
    d=Debugger();rows=[];b=None
    try:
        b=next(x['address'] for x in d.call('hle.module.list')['modules'] if x['name']=='hp_proj')
        word=struct.unpack_from('<I',exe,0xec040+0xc0)[0]
        expected=(word&0xfc000000)|(((word&0x03ffffff)+(b>>2))&0x03ffffff)
        if d.read(b+0xec040,4)!=struct.pack('<I',expected):raise ValueError('Loaded speaker hook differs')
        if a.gallery:
            word=struct.unpack_from('<I',exe,0xee35c+0xc0)[0]
            expected=(word&0xfc000000)|(((word&0x03ffffff)+(b>>2))&0x03ffffff)
            if d.read(b+0xee35c,4)!=struct.pack('<I',expected):raise ValueError('Loaded mode-4 body route differs')
        returns={0xee364} if a.gallery else {0xec048} if a.speaker_only else {0xee2dc,0xee364,0xec048}
        for n in range(a.draws*4):
            d.call('cpu.runUntil',address=b+0xea45c,expect='cpu.stepping');r=regs(d)
            if r['ra']-b not in returns:continue
            if not 32<=r['t1']<=128 or r['t1']==127:raise ValueError('Unsupported Latin code')
            row={'code':r['t1'],'glyph':chr(r['t1']) if r['t1']!=128 else 'è',
                'x':r['a1'],'y':r['a2'],'renderer_return':hex(r['ra']-b)}
            d.call('cpu.runUntil',address=b+0x1b7e1c,expect='cpu.stepping');u=regs(d)
            d.call('cpu.runUntil',address=b+0xd8e4,expect='cpu.stepping');v=regs(d)
            row['texture']={k:u[q] for k,q in [('width','a1'),('height','a2'),('pitch_pixels','a3'),('pointer','t0')]}
            row['sprite']={k:v[q] for k,q in [('dest_width','a3'),('dest_height','t0'),('u','t1'),('v','t2'),('source_width','t3')]}
            row['sprite']['source_height']=struct.unpack('<I',d.read(v['sp'],4))[0]
            if any(row['texture'][k]!=64 for k in ('width','height','pitch_pixels')):raise ValueError('Unexpected upload size')
            if any(row['sprite'][k]!=z for k,z in {'dest_width':16,'dest_height':16,'u':0,'v':0,'source_width':64,'source_height':64}.items()):raise ValueError('Unexpected sprite size')
            bank=b+build['high_bank'];slot_bytes=2048
            if 'high_glyph_offsets' in build:
                if u['t0']!=bank+build['high_glyph_offsets'][str(row['code'])] or u['t0']+slot_bytes>bank+build['high_bank_bytes']:raise ValueError('Packed glyph pointer differs')
            elif not bank<=u['t0']<bank+build['high_glyph_count']*slot_bytes or (u['t0']-bank)%slot_bytes:raise ValueError('Texture outside owned bank')
            rows.append(row)
            if len(rows)==a.draws:break
        if len(rows)!=a.draws:raise ValueError('Required bounded draws not observed')
        groups=[]
        for row in rows:
            if not groups or row['renderer_return']!=groups[-1][0]['renderer_return'] or row['y']!=groups[-1][0]['y'] or row['x']<=groups[-1][-1]['x']:groups.append([])
            groups[-1].append(row)
        lines=[{'text':''.join(r['glyph'] for r in group),'x':group[0]['x'],'y':group[0]['y'],
            'positions':[r['x'] for r in group],'advances':[q['x']-r['x'] for r,q in zip(group,group[1:])]} for group in groups]
        if a.speaker_only and not any(line['text']=='Sgt. Keroro' for line in lines):raise ValueError('Complete selected speaker label not observed')
        info={'version':build['version'],'status':'glyph_rendering_observed_layout_qa_pending',
            'loaded_executable_sha256':build['output_elf_sha256'],'module_base':hex(b),
            'installation':'cold_boot_executable','glyph_draws_observed':len(rows),'lines':lines,
            'source_rect':[64,64],'destination_rect':[16,16],'native_output':[480,272],
            'speaker_only':a.speaker_only,'full_game_verified':False,'dialogue_record_display_qa_passed':False,'draws':rows}
        if a.gallery:
            info.update(gallery_mode4_only=True,gallery_record_display_qa_passed=False)
        print(json.dumps({k:v for k,v in info.items() if k!='draws'},indent=2))
        if a.write:a.output.write_text(json.dumps(info,indent=2)+'\n',encoding='utf8')
        else:print('DRY RUN: no trace written.')
    finally:
        if b is not None:
            for offset in (0xea45c,0x1b7e1c,0xd8e4):
                d.call('cpu.breakpoint.remove',address=b+offset)
        if d.call('cpu.status')['stepping']:d.call('cpu.resume',expect='cpu.resume')
        d.close()

if __name__=='__main__':main()
