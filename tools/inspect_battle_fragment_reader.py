"""Audit native sprite group/animation contracts; optional fresh review JSON only."""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path('work/source/analysis_packages').resolve()))
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

ELF = Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf')
ELF_SHA = '03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1'

def prepare():
    elf = ELF.read_bytes()
    assert hashlib.sha256(elf).hexdigest() == ELF_SHA
    resource = Path('work/source/cpk/btl/sys_all.bin').read_bytes()
    resource_sha=hashlib.sha256(resource).hexdigest()
    assert resource_sha == '5eb0b94feb90861f921cc84de6b8421b44c1ffc1f649eaaf042e5b4bd5c197a8'
    offsets = struct.unpack_from('<80I', resource)
    base = offsets[71]
    header = struct.unpack_from('<16I', resource, base)
    assert offsets[71] == 0x56600 and header[11:16] == (5,3196,27,3276,5544)
    assert struct.unpack_from('<I',resource,offsets[67]+4)[0] == 3
    for index in [43,44,45,48,49,50,51]:
        part=base+header[6]+index*56
        assert struct.unpack_from('<H',resource,part+2)[0] == 0
        assert struct.unpack_from('<3f',resource,part+40) == (1.,1.,0.)
    decoder = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
    regions = [(0x97358,0x97450),(0xbf32c,0xbf3e8),(0xbf4c0,0xbf658),
               (0xddd5c,0xdddec),(0xddea8,0xddf60),(0xded0c,0xdee04),
               (0xdfbec,0xdfca0),(0xdd5a0,0xdd66c),
               (0xe28cc,0xe2a9c),(0xe2a9c,0xe2cd0),
               (0xe208c,0xe21c0),(0xe2678,0xe28cc),(0xaaf78,0xab018)]
    evidence=[]
    instructions={}
    for start,end in regions:
        raw=elf[start+0xc0:end+0xc0]
        disassembly=[]
        for instruction in decoder.disasm(raw,start):
            instructions[instruction.address]=(instruction.mnemonic,instruction.op_str)
            disassembly.append(dict(rva=instruction.address,mnemonic=instruction.mnemonic,operands=instruction.op_str))
        evidence.append(dict(start_rva=start,end_exclusive_rva=end,sha256=hashlib.sha256(raw).hexdigest(),instructions=disassembly))
    # Exact original instructions supporting the parsed, ordered part traversal.
    required={0xdddac:('move','$a2, $a1'),0xdddd8:('lw','$v0, 4($a0)'),
              0xddde0:('subu','$v0, $v0, $a0'),0xe29a0:('addiu','$s2, $s2, 0x38'),
              0xe2ccc:('addiu','$s3, $s3, 0x38'),0xdfc60:('addiu','$t1, $t1, 8'),
              0xdd5bc:('negu','$t1, $t2'),0xe20ac:('add.s','$f12, $f13, $f12')}
    for address,expected in required.items():
        assert instructions[address] == expected, (hex(address),instructions[address],expected)
    animations=[]
    for animation in range(header[11]):
        count,layer_offset,duration,_=struct.unpack_from('<II f I',resource,base+header[12]+16*animation)
        layers=[]
        for index in range(count):
            position=base+header[14]+layer_offset+84*index
            channel_base=struct.unpack_from('<I',resource,position)[0]
            name=resource[position+4:position+20].split(b'\0')[0].decode('ascii')
            count_groups,group_offset=struct.unpack_from('<2I',resource,position+36)
            channel=base+header[15]+channel_base+group_offset
            assert channel+8*count_groups <= offsets[72]
            keys=[dict(time=t,group=g,unused=u) for t,g,u in
                  [struct.unpack_from('<fhH',resource,channel+8*j) for j in range(count_groups)]]
            layers.append(dict(index=index,native_layer_name=name,file_offset=position,
                               group_channel_file_offset=channel,group_keys=keys))
        animations.append(dict(animation=animation,duration_native_units=duration,layers=layers))
    assert animations[2]['layers'][1]['group_keys'][0]['group'] == 5
    assert animations[3]['layers'][7]['group_keys'][0]['group'] == 6
    assert animations[4]['layers'][6]['group_keys'][0]['group'] == 8
    return dict(schema_version=1,status='native_reader_static_proof_runtime_placement_pending',
        source_elf=ELF.as_posix(),source_elf_sha256=ELF_SHA,source_resource_sha256=resource_sha,
        loader=dict(rva=0x972fc,first_container=67,first_texture_count=3,next_container=71,
                    battle_descriptor_offset=0xa480,texture_header_index=72),
        group_contract=dict(reader_rva=0xddd5c,count_rva=0xdddac,
            group_count_header_offset=12,index_lut_header_offset=16,part_base_header_offset=24,
            stride=56,part_order='ascending native record index',
            draws=[dict(rva=0xe28cc,draw_part=0xe1df0),dict(rva=0xe2a9c,draw_part=0xe2678)],
            pivot_geometry_rva=0xdd5a0,position_add_rva=0xe208c,
            zero_rotation_unit_scale_formula='local XY = signed position + (UV dimensions - pivot bounds); global owner transforms apply afterwards',
            translated_group_record_ranges={'5':[43,44],'6':[44,46],'8':[48,52]},
            all_translated_parts_flags_zero=True,all_translated_parts_scale_one=True,all_translated_parts_rotation_zero=True),
        animation_contract=dict(descriptor_reader=0xddea8,layer_reader=0xdded4,
            descriptor_stride=16,layer_stride=84,group_channel_count_layer_offset=36,
            group_channel_pointer_layer_offset=40,group_key_stride=8,group_key_value_offset=4,
            timed_group_reader=0xdfbec,battle_actor_offset=0xa3e0,
            initializer=0xbf4c0,descriptor_slot=1,
            type_to_animation={'2':3,'3':4,'6':2,'7':2},animations=animations),
        runtime_prerequisites=[
            'Observe battle+A480 source pointer equal sys_all header71 and atlas72 texture selection.',
            'At native draw E28CC/E2A9C correlate actor resource/group and ascending part pointers for groups5/6/8.',
            'Record global position, scale, rotation, color and clipping throughout appearance/hold/disappearance; simple composite is only local static geometry.',
            'Verify native palette alpha, texture filtering and blending preserve readable overlap edges for First Strike Formation and Ambush.',
            'Capture representative Failed, First Strike Formation and Ambush outcomes plus unchanged OFFENSE/DEFENSE TURN groups.'],
        evidence=evidence,assets_written=False,runtime_verified=False,verified_dialogue_records=0)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('work/ui/battle/fragment_native_reader.en.json'))
    args=parser.parse_args();report=prepare()
    print(json.dumps({k:report[k] for k in ('status','source_elf_sha256','loader','group_contract','assets_written','runtime_verified')},indent=2))
    if args.write:
        assert not args.output.exists(),'Refusing to overwrite prior evidence'
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf8')
