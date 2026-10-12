# Save Points correction — 0.1.29

The reported clipped text came from the Field Tutorial panel's separate constructor, rather than the shared dialogue measurement hook. At module RVA `0x93D08`, it calculated `13 × glyph count` and stored half of that width in the row. The inherited VWF renderer already drew Latin with narrower advances, so its origin could fall off the left edge.

`tools/prepare_save_tutorial.py` appends a bounded width helper from `tools/field_tutorial_width.py` and redirects that calculation. The source cursor, row allocation, controls and reveal counts remain unchanged. ASCII/private Latin uses the existing integer advance table; valid native pairs retain 13px. Reviewed formatting arguments contribute no width. Unknown controls, runtime substitutions, ruby, malformed pairs and excessive probes retain the original calculation. The helper modifies only A0 and restores its temporary registers and stack.

| Save Points body | Native width | Centered left edge |
|---|---:|---:|
| Use this object to save your data. | 216px | 132px |
| It also restores HP and PP to their maximum values. | 338px | 71px |

The header is composed from the already translated Field and Tutorial table entries. Their shared origin is now x197, with a 36px Field-plus-space advance. It retains native y103 and the same rendering route.

The Save, Delete Data and Cancel labels use uniquely verified table0 pointers at indices 126, 127 and 16. The full system-data warning uses table1/index44. All targets are relocated without truncation; the notice preserves its three newline controls and terminal control. Its longest line measures 270px. Working targets are local; the exported English-only copy is `work/translation/en/executable_save_ui_0001.en.json`.

The frozen input is 0.1.28 executable SHA256 `c7435d60f2599991d279adba6147aa4f387f1839089692e0bf1d60533d305f17`. The new executable is `6c4f596036c0bc310cef44dbb326d9aa1511ebd0d3f388cf0d23b3ca3c2f5de7`. The patch adds 960 loaded bytes and four relocation records. All inherited LOAD1/LOAD2 bytes and unselected LOAD0 bytes remain exact under three section/program loader models. Each model executes 14 width, control, malformed-input and boundary cases.

Current native title/version/credit and main menu are reviewed. Five native width/ABI cases pass. `tools/show_save_tutorial_qa.py` invokes the game's existing load/show sequence for `menu/Gallery/tf/TfHelp000.bin`, bypassing only its unlock requirement in the disposable test session. Native captures show the complete Save Points panel heading and both sentences centered without clipping. The underlying Gallery page remains visible because this is a debugger-triggered panel, rather than a guild event. Natural guild arrival and the save menu/system warning still require gameplay review.

Versioned captures and coordinates are in `work/ui/field/0.1.29`; current title evidence is in `work/ui/title/0.1.29`. The English prologue and all 5,185 non-title archive records remain unchanged. The 4x source glyph bank and Latin protagonist defaults are retained. This build does not certify whole-game translation or resolve existing speech-bubble tail defects.
