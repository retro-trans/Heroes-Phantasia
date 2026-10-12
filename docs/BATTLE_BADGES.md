# Compact battle stat labels — 0.1.44

Version **0.1.45** extends bold bitmap lettering across the remaining twelve whole labels and three encounter headings, bringing this shared category to **23 labels**. The eight stat badges below remain exact. Most remaining labels keep their full display wording; Observe displays OBS, HP Modifier displays HP MOD, and Enemy Side displays Foe. Semantic targets remain complete. Font size grows where the native rectangle permits; constrained labels gain heavier opaque strokes. Failed and First Strike Formation keep their native font size with a bold face; Ambush grows from 20px to 28px.

The original three heading partitions, positions, UVs and palettes remain exact. Reassembling the changed atlas fragments produces the proposed opaque heading pixels exactly, including the overlapping seams. `tools/prepare_battle_labels_045.py` and `tools/verify_battle_labels_045.py` provide dry-run preparation and installation checks. The before/after asset comparison is in `work/ui/battle/0.1.45/comparison.png`. Native battle display remains unverified.

Version 0.1.45 archive and nested ISO readbacks pass against the reviewed candidate. Only the battle resource and title rows differ from 0.1.44; 5,184 other archive rows remain exact. Fresh isolated startup, title and main-menu captures pass visual review with v0.1.45 above the credit. Their identities are recorded in `work/ui/title/0.1.45/startup_validation.en.json`.

The user's badge beneath Monster reads **Defense**, with a green downward arrow indicating decreased defense. The previous English atlas squeezed the full word into a 32x14-pixel rectangle at an 8px font size, leaving only six pixels of glyph height. Version **0.1.44** displays **DEF** in 16px bold lettering with 12 pixels of glyph height. The existing palette's fully opaque white pixels replace softened small text; all pixels stay inside the original label rectangle.

The same treatment covers the eight adjacent stat labels in `btl/sys_all.bin`:

| Full term | Badge | Font size | Ink height |
| --- | --- | --- | --- |
| Attack | ATK | 16px | 12px |
| Defense | DEF | 16px | 12px |
| Charm | CHA | 15px | 11px |
| Teamwork | TEAM | 11px | 8px |
| Power | PWR | 15px | 11px |
| Accuracy | ACC | 16px | 12px |
| Hits | HITS | 14px | 10px |
| Critical | CRIT | 14px | 10px |

Full semantic terms remain in the translation queue and glossary. Short display forms are recorded separately in the preparation proof and queue notes. Only the eight 32x14 rectangles at texture coordinates `(32*index,34)` change. All other atlas pixels, arrow graphics, palettes, texture headers, dimensions, native coordinates and nonpixel resource bytes remain exact. Other twelve whole labels and three fragment headings retain their existing English images.

`tools/prepare_battle_badges_044.py` defaults to dry-run and requires the exact candidate hash for fresh review or asset writes. The font is Roboto Condensed Bold, rasterized at 4x, downsampled and thresholded to solid native pixels. `work/ui/battle/0.1.44/comparison.png` shows the actual old/new asset crops enlarged by 2x; it is **an asset preview, not a gameplay capture**.

`tools/verify_battle_badges_044.py` checks the final archive and nested ISO readbacks against the reviewed asset. Only `btl/sys_all.bin` and the title row change from 0.1.43; 5,184 other archive rows remain exact. All 30 translated location banners, the executable, VWF, default-name and speech-bubble fixes, and English prologue are preserved. The new local ISO and title stamp are built through `tools/build_local.py`. Natural battle sampling, animation and full-game visual readability remain unverified.

Fresh isolated startup, title and main-menu captures pass review with **v0.1.44** above the title credit. Their hashes and current ISO/executable identities are recorded in `work/ui/title/0.1.44/startup_validation.en.json`. This evidence verifies startup, not natural battle badge rendering.
