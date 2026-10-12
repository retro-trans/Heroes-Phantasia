"""Dry English side-lookup for reviewed native atlas labels; no hook/writer.

The original u16 strings and atlas remain untouched. Dispatch is NOT authorized
until a caller proves ownership of the loaded sys_tbl resource and row index.
This table is not interchangeable with the CP932 CPL Monster-name path.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from decode_glyph_tables import table, decode


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(start=0):
    if not 0<=start<=0xffff0000 or start%16:raise ValueError('Lookup start must be aligned and fit u32')
    source=Path('work/source/cpk/btl/sys_tbl.bin').read_bytes()
    original_elf=Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf').read_bytes()
    if sha(original_elf)!='03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1':raise ValueError('Original executable SHA differs')
    if b'sys_tbl' in original_elf or 'sys_tbl'.encode('utf-16le') in original_elf:raise ValueError('Previously absent native owner string requires new route audit')
    seeds_path=Path('work/source/font_audit/glyph_seeds.json')
    seeds=json.loads(seeds_path.read_text(encoding='utf8'))
    if seeds['file']!='btl/sys_tbl.bin':raise ValueError('Wrong original glyph owner')
    rows=table(source);mapping,_=decode(rows,seeds)
    queue_path=Path('work/translation/en/glyph_labels_0001.json')
    queue_raw=queue_path.read_bytes();queue=json.loads(queue_raw)['rows']
    targets={r['id']:r for r in queue}
    if len(targets)!=67 or len(rows)!=256:raise ValueError('Original reviewed table shape differs')
    manifest_path=Path('work/output/0.1.15-title-credit-vwf-4x-candidate/manifest.en.json')
    manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    elf=Path('work/output/0.1.15-title-credit-vwf-4x-candidate/EBOOT.BIN').read_bytes()
    if sha(elf)!=manifest['output_elf_sha256']:raise ValueError('Width source executable SHA differs')
    phoff=struct.unpack_from('<I',elf,28)[0]
    ph=struct.unpack_from('<8I',elf,phoff+64)
    widths=struct.unpack_from('<129f',elf,ph[1]+0x800)
    if any(not 0<w<32 for w in widths[32:127]):raise ValueError('Unexpected Latin width LUT')
    # Each row has a module-relative English pointer, encoded length and pixel
    # advance. Native entry identity is supplied separately by the audited row
    # index, never by interpreting the first local glyph ID as a codepoint.
    payload=bytearray(256*12);strings={};relocation_sites=[];records=[]
    for row in rows:
        if row['unresolved_glyphs']:raise ValueError('Unresolved glyph source')
        identity=sha(('glyph-index:'+row['source']).encode('utf8'))[:20]
        target=targets[identity]
        if target['source']!=row['source']:raise ValueError('Working glyph source mismatch')
        occurrence={'row_index':row['row_index'],'offset':row['offset'],'reference_offset':row['reference_offset'],'byte_length':row['byte_length'],'role':row['role']}
        if occurrence not in target['occurrences']:raise ValueError('Original glyph occurrence metadata mismatch')
        text=target['target'];encoded=text.encode('ascii')
        if not encoded or len(encoded)>31 or any(c<32 or c>126 for c in encoded):raise ValueError('Unsupported side-lookup label')
        original=source[row['offset']:row['offset']+row['byte_length']]
        inverse={v:k for k,v in mapping.items()}
        rebuilt=b''.join(struct.pack('<H',inverse[c]) for c in row['source'])
        rebuilt+=bytes(row['byte_length']-len(rebuilt))
        if rebuilt!=original:raise ValueError('Original native glyph round-trip mismatch')
        if encoded not in strings:
            strings[encoded]=len(payload);payload.extend(encoded+b'\0')
        offset=strings[encoded];width=sum(widths[c] for c in encoded);slot=row['row_index']*12
        struct.pack_into('<IIf',payload,slot,start+offset,len(encoded),width)
        relocation_sites.append(slot)
        records.append({'index':row['row_index'],'id':identity,'original_reference_offset':row['reference_offset'],'original_source_offset':row['offset'],'original_bytes_sha256':sha(original),'english_offset':offset,'encoded_bytes':len(encoded),'pixel_advance':width,'source_role':row['role'],'runtime_verified':False})
    for row in records:
        pointer,length,width=struct.unpack_from('<IIf',payload,row['index']*12)
        if payload[pointer-start:pointer-start+length+1][-1]!=0:raise ValueError('Side lookup NUL bound failed')
        if pointer-start<256*12 or pointer-start+length>=len(payload):raise ValueError('Side lookup pointer escapes payload')
    # Independent R32 data model at the established and two alternative bases.
    for base in (0x08804000,0x08900000,0x09a00000):
        loaded=bytearray(payload)
        for site in relocation_sites:
            word=struct.unpack_from('<I',loaded,site)[0]
            struct.pack_into('<I',loaded,site,(word+base)&0xffffffff)
        for row in records:
            pointer=struct.unpack_from('<I',loaded,row['index']*12)[0]
            if pointer!=base+start+row['english_offset']:raise ValueError('R32 relocation model differs')
    report={'schema_version':1,'status':'dry_lookup_only_no_renderer_hook','native_resource':'btl/sys_tbl.bin','native_source_sha256':sha(source),'target_snapshot_sha256':sha(queue_raw),'seed_sha256':sha(seeds_path.read_bytes()),'width_source_elf_sha256':sha(elf),'rows':256,'unique_translation_rows':67,'unique_english_strings':len(strings),'record_stride':12,'record_fields':['module-relative English pointer u32','encoded bytes excluding NUL u32','pixel advance float32'],'payload_bytes':len(payload),'payload_sha256':sha(payload),'module_relative_start':start,'required_relocations':[{'payload_offset':site,'type':'PSPREL1 R32','patch_segment':2,'target_segment':0} for site in relocation_sites],'records':records,'source_assets_changed':False,'renderer_hook_ready':False,'critical_gates':['Prove original sys_tbl file load/ownership and exact256-entry selector; no such native consumer is established yet.','Prove per-label source/destination size, palette, alignment/origin, clipping and native atlas fallback.','Dispatch must compare validated owner/table identity plus index; local glyph values alone are not globally unique.','Do not route this u16 atlas table through CPL978D8/EC5BC: that path reads byte CP932 names from a different owner.','12px native atlas cells do not establish 16px resident VWF destination size or logical baseline.'],'static_native_loader_evidence':{'sys_all_path_rva':'0x2ed93c','sys_all_load_calls':['0xaa5c0','0xab198'],'sys_tbl_literal_in_original_elf':False,'sys_tbl_literal_in_extracted_cpk_files':False,'sys_tbl_index_and_texture_embedded_in_sys_all':False},'runtime_verified':False,'full_game_translation_complete':False}
    return bytes(payload),report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--start',type=lambda v:int(v,0),default=0);p.add_argument('--details',action='store_true');a=p.parse_args()
    payload,report=build(a.start)
    if not a.details:
        report={k:v for k,v in report.items() if k not in ('records','required_relocations')}
    print(json.dumps(report,ensure_ascii=True,indent=2));print('DRY RUN: no files written; no renderer hook emitted.')


if __name__=='__main__':main()
