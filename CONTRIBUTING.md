# Contributing

Report the release version, emulator/version, scene and steps to reproduce a bug. A screenshot helps with text overflow or a misplaced speech-bubble tail. Boot the ISO fresh and load a normal save before testing; old save states can restore earlier data.

For translation changes, identify the row ID and resource, compare the source locally, and read the surrounding scene. Preserve control arguments, placeholders and row boundaries. Use researched glossary spellings. Record uncertain interpretations and the checks performed; do not mark a static fit check as an in-game result.

Do not commit Japanese script dumps, game binaries, extracted assets, original fonts, screenshots, saves, memory dumps, private paths or credentials. Japanese names and short UI terms are allowed. Export working translations through `tools/strip_jp.py`; commit only the `*.en.json` copies.

Preview every data-changing script before `--write`. The current tools are analysis and development workflows, with local inputs documented in their source; a clean checkout is not a complete release rebuild. New local builds use a fresh version and `tools/build_local.py`, with a changelog entry. Publishing a GitHub release requires the project lead's explicit request.

See [the translation guide](docs/TRANSLATING.md) and [tool guide](docs/TOOLS.md). The project also welcomes reports in the [Retro Trans community](https://discord.gg/MssepShjmB).
