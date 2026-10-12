# Executable inventory and renderer investigation

Analysis date: 2026-10-10. No build or release was produced; the ISO was not changed. Later live tracing is recorded in `runtime_font_trace.md`: the actual module base, five observed main-menu labels in an initially omitted code-section pool, decoder and fixed-advance draw path are now identified. The original scan's 640 candidates remain separate from those five labels.

## Original files

| File | Size | Finding |
| --- | ---: | --- |
| BOOT.BIN | 5,277,797 bytes | Entirely zero-filled placeholder; no executable or strings. |
| EBOOT.BIN | 5,278,144 bytes | Encrypted `~PSP` module, name `hp_proj`, key tag `0xD91613F0`, compression attribute zero. |
| EBOOT.decrypted.elf | 5,277,797 bytes | Successfully decrypted ELF32 little-endian MIPS, PSP PRX type `0xFFA0`. |

Original EBOOT SHA-256: `35ed860299129acbf23230b0f6e4b1e64c9fed417528baea7519c69ab1423c16`.

Decrypted ELF SHA-256: `03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1`.

## Reproduction

The small upstream [pspdecrypt project](https://github.com/John-K/pspdecrypt) contains the required key and PPSSPP-derived PRX decryption code. This analysis used revision `c156627db7634d395c380c0a9589130f603307fc`. The full CLI requires OpenSSL; the included minimal driver uses only `PrxDecrypter.cpp` and bundled libkirk, built with the installed MinGW compiler. It accepts uncompressed PSP inputs, verifies ELF magic before saving, and refuses an existing output. The local third-party checkout, compiler objects and decrypted binary remain under ignored `work/source/`.

Run `tools/decrypt_executable.ps1` to review the plan, then add `-Execute` to reproduce decryption when the output does not exist. Compilation emits existing upstream warnings in its ECDSA signing function; this workflow only decrypts.

Review a string scan before saving it:

```powershell
python tools/scan_executable.py work/source/PSP_GAME/SYSDIR/BOOT.BIN work/source/PSP_GAME/SYSDIR/EBOOT.BIN work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf --text-range 0x2ea250:0x2f37cc --text-range 0x305e88:0x306380
```

Add `--write work/source/executable_strings.json` after reviewing the sample. Source text is deliberately absent from this document.

The 640 extracted candidates are queued in eight consecutive 80-row batches under `work/translation/en/executable_0001.json` through `executable_0008.json`. The first batch has English drafts; the remaining seven contain 560 untranslated records. IDs, offsets, encoded byte lengths and source order are retained. This queue covers the scanner's candidates only, not every runtime UI string.

## Strings and limits

The reviewed pools contain **640 heuristic CP932 records**, including install/save prompts, protagonist and character labels, reference terms, episode titles and acquisition notifications. These candidates still need in-game verification. Five separately queued menu labels were found later in the code section and observed in Japanese and in the reversible English VWF test; they are outside this 640-record count. The scanner preserves file offsets, module-relative addresses, byte lengths and percent placeholders. It does not scan encrypted bytes or MIPS instructions as text.

An unrestricted decoder generates garbage from embedded PNGs, compressed data and numeric tables. The reviewed pool filter rejects that material and halfwidth mixtures. It may omit a genuine halfwidth label, encoded text elsewhere, an interior substring pointer or a non-null-terminated string. UTF-16 and custom glyph-code data are not covered by this CP932-oriented pass. PNG signatures occur at offsets `0x294ED0`, `0x29CD00`, `0x2A3FD0`, `0x2A9780`, and `0x2AECE0`; their accidental decodes must not enter translation batches.

Raw neighboring-data inspection confirmed omissions relevant to insertion: standalone `%d` at `0x2EA81C`, ten full-width digit labels at `0x2EA67C`–`0x2EA6A0`, and a title/connector fragment at `0x2EA868`. These do not add rows to the current 640-candidate queue. Preserve them in the binary and incorporate their assembly context before inserting translated save prompts. Other shared string fragments may also be omitted by the Japanese-character filter.

## Relocation and VWF prospects

The decrypted PRX has three program headers, 55 section headers and PSP relocation sections (`0x700000A0`). Section names and symbols are stripped. A normal loadable region starts at file offset `0xC0` with module-relative address zero; the second segment starts at `0x47B040`. The source header entry offset is `0x127214`. Absolute runtime addresses require the emulator's actual load base and applied relocations. Aligned data-word matches in the inventory are only reference clues, and do not include MIPS high/low instruction pairs or relocation resolution.

The import table at file offsets `0x294788`–`0x294954` has 23 libraries, including `sceGe_user` and `sceDisplay`; it has **no `sceFont` library**. No ASCII `font` or `pgf` marker occurs in the ELF. This suggests a game-owned rendering path, but does not establish which routine draws text or whether it already supports variable advance widths.

A VWF needs the text decoder, glyph lookup, cursor advance, line wrapping, centering and clipping routines traced together. Subsequent live work has demonstrated relocated English menu labels with native variable widths; see `runtime_font_trace.md` and `VWF.md`. The reversible test was restored and does not modify this executable. [Ghidra](https://github.com/NationalSecurityAgency/ghidra) remains applicable for broader caller and relocation analysis.

Native and 4x atlas prototypes now exist. Four-times appearance has not been demonstrated; static analysis found an existing sprite routine that separates source UV extent from destination size, allowing a candidate 64x64 English glyph region at 16x16 logical size. See `vwf_4x_feasibility.md` for swizzle, texture-state and allocation requirements. Full dialogue, centering and persistent build coverage remain unfinished.

Header fields were checked against [PPSSPP's PRX header definition](https://github.com/hrydgard/ppsspp/blob/master/Core/ELF/PrxDecrypter.h); the tool's own [PRX implementation](https://github.com/John-K/pspdecrypt/blob/c156627db7634d395c380c0a9589130f603307fc/PrxDecrypter.cpp) supplies the decryption route.
