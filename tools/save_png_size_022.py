"""Fix four savedata PNG size scalars; dry default and guarded fresh writer."""
import argparse,copy,hashlib,json,struct
from pathlib import Path
from executable_text_patch import Elf
from prepare_relocation_019 import section_load
from save_logo_overlay import validate_native_png_metadata,validate_historical_stale21_png_metadata
from build_local import authoritative_font_metadata
from savedata_tail_proof import prove

SOURCE=Path('work/output/0.1.21-render-verified-assets/EBOOT.BIN')
SOURCE_SHA='060f55250d659657ae12293850b132f0a1cf2b06183ed174eaa05bc86af91d0f'
OLD_SIZES={'play':26047,'play_dim':23352,'system':18985,'system_dim':18355}

def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(report):return sha(json.dumps(report,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())

def validate_triples(data,metadata):
    results=validate_native_png_metadata(data,metadata);elf=Elf(data)
    for p in metadata['trailer_recovery']['pngs']:
        for slot in p['pointer_slot_rvas']:
            expected=(p['original_pointer_rva'],p['proposed_bytes'],p['proposed_bytes'])
            if tuple(elf.word(slot+n)for n in (0,4,8))!=expected:raise ValueError('Native PNG pointer/capacity/size differs')
    return dict(png_stream_pixel_metadata=results,all_five_pointer_capacity_size_triples_passed=True)

def build():
    incoming=SOURCE.read_bytes();metadata_raw=SOURCE.with_name('executable.en.json').read_bytes()
    metadata=json.loads(metadata_raw);elf=Elf(incoming)
    if sha(incoming)!=SOURCE_SHA or metadata['output_elf_sha256']!=SOURCE_SHA:raise ValueError('Frozen21 input differs')
    previous_font=authoritative_font_metadata(incoming,metadata)
    # Only the explicitly frozen defective21 input may carry stale size words.
    validate_historical_stale21_png_metadata(incoming,metadata)
    result=bytearray(incoming);changes=[]
    for p in metadata['trailer_recovery']['pngs']:
        if p['name'] not in OLD_SIZES:continue
        old=OLD_SIZES[p['name']];new=p['proposed_bytes']
        if p['storage_extent_reserved_bytes']!=old or new>=old:raise ValueError('Reserved/current PNG extent differs')
        for slot in p['pointer_slot_rvas']:
            if tuple(elf.word(slot+n)for n in (0,4,8))!=(p['original_pointer_rva'],new,old):raise ValueError('Exact stale triple differs')
            if any(address==slot+8 and flags>>8&255==0 for address,flags in elf.relocs):raise ValueError('PNG size is unexpectedly relocated')
            struct.pack_into('<I',result,elf.file_offset(slot+8),new)
            changes.append(dict(name=p['name'],slot_rva=slot,size_site_rva=slot+8,file_offset=elf.file_offset(slot+8),
                expected_old_word=old,replacement_word=new,pointer_rva=p['original_pointer_rva'],
                capacity_word_unchanged=new,png_stream_sha256=p['output_sha256']))
    if len(changes)!=4:raise ValueError('Expected exactly four stale scalar sizes')
    output=bytes(result);out=Elf(output);mask=bytearray(incoming)
    for c in changes:mask[c['file_offset']:c['file_offset']+4]=output[c['file_offset']:c['file_offset']+4]
    if output!=mask or out.ph!=elf.ph or out.relocs!=elf.relocs:raise ValueError('Unselected bytes/layout/relocs changed')
    updated=copy.deepcopy(metadata);updated.update(version='0.1.22',input_version='0.1.21',input_sha256=SOURCE_SHA,
        output_elf_sha256=sha(output),output_sha256=sha(output),elf_bytes=len(output),
        status='dry_savedata_png_size_scalar_candidate',runtime_verified=False)
    triple_checks=validate_triples(output,updated)
    if authoritative_font_metadata(output,updated)!=previous_font:raise ValueError('Authoritative font contract changed')
    models=[]
    for base in (0x08804000,0x08900000,0x08fff000):
        memory,visited,skipped,pairs=section_load(output,base)
        for c in changes:
            if struct.unpack_from('<3I',memory[0],c['slot_rva'])!=(base+c['pointer_rva'],c['replacement_word'],c['replacement_word']):raise ValueError('Loaded savedata triple differs')
        models.append(dict(base=base,relocations=len(visited),skipped_sections=skipped,all_four_full_triples_passed=True))
    native=prove(output)
    proof=dict(schema_version=1,input_elf_sha256=SOURCE_SHA,input_metadata_sha256=sha(metadata_raw),
        output_elf_sha256=sha(output),changed_scalar_words=changes,changed_file_bytes=16,
        loaded_growth_bytes=0,new_relocations=0,all_unselected_file_bytes_exact=True,
        all_PNG_streams_pixels_and_active_tail_code_data_exact=True,all_PH_SHT_and_relocations_exact=True,
        authoritative_font_metadata_exact_predecessor=True,triple_metadata_checks=triple_checks,
        actual_SHT_three_base_models=models,native_savedata_consumer_proof=native,
        failure_evidence={'path':'work/source/runtime_021/runtime.log','error':'Savedata subdata buffer overflow: 18985 / 18601'},
        utility_save_validation='SavedataParam.cpp420..427 rejects valid subdata when size>bufSize; fixed native size equals already validated capacity.',
        utility_source_sha256=sha(Path('work/source/ppsspp_reference/SavedataParam.cpp').read_bytes()),
        code_input_sha256={str(p):sha(p.read_bytes())for p in [Path('tools')/(n+'.py')for n in
            ('save_png_size_022','save_logo_overlay','savedata_tail_proof','executable_text_patch','prepare_relocation_019','build_local')]},
        runtime_verified=False,limitations=['Runtime save success requires fresh22 ISO QA by root; no emulated-memory or savedata-file changes performed.'])
    updated['savedata_png_size_correction']=proof
    return output,updated

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path)
    p.add_argument('--write',action='store_true');p.add_argument('--output',type=Path);p.add_argument('--approved-plan-sha256');a=p.parse_args()
    data,report=build();key=canonical(report)
    print(json.dumps(report['savedata_png_size_correction'],indent=2));print('DRY PLAN SHA256',key)
    if a.report:
        if a.report.exists():raise ValueError('Refuse evidence overwrite')
        a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    if a.write:
        if a.approved_plan_sha256!=key:raise ValueError('Exact reviewed dry plan required')
        destination=a.output.resolve()if a.output else None
        if destination is None or destination.exists()or not destination.is_relative_to(Path('work/output').resolve()):raise ValueError('Fresh output directory required')
        fresh,current=build()
        if canonical(current)!=key or fresh!=data:raise ValueError('Preparation inputs changed since preview')
        destination.mkdir(parents=True);path=destination/'EBOOT.BIN';path.write_bytes(fresh);readback=path.read_bytes()
        if sha(readback)!=report['output_elf_sha256']:raise ValueError('Written executable hash differs')
        validate_triples(readback,report);authoritative_font_metadata(readback,report)
        report.update(status='written_savedata_png_size_scalar_candidate_runtime_unverified',output=str(path),
            approved_dry_plan_sha256=key,written_readback_verified=True)
        (destination/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        print('Verified fresh preparation:',path)
    else:print('DRY RUN: no executable/ISO/emulator changes.')
