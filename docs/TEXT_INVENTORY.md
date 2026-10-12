# Japanese text inventory and progress — 0.1.29

Verified structured resources contain **31,003 Japanese-bearing record occurrences** and **16,568 distinct Japanese-bearing records** to translate. The executable contributes another **666 heuristic candidates**, counted separately. Another 17 supplemental setup records are queued separately (17 Japanese-bearing, 0 non-Japanese); they do not increase the headline pending executable-pool overlap reconciliation. This is a lower bound, not a complete on-screen text count.

| Category | Resource occurrences | Distinct records assigned to category |
| --- | ---: | ---: |
| battle dialogue | 770 | 611 |
| battle skits | 256 | 114 |
| field dialogue | 632 | 614 |
| dictionary | 135 | 135 |
| world lore | 49 | 49 |
| character profiles | 131 | 130 |
| main quest objectives | 30 | 30 |
| side quests | 16 | 16 |
| tutorials | 24 | 24 |
| field tutorials | 13 | 13 |
| menu tutorials | 22 | 22 |
| story dialogue | 28,415 | 14,516 |
| song titles | 57 | 57 |
| enemy names | 39 | 39 |
| map names | 26 | 26 |
| accessory descriptions | 36 | 9 |
| charm descriptions | 16 | 16 |
| charm effects | 16 | 16 |
| spirit effects | 62 | 62 |
| Glyph-index battle/system labels | 256 | 67 |
| Runtime-observed executable UI labels | 14 | 14 |

Tables contain 252 records (225 distinct); 12 are already English song titles in fullwidth characters, so they are excluded from the Japanese-bearing headline and queued for normalization.

Counts use validated table references, not raw string guesses. A record is one original dialogue reference, prose entry, or item/list entry; it can contain several lines or pages. Exact-byte duplicates share one English target while every original occurrence keeps its file, offset and references. Category assignment for shared records follows the first archive occurrence, so distinct category counts are exclusive rather than totals of every usage.

Japanese-character occurrences total 592,581; these count kana and CJK characters, including inline speaker names and ruby readings. They are not words and exclude digits, Latin text and most punctuation. Sorted font character maps and texture noise are excluded.

## Translation progress

18,137 English drafts are written across the queued categories; 99 queued records remain unfilled. The total queue of 18,236 includes the heuristic executable candidates, supplemental setup records and English-title normalization. Unfilled breakdown: 79 excluded technical candidates, 1 held Mao formatter record, 17 held staff-credit blocks, 2 held native-menu labels and 0 other records. These include excluded technical candidates and held formatter/staff records, rather than a count of confirmed untranslated player texts. See `translation_progress.en.json` for current per-category counts and statuses.

The glossary contains 936 entries across 15 files. Source-backed franchise spellings are distinguished from provisional game-original names. Unknown gender and traits remain explicit.

All drafts pass control-order, recognized numeric-argument (including fixed-width glossary-link and color arguments), percent-placeholder and Japanese-in-target checks. English-only `*.en.json` exports contain no Japanese script. Draft statuses remain provisional. 5 main-menu labels have separate cold-boot rendering evidence; dialogue drafts still require meaning review, complete-scene context, measured layout, ruby-span rebuilding and in-game testing.

## Remaining audit and build work

- Title credit candidate: 0.1.29; bottom-right version/credit display QA: True. New builds regenerate the stamp from build.json and require an incremented version. See TITLE_SCREEN.md.
- The 417 MB HP.DNS installer is PGD-encrypted; duplication with the main archive has not been established.
- btl/sys_tbl.bin contributes 256 decoded glyph-label occurrences and 67 distinct labels, with exact byte round trips. 37 match drafted executable sources and 67 match CPL entity-name sources. These are overlapping resource observations, not additional missing translations. This glyph-index resource's native visibility remains unproved; other glyph-index tables still need audit.
- Media audit sampled 10 movies / 77 frames and observed Japanese in 9 movies. Sampled observations do not establish an exhaustive text count. Current 0.1.29 installs 1 translated movie asset(s), with 17 primary prologue captions, 10 superseding fields and 1 moving sign(s). Other movie translations remain outside installation. It also installs 20 whole battle labels and 3 fragment groups, 14 copyright/notice records in 2 textures, and 3 external PSP metadata images. Installation/static pixel review is separate from runtime display proof; copyright and external PSP metadata display QA remain pending. These counts stay separate from the structured-text headline.
- Supplemental gallery labels: 25 records (7 generic UI labels, 11 franchise/season titles, 6 Knowledge categories and 1 Original category label). They remain separate from the confirmed Japanese-bearing headline pending overlap reconciliation. Current installation: 25 typed labels. Native gallery QA: False; status runtime_qa_pending. Scope: none. Evidence: None. Remaining limitations: ['Current native gallery display/layout proof pending.'].
- Broader typed-menu working queue: 154 drafts and 2 held records. Of the drafts, 26 source labels are installed through the current field UI patch, including compact display variants. Other drafts remain uninstalled; broader native visibility and consumer routes remain unproved. They are separate from the structured Japanese-bearing headline.
- Current field UI patch: 48 relocated labels/help/action prompts and 1 guarded episode-banner replacement. Shared Options display QA: False. Other field screens verified: False. Natural Episode 1 interception verified: False. Evidence: work\ui\field\0.1.29\validation.en.json. The 45 supplemental queue records overlap earlier source drafts and do not add to the distinct Japanese-bearing headline.
- Supplemental battle HUD labels: 1 typed executable record(s); 1 installed Special Move label, displayed as Special. The inherited unscaled ASCII advances measure Special at47px and the full term at86px within a55px region; only the abbreviation fits. Static proof: work\ui\battle\0.1.26\special_label\validation.en.json. Native battle appearance remains unverified. This record stays separate from the structured-text headline.
- Dungeon-name image banners: 30 separate native texture observations; 1 English bitmap installed and 29 other banner assets pending. Forest of Encounters uses the existing glossary spelling and 4x lettering rasterization within its unchanged 256x32 allocation. Static installation proof: work\ui\map_banners\0.1.25\validation.en.json. Native banner display/UV remain unverified. These image observations stay outside the structured-text headline; 26 encoded map-name records do not cover these separate images.
- Current native prologue/media QA: False; status runtime_qa_pending. Scope: none. Evidence: None. Remaining limitations: ['Current native prologue/media display proof pending.']. PC decoding and prepared timing do not establish PSP playback or full-movie readability.
- Executable scanning deliberately omits some ASCII/numeric runtime fragments; those must be preserved and accounted for when rebuilding prompts. Installed executable scopes and supplemental cast-bank integration are recorded in the current build manifest; broader consumer and runtime expansion coverage remains unproved.
- Title/main-menu screenshots and framebuffer metadata are captured. Measure additional dialogue boxes, line counts and runtime name expansions. Original byte slots are not the English text budget; relocation is required.
- All 420 extracted gallery resources pass byte-identical identity rebuilding and original occurrence/hash checks. Historical 0.1.7 selected-prose display QA: 1 passed, covering one complete Red Shield target with six measured soft breaks in three scroll positions. Current wrapping audit: 419 drafts, 370 structurally prepared and 49 requiring additional handling at 330px / 45 glyphs using the historical 0.1.6 font metrics. This is the observed dictionary geometry; other layouts still require measurement. It does not certify current executable display or install the wrapping. See GALLERY_BUILD.md and VWF.md.
- Supplemental CPL battle resources: 1616 byte-string occurrences / 429 distinct queue records. The name-index0 selector is statically proved; later skill/action consumers and debug visibility remain unresolved. These counts stay separate from the Japanese headline until player-facing overlaps are reconciled.
- The 0.1.3 opening candidate cold-boots with all 96 supported Latin glyphs loaded in compact 64×64 source slots. Twelve hook sites and all loaded glyph pixels/lookup entries passed checks; 76 actual menu uploads/sprites verify the five labels. Earlier menu-only builds remain separate under work/output.
- Current 0.1.29 selected opening text: 0 records have scoped native display evidence; selected opening display QA: False, status runtime_qa_pending. Scope: none. This evidence does not certify broader dialogue or gameplay. Only matching version/ISO/executable/archive proofs contribute. Historical 0.1.6 separately verified 1 relocated record, both pages and speaker, with traced proportional draws. See DIALOGUE_BUILD.md and the version-specific opening proof for the latest scope.
- Current 0.1.29 setup display QA: False; status runtime_qa_pending. Scope: none. Setup fields use Latin defaults and resident 4x VWF; ASCII OSK limits remain subordinate to saved CP932 byte capacities. Remaining setup limitations: ['Current setup proof pending; broader runtime-name contexts also require verification.']. See SETUP_BUILD.md. Verified setup screens do not establish every later game-name expansion or cached-name context.
- Current 0.1.29 battle display QA: False; status runtime_qa_pending. Scope: none. Observations: {}. Display defects: []. Remaining limitations: ['Current battle proof pending; all-label visibility and broader battle coverage remain unverified.']. Encounter evidence does not establish visibility/readability of all installed atlas labels or full-game battle coverage.
- Historical0.1.23 battle follow-up: Selected first-encounter English dialogue, Monster HUD, Offense/Defense graphics and full reviewed100AP/combo/formation/exception panels fit. Encounter has not completed; root remains at the Cross-input hint. This does not pass the whole battle or every installed bitmap context. Evidence: work\ui\battle\0.1.23\validation.en.json. This is a separate previous-build observation and does not establish current encounter completion.
- Current 0.1.29 save display QA: False; system-save creation: False; status runtime_qa_pending. Scope: none. Remaining limitations: ['Current save proof pending.']. This is the historical creation observation; restart loading is reported separately below.
- Current 0.1.29 system-save restart loading: False; status runtime_qa_pending. Scope: none. Evidence: None. Remaining limitations: ['System-save restart proof pending.']. System-save proofs do not certify game-save creation/loading.
- The 0.1.4 geometry experiment failed movie AudioThread creation with NO_MEMORY. The 0.1.5 replacement saved 11,328 loaded bytes and cold-boots successfully, but its manager lookup left the native bubble unchanged. Version 0.1.6 corrects target-segment address relocation, embedded-array lookup and page-range validation. Scope remains stationary, unrotated centered control-light Latin pages. Wider scene/template/animation coverage still needs testing.
- Output is native 480×272. Historical 4× glyph-source observations cover menu, opening body/speaker and selected dictionary body draws; current setup/opening/battle/save proof scopes are stated separately above. Increased emulator internal resolution, complete font/measurement coverage, wrapping outside the selected gallery path, ruby, broader runtime-name expansions, both protagonist variants outside the reviewed setup, game-save/load/restart, broader battles and native hardware remain unverified. The supplied original ISO is unchanged; local candidates are separate and no release was created.

## Reproduce

Use tools/inspect_iso.py, tools/unpack_cpk.py, tools/decrypt_executable.ps1, tools/extract_corpus.py, tools/extract_tables.py and tools/scan_executable.py. tools/rebuild_gallery.py --audit-all reproduces the gallery identity/occurrence checks; tools/audit_translation_encoding.py audits draft serialization. Every writer has an explicit opt-in after dry-run review. Source data and translation working files stay ignored. Existing translation IDs/targets are retained when corpus extraction is rerun. Run tools/strip_jp.py on completed working batches before future commits. The folder currently has no project Git history; no commit or GitHub release was made.
