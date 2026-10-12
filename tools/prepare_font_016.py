"""Dry .16 compressed owned-VRAM font and private accents; no asset writer.

Current frozen .15 is required. The returned candidate is never saved here.
Additional executable UI translation relocation is a separate preparation stage.
"""
import copy,hashlib,json,struct
from pathlib import Path
from PIL import ImageFont
from build_menu_patch import START,align,relocate_code
from compact_vwf_patch import loaded
from font_payload_compaction import replace_range
from font_ram_plan import SOURCE,SHA,encode,raster_glyph
from font_vram_hooks import decompress,initialize,uploader
from dialogue_vwf_hooks import decoder
from dialogue_ruby_hooks import association_records,pack_associations,ruby_center,name_glyph_units,NAME_COUNT_CALLS
from dialogue_measure import measure
from dialogue_wrap import literal_reveal_cap
from audit_ruby_spans import audit
from private_latin import GLYPH_CODES
from live_vwf import FONT,i,j,jal

GATES=(0x16f9c10,0x172991c,0x172995c,0x17299a0,0x1729bbc,0x1729c00,
       0x172aedc,0x172b5d8,0x172b60c,0x172b65c,0x172b6dc,
       0x172c50c,0x172c76c,0x172db88,0x172dc00,0x172e32c,0x172e380)
BODY_LUTS=(0x1729700,0x172b3a0,0x172c540,0x172c9a0,0x172e030)
SMALL_LUT=0x172cee0


def sha(data):return hashlib.sha256(data).hexdigest()


def build():
    original=SOURCE.read_bytes();before=json.loads(SOURCE.with_name('setup_patch.en.json').read_text())
    if sha(original)!=SHA or before['output_elf_sha256']!=SHA:raise ValueError('Frozen .15 changed')
    po=struct.unpack_from('<I',original,120)[0];size=struct.unpack_from('<I',original,132)[0]
    old=original[po:po+size];bankstart=before['high_bank']-START;banksize=before['high_bank_bytes']
    bank=old[bankstart:bankstart+banksize]
    if sha(bank)!=before['high_bank_sha256'] or banksize!=188928:raise ValueError('Frozen96-glyph bank changed')
    extended=bank+raster_glyph('\u00e1')+raster_glyph('\u00e9');packed=encode(extended)
    if len(extended)!=193024 or len(packed)!=24790:raise ValueError('Exact98-glyph bank changed')
    intermediate,comp=replace_range(original,bankstart,banksize,packed+bytes((-len(packed))%16),[(0x200,0x300)])
    delta=comp['delta'];end=START+bankstart+banksize
    def mapped(a):
        if before['high_bank']<=a<end:raise ValueError('Active metadata into old bank')
        return a+delta if end<=a<START+len(old)else a
    phoff,shoff=struct.unpack_from('<II',intermediate,28)
    ph=[list(struct.unpack_from('<8I',intermediate,phoff+n*32))for n in range(4)]
    sections=[list(struct.unpack_from('<10I',intermediate,shoff+n*40))for n in range(struct.unpack_from('<H',intermediate,48)[0])]
    prefix=bytearray(intermediate[:0x508880]);payload=bytearray(intermediate[ph[2][1]:ph[2][1]+ph[2][4]])
    records=list(struct.iter_unpack('<II',intermediate[ph[3][1]:ph[3][1]+ph[3][4]]));extra=[];patches=[]
    def change(seg,off,value,reason):
        target=payload if seg==2 else prefix;where=off if seg==2 else ph[seg][1]+off
        oldword=struct.unpack_from('<I',target,where)[0];struct.pack_into('<I',target,where,value)
        patches.append(dict(segment=seg,offset=off,expected_word=oldword,replacement_word=value,reason=reason))
    def append(data):
        payload.extend(bytes((-len(payload))%16));off=len(payload);payload.extend(data);return off
    def block(code):
        off=append(code);extra.extend(struct.iter_unpack('<II',b''.join(relocate_code(payload,off,len(code)))));return START+off
    def retarget(site,target,call=False):
        if (site,4)not in records:raise ValueError('Existing native R26 relocation missing')
        oldword=struct.unpack_from('<I',prefix,site+192)[0]
        if oldword>>26!=(3 if call else 2):raise ValueError('Native hook jump type changed')
        change(0,site,jal(target)if call else j(target),'Retarget reviewed installed hook')
    # Grow LUTs only into explicitly proven zero padding. All old targets stay.
    floats=list(struct.unpack_from('<129f',old,0x800));font=ImageFont.truetype(str(FONT),16)
    newfloat=[font.getlength('\u00e1'),font.getlength('\u00e9')];widths=[round(x)for x in floats+newfloat]
    if old[0xa04:0xa0c]!=bytes(8):raise ValueError('Float LUT padding occupied')
    payload[0xa04:0xa0c]=struct.pack('<2f',*newfloat)
    bodypattern=struct.pack('<129I',*widths[:129]);small=[0 if n<32 or n==127 else max(1,(w+1)//2)for n,w in enumerate(widths)]
    for addr in BODY_LUTS+(SMALL_LUT,):
        index=addr-START;expected=bodypattern if addr in BODY_LUTS else struct.pack('<129I',*small[:129])
        if old[index:index+516]!=expected or old[index+516:index+524]!=bytes(8):raise ValueError('Exact LUT/padding changed')
        pos=mapped(addr)-START+516;payload[pos:pos+8]=struct.pack('<2I',*(widths[129:]if addr in BODY_LUTS else small[129:]))
    offsets={**before['high_glyph_offsets'],'129':188928,'130':190976}
    lookup=[65535]*131
    for code in GLYPH_CODES:lookup[code]=offsets[str(code)]//256
    payload[0x600:0x706]=struct.pack('<131H',*lookup)
    # These17 exact sites are decoded-glyph gates. Raw CP932 lead tests are
    # deliberately excluded; cap/measurement byte parsers get separate code.
    for addr in GATES:
        w=struct.unpack_from('<I',old,addr-START)[0]
        if w>>26!=11 or w&65535!=129:raise ValueError('Decoded glyph gate signature changed')
        change(2,mapped(addr)-START,(w&0xffff0000)|131,'Decoded98-glyph repertoire; not raw lead-byte range')
    # Descriptor word0 is an inclusive highest sorted-record index, not count.
    hi,lo=struct.unpack_from('<II',old,0x52c)
    table=(((hi&65535)<<16)+struct.unpack('<h',struct.pack('<H',lo&65535))[0])-START
    entries=list(struct.iter_unpack('<Iff',old[table:table+326*12]))
    if len(entries)!=326 or len(set(x[0]for x in entries))!=326:raise ValueError('Resident table changed')
    newtable=START+append(b''.join(struct.pack('<Iff',*x)for x in sorted(entries+[(129,326.,-1.),(130,327.,-1.)])))
    if struct.unpack_from('<I',old,0x524)[0]!=i(13,0,9,325):raise ValueError('Old inclusive bound changed')
    change(2,0x524,i(13,0,9,327),'328 sorted records inclusive upper bound327')
    change(2,0x52c,i(15,0,9,(newtable+0x8000)>>16),'New complete sorted resident records')
    change(2,0x530,i(9,9,9,newtable),'New complete sorted resident records')
    state=START+append(bytes(8));decoderaddr=START+append(decompress())
    initoff=align(len(payload),16);initaddr=START+initoff
    code,rel=initialize(START+0x500,state,before['high_bank'],len(packed),len(extended),decoderaddr)
    assert append(code)==initoff;extra.extend((initoff+a,0x200|t)for a,t in rel)
    up,rel=uploader(state,START+0x600);payload[0x200:0x300]=up+bytes(256-len(up))
    extra.extend((0x200+a,0x200|t)for a,t in rel)
    retarget(0x4c0ec,initaddr,True)
    classify=block(decoder(True,(0xf0cf0,0xf0d98,0xec644),private_pairs=True));retarget(0xe9cc8,classify)
    measurement=block(measure(mapped(0x172c9a0),True));retarget(0xed15c,measurement)
    reveal=block(literal_reveal_cap(True,True,True));retarget(0xee984,reveal)
    ruby=audit()
    if ruby['counts'].get('needs_context',0):raise ValueError('Ruby associations unresolved')
    if any(b'\xf0\x40'in bytes.fromhex(x['runtime_signature_hex'])or b'\xf0\x41'in bytes.fromhex(x['runtime_signature_hex'])for x in ruby['rows']):raise ValueError('New PUA ruby requires explicit association tokenizer review')
    associations=association_records(ruby,widths);tableoff=align(len(payload),16);rubyaddr=START+tableoff
    data,ptrs=pack_associations(associations,rubyaddr);assert append(data)==tableoff
    extra.extend((a-START,0x202)for a in ptrs)
    center=block(ruby_center(rubyaddr));retarget(0xf0d2c,center)
    namecount=block(name_glyph_units(True))
    for site in NAME_COUNT_CALLS:retarget(site,namecount,True)
    # Native small-font and ruby cursor gates above now accept decoded130;
    # runtime02 paths retain inherited font selection and native expansions.
    records.extend(extra)
    if len(set(records))!=len(records):raise ValueError('Duplicate relocation')
    rel=b''.join(struct.pack('<II',*x)for x in records)
    payloadfile=align(len(prefix),64);prefix.extend(bytes(payloadfile-len(prefix)));prefix.extend(payload)
    relfile=align(len(prefix),16);prefix.extend(bytes(relfile-len(prefix)));prefix.extend(rel)
    for s in sections:
        if s[1]==0x700000a0:s[4]=relfile+s[4]-ph[3][1]
        elif s[3]==START and s[4]==ph[2][1]:s[4]=payloadfile;s[5]=len(payload)
    last=max((s for s in sections if s[1]==0x700000a0),key=lambda s:s[4]+s[5]);last[5]+=len(extra)*8
    newsh=align(len(prefix),4);prefix.extend(bytes(newsh-len(prefix)))
    for s in sections:prefix.extend(struct.pack('<10I',*s))
    ph[2][1]=payloadfile;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=relfile;ph[3][4]=len(rel)
    for n,p in enumerate(ph):struct.pack_into('<8I',prefix,phoff+n*32,*p)
    struct.pack_into('<I',prefix,32,newsh);struct.pack_into('<H',prefix,48,len(sections))
    new_reloc_checks=0
    for base in (0x8804000,0x8900000,0x8fff000):
        segs,_,_=loaded(prefix,base)
        if segs[1]!=loaded(original,base)[0][1]:raise ValueError('Native LOAD1 changed')
        for site,target in [(0x4c0ec,initaddr),(0xe9cc8,classify),(0xed15c,measurement),(0xee984,reveal),(0xf0d2c,center)]+[(x,namecount)for x in NAME_COUNT_CALLS]:
            w=struct.unpack_from('<I',segs[0],site)[0]
            if (w&0x3ffffff)*4!=base+target:raise ValueError('New native jump relocation failed')
        for n,(off,flags)in enumerate(extra):
            typ=flags&255;raw=struct.unpack_from('<I',payload,off)[0];value=struct.unpack_from('<I',segs[2],off)[0]
            if typ==2:expected=(raw+base)&0xffffffff
            elif typ==4:expected=(raw&0xfc000000)|((((raw&0x3ffffff)*4+base)>>2)&0x3ffffff)
            elif typ==6:expected=(raw&0xffff0000)|((raw+base)&65535)
            elif typ==5:
                oo,ff=next(x for x in extra[n+1:]if x[1]&255==6)
                lo=struct.unpack_from('<I',payload,oo)[0]
                a=((raw&65535)<<16)+struct.unpack('<h',struct.pack('<H',lo&65535))[0]
                expected=(raw&0xffff0000)|(((a+base+0x8000)>>16)&65535)
            else:raise ValueError('New relocation format changed')
            if value!=expected:raise ValueError('New loaded relocation semantics failed')
            new_reloc_checks+=1
    def metadata(value):
        if isinstance(value,dict):return {k:metadata(v)for k,v in value.items()}
        if isinstance(value,list):return [metadata(x)for x in value]
        if isinstance(value,str)and value.startswith('0x'):
            try:a=int(value,16)
            except ValueError:return value
            return hex(mapped(a))
        return value
    history=copy.deepcopy(before);active={k:v for k,v in before.items()if k not in ('memory_compaction','historical_build_proofs','high_bank','high_glyph_offsets')}
    report=metadata(active)
    for key in ('old_payload_sha256','inherited_payload_sha256','old_relocations_sha256','inherited_relocation_table_sha256','payload_growth','old_payload_preserved','old_relocations_preserved','relocation_prefix_unchanged'):report.pop(key,None)
    report.update(version='0.1.16',status='dry_owned_vram_font_candidate',runtime_verified=False,input_sha256=SHA,
        output_elf_sha256=sha(prefix),output_sha256=sha(prefix),elf_bytes=len(prefix),payload_bytes=len(payload),
        payload_growth=len(payload)-len(old),module_growth_bytes=len(payload),total_relocations=len(records),added_relocations=len(extra),
        high_bank=before['high_bank'],high_bank_bytes=len(extended),high_bank_sha256=sha(extended),high_glyph_count=98,
        high_codes=GLYPH_CODES,high_glyph_offsets=offsets,high_lookup_rva=START+0x600,high_lookup_entry_bytes=2,high_lookup_unit=256,
        font_runtime_storage='owned_vram_lz4_v1',high_bank_address_kind='compressed_source_rva_not_texture',font_compressed_bytes=len(packed),
        font_compressed_sha256=sha(packed),font_runtime_state_rva=state,font_codec_model='cp932-pua-f040-f041-v1',font_raster_sha256=sha(Path(FONT).read_bytes()),
        old_payload_preserved=False,old_relocations_preserved=False,relocation_prefix_unchanged=False,
        font_compaction=comp,font_word_changes=patches,input_build_history=dict(scope='Frozen .15 historical proofs only, not current preservation assertions.',report=history),
        font_hooks=dict(initializer=initaddr,decompressor=decoderaddr,decoder=classify,uploader=START+0x200,measurement=measurement,reveal=reveal,ruby_center=center,name_count=namecount),
        font_descriptor=dict(record_count=328,inclusive_upper_bound=327,native_records_preserved=230),
        ruby_current_snapshot=dict(spans=ruby['ruby_spans'],signature_count=len(associations),table_bytes=len(data),table_rva=rubyaddr,private_pairs=0),
        memory_forecast=dict(recovered_bytes=len(old)-len(payload),observed_fpl_deficit=133376,margin_before_new_ui=len(old)-len(payload)-133376),
        limitations=['Font allocation failure must fail candidate QA; Latin draws safely skipped, Japanese native path retained.',
                    'Owned VRAM availability/backup lifetime and scene GPU texture demand need runtime QA.',
                    'New executable UI strings not included yet; reserve their final allocation before ISO preparation.',
                    'Compressed sourceRVA is not a runtime texture address; resolve owned state pointer for font traces.'])
    report.setdefault('hooks',{}).update(ruby_decoder=hex(classify),battle_label_decoder=hex(classify))
    report['dialogue_control_patch']['measurement_hook']=hex(measurement)
    report['reveal_terminal_patch']['new_hook']=hex(reveal)
    report['dialogue_ruby_patch']['hooks']['ruby_decoder']=hex(classify)
    report['dialogue_ruby_patch']['hooks']['name_glyph_units']=hex(namecount)
    report['dialogue_ruby_patch'].update(association_table=hex(rubyaddr),association_ledger_sha256=sha(data),
                                       association_records=len(associations),ruby_spans=ruby['ruby_spans'],association_counts=ruby['counts'])
    report['battle_label_patch']['hooks']['battle_label_decoder']=hex(classify)
    report['ruby_current_snapshot']['current_target_audit_sha256']=sha(json.dumps(ruby,sort_keys=True,separators=(',',':')).encode())
    report['relocation_table_sha256']=sha(rel)
    report['new_relocation_model']=dict(bases=[0x8804000,0x8900000,0x8fff000],comparisons=new_reloc_checks,passed=True)
    from build_local import authoritative_font_metadata
    authoritative_font_metadata(bytes(prefix),report)
    return bytes(prefix),report


if __name__=='__main__':
    data,report=build();print(json.dumps(report,indent=2));print('DRY RUN: no executable, assets or reports written.')
