# Field UI installation — 0.1.28

The reported screens used original executable menu tables despite earlier English drafts. This build relocates 44 complete labels, descriptions and action prompts, then retargets their typed pointers. Party, Catalog and Tutorial categories are included. All eight Options rows, their values, the Volume helper and Talk are included. Other contextual actions are Jump, Inspect, Push and Warp.

Long option drafts retain their full canonical glossary terms. The displayed variants are SFX/Voice Volume, Default Defense Turn, Allies, Enemies and Distant. Their widths use the current unscaled Latin advances, not Japanese character spacing. Existing controls and input behavior are retained.

The Episode 1 modal comes from an inline event script rather than the executable's separate episode-selection title table. Inserting longer text directly would shift following script instructions. The patch therefore compares the entire original 36-byte payload, including its NUL, at the common styled parser. An exact match selects the complete 48-byte English payload: Episode 1 / The First Investigation Request. Different payloads retain their original pointer. The event archive remains byte-identical. Style/alignment selectors, newline/end controls and the native cursor/reset/allocation behavior are preserved.

The patch adds 740 loaded bytes and six relocation records. Three section-driven loader models preserve all inherited memory apart from 44 pointer words and one parser-entry jump. Each model executes 73 exact/mismatched/truncated/null cases against the emitted instructions. Installed ISO readback matches the candidate executable. Only the versioned title changes in the archive; the other 5,185 archive rows and the English prologue are retained.

Native captures show the correct title stamp, five English main-menu labels and all shared Options labels. Default-to-Allies selection and restoration work. System-save creation succeeds. A temporary native parser object also passes exact-match, English-fallback and null-pointer tests, restoring all test registers and stack bytes afterward.

The banner test does not establish natural Episode 1 interception. Party, Catalog, Tutorial and Talk appearance in the guild scene also remain unverified. Existing speech-bubble tail geometry, other untranslated image banners and full-game QA remain outside this change.

Evidence and the player's original screenshots are in `work/ui/field/0.1.28/`; title captures are in `work/ui/title/0.1.28/`. The source-bearing working queue is ignored locally; its English-only export is `work/translation/en/executable_field_ui_0001.en.json`. Build preparation is `tools/field_ui_patch.py`, and final builds use `tools/build_local.py`.
