# 0.1.61 local test build

Ryudock's teleportation line now has a space before the red Gift in
`phase/bin/p101110.bin` and `p101111.bin`, reference 11. The two complete
containers retain their authored tracks, bubble template and speaker endpoint.
Only one literal space is added; semantic controls and page breaks remain exact.

Two event notices are translated:

- HQ database discovery: “Shinobu found hidden files in the database!” The
  saved given-name selector remains dynamic. The first line is bounded at
  390 native units for the permitted 17-character name, and the second at 286.
- World Map unlock: “New Party Menu features have been unlocked.” Its two
  lines are bounded at 299 and 247 native units.

Both complete original event resources remain byte-for-byte unchanged. Their
styled payloads are mapped to complete English copies at the existing parser
entry. The discovery retains style 2, its name selector and one line break;
the unlock retains style 5 and adds one layout line break. No event command,
branch destination or source string length is rewritten.

The exact-match helper now uses a pointer table inside its already-owned
936-byte allocation. Original loaded extents and relocations are preserved;
new table pointers and code references receive typed loader relocations. The
font, bubble geometry and maximum-name exception fingerprints are unchanged.
Instruction tests cover every existing and new notice, null and empty inputs,
unrelated text, every one-byte mutation and every shortened source payload,
at three module bases. Only a complete match changes the parser's text cursor.

The new screenshots were identified as 0.1.58. Their name-width reflows are
already present in the 0.1.60 base:

| Dialogue | References, both branches | Maximum whole-owner width |
| --- | --- | --- |
| Mitch's spear question | p101140/p101141, 15 | 364 |
| Ryudock's first-battle challenge | p101140/p101141, 23 | 338 |
| Ryudock's combat-device explanation | p101150/p101151, 5 | 351 |

All six references pass the current model. Native QA for this build exercises
these pages and the two Gift references at every nonzero authored position key
and bounded owner width. This is a native helper/geometry regression check;
it does not substitute for a natural playthrough of those scenes.

Package readback, the mandatory corpus guard, installed native checks and a
fresh title-screen capture are recorded under `work/ui/dialogue/0.1.61/`.
All 3,840 instruction-model cases, 45 installed notice cases and 84 installed
geometry cases pass. Readback checks both notices and Gift branches inside the
ISO; 5,183 unselected archive TOC rows remain exact. The fresh title capture
confirms 0.1.61 above the project credit.
The inherited 91 name-layout risks and 127 unsupported layouts remain explicit
limitations; this build does not claim that every dialogue in the game is safe.
Public release 0.1.61 was explicitly requested on 2026-10-13. The release uses
this exact reviewed ISO; packaging and publication evidence is recorded under
`docs/releases/0.1.61/`.

Published as `v0.1.61` with both patch round trips and all uploaded digests
verified. The public Retro Trans catalog includes the exact canonical manifest;
original and 0.1.50 direct routes and the 0.1.45 intermediate route pass.
