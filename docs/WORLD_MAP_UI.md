# World-map UI

Build 0.1.32 installs four text replacements and the separate HOLD Headquarters bitmap reported in the user's screenshots. The organization spelling follows `term_007` in the existing glossary.

| Element | English | Original pointer slot RVA | Native font advance | Reviewed available width |
| --- | --- | --- | --- | --- |
| Confirmation | Go to the World Map? | 0x95480 | 139px | 440px |
| Destination | HOLD Headquarters | 0x96AC0 | 129px | 208px |
| R-button footer | Zoom | 0x94A28 | 36px | 49px |
| Square-button footer | Camp Menu | 0x94A94 | 77px | 104px |

The confirmation retains its terminal 0E control. Each original string has one reviewed typed R32 owner. The installer retargets those existing pointers and places the complete strings in previously proved, excluded PNG tail regions; it adds no loaded bytes, changes no instruction and adds no relocation record. Unselected executable bytes, all relocation records and active font/image contracts are preserved. Three loader bases check the resulting pointers and all unselected loaded memory.

“Zoom In” is the existing full draft. Its 52px native advance exceeds the narrow region before the adjacent Menu control; the installed footer uses the action label “Zoom” at 36px. This local display wording does not rewrite unrelated translation rows.

The location banner is an image in `fld/dngn/d01.bin`; translating the map string alone cannot replace its lettering. Its full English lettering occupies x1–199, y1–27 in the unchanged 256x32 texture. The palette and nonpixel container bytes remain exact. See [MAP_BANNERS.md](MAP_BANNERS.md) for the separate image coverage.

Evidence is saved under `work/ui/world_map/0.1.32`, `work/ui/map_banners/0.1.32` and `work/ui/title/0.1.32`. The source screenshots are user-provided references with unknown build version, not current-build gameplay captures. Current runtime checks verify all four loaded pointers and complete target bytes. Cold startup, system-data load and the title/menu are observed; the version and credit pass a scoped pixel comparison. The builder verifies complete archive/ISO spans and hashes, and the scoped verifier rereads the selected nested executable and image assets.

The natural world-map/headquarters placement, destination text centering and banner UV coverage require current gameplay screenshots. This build does not establish full-game translation coverage or correct every speech-bubble tail.

Tools: `prepare_world_map_ui.py` (dry-run then guarded write), `check_world_map_loaded.py` (read-only native checks), `verify_world_map_build.py` (dry-run then reviewed evidence write). Use `build_local.py` for the versioned ISO and title stamp.
