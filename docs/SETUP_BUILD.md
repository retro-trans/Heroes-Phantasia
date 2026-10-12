# Setup and opening candidate 0.1.11

Version 0.1.11 fixes printable-ASCII conversion for setup initialization, restore and name-editor calls, extending the inherited Latin keyboard and proportional name-field drawing. Its executable preparation report is `work/output/0.1.11-setup-assets/setup_patch.en.json`; executable SHA256 is `d53dce4ae053ed04fb3701b80434ba47adfa12a4561253d12c7ba7b93f0828ee`. The preparation report retains its original runtime-unverified status; the separate live checks below establish the reviewed setup scope. The saved evidence record is [setup validation](../work/ui/setup/0.1.11/validation.en.json), matching the current manifest's version and ISO/executable/archive hashes.

The 0.1.10 candidate displayed the title, menu and all six opening records successfully, but its name converter initialized an empty editor; finishing that editor erased the surname. It is superseded by 0.1.11. Earlier captures do not certify this changed executable.

## Setup text and defaults

The setup labels are Gender, Surname, Given Name, Title, Restore Defaults, Confirm, Male, Female and Play Voice. The restore prompt reads “Restore the default surname, given name, and title.” followed by “Are you sure?” Start and discard confirmations preserve their complete actions.

| Selection | Surname | Given name | Title |
| --- | --- | --- | --- |
| Male | Watari | Eiji | S.I.R. Ace |
| Female | Fudo | Shinobu | S.I.R. Ace |

Field order remains surname then given name; English full names are Eiji Watari and Shinobu Fudo. Their readings and genders are researched, while the established Latin spellings remain project romanizations. S.I.R. Ace is the descriptive English default epithet; personal nicknames are unknown. The relocated OSK description/default table deliberately synchronizes its fallback title with the setup title, including the space in S.I.R. Ace. The sixth unrelated OSK record remains unchanged.

## Keyboard and rendering

The OSK input mask changes from `0xDB00` to `0xDB0F`, adding Latin uppercase, lowercase, digits and symbols while retaining Japanese input bits and the original Japanese language setting. Keyboard descriptions are in English. The invalid-input messages now read “The name could not be accepted.” and “Enter a name within the allowed length.”

| Field | OSK character limit | Persistent CP932 capacity, including NUL |
| --- | ---: | ---: |
| Surname | 9 | 10 bytes |
| Given name | 17 | 18 bytes |
| Title | 25 | 26 bytes |

These character limits are subordinate to the unchanged CP932 byte-capacity checks. Nine ASCII surname characters occupy nine bytes plus the terminator; multibyte input can reach the byte limit sooner. The independent temporary OSK output buffer is 128 UTF-16 bytes; it does not enlarge saved-name storage. The unrelated sixth keyboard limit remains 15 characters.

The 0.1.11 converter bypass handles each printable ASCII character (32–126) at the conversion-table lookups only for setup callers. Independent code review confirmed retained native Japanese conversion, character counting, NUL handling and capacity checks. This scope does not establish conversion behavior in every other game caller.

Setup fields use the inherited resident Latin VWF bank rasterized at 4× source resolution. Added field advances and surname-width measurement account for proportional Latin glyphs, retaining native 13px advances for valid two-byte CP932 glyphs. Two resident-font player-name callers also route Latin glyphs through that bank. Japanese cache paths are retained. Long custom-name layout, subsequent runtime substitutions and other cached-name callers still require live verification.

## Opening dialogue

The archive prepared under `work/output/0.1.9-setup-assets/` contains all six translated rows of `fld/talk/f101010.bin`, with their control sequences and row boundaries preserved. Complete-scene meaning review passed: Keroro's confusion, location question and missing dimensional monster, “Still...”, observation that nobody is around, croaking cry, and two startled monster questions. Rows 0, 2 and 4 intentionally remain non-clausal or unfinished. The shared “Still...” transition was also checked in both complete protagonist variants, where it leads into a question about arriving in this world.

The English-only source review is `work/ui/setup/0.1.9/meaning_review.en.json`: 150 complete row views, including 80 executable rows and 70 original dialogue references, plus four omitted raw default-name components. This establishes meaning, not display or voice validation.

All six records and eight English pages passed fresh actual display review in 0.1.11: native speaker/body text fits the bubble shapes and screen. The saved [opening validation](../work/ui/opening/0.1.11/validation.en.json) matches the current manifest's version and ISO/executable/archive hashes. The earlier 0.1.10 pass remains historical evidence. This scoped opening pass does not certify other dialogue scenes, wrapping, ruby or later runtime-name expansions.

## Reviewed 0.1.11 setup scope

Live review passed the white gender header and both Latin default selections: Watari / Eiji and Fudo / Shinobu, with S.I.R. Ace. All three female OSK fields initialize with English descriptions and their current defaults; finishing unchanged retains those values. Male surname initialization and unchanged completion retain Watari.

A custom nine-character ASCII surname, Wataraaaa, was accepted and displayed; attempted additional OSK characters were blocked at nine. Restore Defaults returned that male custom surname to Watari. Editing the female given name from Shinobu to Shinob and then restoring reset all three fields to the female Latin defaults.

Cancellation was not verified. Mixed Japanese/Latin names, maximum-length given-name/title layout, later cached-name contexts and broader runtime substitutions remain unverified. These observations do not establish native-hardware or full-game compatibility.

## Preparation and packaging

`python tools/setup_osk_patch.py` prepares the historical 0.1.10 keyboard patch from the hash-checked 0.1.9 input; `python tools/setup_converter_patch.py` previews the 0.1.11 converter extension. Inspect the report before adding `--write`; fresh-version output protection prevents overwriting existing assets. Do not rerun a written version as a new build. Package through `tools/build_local.py` as documented in [TITLE_SCREEN.md](TITLE_SCREEN.md), supplying the matching executable preparation report whenever a custom executable is selected. The six-row archive also has its preparation report at `work/output/0.1.9-setup-assets/opening.en.json`.

The preparation report records preserved inherited font payload and relocation prefix. Static preparation checks and the scoped live checks have separate evidence: only the observed setup fields, edits, unchanged completions, surname boundary and restores above are established. Remaining layout, cancellation and game-name-context checks require further runtime review.
