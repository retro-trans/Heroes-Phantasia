English fan translation of **Heroes Phantasia** for PSP (**ULJS-00456**), including the translated prologue movie.

### Apply

**Recommended:** Use the latest [Retro Trans](https://github.com/retro-trans/retro-trans-tools/releases/latest) app. Click **Refresh catalog**, open **Automatic**, select your original Japanese ISO or the published 0.1.45 English ISO, choose **0.1.50** or **Latest**, and select a new output filename. The app downloads the matching patch and verifies the result.

**Manual patching:** [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher) and [xdelta3](https://github.com/jmacd/xdelta) accept the same assets:

| Your source image | Patch |
| --- | --- |
| Original Japanese ISO | `Heroes-Phantasia-English-0.1.50.xdelta` |
| Published English 0.1.45 ISO | `Heroes-Phantasia-English-0.1.45-to-0.1.50.xdelta` |

```text
xdelta3 -d -s "Heroes Phantasia (Japan).iso" Heroes-Phantasia-English-0.1.50.xdelta "Heroes Phantasia English 0.1.50.iso"
```

To upgrade from the published 0.1.45 image:

```text
xdelta3 -d -s "Heroes Phantasia English 0.1.45.iso" Heroes-Phantasia-English-0.1.45-to-0.1.50.xdelta "Heroes Phantasia English 0.1.50.iso"
```

Both patches produce the same release image. The upgrade requires the exact published 0.1.45 image; other local test builds are not supported upgrade inputs.

Original Japanese ISO: **1,415,020,544 bytes**; SHA-256 `2c3583f377cdaa9132d349a0039d7f6ffe21cac093476c7746705e8af2b03b40`.

Published 0.1.45 upgrade source: **2,644,776,960 bytes**; SHA-256 `5a59a2c07b1de69cac94efcc0d1114d97b0a48c91c08de95d8a55460b6d4b4ac`.

Release output: **2,647,455,744 bytes**; SHA-256 `fa420a494942817a7498615716b8b43bbc5ff4a817abb3cdb4354a90e89df8b8`.

Exact source, target and patch hashes are in `BUILD-MANIFEST.json`. `VALIDATION.json` records both complete patch round trips, and `SHA256SUMS.txt` covers the downloads.

### What changed since v0.1.45

* **HQ exit confirmation:** Fixes the blank “Go to the World Map?” question above Yes/No. Repairs English drawing at all 26 callers of the shared plain confirmation path and updates 19 associated centered layouts.
* **Quest, Camp, Shop and map menus:** Translates 28 shared labels, including Main Quests, Subquests, Shop, map controls and landmark categories.
* **Headquarters notices:** Translates 12 unique system notices across 15 event occurrences, including the unavailable elevator, Data Room guidance, party arrivals and unlocked destinations.
* **Battle commands:** Translates eight command labels, including Commands, Breakthrough, Declare Victory and End Turn. Widens the affected panels while preserving command costs and button placement.
* **Lina's introduction:** Rewraps the complete sentence into six lines in both protagonist scenes and supports the preserved Latin pronunciation reading. Native checks confirm the body fits the sloping bubble and preserves the original tail endpoint and outline.
* **Title:** Displays **v0.1.50** above the project credit.

Retains the previous dialogue and gallery translations, English prologue, battle bitmap labels, location banners, 4x variable-width Latin font, English protagonist defaults and reviewed bubble fixes. See the [changelog](https://github.com/retro-trans/Heroes-Phantasia/blob/main/CHANGELOG.md).

### Release status

**This is a work-in-progress translation. Further proofreading and full gameplay testing are needed.** File and patch verification establishes that the intended data is included and both patches reproduce the release image; it does not certify all emulator or hardware behavior.

Fresh isolated startup and the current title stamp pass review. Installed native confirmation checks reproduce the old blank and verify all question glyphs, spacing, Yes/No and Japanese fallback. The preceding Lina build passes 224 scoped native bubble checks. Natural HQ exit interaction, updated field and command-menu placement, conversation playback, unsupported bubble shapes and full-game routes still need playtesting.

A static corpus audit flags 1,192 possible existing bubble fallback pages; these are warnings, not confirmed visual overflows. Some image-based text and other movies remain outside confirmed translated coverage. The shared bubble fit covers 120 standard templates; scoped checks do not establish every scene's visual behavior.

**Boot the patched ISO fresh and load a normal save.** Older emulator save states can restore old text, fonts, coordinates and movie data.

### What's included

English for supported dialogue, battle/skit and gallery containers; executable/menu/help labels; save-point, tutorial, quest, Camp, Shop and world-map UI; translated prologue movie; readable shared battle bitmap labels, including **DEF** for Defense; all 30 identified dungeon-entry name images; supported custom English bubbles with unequal side slopes, outlined tails and reviewed native speaker anchors; a 4x variable-width Latin font; English protagonist defaults, including Restore Defaults; and the current title version stamp. Custom player input is retained.

### How it was translated

This is a **machine translation**, produced with large language models and reviewed and edited using scene context and a researched glossary. English source files retain context, decisions and uncertainties. Human proofreading and playtesting are welcome.

### Acknowledgements

* **Project lead and testing:** [binhlt0402](https://github.com/binhlt0402)
* **Translation and implementation assistance:** OpenAI Codex
* **Patching and release packaging:** [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools)

### Source code

English translation text, glossaries, selected layout metadata and tools are available in the [project repository](https://github.com/retro-trans/Heroes-Phantasia). GitHub's source archives contain the repository snapshot at the release tag. Use the `.xdelta` assets to patch the game; source archives do not include a complete clean-checkout ISO rebuild.

### Contribute

Bug reports, proofreading and playtesting are welcome in [Issues](https://github.com/retro-trans/Heroes-Phantasia/issues) and at **[discord.gg/MssepShjmB](https://discord.gg/MssepShjmB)**.

No complete game images are included. Apply the patches to your own disc image.
