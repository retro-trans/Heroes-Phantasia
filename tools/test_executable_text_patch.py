"""Safety regression tests for the dry executable relocation inventory."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

from executable_text_patch import Elf, address_pair, encoded_text, installed_check, payload_models, reference_index, select_rows, scoped_template


def fixture(words, relocations):
    data = bytearray(0x500)
    data[:7] = b'\x7fELF\x01\x01\x01'
    struct.pack_into('<H', data, 18, 8)
    struct.pack_into('<I', data, 28, 0x34)
    struct.pack_into('<HH', data, 42, 32, 3)
    struct.pack_into('<8I', data, 0x34, 1, 0x100, 0, 0, 0x100, 0x100, 7, 4)
    struct.pack_into('<8I', data, 0x54, 1, 0x200, 0x1000, 0, 0x100, 0x100, 6, 4)
    struct.pack_into('<8I', data, 0x74, 0x700000a0, 0x300, 0, 0, len(relocations)*8, 0, 0, 8)
    for rva, word in words.items():
        off = 0x100+rva if rva < 0x100 else 0x200+rva-0x1000
        struct.pack_into('<I', data, off, word)
    for n, pair in enumerate(relocations):
        struct.pack_into('<II', data, 0x300+n*8, *pair)
    return bytes(data)


class SafetyTests(unittest.TestCase):
    def test_signed_carry_and_register_guard(self):
        hi = 15 << 26 | 8 << 16 | 0x31
        lo = 9 << 26 | 8 << 21 | 9 << 16 | 0xff80
        self.assertEqual(address_pair(hi, lo), 0x30ff80)
        with self.assertRaises(ValueError):
            address_pair(hi, lo ^ (1 << 21))
        with self.assertRaises(ValueError):
            address_pair(hi, 13 << 26 | 8 << 21 | 8 << 16 | 0xff80)

    def test_only_relocation_backed_numbers(self):
        image = fixture({0x10:0x1234, 0x14:0x1234}, [(0x10,2)])
        refs, issues = reference_index(Elf(image))
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]['sites'], [0x10])
        self.assertFalse(issues)
        self.assertEqual(image, fixture({0x10:0x1234, 0x14:0x1234}, [(0x10,2)]))

    def test_storage_and_target_segment_bases(self):
        image = fixture({0x1010:0x24}, [(0x10,2 | 1 << 8 | 1 << 16)])
        refs, issues = reference_index(Elf(image))
        self.assertEqual(refs[0]['sites'], [0x1010])
        self.assertEqual(refs[0]['address'], 0x1024)
        self.assertFalse(issues)

    def test_multiple_register_groups_and_unpaired_low(self):
        h8, h9 = 15 << 26 | 8 << 16 | 0x30, 15 << 26 | 9 << 16 | 0x31
        l8, l9 = 9 << 26 | 8 << 21 | 8 << 16 | 0x100, 35 << 26 | 9 << 21 | 10 << 16 | 0xff80
        refs, issues = reference_index(Elf(fixture({0x10:h8,0x14:h9,0x18:l8,0x1c:l9,0x20:l9},
                                                  [(0x10,5),(0x14,5),(0x18,6),(0x1c,6),(0x20,6)])))
        self.assertEqual([r['address'] for r in refs], [0x300100,0x30ff80,0x30ff80])
        self.assertFalse(issues)  # LW into T2 preserves T1's LUI base.
        self.assertTrue(refs[2]['shared_high_site'])
        self.assertFalse(refs[2]['loader_mate_is_semantic_low'])

    def test_reused_high_never_crosses_call_or_clobber(self):
        high = 15 << 26 | 8 << 16 | 0x30
        low = 35 << 26 | 8 << 21 | 9 << 16 | 0x100
        for barrier in (3 << 26, 9 << 26 | 8 << 16 | 7):
            refs, issues = reference_index(Elf(fixture({0x10:high,0x14:low,0x18:barrier,0x1c:low},
                                                       [(0x10,5),(0x14,6),(0x1c,6)])))
            self.assertEqual(len(refs), 1)
            self.assertEqual(len(issues), 1)

    def test_inherited_payload_and_pointer_guard(self):
        raw = bytearray(fixture({0x10:0x1020}, [(0x10,2)]))
        raw[0x220:0x226] = b'Watari'
        raw[0x226] = 0
        entry = dict(payload_rva='0x1020', target='Watari', pointer_rvas=['0x10'], route='installed_ascii_setup')
        self.assertEqual(installed_check(Elf(bytes(raw)), entry)['target'], 'Watari')
        raw[0x220] = ord('X')
        with self.assertRaises(ValueError):
            installed_check(Elf(bytes(raw)), entry)

    def test_authoritative_defaults_override_but_source_must_match(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            names = [f'executable_{n:04}.json' for n in range(1,9)]
            names += ['executable_supplement_0001.json','menu_ui_0001.json','setup_osk_0001.json','setup_defaults_0001.json']
            for name in names:
                (path/name).write_text(json.dumps(dict(rows=[])))
            row = dict(id='same',offset=32,encoding='cp932',source='A',byte_length=1,status='draft',target='Prefix')
            (path/names[0]).write_text(json.dumps(dict(rows=[row])))
            row = dict(row,target='Heroes Phantasia')
            (path/names[-1]).write_text(json.dumps(dict(rows=[row])))
            rows, _, conflicts, reused = select_rows(path)
            self.assertEqual(rows[0]['row']['target'], 'Heroes Phantasia')
            self.assertTrue(conflicts[0]['resolved_by_authoritative_queue'])
            self.assertEqual(len(reused), 1)
            row['byte_length'] = 2
            (path/names[-1]).write_text(json.dumps(dict(rows=[row])))
            with self.assertRaises(ValueError):
                select_rows(path)

    def test_controls_are_bytes_not_braces_and_encodings_not_selected(self):
        self.assertEqual(encoded_text('A{02}0019{0F}M{0F}', 'utf-8'), b'A\x020019\x0fM\x0f')
        models = payload_models('Cinq Flèches')
        self.assertFalse(models['engine_private_latin']['selected'])
        self.assertNotEqual(models['utf8']['bytes_including_nul'], models['engine_private_latin']['bytes_including_nul'])
        self.assertIn('unsupported', payload_models('★')['engine_private_latin'])

    def test_scoped_template_leaves_same_pool_other_consumers_and_encodes_accents(self):
        ref=dict(kind='R_MIPS_32',sites=['0x3071e4'],interior_source_byte_offset=0,
                 already_changed=False,base_words=['0x2eb000'])
        row=dict(id='name',inherited=None,source_rva='0x2eb000',target='Lycée de Cinq Flèches',
                 renderer_evidence='native_control02_name_table_engine_latin_static',
                 references=[ref,dict(ref,sites=['0x1234'])])
        report=dict(allocation_model={'candidate_append_rva':'0x2000000'},rows=[row],
                    base_sha256='base',original_sha256='original',version='0.1.15',inherited_entries_verified=61)
        template=scoped_template(report)
        self.assertEqual(template['typed_pointer_writes'],1)
        self.assertEqual(len(template['untouched_other_consumers']),1)
        self.assertIn('f041',template['entries'][0]['payload_hex'])
        self.assertFalse(template['install_ready'])
        row['references'][0]['base_words']=['0xBAD']
        with self.assertRaises(ValueError):scoped_template(report)


if __name__ == '__main__':
    unittest.main()
