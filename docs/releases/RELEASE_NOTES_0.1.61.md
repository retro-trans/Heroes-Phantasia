English fan translation of **Heroes Phantasia** for PSP (**ULJS-00456**), including the translated prologue movie.

### Apply

**Recommended:** Use the latest [Retro Trans](https://github.com/retro-trans/retro-trans-tools/releases/latest) app. Click **Refresh catalog**, open **Automatic**, select your original Japanese ISO or the published 0.1.50 English ISO, choose **0.1.61** or **Latest**, and select a new output filename. The app downloads the matching patch and verifies the result. Published 0.1.45 can upgrade through the existing 0.1.50 route.

**Manual patching:** [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher) and [xdelta3](https://github.com/jmacd/xdelta) accept the same assets:

| Your source image | Patch |
| --- | --- |
| Original Japanese ISO | `Heroes-Phantasia-English-0.1.61.xdelta` |
| Published English 0.1.50 ISO | `Heroes-Phantasia-English-0.1.50-to-0.1.61.xdelta` |

```text
xdelta3 -d -s "Heroes Phantasia (Japan).iso" Heroes-Phantasia-English-0.1.61.xdelta "Heroes Phantasia English 0.1.61.iso"
```

To upgrade from the published 0.1.50 image:

```text
xdelta3 -d -s "Heroes Phantasia English 0.1.50.iso" Heroes-Phantasia-English-0.1.50-to-0.1.61.xdelta "Heroes Phantasia English 0.1.61.iso"
```

Both patches produce the same release image. The upgrade requires the exact published 0.1.50 image; local test builds are not supported upgrade inputs.

Original Japanese ISO: **1,415,020,544 bytes**; SHA-256 `2c3583f377cdaa9132d349a0039d7f6ffe21cac093476c7746705e8af2b03b40`.

Published 0.1.50 upgrade source: **2,647,455,744 bytes**; SHA-256 `fa420a494942817a7498615716b8b43bbc5ff4a817abb3cdb4354a90e89df8b8`.

Release output: **2,868,887,552 bytes**; SHA-256 `154eba01e36a83d9dac00ae8f5d93d8473e7c5310a398b7942a83c68f2fc5674`.

Exact source, target and patch hashes are in `BUILD-MANIFEST.json`. `VALIDATION.json` records both complete patch round trips, and `SHA256SUMS.txt` covers the downloads.

### What changed since v0.1.50

* **Dialogue fit:** Reflows 4,606 indexed references using the maximum width across the complete dialogue block, followed by 239 name-dependent reflows. Corrects the reported HOLD soldier boxes, Shinobu thought, Mitch spear question and Ryudock dialogue in both protagonist branches. Preserves words, substitutions and authored speaker anchors; long blocks gain page breaks where needed.
* **Bubble drawing:** Corrects raster-rounded tail fan selection and enforces native corner-height limits for short bubbles. Adds a mandatory corpus guard that rejects new modeled overflow and changed unreviewed inputs. Existing scoped speaker landmarks remain in use.
* **Elevator notices:** Repairs the missing Latin-font route implicated by the 0.1.52 crash, covering both native notice font sizes. Installed renderer checks pass; natural elevator interaction still needs playtesting.
* **Pronunciation and spacing:** Removes 615 duplicate English pronunciation readings, including the extra Ryuho above Ryuho. Adds the missing space before the highlighted Gift in both Ryudock teleportation branches.
* **Party, Brave and Equip:** Translates shared party labels/help, result notices including Chain Action, 31 shared image labels, 99 move/weapon names, 31 world-map locations and ten related menu/help strings. Uses compact Bond Stone names in the narrow equipment list.
* **Story and field text:** Repairs protagonist profile layouts, Kogoro's introduction and Gourry's Sword of Light line. Translates three quest chapter headings, four remaining numeric Kogoro labels, the HQ hidden-file discovery and the World Map Party Menu unlock notice.
* **Title:** Displays **0.1.61** above the project credit.

Retains the previous English dialogue, gallery, prologue, battle bitmap labels, location banners, 4x variable-width Latin font, protagonist defaults and reviewed bubble fixes. See the [changelog](https://github.com/retro-trans/Heroes-Phantasia/blob/main/CHANGELOG.md) for the intervening local builds.

### Release status

**This is a work-in-progress translation. Further proofreading and full gameplay testing are needed.** Patch verification establishes that both patches reproduce the reviewed image; it does not certify every scene, emulator or hardware route.

The final 0.1.61 checks pass 3,840 notice instruction cases, 45 installed native notice cases, 84 installed native geometry cases, nested asset readback and fresh startup/title review. The inherited 0.1.60 geometry checks pass 1,443 cases. These exercise the installed helpers and geometry; they are not a natural playthrough of the reported scenes.

The current corpus guard models 29,718 fitting English references and retains **91 name-layout risks and 127 unsupported layouts**. Animated intermediate poses, transformed bubbles, remaining pronunciation readings and full-game routes need review. Natural HQ/elevator scene playback remains unverified. Other image-based text and movies remain outside confirmed translated coverage.

**Boot the patched ISO fresh and load a normal save.** Older emulator save states can restore old text, fonts, coordinates and movie data.

### What's included

English for supported dialogue, battle/skit and gallery containers; executable/menu/help labels; save-point, tutorial, quest, Camp, Shop, Party, Brave, Equip and world-map UI; translated prologue movie; readable shared battle bitmap labels, including **DEF** for Defense; all 30 identified dungeon-entry name images; supported custom English bubbles with unequal side slopes, outlined tails and reviewed native speaker anchors; a 4x variable-width Latin font; English protagonist defaults, including Restore Defaults; and the current title version stamp. Custom player input is retained.

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
