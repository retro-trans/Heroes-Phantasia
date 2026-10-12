"""Dictionary-only soft breaks from exact .16 prepared font; no asset writer.

Measured dictionary viewport/scroll provenance remains distinct from candidates.
Native symbols, runtime substitutions, ruby and unmeasured control paths reject.
"""
import hashlib,json,math,re,struct
from pathlib import Path
from dialogue_tokens import tokenize_bytes
from dialogue_tokens import validate_controls
from rebuild_dialogue import format_placeholders

PROOF=Path('work/ui/runtime/gallery_candidate_validation.en.json')
FONT_REPORT=Path('work/source/font_016_preparation_dry.en.json')

def sha(b):return hashlib.sha256(b).hexdigest()

def reference():
    from prepare_font_016 import build
    raw,report=build();saved_text=FONT_REPORT.read_text(encoding='utf8')
    saved,end=json.JSONDecoder().raw_decode(saved_text)
    if saved_text[end:].strip() not in ('','DRY RUN: no executable, assets or reports written.'):
        raise ValueError('Unexpected font dry report suffix')
    if sha(raw)!=saved['output_elf_sha256'] or report['output_elf_sha256']!=saved['output_elf_sha256']:raise ValueError('Final .16 font differs from approved dry report')
    phoff=struct.unpack_from('<I',raw,28)[0];ph=struct.unpack_from('<8I',raw,phoff+64)
    floats=struct.unpack_from('<131f',raw,ph[1]+0x800);codes=tuple(range(32,127))+(128,129,130)
    if any(not math.isfinite(floats[c]) or not 0<floats[c]<=16 for c in codes):raise ValueError('Invalid final Latin font metrics')
    widths={c:round(floats[c]) for c in codes}
    proofraw=PROOF.read_bytes();proof=json.loads(proofraw)
    if proof['text_viewport']!=[4,72,330,154] or proof['glyph_limit']!=45 or proof['physical_lines']!=15 or not proof['gallery_record_display_qa_passed']:raise ValueError('Dictionary geometry/scroll proof differs')
    for item in proof['scroll_captures']+proof['scroll_traces']:
        if sha(Path(item['path']).read_bytes())!=item['sha256']:raise ValueError('Saved scroll evidence hash differs')
    dependencies=('dictionary_wrap','prepare_font_016','font_payload_compaction','font_vram_hooks','font_ram_plan','compact_vwf_patch','live_vwf','build_menu_patch','dialogue_tokens','private_latin','dialogue_measure','dialogue_vwf_hooks','dialogue_ruby_hooks','dialogue_wrap','audit_ruby_spans','build_local')
    code_inputs={str(Path('tools')/(name+'.py')):sha((Path('tools')/(name+'.py')).read_bytes()) for name in dependencies}
    return widths,{'font_elf_sha256':sha(raw),'font_dry_report_sha256':sha(FONT_REPORT.read_bytes()),'font_report':str(FONT_REPORT),'code_input_sha256':code_inputs,'float_lut_sha256':sha(struct.pack('<131f',*floats)),'rounded_integer_advances':widths,'geometry_proof':str(PROOF),'geometry_proof_sha256':sha(proofraw),'viewport':[4,72,330,154],'line_pitch_px':22,'visible_rows':7,'runtime_observed_physical_lines':15,'runtime_observed_scroll_first_line_indices':[0,4,8],'runtime_observed_complete_line_indices':proof['complete_line_indices'],'other_gallery_routes_measured':False}

def wrap(encoded,source,target,widths):
    errors=validate_controls(source,target)
    if errors:raise ValueError('Source control validation failed: '+str(errors))
    if format_placeholders(source)!=format_placeholders(target,source):raise ValueError('Source-aware format placeholder mismatch')
    if format_placeholders(source):raise ValueError('Runtime expansion width not measured')
    if not encoded.endswith(b'\x12\x0e') or encoded.count(b'\x12')!=1 or encoded.count(b'\x0e')!=1:
        raise ValueError('Dictionary requires a single terminal12/0E fence; midpage streams are unreviewed')
    tokens=tokenize_bytes(encoded,private_latin=True)
    for t in tokens:
        if t.kind=='latin' and not t.ruby and t.code in widths:continue
        if t.kind=='control' and t.code in (0x11,0x12,0x0e):continue
        raise ValueError(f'Unmeasured dictionary token at{t.offset}: {t.kind}/{t.code}')
    out=bytearray(encoded);breaks=[]
    def dims(start,end):
        pen=extent=count=0
        for t in tokens:
            if start<=t.offset<end:
                if t.kind!='latin':raise ValueError('Control in word segment')
                if t.code!=32:extent=max(extent,pen+16)
                pen+=widths[t.code];count+=1
        return pen,extent,count
    cursor=0
    while cursor<len(tokens):
        if tokens[cursor].kind=='control':cursor+=1;continue
        segment=[]
        while cursor<len(tokens) and tokens[cursor].kind=='latin':segment.append(tokens[cursor]);cursor+=1
        line_start=segment[0].offset;word=[];words=[]
        for token in segment:
            if token.code==32:
                if word:words.append(word);word=[]
            else:word.append(token)
        if word:words.append(word)
        for word in words:
            a=word[0].offset;b=word[-1].offset+len(word[-1].data)
            if dims(a,b)[1]>330 or dims(a,b)[2]>45:raise ValueError('Unbreakable dictionary word exceeds measured width/capacity')
            if dims(line_start,b)[1]<=330 and dims(line_start,b)[2]<=45:continue
            split=a-1
            if split<line_start or out[split]!=32:raise ValueError('No safe separating space')
            out[split]=0x11;breaks.append(split);line_start=a
    restored=bytearray(out)
    for offset in breaks:
        if encoded[offset]!=32 or out[offset]!=0x11:raise ValueError('Break ledger mismatch')
        restored[offset]=32
    if bytes(restored)!=encoded:raise ValueError('Wrap wording/control identity differs')
    lines=[]
    body=bytes(out).split(b'\x12',1)[0].split(b'\x0e',1)[0]
    for line in body.split(b'\x11'):
        pen=extent=count=0
        for t in tokenize_bytes(line,private_latin=True):
            if t.kind!='latin':raise ValueError('Wrapped line contains unmeasured token')
            if t.code!=32:extent=max(extent,pen+16)
            pen+=widths[t.code];count+=1
        if extent>330 or count>45:raise ValueError('Final line exceeds measured bounds')
        lines.append({'advance_px':pen,'destination_extent_px':extent,'glyphs':count})
    return bytes(out),{'width_px':330,'glyph_limit':45,'physical_lines':len(lines),'soft_breaks':len(breaks),'space_to_linebreak_offsets':breaks,'lines':lines,'single_terminal_page_fence_verified':True,'original_controls_preserved_at_original_offsets':True,'wording_reconstructed_byte_exact':True,'scroll_beyond_seven_rows_observed':True,'within_observed_15_physical_line_scroll_range':len(lines)<=15,'runtime_verified_for_this_row':False}
