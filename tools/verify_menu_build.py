"""Validate a cold-boot menu candidate against live RAM; no patch installation."""
import argparse,hashlib,json,pathlib,struct
from build_menu_patch import build,ROOT
from live_vwf import kernel_call
from ppsspp_debug import Debugger

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true')
    p.add_argument('--full-4x',action='store_true');p.add_argument('--opening',action='store_true');p.add_argument('--speaker-labels',action='store_true');p.add_argument('--bubble-layout',action='store_true');p.add_argument('--compact-font',action='store_true');p.add_argument('--association-fix',action='store_true');a=p.parse_args()
    if a.association_fix:a.compact_font=True
    if a.compact_font:a.bubble_layout=True
    if a.bubble_layout:a.speaker_labels=True
    if a.speaker_labels:a.opening=True
    if a.opening:a.full_4x=True
    output_root=pathlib.Path('work/output/0.1.5-opening-vwf-4x-candidate') if a.compact_font else pathlib.Path('work/output/0.1.4-opening-vwf-4x-candidate') if a.bubble_layout else pathlib.Path('work/output/0.1.3-opening-vwf-4x-candidate') if a.speaker_labels else pathlib.Path('work/output/0.1.2-opening-vwf-4x-candidate') if a.opening else pathlib.Path('work/output/0.1.1-menu-full-vwf-4x-candidate') if a.full_4x else ROOT
    if a.association_fix:output_root=pathlib.Path('work/output/0.1.6-opening-vwf-4x-candidate')
    candidate,info=build(a.full_4x,dialogue=a.opening,speaker_labels=a.speaker_labels,bubble_layout=a.bubble_layout,compact_font=a.compact_font,association_fix=a.association_fix)
    if hashlib.sha256((output_root/'EBOOT.BIN').read_bytes()).hexdigest()!=info['output_elf_sha256']:raise ValueError('Candidate differs from current builder')
    ph=struct.unpack_from('<8I',candidate,0x34+64)
    # Bank layout is encoded by startup's two signed address pairs.
    code=struct.unpack_from('<22I',candidate,ph[1]+0x500)
    def pair(n):
        lo=code[n+1]&65535
        return ((code[n]&65535)<<16)+(lo-65536 if lo&32768 else lo)
    table,pixels=pair(11),pair(14)
    d=Debugger();paused=False
    try:
        mod=next(m for m in d.call('hle.module.list')['modules'] if m['name']=='hp_proj');b=mod['address']
        d.call('cpu.runUntil',address=b+0x87d54,expect='cpu.stepping');paused=True
        hooks=[]
        for off in (0xe9cc8,0x87dc0,0xea5c4,0xea6a0,0xea6e4,0x4c0ec)+((0xee2d4,0xee35c,0xee8d4,0xed15c) if a.opening else ())+((0xec040,0xec04c) if a.speaker_labels else ())+((0xe4e0c,) if a.bubble_layout else ()):
            old=struct.unpack_from('<I',candidate,off+0xc0)[0]
            expected=(old&0xfc000000)|(((old&0x03ffffff)+(b>>2))&0x03ffffff)
            if d.read(b+off,4)!=struct.pack('<I',expected):raise ValueError(f'Live hook differs at {off:x}')
            hooks.append(hex(off))
        state=kernel_call(d,b,0xe928c,[]);descriptor=struct.unpack('<I',d.read(state+4,4))[0]
        if d.read(descriptor,12)!=struct.pack('<III',325,b+table,b+pixels):raise ValueError('Startup font descriptor differs')
        ptrs=struct.unpack('<5I',d.read(b+0x948d4,20));labels=list(info['label_widths'])
        for n,(ptr,label) in enumerate(zip(ptrs,labels)):
            expected=struct.unpack_from('<I',candidate,0x94994+n*4)[0]+b
            if ptr!=expected or d.read(ptr,len(label)+1)!=label.encode()+b'\0':raise ValueError('Relocated menu string differs')
        bank_bytes=info.get('high_bank_bytes',info['high_glyph_count']*info['high_texture_slot'][0]*64//2)
        bank_start=info['high_bank']-ph[2]+ph[1]
        if d.read(b+info['high_bank'],bank_bytes)!=candidate[bank_start:bank_start+bank_bytes]:raise ValueError('Loaded high-resolution pixels differ')
        lookup_bytes=129*info.get('high_lookup_entry_bytes',1)
        if d.read(b+ph[2]+0x600,lookup_bytes)!=candidate[ph[1]+0x600:ph[1]+0x600+lookup_bytes]:raise ValueError('Loaded code-to-slot lookup differs')
        if a.bubble_layout:
            catalog=info['bubble_layout']
            if hashlib.sha256(d.read(b+catalog['catalog_address'],catalog['catalog_bytes'])).hexdigest()!=catalog['catalog_sha256']:raise ValueError('Loaded bubble catalog differs')
        trace_path=pathlib.Path('work/ui/runtime/bubble_candidate_menu_trace.en.json' if a.bubble_layout else 'work/ui/runtime/speaker_candidate_menu_trace.en.json' if a.speaker_labels else 'work/ui/runtime/opening_candidate_menu_trace.en.json' if a.opening else 'work/ui/runtime/cold_boot_full_font_trace.en.json' if a.full_4x else 'work/ui/runtime/cold_boot_menu_vwf_4x_trace.en.json')
        if a.compact_font:trace_path=pathlib.Path('work/ui/runtime/compact_candidate_menu_trace.en.json')
        if a.association_fix:trace_path=pathlib.Path('work/ui/runtime/association_candidate_menu_trace.en.json')
        trace=json.loads(trace_path.read_text())
        if trace['installation']!='cold_boot_executable' or set(trace['unique_complete_labels'])!=set(labels):raise ValueError('Cold-boot trace incomplete')
        if trace['texture_slot']!=info['high_texture_slot']:raise ValueError('Trace texture layout differs')
        proof={'version':info['version'],'status':'cold_boot_menu_verified_only','module_base':hex(b),
            'module_size':mod['size'],'executable_sha256':info['output_elf_sha256'],'hook_sites_verified':hooks,
            'font_descriptor':[325,hex(b+table),hex(b+pixels)],'menu_labels_verified':labels,
            'glyph_source_scale':4,'glyph_draws_traced':trace['glyph_draws_observed'],
            'high_glyphs_loaded_verified':info['high_glyph_count'],'high_glyphs_individually_rendered':False,
            'texture_slot':info['high_texture_slot'],'bank_bytes_verified':bank_bytes,
            'source_rect':[64,64],'dest_rect':[16,16],'native_output':[480,272],
            'full_game_verified':False,'dialogue_translations_in_build':1 if a.opening else 0,
            'trace':str(trace_path),
            'screenshot':'work/ui/runtime/bubble_candidate_menu.png' if a.bubble_layout else 'work/ui/runtime/speaker_candidate_menu.png' if a.speaker_labels else 'work/ui/runtime/opening_candidate_english_menu.png' if a.opening else 'work/ui/runtime/cold_boot_full_font_menu.png' if a.full_4x else 'work/ui/runtime/cold_boot_menu_candidate.png'}
        if not a.full_4x:proof['japanese_options_capture']='work/ui/runtime/cold_boot_options_fallback.png'
        if a.compact_font:proof['screenshot']='work/ui/runtime/compact_candidate_menu.png'
        if a.association_fix:proof['screenshot']='work/ui/runtime/association_candidate_menu.png'
        if a.bubble_layout:proof['bubble_catalog_bytes_loaded_verified']=info['bubble_layout']['catalog_bytes']
        print(json.dumps(proof,indent=2))
        if a.write:
            proof_path=pathlib.Path('work/ui/runtime/bubble_candidate_menu_validation.en.json' if a.bubble_layout else 'work/ui/runtime/speaker_candidate_menu_validation.en.json' if a.speaker_labels else 'work/ui/runtime/opening_candidate_menu_validation.en.json' if a.opening else 'work/ui/runtime/cold_boot_full_font_validation.en.json' if a.full_4x else 'work/ui/runtime/cold_boot_menu_validation.en.json')
            if a.compact_font:proof_path=pathlib.Path('work/ui/runtime/compact_candidate_menu_validation.en.json')
            if a.association_fix:proof_path=pathlib.Path('work/ui/runtime/association_candidate_menu_validation.en.json')
            proof_path.write_text(json.dumps(proof,indent=2)+'\n')
            manifest=json.loads((output_root/'manifest.en.json').read_text())
            manifest['status']=manifest.get('opening_validation',{}).get('status',proof['status'])
            manifest['validation']=proof
            (output_root/'manifest.en.json').write_text(json.dumps(manifest,indent=2)+'\n')
        else:print('DRY RUN: no verification files written.')
    finally:
        if paused:d.call('cpu.resume',expect='cpu.resume')
        d.close()

if __name__=='__main__':main()
