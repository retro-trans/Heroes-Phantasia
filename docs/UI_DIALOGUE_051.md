# 0.1.51: profile cards, battle dialogue and party/result UI

This local candidate repairs the six screenshots reported against public 0.1.50. It is based on the frozen 0.1.50 executable and archive and built through `tools/build_local.py`, with the 0.1.51 title stamp. No release has been requested for this build.

## Changes

- Both `p101020` and `p101021` profile sequences: surname, given name and age occupy separate lines; the introduction and assistant description use short native pages. Existing tailless styles retain the asymmetrical sides. The main description keeps its original width; the name cards select existing two/three-line styles. Runtime player-name and epithet substitutions remain intact. The name-entry, storage and Restore Defaults code is unchanged.
- Both scenes' Kogoro introduction: four shorter lines and support for the original Latin pronunciation span digit 3. Both bounded measurement and geometry scanners now recognize nonempty printable ASCII readings with decimal span digits 1–9. Empty, malformed, native-text and overlong readings retain the original fallback. His position keys, portrait tracks, shape, Japanese tail endpoint and reverse ray remain exact.
- Gourry's Sword of Light result line: the complete sentence wraps into three lines in the authored jagged style. Both position keys move by the same `(20,-37)` offset so the expanded body fits the screen; the relative animation is preserved.
- Shared party labels: Cheer, Items, Brave, Members, Actions and Switch Menu. All six corresponding help records are translated. The small Menu heading is a separate shared image, replaced only within its reviewed 40×16 crop in the resident atlas; palette, dimensions, UV geometry and every outside pixel remain exact.
- Five adjacent battle-result messages: Overcharge-type selection unlock, Gourry's smithing improvement, new Chain Action, item acquisition and background-photo confirmation. The Chain Action notice in the screenshot uses a second native string table, distinct from the already translated field notification bank. Original style/selectors and result logic remain intact.

## Reproduction and checks

Preparation: `tools/prepare_ui_dialogue_051.py`, dry by default, then the guarded writer with the reviewed executable hash. Archive replacement uses `tools/append_cpk.py`; `tools/build_ui_dialogue_051.ps1` runs the current local builder. `tools/strip_jp.py` exports the changed working batches and UI queue as English-only files.

The preparation verifies 28 emitted measurement cases, 27 scanner cases, unique native string ownership and capacity, three relocated load bases, unchanged relocation records and program extents, and exact executable bytes outside the selected ranges. Scene checks preserve all unselected dialogue, nontext suffixes and tracks outside the scoped style/position edits. Font and PNG metadata validate, with zero loaded-memory growth.

`tools/verify_ui_dialogue_051.py` checks nine default-name profile/jagged fit records against the sloping white interiors and settled outline bounds, selected nested executable/archive assets, the generated title stamp and the complete unselected archive-row inventory. `tools/check_ui_dialogue_051_live.py` exercises the installed native geometry, including the earlier regressions and Kogoro's span-3 cases, and checks all 17 newly installed strings in memory. Evidence is stored in `work/ui/dialogue/0.1.51/`.

Natural playback of the reported story/profile/result scenes, all party-menu states and maximum-length custom names remains unverified. These are scoped fixes, not a claim that every dialogue style or scene automatically fits or tracks a speaker's mouth.

The final installed checks pass all 229 native geometry cases, including both span-3 Kogoro scene fixtures, preserved tail endpoints/rays, visible outlines, sloping text interiors and repeated draws. All 17 new party/result strings match memory. Nested executable and all five changed resources match the prepared assets; the other 5,181 archive rows are exact relative to 0.1.50. The nine profile/jagged models pass both text-band and settled screen-edge checks.

Final ISO SHA-256: `05e5f896457de3a30b2b0d610f65087b3347dfe6a034f8df90ec2f7c094d05c6`.

Fresh isolated startup reaches the English title screen. The displayed `v0.1.51` above `github.com/retro-trans` matches the generated title asset after native RGB5551 quantization; the reviewed frame and stamp comparison are recorded in `startup.en.json`.

Two preliminary profile-style candidates were retained privately as rejected preparation artifacts after edge checks found clipped outlines. The delivered candidate keeps the main description's original width and verifies every settled profile outline is inside the screen.
