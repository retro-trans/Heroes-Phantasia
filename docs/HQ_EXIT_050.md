# HQ exit confirmation — 0.1.50

The user reported a blank question above Yes/No at the headquarters globe.
The installed table1 entry 12 already contains `Go to the World Map?` followed
by its original 0E terminator. Neither the translation nor its pointer was lost.

The HQ drawing caller at RVA 914C8 calls the legacy plain-text renderer at
E9F1C. Its decoder return at E9F84 is outside the English glyph classification
gates, so every single-byte English letter is skipped. Yes/No uses a different
working renderer. An isolated native call reproduces the blank in the old path.

The repair redirects all 26 inventoried plain confirmation drawing calls to a
44-byte dispatcher in previously audited, still-unused retired text storage.
Printable Latin input selects the existing VWF renderer at 92D70. Japanese,
empty, null and leading-control inputs retain E9F1C. No event command, input
handler, choice text, portrait track or speech-bubble tail is modified.

Nineteen associated centered question layouts now use the existing English
width helper. Its original trailing 0E terminator is accepted using existing
instruction and delay-slot space. Unknown controls and Japanese retain the
original length calculation. The inherited 13-pixel layout-unit rounding is
retained. Copy/allocation lengths and the unused strlen at 907C0 are intact.

Preparation validates 24 dispatcher cases across three load bases, every changed
byte, both new J26 relocations and exact preservation of unselected loaded bytes.
There is zero loaded-memory growth; the file grows only for relocation metadata.
The original shared Japanese routine and previous font/bubble code remain exact.

Installed native QA in an isolated PPSSPP interpreter checks eight width cases
and five draw cases: original blank reproduction, complete HQ English question,
Yes, No and Japanese fallback. It checks exact glyph codes, VWF positions,
callee-saved registers and stack balance, restoring borrowed memory and state.
Evidence: `work/ui/field/0.1.50/native_confirmation.en.json`.

The local ISO is built through `tools/build_local.py`, preserving the English
prologue and existing translations and showing 0.1.50 above the title credit.
Nested ISO/archive checks and startup/title review are recorded in the build
validation evidence. Public release was authorized on 2026-10-13; its full and
published-0.1.45 upgrade patches use the same reviewed image. See the release notes
and `docs/RETRO_TRANS_RELEASES.md` for packaging and verification.

This QA uses synthetic calls to the installed native routine. It does not prove
a natural HQ exit interaction, all related menu placement or a full playthrough.
