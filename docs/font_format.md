# Native font audit

The asset layouts below were decoded from the extracted original CPK and visually reviewed. This is an asset-format finding; runtime advances, screen positions, and renderer patches require executable tracing and in-game verification.

## Indexed battle names

`btl/sys_tbl.bin` has a 256-entry little-endian u32 offset table at `0x2a0`; offsets are relative to that section. The first string starts at relative `1028`. Strings are null-terminated little-endian u16 local glyph IDs, padded with zeros. The section ends at `0x1380`. IDs are **not** Unicode or CP932.

`tools/decode_glyph_tables.py` uses an explicit, locally reviewed seed file, `work/source/font_audit/glyph_seeds.json`. Seeds were read from the numbered native atlas and checked against existing name lists, the glossary, and the [game's battle sequence](https://w.atwiki.jp/heroes_phantasia/pages/51.html). The script verifies seed lengths, every shared ID, one-to-one character mapping, and exact byte round trips including terminators and padding. This is a reviewed transcription map, not a discovered embedded charset.

The result is 256 nonempty rows, 67 unique labels, 139 mapped IDs, and no unresolved IDs. IDs 1–139 are referenced; ID 0 terminates strings and has a blank cell. ID 2 is a full-width space with a blank cell. Rows 244–255 are level/test labels and are flagged as debug candidates. Runtime visibility of all entries remains unverified; these counts must not be presented as 256 newly observed player-visible strings.

Row 53's native spelling differs by a voiced mark from the [game wiki's beast name](https://w.atwiki.jp/heroes_phantasia/pages/49.html). The extraction retains the native glyph; translation must apply the wiki preference in `BASE_RULES.md`.

## CI8 texture container

Two reviewed font textures use a 128-byte header, a 1024-byte RGBA palette (256 entries), and one byte per pixel. Offsets in this table are relative to the texture header.

| Header offset | Meaning |
| --- | --- |
| `+0x04` | Pixel buffer width |
| `+0x10` | Stored pixel buffer height |
| `+0x1c` | Palette offset, `0x80` |
| `+0x28` | Pixel offset, `0x480` |
| `+0x34` | Total bytes, `0x480 + width * height` |

Pixels are swizzled in 16-byte by 8-row blocks. Within each block, eight consecutive 16-byte rows are stored; blocks run left to right, then top to bottom. The [PSPSDK swizzle example](https://github.com/pspdev/pspsdk/blob/master/src/samples/gu/speed/speed.c) provides the primary reference for this layout. Decoding it produces readable glyphs; treating it as linear pixels does not.

| Asset | Texture offset | Stored dimensions | Total bytes |
| --- | --- | --- | --- |
| `btl/sys_tbl.bin` | `0x1380` | 256 × 88 | `0x5c80` |
| `phase/bin/p000000.bin` | `0xd00` | 512 × 96 | `0xc480` |

The battle texture has a 12 × 12 pixel grid with 21 columns. Glyph `g` starts at `x=(g%21)*12`, `y=(g//21)*12`. There are 140 relevant slots including blank slot 0, occupying 84 rows; stored height is rounded to 88 for swizzling. The phase texture's glyph-cell mapping was not established. Stored buffer heights are not claims about the GU power-of-two texture size configured by the executable.

## Headerless packed fonts

These font banks use 384 bytes per slot. Expand each byte's low nibble first, then high nibble, to obtain a linear 32 × 24 alpha bitmap. Values 0–15 expand to 0–255 for previewing. Most visible glyph ink lies within a roughly 14 × 14 region; the slot dimensions do not establish the text advance.

| Asset/bank | Font range | Following CP932 range | Slots | Charset characters | First charset slot |
| --- | --- | --- | --- | --- | --- |
| Gallery `GcHelp01001` | `0x20–0x9da0` | `0x9da0–0x9e80` | 105 | 104 | 0 |
| Field `f101010` | `0x1040–0x6ec0` | `0x6ec0–0x6f20` | 63 | 45 | 0 |
| `ALLResidentNML`, first | `0x658b0–0x7ccb0` | `0x7ccb0–0x7ce80` | 248 | 230 | 17 |
| `ALLResidentNML`, second | `0x7ce80–0xbfd80` | `0xbfd80–0xc0310` | 714 | 705 | 0 |

Ranges are half-open. Resident bank one begins with 17 extra symbol/icon slots before the sorted charset; its final slot is blank. Other trailing slots are blank: gallery 1, field 18, resident bank two 9. Punctuation, Latin letters, kana, and sampled kanji visually agree with charset order. Unnamed leading symbols have not been assigned semantic IDs.

`tools/inspect_font_assets.py` exports source hashes, slot locations, characters, and measured alpha ink bounds to `work/source/font_audit/native_font_assets.json`, plus readable PNGs. Bounds use an exclusive right/bottom edge. Blank glyphs have null bounds. No advance table has been found in these reviewed headers; ink bounds must not be silently used as game advances.

## VWF and four-times resolution implications

A VWF implementation must change both pen advancement and the game's width/centering/wrapping calculations, retain control-code handling, and rebuild or relocate text/font data. This audit supplies native glyph images and mapping evidence for that work, but does not prove that any runtime patch is installed.

[PSPSDK's texture setup](https://github.com/pspdev/pspsdk/blob/master/src/gu/sceGuTexImage.c) limits GU width/height to 512 and expects powers of two. Direct four-times expansion makes the reviewed widths 1024 and 2048, respectively. Repacking 140 battle slots of 48 × 48 into 512-pixel pages requires more than one page: ten columns produce fourteen rows (672 pixels). A native solution therefore needs paging or other renderer changes; an emulator texture replacement can preserve logical texture dimensions, subject to the emulator integration being verified separately.

## Reproduction

Run both tools without `--write` and inspect their sample output first. Then run `tools/decode_glyph_tables.py --write` and `tools/inspect_font_assets.py --write`; the latter requires Pillow. All Japanese-containing results remain under ignored `work/source/font_audit/`. The tools only read original game assets and write the opt-in audit artifacts.
