# Tools and local inputs

Use Python 3.12+ with `requirements.txt`. Most scripts default to read-only or preview mode; inspect their help and sample before a write. Run development scripts from the repository root. Some historical builders are tied to specific versions and local evidence; their names and source describe their scope.

| Task | Tools | Inputs and limits |
| --- | --- | --- |
| Inspect/extract ISO | `inspect_iso.py` | Explicit original ISO path; selected extraction only |
| Inspect CPK | `unpack_cpk.py` | Original archive; CRILAYLA decoding included |
| Extract dialogue | `extract_corpus.py` | Local original archive/inventory; validated container families only |
| Export English | `strip_jp.py` | Local Japanese-bearing working batches; checks public fields for remaining Japanese |
| Glossary consistency | `build_glossary.py`, `normalize_glossary_names.py` | Researched source records and local batches; preserve context |
| Review controls | `dialogue_tokens.py`, `apply_targets.py` | Working source and English draft; do not drop arguments |
| Relocate dialogue | `rebuild_dialogue.py` | Original resources and translations; authored tracks preserved |
| Prepare font/executable | `build_menu_patch.py`, `compact_vwf_patch.py`, `bubble_layout_hooks.py` | Original decrypted executable, fonts, snapshots and reviewed native analysis |
| Prepare bitmaps | `prepare_battle_labels_045.py`, `prepare_map_banners_043.py` | Original or preceding local archive, font and native slot evidence |
| Append resources | `append_cpk.py` | Exact source hash and selected replacements |
| Build local ISO | `build_local.py` | Prior manifest, prepared assets and original ISO; version from `build.json` |
| Capture native frames | `capture_frame.py`, `ppsspp_debug.py` | Isolated software-renderer debugger and matching executable evidence |
| Package release | `package_release.py` | Verified local ISO, original ISO, source commit and pinned Retro Trans checkout |
| Audit public source | `audit_public_sources.py` | Git index; rejects game assets, local data and unsafe exports |

Original assets, bundled third-party tools, font files, Japanese dumps and emulator installations stay beneath ignored `work/source/` or `incoming/`. Install third-party tools separately according to their own licenses. Generated ISOs and canonical release assets are under ignored `work/output/`.

See the existing format notes in `docs/`, the [changelog](../CHANGELOG.md) and [translation guide](TRANSLATING.md). The old progress inventory is a scoped historical report, not a current completion percentage.
