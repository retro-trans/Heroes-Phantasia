"""Pure native savedata PNG pointer/size lifetime evidence; no writer."""
import hashlib,struct
from executable_text_patch import Elf,reference_index,ORIGINAL,ORIGINAL_SHA

def prove(current):
    source=ORIGINAL.read_bytes()
    if hashlib.sha256(source).hexdigest()!=ORIGINAL_SHA:raise ValueError('Original source hash differs')
    original=Elf(source);candidate=Elf(current);refs,issues=reference_index(original)
    expected={0x294e10:0x4709bc,0x29cc40:0x4709c8,0x2a3f10:0x470998,0x2a96c0:0x4709a4};png_refs=[]
    for address,slot in expected.items():
        found=[x for x in refs if x['address']==address]
        if len(found)!=1 or found[0]['kind']!='R_MIPS_32'or found[0]['sites']!=[slot]:raise ValueError('PNG reference coverage differs')
        png_refs.append(found[0])
    consumers=[x for x in refs if 0x470998<=x['address']<0x4709e0]
    if len(consumers)!=1 or consumers[0]['sites']!=[0x11580c,0x115810]or consumers[0]['address']!=0x470998:raise ValueError('PNG table consumer coverage differs')
    ranges=[(0x1157ec,0x1158e0),(0x115ea0,0x115ec0),(0x116380,0x116390)];calls=[]
    for site in range(0,0x294000,4):
        if original.word(site)==0x0c000000|(0x1157ec>>2):
            delay=original.word(site+4)
            if delay not in(0x00002825,0x34050001):raise ValueError('Unknown PNG row index')
            calls.append(dict(site=site,row_index=0 if delay==0x00002825 else 1,delay_word=delay));ranges.append((site-4,site+8))
    if [x['site']for x in calls]!=[0x116008,0x1160b8,0x11624c,0x11633c]:raise ValueError('Native row callers differ')
    guards=[]
    for start,end in ranges:
        old=source[original.file_offset(start):original.file_offset(start)+end-start]
        new=current[candidate.file_offset(start):candidate.file_offset(start)+end-start]
        if old!=new:raise ValueError('Native savedata transfer instructions differ')
        guards.append(dict(start_rva=start,end_rva=end,code_hex=old.hex(),sha256=hashlib.sha256(old).hexdigest()))
    native=source[original.loads[0][1]:original.loads[0][1]+original.loads[0][4]];bindings=[]
    for offset in range(0x2946c8,0x294894,20):
        name,version,attr,length,varcount,count,nids,stub=struct.unpack_from('<IHHBBHII',native,offset)
        for index in range(count):
            if struct.unpack_from('<I',native,nids+index*4)[0]==0x50c4cd57:
                if native[name:native.index(0,name)]!=b'sceUtility'or stub+8*index!=0x2944dc:raise ValueError('Savedata init import differs')
                bindings.append(dict(module='sceUtility',nid=0x50c4cd57,stub_rva=0x2944dc))
    if len(bindings)!=1:raise ValueError('Savedata import missing')
    pic1_refs=[x for x in refs if x['address']==0x2aec20]
    if len(pic1_refs)!=2 or [x['sites']for x in pic1_refs]!=[[0x4709b0],[0x4709d4]]or any(x['kind']!='R_MIPS_32'for x in pic1_refs):raise ValueError('Shared PIC1 references differ')
    return dict(original_source_sha256=ORIGINAL_SHA,png_references=png_refs,shared_pic1_references=pic1_refs,table_consumers=consumers,native_guards=guards,row_callers=calls,utility_binding=bindings[0],
        parameter_base_object_offset=0x14,icon0_pointer_object_offset=0x598,icon0_capacity_object_offset=0x59c,icon0_size_object_offset=0x5a0,
        new_data_pointer_object_offset=0x5d8,new_data_icon0_fields_object_offsets=[0x2db0,0x2db4,0x2db8],pic1_pointer_capacity_size_object_offsets=[0x5b8,0x5bc,0x5c0],standard_savedata_icon0_parameter_offset=0x584,standard_new_data_parameter_offset=0x5c4,standard_pic1_parameter_offset=0x5a4,
        native_size_transfer='115844..115858 copies normal pointer/capacity/size;115888..1158A4 copies dim pointer/capacity/size into newData;116388 calls SavedataInitStart.',
        emulator_consumer_sources=[dict(url='https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/Dialog/SavedataParam.cpp',lines=[420,594,901,1723,1729],behavior='Size validation; exact .size ICON0 write and normal/newData PNG preview decode; loading existing ICON0 writes at most .bufSize bytes, excluding reclaimed tails.'),dict(url='https://github.com/pspdev/pspsdk/blob/master/src/utility/psputility_savedata.h',behavior='Pointer/bufSize/size SavedataFileData and icon0/newData parameter layout.')],
        excluded_tail_semantics='Capacity and size reduced to exact encoded PNG length; native transfer passes these lengths to utility. Writes/PNG decode exclude bytes following IEND.',
        reference_coverage='Exact typed references and all direct native row-constructor JALs; not universal proof against arbitrary untyped/dynamic fabricated pointers.',other_reference_index_issues=len(issues),runtime_verified=False)
