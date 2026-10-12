# Lina dialogue and battle command repairs — 0.1.48 / 0.1.49

The supplied Lina screenshot shows native fallback measurement: the English
`hero` pronunciation annotation was outside the old exact `Hideo` signature.
Both the width hook and English bubble scanner now accept a nonempty printable
ASCII reading with preserved span digit 2. All probes stay inside the original
1024-byte bound. Empty, malformed, unterminated, native-glyph and control-bearing
annotations retain fallback. The handlers replace their original 140-byte slots;
other instructions, relocation records and loaded program extents remain exact.

The introduction at reference 0 in `phase/bin/p101110.bin` and `p101111.bin` is
rewrapped without changing any words or nonline controls. The first four-line
candidate cannot fit the authored ray and is rejected after native execution.
The replacement six-line body advances are 133, 75, 86, 105, 113 and 146 native
pixels. The small pronunciation annotation is
excluded from body measurement. Original portrait/bubble tracks, other rows,
speaker name and authored tail anchor/ray are preserved. This does not introduce
automatic mouth tracking or certify all scenes.

Native menu table 0 entries 55–62 now select Commands, Breakthrough, Declare
Victory, End Turn, Force a Breakthrough, Skip, Allies and Enemies. The other
Commands help-heading occurrence already selected English. All selected slots
retain their original unique R_MIPS_32 owners. Targets use only unconsumed spans
of the previously audited retired menu/notification storage; current typed
references are checked before allocation. Existing field-label targets and
notice dispatch helpers remain exact.

The R Commands plate extends left by 24 native pixels, keeping its right edge
and gauge fixed. The two action cards occupy x200–328 and x336–472 with an
eight-pixel gap; buttons, text and cost positions are aligned to their respective
cards. The separate Force a Breakthrough/Skip mode plate extends left by 96
pixels, preserving its right edge. Its native tiling helper has exactly two
direct callers, both in that command-mode branch. Full wording fits the existing
VWF advances; numeric costs, selection logic and battle effects are unchanged.

Preparation: `tools/prepare_dialogue_commands_048.py`, dry by default, then
hash-guarded fresh writing; `tools/prepare_lina_reflow_049.py` installs the
native-tested replacement. Build: `tools/build_dialogue_commands_049.ps1` calls
the authoritative `tools/build_local.py`. English-only UI export:
`work/translation/en/dialogue_commands_048.en.json`.

The six-line preparation case passes native sloping-interior, viewport, tail
ray/endpoint/outline, repeat-draw, vertex-count and text/fan setup checks. Tail
reach is 23.24 pixels with a 16-pixel base and a 33.27-degree pointed angle.
These measurements are synthetic native execution, not a natural story capture.

Final installed validation passes in 0.1.49: all 224 native bubble regression
cases, including both six-line Lina resources; 21 emitted measurement cases;
10 bounded scanner cases; three load-base models; all eight new command targets,
28 inherited field labels and 12 complete inherited notice keys/targets in live
memory. Registers, borrowed stack/manager memory and owned breakpoints are
restored after synthetic native tests.

Fresh isolated startup reaches the opening movie, English title and main menu.
The 0.1.49 stamp above the credit is reviewed in both final captures. Scoped
nested-ISO readbacks match the prepared executable, title and both dialogue
resources; 5,183 other archive rows remain exact relative to 0.1.47, including
the original headquarters event. Complete archive/ISO spans and hashes are
verified by the authoritative builder. Font, battle bitmap improvements and
English prologue are carried forward.

Final evidence: `work/ui/dialogue/0.1.49/validation.en.json`,
`native_geometry.en.json`, `loaded_strings.en.json`, and
`work/ui/title/0.1.49`. The checks use the installed executable and synthetic
associated windows; natural playback of Lina and the command-menu screens,
actual battle effects and full-game coverage remain unverified. No release is
authorized for this build.
