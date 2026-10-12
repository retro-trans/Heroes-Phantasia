"""Pure VWF word-wrap proposals; controls and existing page boundaries survive."""
from dialogue_tokens import tokenize_bytes

SUPPORTED = {5,0x16,0x17,0x1a,0x11}

def wrap_page(raw,widths,maximum=180,max_lines=4):
    """Wrap at spaces, treating prior 11 line divisions as soft whitespace.

    Returns a proposal only. Unsupported substitutions/ruby/glyphs, oversized
    words and excessive page height require review rather than dropping text.
    """
    tokens=tokenize_bytes(raw,private_latin=True);words=[];word=bytearray();width=0
    def flush():
        nonlocal word,width
        if word:words.append((bytes(word),width));word=bytearray();width=0
    for token in tokens:
        if token.kind=='control'and token.code in SUPPORTED:
            if token.code==0x11:flush()
            else:word.extend(token.data)
        elif token.kind=='latin':
            if token.code==32:flush()
            else:word.extend(token.data);width+=widths[token.code]
        else:return dict(supported=False,reason='Unverified substitution, ruby or native glyph; manual review required')
    flush();lines=[bytearray()];advances=[0]
    for text,advance in words:
        if advance>maximum:return dict(supported=False,reason='A complete word exceeds the available width')
        gap=widths[32]if lines[-1]else 0
        if advances[-1]+gap+advance>maximum:
            lines.append(bytearray());advances.append(0);gap=0
        if gap:lines[-1].extend(b' ')
        lines[-1].extend(text);advances[-1]+=gap+advance
    if len(lines)>max_lines:return dict(supported=False,reason='Page needs more lines than the current bubble engine supports',required_lines=len(lines))
    proposal=b'\x11'.join(bytes(line)for line in lines)
    signature=lambda data:[t.data for t in tokenize_bytes(data,True)if t.kind=='control'and t.code!=0x11]
    visible=lambda data:b''.join(t.data for t in tokenize_bytes(data,True)if t.kind=='latin'and t.code!=32)
    if signature(raw)!=signature(proposal)or visible(raw)!=visible(proposal):raise ValueError('Wrapping changed prose or controls')
    return dict(supported=True,data=proposal,line_advances=advances,lines=len(lines),maximum=maximum)

def wrap_body(raw,widths,maximum=180,max_lines=4):
    """Body-only input: preserve 10/12 page fences and terminal 0E exactly."""
    tokens=tokenize_bytes(raw,True);start=0;output=bytearray();pages=[]
    for token in tokens:
        if token.kind=='control'and token.code in (0x0e,0x10,0x12):
            if token.offset>start:
                result=wrap_page(raw[start:token.offset],widths,maximum,max_lines)
                if not result['supported']:return result
                output.extend(result['data']);pages.append({k:v for k,v in result.items()if k!='data'})
            output.extend(token.data);start=token.offset+len(token.data)
    if start<len(raw):
        result=wrap_page(raw[start:],widths,maximum,max_lines)
        if not result['supported']:return result
        output.extend(result['data']);pages.append({k:v for k,v in result.items()if k!='data'})
    return dict(supported=True,data=bytes(output),pages=pages)
