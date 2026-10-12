"""Pure first-fit placement into proof-backed, excluded PNG tails; no writer."""
import copy,hashlib

def plan(report, requests):
    """requests: {name, data:bytes, alignment:4|16}. Returns new free list/patches.

    Code needs a separate CFG/relocation review. This helper grants storage only;
    it never interprets bytes as executable code or creates relocation records.
    """
    proof=report['trailer_recovery']
    if not proof.get('png_tails_excluded_by_exact_declared_sizes') or not proof.get('original_relocation_tail_references_rejected') or not proof.get('savedata_native_tail_lifetime'):
        raise ValueError('PNG-tail lifetime/reference prerequisites missing')
    free=copy.deepcopy(proof['free_tail_regions']);patches=[];names=set()
    for req in requests:
        name=req['name'];data=req['data'];alignment=req.get('alignment',4)
        if name in names or not isinstance(data,bytes) or not data or alignment not in (4,16):raise ValueError('Invalid/duplicate allocation request')
        names.add(name)
        for region in free:
            start=(region['start_rva']+alignment-1)&-alignment
            if start+len(data)<=region['end_rva']:
                patches.append(dict(name=name,rva=start,file_offset=start+192,bytes=len(data),alignment=alignment,sha256=hashlib.sha256(data).hexdigest(),data=data,tail=region['name']))
                region['start_rva']=start+len(data);break
        else:raise ValueError('No proved PNG-tail region can hold '+name)
    for region in free:
        region['next_aligned4_rva']=(region['start_rva']+3)&-4
        region['bytes']=region['end_rva']-region['start_rva']
    return dict(patches=patches,free_tail_regions=free,remaining_bytes=sum(x['end_rva']-x['start_rva']for x in free),module_growth_bytes=0,assets_written=False)
