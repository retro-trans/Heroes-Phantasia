"""Bounded embedded save-logo overlay; dry default, guarded fresh writer."""
import argparse,hashlib,io,json,struct,zlib,copy
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from executable_text_patch import Elf
from png_zopfli_repack import optimize
from prepare_relocation_019 import section_load

SOURCE=Path('work/output/0.1.20-render-verified-assets/EBOOT.BIN')
SOURCE_SHA='b1f049db7790b1808970cbde37d6029016a1d993f9155f07808c96f827aa45ed'
FONT=Path('work/source/ppsspp/assets/Roboto_Condensed-Regular.ttf')
BOX=(55,38,98,44)

def sha(data):return hashlib.sha256(data).hexdigest()

def png_check(data):
    if data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('PNG signature differs')
    offset=8;chunks=[]
    while offset<len(data):
        count=struct.unpack_from('>I',data,offset)[0];kind=data[offset+4:offset+8]
        body=data[offset+8:offset+8+count];crc=struct.unpack_from('>I',data,offset+8+count)[0]
        if crc!=zlib.crc32(kind+body)&0xffffffff:raise ValueError('PNG CRC differs')
        chunks.append(kind.decode());offset+=count+12
        if kind==b'IEND':break
    if offset!=len(data) or data[24:29]!=bytes((8,2,0,0,0)):raise ValueError('Native RGB/PNG extent differs')
    if struct.unpack_from('>II',data,16)!=(144,80):raise ValueError('Native icon dimensions differ')
    return chunks

def overlay(original,dim):
    result=original.copy();result.paste((33,29,27,255),BOX)
    text='HEROES PHANTASIA';scale=4;font=ImageFont.truetype(str(FONT),4*scale)
    bb=font.getbbox(text);w=(bb[2]-bb[0]+3)//4;h=(bb[3]-bb[1]+3)//4
    if w>BOX[2]-BOX[0]-2 or h>BOX[3]-BOX[1]-2:raise ValueError('Phonetic text does not fit bounded box')
    mask=Image.new('L',(w*scale,h*scale));ImageDraw.Draw(mask).text((-bb[0],-bb[1]),text,font=font,fill=255)
    mask=mask.resize((w,h),Image.Resampling.LANCZOS)
    x=BOX[0]+(BOX[2]-BOX[0]-w)//2;y=BOX[1]+(BOX[3]-BOX[1]-h)//2
    result.paste((175,175,175,255)if dim else(245,241,232,255),(x,y,x+w,y+h),mask)
    a=original.tobytes();b=result.tobytes();changed=[]
    for pos in range(144*80):
        if a[pos*4:pos*4+4]!=b[pos*4:pos*4+4]:
            xx,yy=pos%144,pos//144
            if not(BOX[0]<=xx<BOX[2]and BOX[1]<=yy<BOX[3]):raise ValueError('Pixels outside replacement box changed')
            changed.append([xx,yy])
    if original.crop((0,64,144,80)).tobytes()!=result.crop((0,64,144,80)).tobytes():raise ValueError('English caption changed')
    stream=io.BytesIO();result.convert('RGB').save(stream,format='PNG',optimize=True)
    return stream.getvalue(),result,dict(text=text,replacement_box=list(BOX),raster_scale=4,font_native_pixels=4,
        text_box=[x,y,w,h],changed_pixels=len(changed),outside_box_pixels_exact=True,existing_English_caption_exact=True)

def image_build():
    incoming=SOURCE.read_bytes();metadata_raw=SOURCE.with_name('executable.en.json').read_bytes();metadata=json.loads(metadata_raw)
    if sha(incoming)!=SOURCE_SHA or metadata['output_elf_sha256']!=SOURCE_SHA:raise ValueError('Frozen20 executable/report differs')
    validate_native_png_metadata(incoming,metadata)
    elf=Elf(incoming);output=bytearray(incoming);items=[];images=[];selected=[]
    for p in metadata['trailer_recovery']['pngs'][:4]:
        name=p['name'];rva=p['original_pointer_rva'];extent=p['proposed_bytes'];offset=elf.file_offset(rva,extent)
        raw=incoming[offset:offset+extent];chunks=png_check(raw)
        for reserved in (metadata['additional_scopes']['tail_reservations']+metadata['native_tail_compaction']['chunks']):
            if reserved['rva']<rva+extent and rva<reserved['rva']+reserved['bytes']:raise ValueError('PNG extent overlaps active native-tail allocation')
        for reserved in metadata['trailer_recovery']['moved_data']:
            if reserved['new_start']<rva+extent and rva<reserved['new_start']+reserved['bytes']:raise ValueError('PNG extent overlaps active moved data')
        if sha(raw)!=p['output_sha256']:raise ValueError('Current native PNG metadata hash differs')
        original=Image.open(io.BytesIO(raw)).convert('RGBA');prepared,proposed,visual=overlay(original,'dim'in name)
        encoded,compression=optimize(prepared,5)
        if len(encoded)>extent:encoded,compression=optimize(prepared,15)
        if len(encoded)>extent:raise ValueError(f'{name}: encoded PNG{len(encoded)} exceeds current declared allocation{extent}')
        png_check(encoded)
        decoded=Image.open(io.BytesIO(encoded)).convert('RGBA')
        if decoded.tobytes()!=proposed.tobytes():raise ValueError('Compressed edited pixels differ')
        output[offset:offset+extent]=encoded+bytes(extent-len(encoded));selected.append((offset,extent))
        pointers=[]
        for slot in p['pointer_slot_rvas']:
            if tuple(elf.word(slot+n)for n in (0,4,8))!=(rva,extent,extent):raise ValueError('Native PNG pointer/capacity/size triple differs')
            for relative in (4,8):
                if any(off==slot+relative and flags>>8&255==0 for off,flags in elf.relocs):raise ValueError('PNG size unexpectedly relocated')
                struct.pack_into('<I',output,elf.file_offset(slot+relative),len(encoded));selected.append((elf.file_offset(slot+relative),4))
            pointers.append(dict(slot=slot,pointer_rva=rva,old_bytes=extent,new_bytes=len(encoded),pointer_unchanged=True,
                                 capacity_and_encoded_size_updated=True))
        items.append(dict(name=name,rva=rva,file_offset=offset,original_current_bytes=extent,new_png_bytes=len(encoded),
            preserved_allocation_bytes=extent,zero_padding_bytes=extent-len(encoded),before_sha256=sha(raw),
            after_png_sha256=sha(encoded),after_padded_extent_sha256=sha(encoded+bytes(extent-len(encoded))),
            original_rgba_sha256=sha(original.tobytes()),proposed_rgba_sha256=sha(proposed.tobytes()),
            original_chunks=chunks,native_color_type=2,png_crc_all_valid=True,pointer_sizes=pointers,
            visual=visual,compression=compression,runtime_verified=False))
        images.append((name,original,proposed))
    mask=bytearray(incoming)
    for offset,size in selected:mask[offset:offset+size]=output[offset:offset+size]
    if output!=mask or len(output)!=len(incoming):raise ValueError('Unselected ELF bytes changed')
    if Elf(bytes(output)).relocs!=elf.relocs or Elf(bytes(output)).ph!=elf.ph:raise ValueError('ELF/relocation layout changed')
    models=[]
    for base in(0x08804000,0x08900000,0x08fff000):
        memory,visited,skipped,pairs=section_load(bytes(output),base)
        for icon in items:
            for pointer in icon['pointer_sizes']:
                slot=pointer['slot'];words=struct.unpack_from('<3I',memory[0],slot)
                if words!=(base+icon['rva'],icon['new_png_bytes'],icon['new_png_bytes']):raise ValueError('Loaded PNG pointer/capacity/size differs')
        models.append(dict(base=base,records=len(visited),skipped_sections=skipped,all_four_PNG_full_triples_passed=True))
    report=dict(schema_version=1,status='pure_four_embedded_save_logo_proposal_no_assets_writer',
        source=SOURCE.as_posix(),input_sha256=SOURCE_SHA,input_metadata_sha256=sha(metadata_raw),
        output_elf_sha256=sha(output),elf_bytes=len(output),icons=items,
        code_input_sha256={p.as_posix():sha(p.read_bytes())for p in(Path('tools/save_logo_overlay.py'),Path('tools/png_zopfli_repack.py'),Path('tools/png_lossless_repack.py'),Path('tools/build_local.py'),Path('tools/prepare_relocation_019.py'))},
        source_font=FONT.as_posix(),source_font_sha256=sha(FONT.read_bytes()),
        loaded_growth_bytes=0,all_unselected_bytes_exact=True,all_active_tail_code_data_exact=True,
        all_original_pointer_words_exact=True,all_PH_SHT_and_relocations_exact=True,
        three_base_actual_section_models=models,active_allocation_intersections_rejected=True,
        no_new_free_tail_claim=True,runtime_verified=False,
        limitations=['Proposed cover plate bounded around visually inspected phonetic lettering; root visual review required.',
            'Native firmware PNG display and tiny English-line readability remain runtime QA.'])
    return bytes(output),report,images

def validate_native_png_metadata(data,metadata):
    """Strict current validation: pointer, bufSize and size must all agree."""
    return _validate_native_png_metadata(data,metadata)

def validate_historical_stale21_png_metadata(data,metadata):
    """Forensic-only validation of the two frozen, defective21 snapshots."""
    if sha(data)not in ('63998e6e446d2209724ebc39c5258487e699040e3d1cf7558e1b4b4998645e92',
                      '060f55250d659657ae12293850b132f0a1cf2b06183ed174eaa05bc86af91d0f'):
        raise ValueError('Historical stale21 validator requires exact frozen21 bytes')
    return _validate_native_png_metadata(data,metadata,{'play':26047,'play_dim':23352,'system':18985,'system_dim':18355})

def _validate_native_png_metadata(data,metadata,historical_sizes=None):
    elf=Elf(data);results=[]
    for p in metadata['trailer_recovery']['pngs']:
        rva=p['original_pointer_rva'];size=p['proposed_bytes'];offset=elf.file_offset(rva,size)
        raw=data[offset:offset+size]
        # PIC1 is a different native dimension, but all stream CRCs and declared
        # pointer/size fields remain guarded by its inherited frozen proof.
        if sha(raw)!=p['output_sha256']:raise ValueError('Authoritative native PNG hash differs')
        for slot in p['pointer_slot_rvas']:
            encoded_size=(historical_sizes or {}).get(p['name'],size)
            if tuple(elf.word(slot+n)for n in (0,4,8))!=(rva,size,encoded_size):raise ValueError('Authoritative PNG pointer/capacity/size triple differs')
        if p['name']!='shared_pic1':
            png_check(raw);pixels=Image.open(io.BytesIO(raw)).convert('RGBA').tobytes()
            expected_pixels=p.get('current_rgba_sha256')
            if expected_pixels is None and p.get('rgba_pixels_identical') and p.get('filter_proof',{}).get('all_pixels_identical'):
                expected_pixels=p['filter_proof'].get('rgba_pixel_sha256')
            if expected_pixels is None or sha(pixels)!=expected_pixels:raise ValueError('Authoritative PNG pixels differ')
            # Older lossless metadata declares only the stream extent; its
            # excluded tail may contain active code and must not be read here.
            capacity=p.get('storage_extent_reserved_bytes',size)
            if data[offset+size:offset+capacity]!=bytes(capacity-size):raise ValueError('Authoritative reserved PNG padding differs')
        results.append(dict(name=p['name'],pointer_sizes_exact=True,declared_stream_sha256_exact=True,
                            pointer_capacity_size_exact=historical_sizes is None or p['name']=='shared_pic1',
                            historical_stale_size_forensic_check=historical_sizes is not None and p['name']!='shared_pic1'))
    return results

def build():
    data,proof,images=image_build()
    metadata=copy.deepcopy(json.loads(SOURCE.with_name('executable.en.json').read_bytes()))
    for item in proof['icons']:
        p=next(p for p in metadata['trailer_recovery']['pngs']if p['name']==item['name'])
        historical=copy.deepcopy(p)
        p.update(current_bytes=item['original_current_bytes'],proposed_bytes=item['new_png_bytes'],
            input_sha256=item['before_sha256'],output_sha256=item['after_png_sha256'],
            current_rgba_sha256=item['proposed_rgba_sha256'],rgba_pixels_identical=False,
            pixels_outside_phonetic_box_identical=True,storage_extent_reserved_bytes=item['preserved_allocation_bytes'],
            reserved_extent_sha256=item['after_padded_extent_sha256'],filter_proof=item['compression'],
            historical_pre_overlay_proof=historical,
            proof_scope='Current bounded phonetic overlay is save_logo_overlay; tail start, active placements and original reader lifetime proofs remain inherited.')
    metadata.update(version='0.1.21',input_version='0.1.20',input_sha256=SOURCE_SHA,
        output_elf_sha256=sha(data),output_sha256=sha(data),elf_bytes=len(data),
        status='dry_embedded_save_logo_candidate',runtime_verified=False)
    from build_local import authoritative_font_metadata
    current=authoritative_font_metadata(data,metadata)
    previous=authoritative_font_metadata(SOURCE,json.loads(SOURCE.with_name('executable.en.json').read_bytes()))
    if current!=previous:raise ValueError('Authoritative font metadata changed')
    proof['authoritative_font_metadata_passed']=True
    proof['authoritative_font_contract_exact_predecessor']=True
    proof['native_png_full_metadata_checks']=validate_native_png_metadata(data,metadata)
    proof['active_native_tail_chunk_hashes_verified_by_builder']=True
    metadata['save_logo_overlay']=proof
    metadata['save_logo_preparation_code_input_sha256']=proof['code_input_sha256']
    return data,metadata,images

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path);p.add_argument('--previews',type=Path)
    p.add_argument('--write',action='store_true');p.add_argument('--output',type=Path);p.add_argument('--approved-plan-sha256');a=p.parse_args()
    _,report,images=build()
    print(json.dumps({key:report[key]for key in('version','output_elf_sha256','elf_bytes','payload_bytes','save_logo_overlay')},indent=2))
    if a.report:
        if a.report.exists():raise ValueError('Refuse evidence overwrite')
        a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    if a.previews:
        if a.previews.exists():raise ValueError('Fresh review directory required')
        a.previews.mkdir(parents=True)
        sheet=Image.new('RGB',(576,640))
        for n,(name,original,proposed)in enumerate(images):
            original.save(a.previews/(name+'_original.png'));proposed.save(a.previews/(name+'_proposed.png'))
            sheet.paste(original.convert('RGB').resize((288,160)),(0,n*160));sheet.paste(proposed.convert('RGB').resize((288,160)),(288,n*160))
        sheet.save(a.previews/'comparison.png')
    canonical=sha(json.dumps(report,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
    print('DRY PLAN SHA256',canonical)
    if a.write:
        if a.approved_plan_sha256!=canonical:raise ValueError('Exact reviewed dry plan SHA required')
        destination=a.output.resolve()if a.output else None
        if destination is None or destination.exists()or not destination.is_relative_to(Path('work/output').resolve()):raise ValueError('Fresh preparation folder inside work/output required')
        data,fresh,_=build()
        if sha(json.dumps(fresh,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())!=canonical:raise ValueError('Fresh inputs changed after dry preview')
        destination.mkdir(parents=True);path=destination/'EBOOT.BIN';path.write_bytes(data)
        readback=path.read_bytes()
        if sha(readback)!=report['output_elf_sha256']:raise ValueError('Written executable readback differs')
        validate_native_png_metadata(readback,report)
        from build_local import authoritative_font_metadata
        authoritative_font_metadata(readback,report)
        report.update(status='written_embedded_save_logo_candidate_runtime_unverified',approved_dry_plan_sha256=canonical,
            output=str(path),written_readback_verified=True)
        (destination/'executable.en.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        print('Verified fresh preparation:',path)
    else:print('DRY RUN: no executable/ISO written; optional images are review previews.')
