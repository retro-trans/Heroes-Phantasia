"""Pure dry104 typed-pointer and scoped tutorial renderer integration."""
import copy,hashlib,json,struct
from pathlib import Path
from build_menu_patch import START,align,relocate_code
from live_vwf import j,jal
from compact_vwf_patch import loaded
from dialogue_vwf_hooks import decoder,route
from tutorial_heading_hooks import title_width,center,trailing_icon,detail_center,menu_advance,CENTERS,STRLEN_CALLS,cases

TEMPLATE=Path('work/source/executable_routes_104_dry.en.json')
ORIGINAL=Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf')
def sha(data):return hashlib.sha256(data).hexdigest()


def build(base,report):
    report=copy.deepcopy(report);template_bytes=TEMPLATE.read_bytes();t=json.loads(template_bytes);original=ORIGINAL.read_bytes()
    if sha(original)!=t['original_sha256']or t['records']!=104 or t['typed_pointer_writes']!=104 or t['payload_bytes']!=2201:raise ValueError('104 source/count guard changed')
    for path,digest in t['queue_sha256'].items():
        if sha(Path(path).read_bytes())!=digest:raise ValueError('104 target queue changed: '+path)
    for addr,word in t['guarded_original_caller_words'].items():
        if struct.unpack_from('<I',base,int(addr,16)+192)[0]!=int(word,16):raise ValueError('104 caller guard changed: '+addr)
    po,so=struct.unpack_from('<II',base,28);ph=[list(struct.unpack_from('<8I',base,po+n*32))for n in range(4)]
    sections=[list(struct.unpack_from('<10I',base,so+n*40))for n in range(struct.unpack_from('<H',base,48)[0])]
    payload=bytearray(base[ph[2][1]:ph[2][1]+ph[2][4]]);oldpayload=bytes(payload)
    prefix=bytearray(base[:0x508880]);records=list(struct.iter_unpack('<II',base[ph[3][1]:ph[3][1]+ph[3][4]]));extra=[];patches=[];strings=[]
    def append(data):
        payload.extend(bytes((-len(payload))%16));off=len(payload);payload.extend(data);return off
    def block(code):
        off=append(code);extra.extend(struct.iter_unpack('<II',b''.join(relocate_code(payload,off,len(code)))));return START+off
    def patch(site,target,call=False):
        size=4 if call else 8;expected=original[site+192:site+192+size]
        if prefix[site+192:site+192+size]!=expected:raise ValueError('Tutorial native instruction guard changed: '+hex(site))
        if call:
            if struct.unpack_from('<I',expected)[0]>>26!=3 or(site,4)not in records:raise ValueError('Original JAL/R26 required')
        elif(site,4)in records:raise ValueError('New jump site already relocated')
        replacement=struct.pack('<I',jal(target)if call else j(target))+(b''if call else bytes(4))
        prefix[site+192:site+192+size]=replacement
        if not call:records.append((site,4))
        patches.append(dict(site=site,expected_hex=expected.hex(),replacement_hex=replacement.hex(),target=target,call=call))
    initial=align(len(payload),16);payload.extend(bytes(initial-len(payload)))
    for row in t['rows']:
        raw=bytes.fromhex(row['payload_hex'])
        if len(raw)!=row['payload_bytes']or not raw.endswith(b'\0')or b'\0'in raw[:-1]:raise ValueError('104 string storage changed')
        if (row.get('quest_buffer_bytes_worst_case_including_nul')or 0)>256:raise ValueError('Quest assembly exceeds native stack buffer')
        offset=len(payload);payload.extend(raw);changes=[]
        for change in row['pointer_writes']:
            slot=int(change['pointer_rva'],16);expected=int(change['expected_word'],16)
            if struct.unpack_from('<I',prefix,slot+192)[0]!=expected:raise ValueError('104 typed pointer changed')
            found=[n for n,(off,flags)in enumerate(records)if off==slot and flags>>8&255==0 and flags&255==2]
            if len(found)!=1:raise ValueError('104 typed native R32 missing/ambiguous')
            records[found[0]]=(slot,0x20002);struct.pack_into('<I',prefix,slot+192,offset)
            changes.append(dict(slot=slot,resolved_rva=START+offset,stored_offset=offset,expected_word=expected))
        strings.append(dict(id=row['id'],target=row['target'],family=row['family'],payload_rva=START+offset,payload_bytes=len(raw),pointer_changes=changes,runtime_verified=False))
    if len(payload)-initial!=2201:raise ValueError('104 payload total changed')
    # Reuse the already active body integer LUT: rounded16px VWF advance.
    # The reviewed compaction delta maps every old integer bank after the font.
    from prepare_font_016 import BODY_LUTS
    old_lut=BODY_LUTS[0];delta=report['font_compaction']['delta'];bankend=report['input_build_history']['report']['high_bank']+188928
    lut=old_lut+delta if old_lut>=bankend else old_lut
    widths=struct.unpack_from('<131I',payload,lut-START)
    if any(widths[n]>64 for n in (*range(32,127),128,129,130)):raise ValueError('Tutorial integer LUT invalid')
    widthaddr=block(title_width(lut));centers={entry:block(center(entry))for entry in CENTERS}
    icon=block(trailing_icon());detail=block(detail_center());advance=block(menu_advance(lut))
    classify=block(decoder(True,(0xf0cf0,0xf0d98,0xec644,0x881e8),private_pairs=True))
    # E9CC8 is an already installed jump, not an original instruction.
    oldclass=report['font_hooks']['decoder'];expected=j(oldclass)
    if struct.unpack_from('<I',prefix,0xe9cc8+192)[0]!=expected or(0xe9cc8,4)not in records:raise ValueError('Inherited decoder changed')
    struct.pack_into('<I',prefix,0xe9cc8+192,j(classify));patches.append(dict(site=0xe9cc8,expected_hex=struct.pack('<I',expected).hex(),replacement_hex=struct.pack('<I',j(classify)).hex(),target=classify,call=False))
    normalroute=block(route(0xeab10,131));nameroute=block(route(0xe9918,131))
    for site in STRLEN_CALLS:patch(site,widthaddr,True)
    for entry,target in centers.items():patch(entry,target)
    patch(0x943a8,icon);patch(0x944ec,detail);patch(0x88270,advance)
    patch(0x88268,normalroute,True);patch(0x8823c,nameroute,True)
    records.extend(extra)
    if len(set(records))!=len(records):raise ValueError('Duplicate tutorial relocation')
    rel=b''.join(struct.pack('<II',*x)for x in records);pf=align(len(prefix),64);prefix.extend(bytes(pf-len(prefix)));prefix.extend(payload)
    rf=align(len(prefix),16);prefix.extend(bytes(rf-len(prefix)));prefix.extend(rel)
    for s in sections:
        if s[1]==0x700000a0:s[4]=rf+s[4]-ph[3][1]
        elif s[3]==START and s[4]==ph[2][1]:s[4]=pf;s[5]=len(payload)
    newsh=align(len(prefix),4);prefix.extend(bytes(newsh-len(prefix)))
    for s in sections:prefix.extend(struct.pack('<10I',*s))
    ph[2][1]=pf;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=rf;ph[3][4]=len(rel)
    for n,p in enumerate(ph):struct.pack_into('<8I',prefix,po+n*32,*p)
    struct.pack_into('<I',prefix,32,newsh);struct.pack_into('<H',prefix,48,len(sections))
    checks=0;relchecks=0
    for baseaddr in (0x8804000,0x8900000,0x8fff000):
        segs,_,_=loaded(prefix,baseaddr);oldsegs,_,_=loaded(base,baseaddr)
        if segs[1]!=oldsegs[1]or segs[2][:len(oldpayload)]!=oldsegs[2]:raise ValueError('Inherited LOAD1/payload changed')
        masked=bytearray(oldsegs[0])
        for row in strings:
            for x in row['pointer_changes']:
                if struct.unpack_from('<I',segs[0],x['slot'])[0]!=baseaddr+x['resolved_rva']:raise ValueError('104 loaded pointer wrong')
                masked[x['slot']:x['slot']+4]=segs[0][x['slot']:x['slot']+4];checks+=1
        for x in patches:
            n=len(bytes.fromhex(x['replacement_hex']));masked[x['site']:x['site']+n]=segs[0][x['site']:x['site']+n]
            if (struct.unpack_from('<I',segs[0],x['site'])[0]&0x3ffffff)*4!=baseaddr+x['target']:raise ValueError('Tutorial loaded jump wrong')
        if masked!=segs[0]:raise ValueError('Unselected native byte changed')
        for n,(off,flags)in enumerate(extra):
            typ=flags&255;raw=struct.unpack_from('<I',payload,off)[0];value=struct.unpack_from('<I',segs[2],off)[0]
            if typ==4:expected=(raw&0xfc000000)|((((raw&0x3ffffff)*4+baseaddr)>>2)&0x3ffffff)
            elif typ==6:expected=(raw&0xffff0000)|((raw+baseaddr)&65535)
            elif typ==5:
                oo,_=next(x for x in extra[n+1:]if x[1]&255==6);lo=struct.unpack_from('<I',payload,oo)[0]
                a=((raw&65535)<<16)+struct.unpack('<h',struct.pack('<H',lo&65535))[0]
                expected=(raw&0xffff0000)|(((a+baseaddr+0x8000)>>16)&65535)
            else:raise ValueError('Unknown tutorial relocation')
            if value!=expected:raise ValueError('Tutorial added code relocation wrong')
            relchecks+=1
    result=bytes(prefix);report.update(status='dry_font_and_555_typed_ui_candidate',output_elf_sha256=sha(result),output_sha256=sha(result),elf_bytes=len(result),payload_bytes=len(payload),module_growth_bytes=len(payload),payload_growth=len(payload)-217152,total_relocations=len(records),added_relocations=report['added_relocations']+len(extra)+6,relocation_table_sha256=sha(rel))
    report['font_hooks']['decoder']=classify
    report['scoped_tutorial_quest_ui']=dict(template_sha256=sha(template_bytes),selected_records=104,typed_pointer_writes=104,text_bytes=2201,
        appended_bytes=len(payload)-len(oldpayload),strings=strings,hooks=dict(width=widthaddr,centers=centers,icon=icon,detail=detail,advance=advance,decoder=classify,normal_route=normalroute,name_route=nameroute),
        native_instruction_changes=patches,integer_lut_rva=lut,emitted_instruction_tests=cases(),new_code_relocations=len(extra),new_native_jump_relocations=6,
        loaded_pointer_comparisons=checks,loaded_code_relocation_comparisons=relchecks,inherited_payload_prefix_exact=True,inherited_LOAD1_exact=True,
        unselected_native_bytes_exact=True,original_call_delay_slots_preserved=True,runtime_verified=False,
        limitations=['Only named tutorial render branches are scoped; other consumers/layouts require runtime QA.','Unknown/native/control titles retain original strlen and 13px arithmetic.','Body text and notification buffers are outside this scope.'])
    report['memory_forecast'].update(recovered_bytes=217152-len(payload),margin_before_new_ui=217152-len(payload)-133376,typed_ui_bytes_included=9440,other_ui_not_integrated=True)
    for section in ('dialogue_ruby_patch','battle_label_patch'):
        report[section]['hooks']['ruby_decoder'if section=='dialogue_ruby_patch'else'battle_label_decoder']=hex(classify)
    report.setdefault('hooks',{}).update(ruby_decoder=hex(classify),battle_label_decoder=hex(classify))
    return result,report
