English fan translation of **Heroes Phantasia** for PSP (**ULJS-00456**), including the translated prologue movie.

### Apply

**Recommended:** Use the latest [Retro Trans](https://github.com/retro-trans/retro-trans-tools/releases/latest) app. Click **Refresh catalog**, open **Automatic**, select your original Japanese ISO, choose **0.1.45** or **Latest**, and select a new output filename. The app downloads the matching patch and verifies the result.

**Manual patching:** [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher) and [xdelta3](https://github.com/jmacd/xdelta) accept the same patch:

| Your source image | Patch |
| --- | --- |
| Original Japanese ISO | `Heroes-Phantasia-English-0.1.45.xdelta` |

```text
xdelta3 -d -s "Heroes Phantasia (Japan).iso" Heroes-Phantasia-English-0.1.45.xdelta "Heroes Phantasia English 0.1.45.iso"
```

Original Japanese ISO: **1,415,020,544 bytes**; SHA-256 `2c3583f377cdaa9132d349a0039d7f6ffe21cac093476c7746705e8af2b03b40`.

Release output: **2,644,776,960 bytes**; SHA-256 `5a59a2c07b1de69cac94efcc0d1114d97b0a48c91c08de95d8a55460b6d4b4ac`.

The output includes appended translation resources. Exact source, target and patch hashes are in `BUILD-MANIFEST.json`; `VALIDATION.json` records the patch round trip, and `SHA256SUMS.txt` covers the downloads. This first public release has no upgrade patch from earlier local test builds.

### What's included

* **Dialogue and gallery text:** English for the supported dialogue, battle/skit and gallery containers, with researched character and organization names.
* **Menus and help:** Supported executable/menu/help labels, plus save-point, tutorial and world-map UI translations.
* **Prologue movie:** Embedded English translation of the prologue movie.
* **Battle labels:** Bold shared bitmap lettering across 20 whole labels and three encounter headings. Stat badges use readable abbreviations, including **DEF** for Defense. Original sprite rectangles, arrows, palettes and heading partitions are preserved.
* **Location banners:** All 30 identified dungeon-entry name images have English lettering, including **Cave of the Red Mist**.
* **Dialogue bubbles:** Custom English fitting, unequal side slopes, outlined tails, native speaker-anchor preservation and reviewed scene-specific fixes for supported standard templates.
* **Fonts and names:** A 4x variable-width Latin font and English protagonist defaults, including Restore Defaults. Custom player input is retained.
* **Title:** Displays **v0.1.45** above the project credit.

See the [changelog](https://github.com/retro-trans/Heroes-Phantasia/blob/main/CHANGELOG.md) for the complete local development history.

### Release status

**This is a work-in-progress translation. Further proofreading and full gameplay testing are needed.** Static resource checks and patch verification establish that the intended bytes are installed and reproduced; they do not certify emulator or hardware behavior.

Fresh isolated startup, title and English main-menu captures pass review. The latest battle-label and dungeon-banner revisions have been reviewed as assets and verified inside the ISO; their natural gameplay display remains unverified. Natural conversation playback, unsupported/nonstandard bubble shapes and full-game routes also need testing. A static corpus audit flags 1,192 possible existing bubble fallback pages; these are warnings, not confirmed visual overflows. Some image-based text and other movies remain outside confirmed translated coverage.

The shared bubble fit code covers 120 standard templates; 219 scoped native instruction cases pass in the included executable build. These checks do not establish every scene's visual behavior.

**Boot the patched ISO fresh and load a normal save.** Older emulator save states can restore old text, fonts, coordinates and movie data.

### How it was translated

This is a **machine translation**, produced with large language models and reviewed and edited using scene context and a researched glossary. English source files retain context, decisions and uncertainties. Human proofreading and playtesting are welcome.

### Acknowledgements

* **Project lead and testing:** [binhlt0402](https://github.com/binhlt0402)
* **Translation and implementation assistance:** OpenAI Codex
* **Patching and release packaging:** [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools)

### Source code

English translation text, glossaries, selected layout metadata and tools are available in the [project repository](https://github.com/retro-trans/Heroes-Phantasia). GitHub's source archives contain the repository snapshot at the release tag. Use the `.xdelta` asset to patch the game; source archives do not include a complete clean-checkout ISO rebuild.

### Contribute

Bug reports, proofreading and playtesting are welcome in [Issues](https://github.com/retro-trans/Heroes-Phantasia/issues) and at **[discord.gg/MssepShjmB](https://discord.gg/MssepShjmB)**.

No complete game images are included. Apply the patch to your own disc image.
