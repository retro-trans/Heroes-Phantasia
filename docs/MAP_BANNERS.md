# Dungeon location images

The current local build is **0.1.43**, with all **30 observed dungeon-entry name images in English**. Earlier scoped preparations are documented below as history.

## Complete category — 0.1.43

The user's cave screenshot reads **Cave of the Red Mist**, from `fld/dngn/d24.bin`. `work/ui/map_banners/labels.en.json` records all 30 source labels and their full English targets, matched against the original asset contact sheet. Existing glossary names take precedence. Ten previously missing compound names are recorded in `work/glossary/map_banner_terms.en.json` with the original asset and game-wiki sources; the canonical glossary also includes the world-map terms. The shared glossary builder accepts both the `entries` and `terms` source formats and reports no spelling conflicts.

`tools/prepare_map_banners_043.py` covers every observed 256x32 texture in the dungeon category. It replaces 28 remaining Japanese images and verifies that d01/d06 retain the exact earlier English assets. Complete names use Roboto Condensed Italic at 14–26 native pixels, rasterized at 4x and downsampled. No words are omitted. The native allocation, white alpha palette, swizzle and every nonpixel resource byte stay exact. The five excluded containers are d31/d92/d97/d98/d99; they use different headers without the corresponding banner section.

The reviewed English contact sheet is `work/ui/map_banners/0.1.43/english_assets.png`, an **asset preview**, not a gameplay capture. The full preparation report records source/base/candidate hashes, dimensions, bounds and each font size. The working bitmap translation queue now has 30 rows, with a Japanese-free export produced by `tools/strip_jp.py`.

The separate ISO inherits the executable and all prior translations from 0.1.42. Only 28 dungeon resources and the title row change; 5,157 other archive rows remain exact. `tools/verify_map_banners_043.py` independently checks all 30 resource hashes, palettes and nonpixel bytes, reviewed pixels, nested ISO readbacks, the retained English battle atlas and English prologue. The build's complete banner coverage replaces the older one-banner manifest count. Native banner UV coverage, entry animation and readability in natural scenes remain unverified.

The other user screenshot shows **Defense** with a green downward arrow. The already installed battle atlas renders that label at 8 native pixels inside its original 32x14 region. Its 20 whole English labels and three fragment headings are retained in 0.1.43. This category patch does not enlarge the battle badge.

Fresh isolated software-renderer startup, title and main-menu captures pass visual review with **v0.1.43** above the title credit. `work/ui/title/0.1.43/startup_validation.en.json` links their identities to the current ISO/executable. This startup proof does not establish natural dungeon-banner placement or UV coverage.

## Initial forest banner — 0.1.25

The forest screenshot shows a location name drawn from a bitmap rather than an encoded dialogue string. Its source is the third section of `fld/dngn/d06.bin`; the existing glossary target is **Forest of Encounters**. Translating the 26 encoded map-name records did not replace these separate images.

`tools/audit_dungeon_banners.py` decoded 30 native 256x32 CI8 textures in 64-byte-header dungeon containers. Five other files use a different 32-byte container and are excluded from the banner count. The source contact sheet and hashes are in `work/ui/map_banners/source_snapshot`. These are image observations, not additions to the structured Japanese-bearing record totals.

The current patch replaces all lettering in the d06 image. It retains the original palette, tint-compatible white alpha pixels, 16x8 swizzle, 256x32 allocation, container offsets and all other sections. English lettering uses Roboto Condensed Italic, rasterized at 4x and downsampled to the unchanged native allocation. Its ink bounds are `[1,2,209,23]`, compared with `[1,2,100,23]` for the source. The complete English name fits; the source UV consumer has not been observed.

The English bitmap is installed in the separate 0.1.25 ISO. The resource's readback from both HP.CPK and the nested archive inside the ISO matches the reviewed candidate exactly. The executable, VWF and protagonist defaults are byte-identical to 0.1.24. Append and ISO build validation preserve unrelated resources and original disc bytes. Title/version/credit and the five main-menu labels pass current native capture review.

Static banner proof: `work/ui/map_banners/0.1.25/validation.en.json`. Source/English asset comparison and approximate user-screenshot regions: `work/ui/map_banners/0.1.25/comparison.png` and `layout.en.json`. The user reference has unknown build identity. No matching 0.1.25 gameplay capture of this banner was obtained, so native placement, UV coverage and readability remain pending. The other 29 image banners are not translated in this patch.

Preparation defaults to dry-run. `tools/prepare_dungeon_banner.py --write-review` writes only a fresh review directory. Asset writing requires the reviewed candidate hash and a fresh separate output. `tools/append_cpk.py` appends the raw candidate and verifies all untouched archive bytes and rows. `tools/build_local.py` produces the version stamp and ISO from one build configuration; carrying the English prologue requires all four prologue input/proof/hash arguments. `tools/verify_dungeon_banner_build.py` independently verifies the original compressed bitmap, installed resource, nested ISO readback and preservation scope before writing a fresh proof.

Working transcription: `work/translation/en/bitmaps/dungeon_banner_0001.json`. Its English-only export is produced by `tools/strip_jp.py`; the Japanese working source remains ignored. This bitmap unit is counted separately from the top-level byte-string translation queue.

## HOLD Headquarters — 0.1.32 preparation

The headquarters screenshot matches `fld/dngn/d01.bin` in the source contact sheet. Its complete target is **HOLD Headquarters**, following the HOLD organization entry in `work/glossary/glossary.en.json` and the existing encoded map-name targets. `tools/prepare_hold_banner.py` reuses the reviewed dungeon bitmap workflow with d01-specific source hash, section offsets and lettering bounds. Dry-run and static source/English comparison precede guarded asset writing.

The candidate retains all 115648 resource bytes except its 8192-byte swizzled pixel allocation, including the original palette and container offsets. Roboto Condensed Italic is rasterized at 4x and reduced to the unchanged 256x32 texture. Complete English ink bounds are `[1,1,199,27]`. This is supersampled rasterization within the native allocation, not an enlarged game texture. Review: `work/ui/map_banners/0.1.32/comparison.png`; proposal: `work/ui/map_banners/0.1.32/proposal.en.json`; asset: `work/output/0.1.32-banner-assets/d01.bin` and its `.en.json` proof.

Archive preparation uses the exact 0.1.31 HP.CPK baseline and replaces only d01, preserving the existing English Forest of Encounters banner and every other resource. The separate archive and append proof are `work/output/0.1.32-hold-banner-archive/HP.CPK` and `HP.CPK.manifest.en.json`. Final ISO installation and title-version update are performed by `tools/build_local.py`. Two of the 30 observed dungeon banners have English candidates; 28 remain pending. Native headquarters banner display, UV coverage and readability remain unverified until the resulting build is captured in this scene.
