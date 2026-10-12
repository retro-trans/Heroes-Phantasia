# Translation workflow

The checked-in `work/translation/en/*.en.json` files contain English targets, stable IDs, resource paths and review notes. Japanese script text remains in ignored local working files. Short UI terms and researched Japanese names may appear in glossary data.

## Extract and compare locally

Use Python 3.12 or later and install `requirements.txt`. Inspect your own Japanese ISO with `tools/inspect_iso.py`. Its read-only default lists files; `--write --extract PSP_GAME/USRDIR/HP.CPK` extracts the selected archive beneath ignored `work/source/`. Inspect the archive with `tools/unpack_cpk.py`; read the tool's argument help before extracting resources.

`tools/extract_corpus.py` reads the locally prepared original archive inventory and validated text containers. Preview its sample before `--write`. It creates Japanese-bearing working batches under `work/translation/en/`, retaining prior targets by stable ID. Executable labels, glyph-index labels, image text and movies have separate preparation tools; the primary corpus does not cover them.

Read each row's adjacent dialogue and review notes before editing. Use `work/glossary/glossary.json` and its source records for names. Preserve every control token and its arguments. Keep a row-for-row mapping; complete the English meaning before making a display abbreviation. Record anything the scene does not settle.

## Export public English text

```text
python tools/strip_jp.py work/translation/en/batch_0001.json
python tools/strip_jp.py work/translation/en/batch_0001.json --write
```

The first command previews the export; the second writes `batch_0001.en.json`. Never commit the Japanese-bearing working file. Review metadata and glossary terms may require separate English-only exports.

## Build and verify

Advanced builders require original assets, native analysis evidence, previous local candidates and scoped preparation reports. The repository does not distribute those inputs. Read [TOOLS.md](TOOLS.md) and each tool's source/docstring; do not expect an English-only batch to reproduce the full release by itself.

`tools/rebuild_dialogue.py` rebuilds validated dialogue containers with relocated English text rather than a fixed source-byte budget. Other formats have separate builders. Native rendering limits, loaded font capacity, authored animation tracks and player-name storage limits still apply.

Use `tools/build_local.py` for every new local ISO so the title version matches the build manifest. Omit `--write` first and review the planned changes. Run the applicable verifier after writing, then boot fresh in an isolated emulator for the affected scene. Static bounds checks and archive readbacks do not establish full-game visual coverage.

The [release guide](RETRO_TRANS_RELEASES.md) describes publication and the canonical patch format. Public builds need a new version whenever their bytes change; never replace a published patch with different bytes.
