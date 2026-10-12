"""Guard the reviewed native dictionary allocation/scroll evidence; no writer."""
import hashlib
import json
from pathlib import Path
import struct

PROOFS = {
    'work/ui/gallery/dictionary_capacity_static.en.json': 'dbeb478f15717274aea18d2776d99a15422fdcfe0fbe842c4ef1bc23a21c7781',
    'work/ui/gallery/dictionary_capacity_disassembly.en.json': 'ddad60d774c1232f40d650fe1f847a2cb0e78a8d31eff1de824fc05dc071510f',
}
LONG_ROWS = dict(zip((12,37,50,51,128,130,131,134), (
    'f2e93152825828208696','02f66bb39ed9b12f83cc',
    'af6d08cba41bf0b3e321','7b538bb65ba9dc0055fc','1625e8c88bcb39eb9161',
    '5de2dcc5b8271c3533d9','3d6a5f32fcfc2f7d7359','394792e53420a0b93850')))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def reference():
    documents = []
    snapshots = []
    for name, expected in PROOFS.items():
        raw = Path(name).read_bytes()
        if sha(raw) != expected:
            raise ValueError('Reviewed dictionary capacity evidence changed')
        documents.append(json.loads(raw))
        snapshots.append(dict(path=name,sha256=expected))
    proof, disassembly = documents
    elf_path = Path(disassembly['source_elf'])
    elf = elf_path.read_bytes()
    if sha(elf) != disassembly['source_elf_sha256'] or sha(elf) != proof['original_elf_sha256']:
        raise ValueError('Native dictionary executable changed')
    phoff = struct.unpack_from('<I',elf,28)[0]
    ph = struct.unpack_from('<8I',elf,phoff)
    if ph[0] != 1 or ph[2] != 0 or ph[1] != 0xc0:
        raise ValueError('Native LOAD0 mapping changed')
    checked = 0
    for routine in disassembly['routines']:
        for instruction in routine['instructions']:
            rva = instruction['rva']
            if not routine['start_rva'] <= rva < routine['end_rva_exclusive'] or rva+4 > ph[4]:
                raise ValueError('Native instruction outside reviewed routine')
            if struct.unpack_from('<I',elf,ph[1]+rva)[0] != instruction['word']:
                raise ValueError('Native dictionary instruction changed')
            checked += 1
    if checked != 353:
        raise ValueError('Reviewed native dictionary instruction scope changed')
    model = proof['modeled_42_record_case']
    if proof['reset_and_allocation']['element_bytes'] != 232 or model['array_bytes'] != 9744 or model['line_records'] != 42:
        raise ValueError('Dictionary allocation model changed')
    if model['reachable_first_row_indices'] != list(range(36)) or model['last_draw_indices'] != list(range(35,42)):
        raise ValueError('Dictionary scroll model changed')
    snapshots.append(dict(path=str(elf_path),sha256=sha(elf)))
    return dict(input_snapshots=snapshots,checked_native_instructions=checked,
                static_capacity_supported=True,max_physical_lines=42,element_bytes=232,
                native_allocation_failure_guard=False,runtime_verified=False,
                policy='Only the eight reviewed dictionary records may exceed the historical 15-line runtime observation; complete wording and original controls remain preserved.')
