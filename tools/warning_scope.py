"""Guarded pure warning integration. Returns bytes/report; never writes an ELF."""
import copy, hashlib, json, struct
from pathlib import Path
from build_menu_patch import align, relocate_code
from compact_vwf_patch import loaded
from executable_text_patch import Elf, reference_index
from private_latin import encode_character
from live_vwf import j, jal
from warning_wrap_hooks import span_scanner, block_wrapper
from warning_draw_hooks import blocks as draw_blocks

DESIGN = Path('work/source/executable_warning_compact_wrap_design.en.json')
ORIGINAL = Path('work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf')

def sha(data): return hashlib.sha256(data).hexdigest()

def native18_guard_profile(base, report, design):
    """Prove changed native words solely through the two typed font remaps."""
    if sha(base) != '6c51c380c048dfa2287b1e888cadb1a30ca673f6720447678f52cafe16448e47':
        raise ValueError('Unreviewed native18 warning guard candidate')
    source = Path('work/output/0.1.17-dialogue-assets/EBOOT.BIN').read_bytes()
    if sha(source) != '321d1e5918ddb9ea7258163acc9185fe6a0e54c04d38d50e2cc8ee6fb14c1235':
        raise ValueError('Reviewed17 warning guard source changed')
    prior, incoming = Elf(source), Elf(base)
    stages = (report['trailer_recovery']['address_changes'],
              report['native_tail_compaction']['address_changes'])
    typed_refs,_ = reference_index(prior)
    low_mates = {ref['sites'][1]:ref['sites'][0] for ref in typed_refs
                 if ref['kind']=='R_MIPS_HI16_LO16' and ref['loader_mate_is_semantic_low']
                 and not ref['shared_high_site']}
    a,b = (int(x,16) for x in design['function_range'])
    start = prior.file_offset(a,b-a)
    if sha(source[start:start+b-a]) != '1a12d250ed44752e058065d0474711c64952f25fd0f337ff7df59b81138c1823':
        raise ValueError('Reviewed17 complete warning function changed')
    sites = set(range(a,b,4)) | {int(row['rva'],16) for row in design['current17_word_guards']}
    changes = []
    for site in sorted(sites):
        before, after = prior.word(site), incoming.word(site)
        if before == after:
            continue
        chain = []
        lookup_site = site
        # Font remappers report a paired HI/LO address once at the HI site.
        # Its semantic LO mate must be checked against the same full address.
        if site in low_mates:
            lookup_site = low_mates[site]
        for records in stages:
            matches = [row for row in records if row['old_site'] == lookup_site
                       and row['new_site'] == lookup_site and (row['old_flags'] >> 8 & 255) == 0]
            if len(matches) > 1:
                raise ValueError('Ambiguous native18 typed remap')
            if matches:
                chain.append(matches[0])
        if not chain:
            raise ValueError('Unproved complete-function delta: '+hex(site))
        for first,second in zip(chain,chain[1:]):
            if first['new_resolved_rva'] != second['old_resolved_rva']:
                raise ValueError('Native18 typed remap chain mismatch')
        mapped_kind = chain[0]['old_flags'] & 255
        kind = 6 if lookup_site != site else mapped_kind
        if any((row['old_flags'] & 255) != mapped_kind or (row['new_flags'] & 255) != mapped_kind for row in chain):
            raise ValueError('Native warning relocation type changed')
        def expected(word,address):
            if kind == 4: return (word & 0xfc000000) | (address >> 2 & 0x3ffffff)
            if kind == 5: return (word & 0xffff0000) | ((address+0x8000) >> 16 & 65535)
            if kind == 6: return (word & 0xffff0000) | (address & 65535)
            raise ValueError('Unsupported warning remap kind')
        if expected(before,chain[0]['old_resolved_rva']) != before:
            raise ValueError('Typed source17 address does not reproduce native word')
        if expected(before,chain[-1]['new_resolved_rva']) != after:
            raise ValueError('Typed native18 address does not reproduce native word')
        if incoming.relocs.count((site,kind)) != 1:
            raise ValueError('Native18 typed warning relocation absent')
        changes.append({'site':site,'old_word':before,'new_word':after,'type':kind,
                        'source_rva':chain[0]['old_resolved_rva'],
                        'final_rva':chain[-1]['new_resolved_rva'],'stages':len(chain),
                        'semantic_HI_site':lookup_site if kind==6 else None})
    return {'source17_sha256':sha(source),'native18_sha256':sha(base),
            'all_other_complete_function_words_exact':True,'typed_word_changes':changes,
            'current_word_guards':[{'rva':row['rva'],'word':hex(incoming.word(int(row['rva'],16)))}
                                   for row in design['current17_word_guards']]}

def build(base, inherited_report, *, lut_rva=0x16ff4e0):
    """Compose only reviewed warning scope into the exact incoming candidate.

    Existing code/data are retained. New code uses inherited target0/full-RVA
    relocation convention; no target2 pointer is accidentally given a full RVA.
    Caller must independently review returned report before any installation.
    """
    report = copy.deepcopy(inherited_report)
    if sha(base) != report.get('output_elf_sha256', report.get('output_sha256')):
        raise ValueError('Incoming executable/report hash mismatch')
    original = ORIGINAL.read_bytes(); design_bytes = DESIGN.read_bytes()
    design = json.loads(design_bytes)
    if sha(original) != design['original_elf_sha256']:
        raise ValueError('Original executable changed')
    old = Elf(original); incoming = Elf(base)
    def native_word(addr): return incoming.word(addr)
    def native_offset(addr, size=4): return incoming.file_offset(addr, size)
    lut_bytes = base[native_offset(lut_rva, 524):native_offset(lut_rva, 524)+524]
    if sha(lut_bytes) != design['current17_width_lut']['sha256']:
        raise ValueError('Reviewed integer width LUT changed')
    guard_profile = (native18_guard_profile(base, report, design)
                     if sha(base) == '6c51c380c048dfa2287b1e888cadb1a30ca673f6720447678f52cafe16448e47' else None)
    guards = guard_profile['current_word_guards'] if guard_profile else design['current17_word_guards']
    for row in guards:
        if native_word(int(row['rva'],16)) != int(row['word'],16):
            raise ValueError('Inherited warning hook changed: '+row['rva'])
    # The .17 function already contains inherited setup prompt HI/LO pairs.
    # Guard its complete reviewed bytes; never roll them back to Japanese.
    a,b = (int(x,16) for x in design['function_range'])
    off = native_offset(a,b-a)
    if not guard_profile and sha(base[off:off+b-a]) != '1a12d250ed44752e058065d0474711c64952f25fd0f337ff7df59b81138c1823':
        raise ValueError('Warning assembly function differs from reviewed source')
    rows = {}
    for path in Path('work/translation/en').glob('executable*.json'):
        if path.name.endswith('.en.json'): continue
        for row in json.loads(path.read_text(encoding='utf-8')).get('rows',[]):
            if row['id'] in design['warning_target_guards']:
                if row['id'] in rows: raise ValueError('Duplicate warning target ID')
                rows[row['id']] = row
    if set(rows) != set(design['warning_target_guards']):
        raise ValueError('Warning targets missing')
    for rid,row in rows.items():
        if row['status']!='draft' or sha(row['target'].encode('utf-8')) != design['warning_target_guards'][rid]:
            raise ValueError('Reviewed warning target changed: '+rid)
    po,so = struct.unpack_from('<II',base,28)
    if struct.unpack_from('<H',base,44)[0] != 4: raise ValueError('Expected four program headers')
    ph = [list(struct.unpack_from('<8I',base,po+n*32)) for n in range(4)]
    if ph[2][0]!=1 or ph[3][0]!=0x700000a0: raise ValueError('Unexpected payload/relocation segment')
    sections = [list(struct.unpack_from('<10I',base,so+n*40)) for n in range(struct.unpack_from('<H',base,48)[0])]
    # Keep every incoming file byte, including unloaded font trailer, at its
    # existing file offset. Old payload/relocation/section copies become unused
    # file data; only the newly described segment copies are loaded. This avoids
    # stale font bootstrap seek constants without adding resident RAM.
    prefix = bytearray(base)
    payload = bytearray(base[ph[2][1]:ph[2][1]+ph[2][4]])
    oldpayload = bytes(payload)
    rels = list(struct.iter_unpack('<II',base[ph[3][1]:ph[3][1]+ph[3][4]]))
    extra=[]; changes=[]; strings=[]
    def write_word(site,value,expected,reason):
        off=native_offset(site)
        if struct.unpack_from('<I',prefix,off)[0]!=expected: raise ValueError('Guard changed: '+hex(site))
        struct.pack_into('<I',prefix,off,value)
        changes.append(dict(site=site,expected_word=expected,replacement_word=value,reason=reason))
    def append(data):
        payload.extend(bytes((-len(payload))%16)); off=len(payload); payload.extend(data); return off
    def code(data):
        off=append(data)
        extra.extend(struct.iter_unpack('<II',b''.join(relocate_code(payload,off,len(data)))))
        return ph[2][2]+off
    refs,_=reference_index(old)
    # These are the fully read warning-construction functions, not all numeric references.
    ranges=((0x4ad00,0x4b260),(0x4ba60,0x4bf84))
    for rid,row in rows.items():
        raw=b''.join(encode_character(c) for c in row['target'])+b'\0'
        if b'\0' in raw[:-1]: raise ValueError('Embedded warning NUL')
        selected=[x for x in refs if x['address']==row['offset']-192]
        if not selected: raise ValueError('No typed warning reference')
        reusable=[]
        for ref in selected:
            hi,lo=ref['sites']; h,l=native_word(hi),native_word(lo)
            if (h&0xffff0000)!=(old.word(hi)&0xffff0000) or (l&0xffff0000)!=(old.word(lo)&0xffff0000):
                raise ValueError('Typed warning instruction changed')
            current=((h&65535)<<16)+struct.unpack('<h',struct.pack('<H',l&65535))[0]
            if current!=row['offset']-192:
                offset=incoming.file_offset(current,len(raw))
                if base[offset:offset+len(raw)]!=raw: raise ValueError('Inherited warning target differs')
                reusable.append(current)
        addr=reusable[0] if reusable else ph[2][2]+append(raw)
        for ref in selected:
            hi,lo=ref['sites']
            if ref['kind']!='R_MIPS_HI16_LO16' or not ref['loader_mate_is_semantic_low'] or ref['shared_high_site']:
                raise ValueError('Unsafe warning HI/LO mate')
            if not all(any(start<=site<end for start,end in ranges) for site in (hi,lo)):
                raise ValueError('Unreviewed warning consumer')
            h,l=old.word(hi),old.word(lo)
            if l>>26!=9: raise ValueError('Expected ADDIU address low')
            for site,typ in ((hi,5),(lo,6)):
                if rels.count((site,typ))!=1: raise ValueError('Missing/changed warning relocation')
            write_word(hi,(h&0xffff0000)|((addr+0x8000)>>16)&65535,native_word(hi),'typed warning string HI')
            write_word(lo,(l&0xffff0000)|(addr&65535),native_word(lo),'typed warning string LO')
        strings.append(dict(id=rid,target=row['target'],bytes_including_nul=len(raw),rva=addr,
                            typed_pairs=len(selected),reused_inherited_payload=bool(reusable)))
    for x in design['proposed_immediate_edits']:
        write_word(int(x['site'],16),int(x['proposed_word'],16),int(x['expected_word'],16),'reviewed compact stack buffer')
    scanner=code(span_scanner()); wrapper=code(block_wrapper(scanner,lut_rva))
    hooks={name:code(data) for name,data in draw_blocks(lut_rva).items()}
    for site,addr,call in ((0x9319c,wrapper,False),(0x92dc0,hooks['warning_classify'],True),
                          (0x92e08,hooks['warning_route'],True),(0x92e10,hooks['warning_advance'],False)):
        expected=native_word(site); had=rels.count((site,4))
        if had not in (0,1) or (site!=0x9319c and had!=1): raise ValueError('Inherited jump relocation changed')
        write_word(site,jal(addr) if call else j(addr),expected,'paired warning renderer')
        if not had: rels.append((site,4))
        if not call: write_word(site+4,0,native_word(site+4),'hook delay slot')
    rels.extend(extra)
    if len(set(rels))!=len(rels): raise ValueError('Duplicate relocation')
    relocation=b''.join(struct.pack('<II',*x)for x in rels)
    pf=align(len(prefix),64); prefix.extend(bytes(pf-len(prefix))); prefix.extend(payload)
    rf=align(len(prefix),16); prefix.extend(bytes(rf-len(prefix))); prefix.extend(relocation)
    for s in sections:
        if s[1]==0x700000a0: s[4]=rf+s[4]-ph[3][1]
        elif s[3]==ph[2][2] and s[4]==ph[2][1]: s[4]=pf;s[5]=len(payload)
    newsh=align(len(prefix),4);prefix.extend(bytes(newsh-len(prefix)))
    for s in sections:prefix.extend(struct.pack('<10I',*s))
    ph[2][1]=pf;ph[2][4]=ph[2][5]=len(payload);ph[3][1]=rf;ph[3][4]=len(relocation)
    for n,p in enumerate(ph):struct.pack_into('<8I',prefix,po+n*32,*p)
    struct.pack_into('<I',prefix,32,newsh)
    result=bytes(prefix); comparisons=0
    for loadbase in (0x8804000,0x8900000,0x8fff000):
        before,_,_=loaded(base,loadbase); after,_,_=loaded(result,loadbase)
        if after[1]!=before[1] or after[2][:len(oldpayload)]!=before[2]: raise ValueError('Inherited data changed')
        masked=bytearray(before[0])
        for x in changes:masked[x['site']:x['site']+4]=after[0][x['site']:x['site']+4]
        if masked!=after[0]: raise ValueError('Unselected native bytes changed')
        for x in strings:
            for ref in [r for r in refs if r['address']==rows[x['id']]['offset']-192]:
                hi,lo=ref['sites'];h,l=struct.unpack_from('<I',after[0],hi)[0],struct.unpack_from('<I',after[0],lo)[0]
                resolved=((h&65535)<<16)+struct.unpack('<h',struct.pack('<H',l&65535))[0]
                if resolved!=loadbase+x['rva']: raise ValueError('Loaded warning pointer differs')
                comparisons+=1
    # Original seek scalars and trailer must survive byte-for-byte, including
    # incoming section/relocation copies which are now inactive file data.
    kept=bytearray(base)
    for x in changes:
        off=native_offset(x['site']);kept[off:off+4]=result[off:off+4]
    kept[po:po+128]=result[po:po+128];kept[32:36]=result[32:36]
    if result[:len(base)]!=kept: raise ValueError('Unselected incoming file bytes changed')
    report.update(output_sha256=sha(result),output_elf_sha256=sha(result),elf_bytes=len(result),payload_bytes=len(payload),
                  total_relocations=len(rels),added_relocations=report.get('added_relocations',0)+len(extra)+1,
                  relocation_table_sha256=sha(relocation))
    report['warning_scope']=dict(status='dry_complete_paired_warning_scope_not_installed',version='0.1.18',
        input_elf_sha256=sha(base),output_elf_sha256=sha(result),design_sha256=sha(design_bytes),
        strings=strings,changes=changes,hooks=dict(scanner=scanner,wrapper=wrapper,**hooks),
        added_payload_bytes=len(payload)-len(oldpayload),added_code_relocations=len(extra),
        file_growth_bytes=len(result)-len(base),preserved_incoming_file_bytes=len(base),
        unloaded_trailer_preserved_at_original_offsets=True,
        unselected_incoming_file_bytes_exact=True,
        unloaded_trailer_sha256=sha(base[so+len(sections)*40:]),
        total_relocations=len(rels),loaded_pointer_comparisons=comparisons,
        inherited_payload_prefix_exact=True,inherited_LOAD1_exact=True,unselected_native_bytes_exact=True,
        lut_rva=lut_rva,lut_sha256=sha(lut_bytes),native_guard_profile=guard_profile,runtime_verified=False,
        limitations=['Screen/controller QA remains pending; synthetic instruction tests are separate.',
                     'Unknown controls and unsupported glyphs fall back before graphics.',
                     'Notification pools, Crack Burst and Mao are outside this warning scope.',
                     'Conservative file-only duplication retains original trailer offsets; compact file relayout requires regenerated bootstrap seek constants.'])
    return result,report
