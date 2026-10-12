# Heroes Phantasia — English patch

English fan translation of the PSP game *Heroes Phantasia* (ULJS-00456). The patch is distributed as an xdelta file that you apply to your own Japanese disc image. This repository contains English translation text, researched glossaries, selected layout metadata and tools. Original script dumps, disc images, extracted artwork, fonts and memory dumps stay local.

## Applying the patch

Use the latest [Retro Trans](https://github.com/retro-trans/retro-trans-tools/releases/latest) for automatic patching:

1. Open **Automatic**, click **Refresh catalog**, and browse to your original Japanese ISO.
2. Select **Heroes Phantasia**, English edition.
3. Leave **Target** on **Latest**, choose a new output filename, and apply the patch. Retro Trans downloads the matching patch and verifies the result.

See the [release notes](https://github.com/retro-trans/Heroes-Phantasia/releases/latest) for included content and testing limits. Boot the result fresh and load a normal save; older emulator save states retain old text, fonts and coordinates.

For manual patching:

1. Dump your own Japanese disc to an ISO. The first release accepts this exact image:
   - `Heroes Phantasia (Japan).iso`, **1,415,020,544 bytes**
   - SHA-256 `2c3583f377cdaa9132d349a0039d7f6ffe21cac093476c7746705e8af2b03b40`
2. Download `Heroes-Phantasia-English-0.1.45.xdelta` from [Releases](https://github.com/retro-trans/Heroes-Phantasia/releases/latest).
3. Apply it with xdelta3 or [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher):

   ```text
   xdelta3 -d -s "Heroes Phantasia (Japan).iso" Heroes-Phantasia-English-0.1.45.xdelta "Heroes Phantasia English 0.1.45.iso"
   ```

4. Check the output against `BUILD-MANIFEST.json`, then boot it in PPSSPP. Version 0.1.45 produces **2,644,776,960 bytes**, SHA-256 `5a59a2c07b1de69cac94efcc0d1114d97b0a48c91c08de95d8a55460b6d4b4ac`.

The larger output contains appended translation resources. This first public release provides a full patch from the original Japanese ISO. Previous local candidates are not supported upgrade inputs.

## Check the translation

The English text is in [work/translation/en](work/translation/en), with context, decisions and review status. Compare it with Japanese extracted locally from your own disc. [The translation guide](docs/TRANSLATING.md) explains the extraction and review workflow. Japanese script text is excluded from Git; character names and short UI terms may appear in glossaries and identification code.

The local [changelog](CHANGELOG.md) records the development builds. Coverage counts describe specific resources and checks, not a whole-game completion percentage. This is a work in progress: human proofreading and full playtesting are still needed.

## Translate it

Fork the project to improve the English or work on another language. Start with [the translation guide](docs/TRANSLATING.md), [tool guide](docs/TOOLS.md) and [contribution guide](CONTRIBUTING.md).

Use researched names from [work/glossary](work/glossary), retain every row and control token, and preview each script before writing. Public `*.en.json` files contain English and review metadata. Working files with Japanese source remain local; `tools/strip_jp.py` creates the safe exports.

The advanced font, archive and ISO builders depend on extracted original resources, native-analysis evidence and versioned local preparation inputs. This repository is not a one-command rebuild from a clean checkout. Those inputs are deliberately excluded; read each tool's requirements before running it. Build new local versions with `tools/build_local.py` so the title stamp and manifest agree.

## Repository layout

- `docs/` — translation/tool guides, format notes, review evidence and release metadata
- `tools/` — extraction, validation, archive, font, bitmap and local-build tools
- `work/glossary/` — researched names and UI terminology, with sources
- `work/translation/en/` — English-only translation batches and UI tables
- `work/ui/` — selected English layout and validation metadata; screenshots remain local
- `work/output/` — ignored local builds and release packages
- `incoming/` — ignored external files for local review

## Credits

| Role | Contributors |
| --- | --- |
| Project lead and testing | [binhlt0402](https://github.com/binhlt0402) |
| Translation and implementation assistance | OpenAI Codex |
| Patch application and release packaging | [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools) |

Translation drafts were produced with large language models and reviewed using scene context and a researched glossary. Review notes retain uncertainties. Bug reports, proofreading and playtesting are welcome in [Issues](https://github.com/retro-trans/Heroes-Phantasia/issues) and the [Retro Trans community](https://discord.gg/MssepShjmB).

## License

Translation text and project tools: [MIT](LICENSE). The game and its assets belong to their respective rights holders. This license does not cover the game, original artwork, music, fonts or third-party software. Bring your own disc image.
