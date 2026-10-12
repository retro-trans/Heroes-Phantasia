# Opening bubble layout audit — 0.1.6

## 0.1.6 scoped runtime result

Both pages of the selected English opening record now fit the resized bubble. The complete body/name sequences, loaded executable, exact rebuilt record and inspected capture hashes are tied together in `work/ui/runtime/association_candidate_opening_validation.en.json`. The five main-menu labels retain their separate verification. One English dialogue record passes display QA; this is a selected-record experiment rather than a full-game layout result.

Original manager address pairs target LOAD1, whose module offset 47AF58 must be included. Correct module-relative flag/manager addresses are 166F2C4/166F2C8; count is manager+24 and its pointer array is embedded at manager+28. Container+18 is overwritten with the first page's line count. The corrected hook derives the complete control-light line count from body bytes before validating start+visible, so both pages are accepted. Earlier defaults remain reproducible.

Live probes observe scale 1.402326 and center X=348.595276, with geometry bounds approximately 211.1673–472. English body origins are [255,168]/[255,190], speaker origin [283,142], and source glyphs remain 64×64 drawn into 16×16 rectangles. Outline and both fill banks match the static model within 0.0001; Y coordinates remain unchanged. After advancing, the same window selects native template 68 and restores all three banks exactly. Its center X=375 is corroborated by the earlier unresized Japanese trace, and its original renderer/13px advances remain intact.

The hook stretches tails horizontally. Other templates, moving/scaled/rotated windows, wrapping, ruby, expanded runtime names and general scene coverage remain unverified. These results do not establish increased emulator internal resolution.

## 0.1.5 compact candidate

The 0.1.4 ISO passed embedded-resource checks and reached the load dialog, but movie AudioThread creation returned `0x80020190` (`SCE_KERNEL_ERROR_NO_MEMORY`). The dormant worker prevented its queued timestamps from advancing; synchronization returned status4 and skipped frame presentation. The observed call at module1253F4 stores its failure at the audio object's first word. Extra loaded memory is the likely cause; the bubble hook did not receive display QA.

The replacement 0.1.5 uses identical overlapping 256-byte swizzled tile runs, with a 16-bit lookup in 256-byte units. Every complete 64×64 glyph source region still matches the earlier bank exactly. The bank shrinks from196608 to188928 bytes. Bounds shared across the four line capacities shrink the catalog from7296 to3648 bytes, preserving all608 float32 triples. Payload327356 is11328 bytes smaller than0.1.4 and2492 bytes smaller than working0.1.3. Independent pointer/bounds/lookup and60-relocation checks pass. Cold boot plays the movie and reaches the menu/dialogue. Both English pages still cross the native bubble borders because the manager lookup uses the wrong relocated address and an extra array dereference. Saved 0.1.5 evidence records failed layout; 0.1.6 corrects this association.

## 0.1.4 experiment

`tools/bubble_metrics.py` derives a centered usable interior from horizontal polygon intersections across actual 16px glyph bands and 22px line pitch. It validates 152 immutable templates, with catalog entries for 1–4 visible lines. Unsupported bands produce zero capacity rather than a guessed text budget. The 7,296-byte packed catalog has SHA256 `32b8f69e2d737ec36fa4da4a6608867115a8af64f31378b08bdc3771d2008c70`.

The candidate hooks `E4E0C` before geometry drawing. Native draw order is owner `DF90C` → `DF940` virtual geometry → `E4E0C` → `E52A4` callback → `DDFD0` → `F15F8` → `F167C` → text adapter. The window owner is +348; +324 is an animation accumulator. Pure lookup uses owner+98 context, context+30 key and owner+EC record key against the initialized manager at module 11F4370 (+24 count/+28 pointer array), matching container+8/+0C. It does not call the drawing lookup routine.

Container +18 is the total initialized line count, +1C the visible page line count and +20 its start index. The hook validates the active range and uses the visible count to select capacity. It restores original XY banks before each decision and then scales X only for a validated control-light Latin record with zero rotation and unit animation scale. Widths beyond the screen remain unsupported; no text is shrunk or dropped. Window +2D0.x clamp moves geometry, body and speaker together. Original text/speaker offsets and Y coordinates remain intact. Horizontal stretching also stretches tails; exact tail shape and world-target preservation are not verified.

For shape79 and two visible lines, the static usable halfwidth is 71.67px. Fitting 185px text with 8px padding per side requires a 1.4023× horizontal stretch. Full-bank bounds are -98..88px, so center369 shifts to348.60 to keep bounds211.17..472.00px. These are model predictions, not runtime observations. The 0.1.4 candidate requires cold-boot and actual page/fallback tests before its layout can pass QA.

## Observed 0.1.3 failure

The English glyphs render, but the fixed opening bubble is too narrow and the text begins at its angled left edge. The four measured line advances are 135, 35, 91 and 185px. Current centering uses a global half-width of 92.5px and places both pages at x=276, y=168/190. The visually estimated original bubble bounds are [276,157,180,59]; these are not measured clipping limits. Changing text half-width updates placement without changing the fixed polygon. No geometry resize is implemented in 0.1.3.

All addresses below are module-relative offsets in the audited decrypted executable. Runtime pointers are observations from the isolated test and must not become hardcoded patch addresses.

| Path | Observed role |
| --- | --- |
| `ED20C` / `ED15C` | Dialogue line construction and the candidate measurement hook. Line objects have stride E8; line half-width is +20 and container maximum half-width is +2C. |
| `ED990`, `EDB60`–`EDB78` | Per-frame body layout. For the observed alignment, subtracts container half-width from incoming x center, then truncates to the integer origin. |
| `ECE34` | Window/text adapter. Combines window translation +2D0 and text offset +30C/+310; alignment -1 ignores the text x offset. |
| `F15F8` / `F167C` | Associates text-manager objects with window metadata and calls the adapter. This is a possible association point for a future measured-width geometry change; no hook is installed here. |
| `E52DC` | Copies a fixed shape template from module 45E2C8, stride 1EC. Template +4/+6 provides text offsets; +8/+A provides speaker offsets. Two XY arrays at +0C/+FC become window +F0/+1E0; an outline also populates the window start. Shape ID is window +318. |
| `E4E0C`, `E4F18`, `E50CC` | Polygon rendering. Outline XY loads at E4F18/E4F1C and fill XY loads at E50CC/E50D0 are followed by rotation, uniform scale +2F0 and translation +2D0. A horizontal-only resize would need to cover outline and both fill arrays consistently. |
| `EBC08`, `EBFF8`, `EC040`, `EC04C` | Separate direct speaker path. The candidate routes Latin to EA45C and uses glyph advances for both its cursor and accumulated bar width. Resource/control speaker paths remain unhooked. |

The observed opening window uses shape 79, translation x=369/y=186 and text offset x=-65/y=-18. Its polygon x bounds are approximately -95..86 before translation. The English container has four initialized lines; its maximum width spans both pages. The current sample contains fewer than the 45-glyph reveal setting on each line. These facts describe this record, not general line or screen budgets.

A future resize must associate the measured text with the correct window, preserve its vertical geometry and tail, account for asymmetric templates and speaker placement, and keep the whole result on screen. It must handle a long page as well as a short page and retain Japanese fallback. No automatic wrapping, template-selection policy, generalized screen clamping or safe horizontal-geometry hook has been verified. Full English sentences remain intact; source byte length is not the target text budget.
