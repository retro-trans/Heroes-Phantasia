# English speech bubbles

Version 0.1.33 introduces a custom body contour for standard English speech
bubbles. The existing native renderer still draws the outline, two fill banks,
speaker plate and variable-width text. Glyphs retain the existing 4x raster
source; the PSP display remains 480x272.

The body uses the measured English container width plus 10px padding on each
side. It provides 16px glyph height and the native 22px line pitch, grows upward
from the authored bottom, and extends downward only when the upper safe bound
prevents further upward growth. Body edges stay within (8,36)-(472,252).
Eight contour families retain ten vertices and the original winding. The
outline and both fill banks have separate preserved tail endpoints; resizing
and horizontal body clamping do not move those endpoints. The earlier reviewed
Princess Serish lip correction remains active for its exact shot.

The helper applies to 120 standard templates, stationary unit-scale unrotated
windows, one to four visible lines, and default centered rows (signed row
alignment -1). It accepts the reviewed Latin glyphs, decimal timing/style
controls, private Latin pairs and exact Hideo reading annotation. Other 32
templates, animated states, other alignments, unsupported substitutions,
malformed controls and overwide bodies restore native geometry and offsets.
This is not automatic portrait-mouth tracking. A tail needs a reviewed scene
landmark before its authored endpoint can safely be changed.

`tools/english_word_wrap.py` proposes word boundaries without splitting control
arguments, changing words or changing non-line controls. Wrapping is performed
offline and reviewed before installation. This build reflows only Kogoro's
reported line in `p101040` and `p101041`, at advances 111, 132 and 95px. Its
highlight and timing remain intact. The small Kogoro speaker has no linked
portrait or confirmed lip landmark; its authored endpoint is preserved rather
than redirected toward the unrelated Cougar portrait.

Preparation uses `tools/prepare_english_bubbles.py` and
`tools/prepare_kogoro_layout.py`, both dry-run first. Code/data reuse the obsolete
geometry catalog and active helper span, adding zero loaded bytes. Twelve new
typed relocations replace seven obsolete records; the original relocation
prefix and unselected memory are checked at three load bases.

`tools/check_english_bubbles_live.py` exercises emitted instructions in an
isolated emulator. Its synthetic window cases verify all 120 contours, padding,
screen clamps, tail endpoints, alignment fallbacks and register/stack restoration.
Preparation evidence is separate from installed-ISO evidence. Captures and
validation records belong under `work/ui/dialogue/0.1.33`. Natural story captures
are identified explicitly; passing synthetic cases does not establish full-game
layout coverage.

Version 0.1.34 corrects body expansion around an authored tail anchor. The tail
endpoint comes from the source template and scene center, rather than the
fitted body center. Each fill-bank endpoint is preserved separately. If the
expanded body would enclose that endpoint, the helper fits the body on another
side of it, with viewport checks, and uses the corresponding contour family.
An impossible fit restores the authored center and native layout. The body can
therefore move without dragging the tip; changes to the authored scene position
continue to move the tip. Native tests cover positions beyond both screen edges.
This remains authored scene anchoring, not portrait mouth detection.

The visible-row scan starts from the current first row and reads each immutable
row source pointer. It no longer rejects later dialogue because a different
earlier text block has fewer lines. The fitting helper additionally validates
the native new-array header, allocation extent, visible range and default
centered alignment. Unsupported input still uses native geometry.

`tools/prepare_bubble_reflows_034.py` changes seven physical references in
`fld/talk/f101070.bin`, `phase/bin/p101040.bin` and `phase/bin/p101041.bin`.
Words, punctuation, highlights, delays and all non-line controls remain exact.
References 16 and 23 (small companion bubbles) and 27 (the fifth reference
example) remain byte-exact. Both reference-27 tips retain their authored world
positions. The English queues and their English-only exports reflect the wraps.

`tools/prepare_english_bubbles_v2.py` builds the emitted runtime code and compact
template descriptors. It uses zero additional loaded memory, removes ten
obsolete typed relocations and adds sixteen, and checks both loader views at
three bases. `tools/check_english_bubbles_v2_live.py` validates 157 native cases
against the installed 0.1.34 executable. `tools/verify_english_bubble_build_v2.py`
checks installed and nested resources, unchanged archive rows, reference text,
title captures and evidence identity. The eight portrait fixture cases use
audited scene centers, templates and the actual prepared dialogue bytes.

Evidence is in `work/ui/dialogue/0.1.34`. `layout_model.png` is a generated model
of native geometry results, not an in-game screenshot; it omits portraits,
nameplates and companion bubbles. Natural playback of the reported conversations
and full-game visual coverage remain unverified. The existing 0.1.33 tools and
evidence remain historical and are not rewritten.

Version 0.1.35 corrects the native fill topology. E4EBC..E5014 originally emits
a GU_TRIANGLE_FAN with vertex zero at the window center, followed by the outline
and its closing point. A fitted body can sit above that original center, or its
concave tail can make the center an invalid fan origin. A polygon-only preview
therefore missed triangles that the game fills outside the intended outline.

The helper now writes an absolute fan origin at point ten, outside the rendered
ten-point contour. It initializes that point to the native center before any
fallback, then uses the tail-base midpoint after fitting. The guarded fan loader
uses it only when the native count is ten; other counts retain the native center.
The native fan converts these coordinates by the same integer truncation used
for outline vertices. The body, scene center and source outline endpoint do not
move because of this fill correction. Both fitted border rails now terminate at
the outline endpoint; source miter offsets for an earlier tail direction are no
longer reused. The existing guarded Serish leaf keeps its reviewed offsets.

Preparation and checks use the v3 tools. `tools/audit_bubble_scenes_035.py` records
the actual English records and phase tracks for references 0, 1 and 4 in both
variants. `tools/check_english_bubbles_v3_live.py` runs 163 installed instruction
cases and compares triangle-fan area to the contour area, including native pixel
truncation. `tools/verify_bubble_fill_035.py` reproduces the old fill defect and
generates `work/ui/dialogue/0.1.35/fill_regression_model.png`; this is a triangle
model, not an in-game screenshot, and omits border texture, text and portraits.
The installed-byte/title checks use `tools/verify_english_bubble_build_v3.py`.

The optional injected draw modes are exploratory. Full native draw calls
completed, but their framebuffer captures did not establish visible bubbles;
a later injected probe timed out. Those captures are not visual validation.
The final title/menu checks use a fresh emulator session without injection.
Natural playback of the reported scenes and full-game visual coverage remain
unverified. Existing wording, control bytes, scene tracks, the 4x font and Latin
defaults remain unchanged from 0.1.34.

Version 0.1.37 keeps the original animation center at window+2D0/+2D4 intact.
The fitted text/body center is stored at unused point eleven (+58), with an
explicit selection marker at +5C. The contour compensates for the difference
between those centers, so the source outline endpoint remains in native scene
coordinates. ECE3C substitutes the fitted X only for selected custom windows;
the original native text setup otherwise continues unchanged. The nameplate's
relative X follows the body. Point ten still holds the absolute fan origin.
Repeated draws of an unchanged window must produce identical geometry.

The reported office and corridor resources preserve the original Japanese
animation, layer and channel bytes. Screenshot 3's contractor question and
screenshot 4's opening interview question are different records: their native
endpoints are (197,118) and (239.5,161), respectively. Keeping those authored
endpoints does not guarantee every tip lies exactly on the visible lips. The
existing reviewed Serish correction remains scoped to its earlier exact shot.
No new portrait landmark or automatic mouth tracking is introduced here.

The old name-control rejection explains the unfitted outline in the S.I.R.
introduction. Name selectors 0..3 now use the native conservative measurement
instead of rejecting the entire record. The English VWF's supported ASCII
advances are at most 12px, bounded by those native 13px units. Both physical
introduction records have three lines, with a space between the untouched
surname and given-name controls. The saved-name capacities remain 9 and 17
ASCII characters; the maximum expanded name line is conservatively 364px.
The logical translation is deduplicated in batch_0014 and exported with
strip_jp.export; both physical phase variants receive the same reflow.

When an enlarged body encloses a corner anchor, fitting first tries the vertical
side suggested by the authored tip, then the other vertical side, and finally
bounded horizontal alternatives. Unequal bevels (left 12, right 8, top 9,
bottom 13px) give the custom outline uneven edges. They are a new convex body
style, rather than an exact reproduction of each native template's sloping
sides. The 3px minimum vertical gap in 0.1.37 resolves the female introduction's
half-pixel placement miss in intermediate build 0.1.36.

The v5 tools install and validate 0.1.37. They reuse existing code/data spans
without loaded growth and preserve the original relocation prefix, font/image
contract and unselected memory at three load bases. All 174 installed native
cases test authored centers/endpoints, text setup, repeated draws, fan fill,
name-layout bounds and fallbacks. The actual title and main menu are reviewed.
Evidence is in work/ui/dialogue/0.1.37 and work/ui/title/0.1.37. The original
track audit and reflow evidence remain in work/ui/dialogue/0.1.36; the v4
candidate and 0.1.36 output are historical. Natural conversation playback,
actual custom-name/cache rendering and full-game visual coverage remain
unverified.

Version 0.1.38 replaces the rectangular body with fifteen native corner
patterns. Eight common body corners are recovered from the original sibling
tail sockets, using majority coordinates where socket miters differ slightly.
Horizontal and vertical growth stretches the spans between those corners;
their pixel insets and left/right side differences remain intact. The reported
gratitude shot uses shape 114: the right side changes X by 6px and the left
side by 10.5px, rather than remaining vertical. Tiny socket-specific variations
are not copied into the new common body.

Every fitted body retains all eight corners. Three additional points form its
one tail, giving eleven rendered vertices. The native E4E68 count hook selects
eleven only when the fitted marker equals one, preserving native counts on
fallback; its displaced E4E6C setup instruction runs inside the helper. No
helper allocation or loaded-memory growth is added. Existing native draw
buffers size themselves from that count. The absolute fan hub moves to unused
point twenty-nine (+E8/+EC), outside both original and fitted contours. Point
eleven still stores the fitted text X and marker, outside the eleven-point
fitted contour.

The tail base is projected onto the actual sloping side edge. The fan hub moves
1.5px inside that edge along the reverse tail ray, so shallow oblique tails
retain a valid visibility kernel after native integer truncation. A normal-only
hub offset and an edge-vertex hub were both rejected by the native fan checks.
The exact-shot Serish guard and reviewed lip remain; its leaf now obtains the
tip index from the selected side ledger, with both border rails sharing that
lip. All other tips retain their original Japanese scene endpoints.

A 44px allowance per horizontal half-span covers the largest native corner
inset (33.5px) and text padding. Geometry checks scan every visible glyph band
against the actual sloping white interior, rather than only its bounding box.
They also compare native side-corner differences, run the installed count and
fan setup hooks, check repeat draws, native text setup, shared tips and triangle
fan areas. Float fan comparisons allow 0.01 square-pixel doubled-area residuals
from separate float32 additions; the integer GE contour check stays exact.

The v6 tools prepare and validate 0.1.38, with 176 installed native cases,
including both physical gratitude-shot variants. The original authored tracks
remain exact, the archive changes only the versioned title from 0.1.37, and all
5,185 other archive rows remain exact. The 4x VWF, name inputs, translations and
prologue are inherited unchanged. Evidence resides in work/ui/dialogue/0.1.38
and work/ui/title/0.1.38. These are controlled associated-window instruction
checks and actual startup/title captures; natural playback of the reported
conversation and full-game visual coverage remain unverified.

One initial installed synthetic run stopped at its first tip check; an immediate
repeat passed. A fresh emulator process also passed all 176 cases with exactly
the same case evidence. No repeatable cause was established for that initial
probe result. The final validation requires both successful installed sessions.

### 0.1.39: preserve the Japanese ray as well as its endpoint

The v7 helpers replace the nearest-edge projection with the original Japanese
tail ray. Its reverse direction is the average of the two adjacent native
base points minus the native outline tip. Body fitting uses that ray; the
attachment is its intersection with a fitted sloping side. Native scene
centers stay unchanged, and body/text X remains independent. Original tips
are shared by all three contour banks. The reviewed Serish exception is
resolved before fitting, under the existing exact shape/center/text guard.
This is authored geometry, not automatic face or mouth tracking.

All eight body corners and their family-specific pixel insets remain. The
half-base cannot exceed 4px or 15% of the perpendicular tail reach. A minimum
3px perpendicular clearance keeps the 1.5px outer border on the intended side
of the tip. Bounds use the actual top/bottom corner insets. Vertical fitting
precedes horizontal fitting; short rays are allowed only where the viewport
requires them. A ray which cannot reach a supported socket retains native
geometry instead of changing its direction or moving its anchor.

The narrow socket requires a different fan-origin check. After the outline
is complete, the helper checks each socket vertex against all eleven edges
using the same native integer truncation as the GE. It selects a valid socket
vertex rather than assuming a fixed floating offset remains inside after
rounding. HI/LO are saved and restored around the signed cross products.
The original native draw allocation and eleven-point contour contract remain;
the helpers fit in the existing reclaimed spans without loaded-memory growth.

The first two-bubble group in p101040/041 had Cougar at layer 2 and Mitch at
layer 3, despite Cougar revealing later. The complete records are reordered
with text keys 2/3 remapped. Names, channels, positions, reveal times and
portrait associations move with their original identities. The unmodified
native phase reader is exercised against both reordered groups. This scoped
ordering change does not introduce an automatic sorter for every scene.

Preserving the ray exposes two English blocks which cannot fit their previous
wrapping. The mainland explanation is rewrapped to six lines in both physical
resources; the field warning is rewrapped to four/two lines. Only whitespace
and line controls change. The existing text-table rebuilder preserves words,
non-line controls, other rows and nontext suffixes. Working queues and their
Japanese-free exports are synchronized. Up to seven visible lines are allowed;
an eight-line fixture retains native geometry.

The preparation evidence contains 185 cases, 164 fitted, with a maximum tip
angle of 17.034453 degrees. It verifies original rays in all contour banks,
native endpoints, sloping text interiors, fixed corner differences, exact
quantized fan areas, repeat draws, ABI and native count/fan/text setup. It
includes both airport pages in both branches and the two native layer-reader
checks. Natural playback of the reported shots remains unverified; installed
and startup evidence is recorded in work/ui/dialogue/0.1.39 and
work/ui/title/0.1.39.

Both installed sessions pass all 185 cases with identical case evidence and
native layer-reader results. The full ISO/archive hashes, nested executable,
title and scoped resources are verified. Four archive rows change from 0.1.38;
the other 5,182 rows remain exact. The actual title and main menu show v0.1.39
above the credit. These captures verify startup, rather than the reported
conversation's natural paint order. The owned QA emulator sessions are closed
after verification; no release is published.

### 0.1.40: elevator overflow and tail visibility

The reported elevator explanation is reference 7 in p101040/041. Its
settled shape 144 has the original endpoint (298.5,179.5) and reverse ray
(-19.75,6.75). A 228px English line plus sloped-side padding made the body
too wide to fit its original ray in the viewport. The renderer therefore
retained the Japanese body, leaving the English text outside. Both pages
are rewrapped with the same words and non-line controls. Their measured
line advances are 164/173 and 158/170/129/94px. The four-line second page
fits through the horizontal socket without moving the source endpoint.
All authored position/shape/reveal/portrait channels remain exact; previous
layer-order and reflow fixes are retained in the .39 archive baseline.

The v8 fitter prefers 12px perpendicular reach for vertical sockets,
then uses the existing 3px minimum if the viewport cannot accommodate
that preference. Base width remains proportional to reach, with a 4px
maximum half-base and 15% ratio, so the tip remains sharp. The reported
Shinobu question, reference 27 in p101041, now has a 12px reach and 3.6px
base at both authored positions. Its settled Japanese endpoint remains
(343,157.5), and its reverse ray remains (-18.75,6.75). All border banks
share the original tip. This change does not relocate anchors to guessed
mouth coordinates or enlarge a tail by changing its direction.

The native test set adds 14 fixtures to the previous 185: both pages of
the elevator explanation at two visible authored positions in both
branches, both positions of the preceding reassurance in both branches,
and both positions of Shinobu's question. Tests assert successful fitting,
clearance inside the actual sloped white interior, original anchors and
rays, shared tips, float and quantized fan containment, repeat draws,
native draw/text/count setup and the saved-register ABI. The Shinobu
fixtures also assert the increased reach and base width. Preparation
evidence is distinct from installed evidence; natural conversation
playback remains unverified. Unsupported layouts retain native fallback.

Both installed sessions pass all 199 cases with identical evidence; 178
cases use fitted geometry. The final ISO/archive hashes and selected
nested resources match the prepared assets. Three archive rows change
from .39: the title and p101040/041; 5,183 other rows remain exact.
Reviewed title and menu captures show v0.1.40. The installer retains zero
loaded-memory growth and the original relocation prefix. Evidence is in
work/ui/dialogue/0.1.40 and work/ui/title/0.1.40. Owned QA sessions are
closed after verification; no release is published.

### 0.1.41: construction-company introduction

The reported upper bubble is reference 16 in p101050/051, shape 75, with
settled center (101,72), original Japanese tip (191,95), and reverse ray
(-13.25,-6). Its 239px first English line could not fit along that ray;
the native fallback left text outside the white body and offscreen.

The v9 body uses the largest horizontal native corner inset of its own
size family plus 10px clearance. Fifteen half-pixel values occupy 15 of
the existing 64 free descriptor bytes, starting at descriptor +848.
Padding ranges from 29.5 to 43.5px; shape 75 receives 29.5px instead of
the global 44px allowance. The existing allocation and loaded-memory
sizes remain unchanged. The original eight body corners, their side
deltas, Japanese tip/ray, and v8 tail-reach policy remain intact.

The selected introduction is rewrapped to five lines with advances
114/41/76/36/85px. Every word and every non-line control, including colour
and delay arguments, is preserved. Both physical protagonist resources
receive the same logical reflow; other dialogue and all authored tracks
remain exact. Working translation and Japanese-free export are synced.

Sixteen new native fixtures cover both upper positions and all three
pages at both positions of the following bubble in both branches. The
215-case suite retains the earlier sloped text, anchors/rays, shared
tips, integer/float fan, repeated draw, ABI and layer-reader checks.
The final verifier also checks each settled upper text band against the
newer lower white polygon on all three pages. These are controlled
geometry checks; natural playback is still visually unverified.

Both installed sessions pass all 215 cases with identical case evidence;
194 cases use fitted geometry. The final ISO/archive hashes, nested
executable and selected resources are verified. All six settled
coexistence checks pass. Three archive rows change from .40: the title
and p101050/051; 5,183 other rows remain exact. Reviewed title and menu
captures show v0.1.41. Evidence is in work/ui/dialogue/0.1.41 and
work/ui/title/0.1.41. Owned QA sessions are closed; no release is published.

Version 0.1.42 enlarges and outlines tails in the shared standard-bubble
fitter. The outline half-base is capped at 8px and 35% of perpendicular
reach, giving a maximum outline tip angle below 40 degrees. The white
socket narrows by 1.5px along its edge; the dark socket widens by 1.5px.
All banks retain the same original Japanese tip, and every socket midpoint
remains on its original reverse ray. This applies to supported centered,
stationary, unit-scale Latin bubbles globally. Other native styles and
unsupported states retain the native layout. It is not automatic mouth
tracking or full-game visual coverage.

The wider base requires greater corner clearance. Top/bottom attachment
reserves use each family's largest corresponding native vertical corner
cut plus 9.5px; side fitting increases body height if those reserves need
it. Thirty half-pixel clearance bytes occupy descriptor +864..893.
The helper still preserves all eight native body corners and their unequal
slopes. A bounded fan-origin search moves inward from the socket midpoint
along the original reverse ray and checks every quantized outline edge.
The native border remains a strip between the two rails, rather than an
independently drawn second tail.

Kogoro's reported secret-base question previously had a 206px first line.
Its original tip (303,96.5) and reverse ray (-12.25,-5.5) could not support
that English width inside the viewport, so fitting fell back to the native
Japanese body. Both p101050/051 now use three lines, with advances
127/156/67px. Every word and non-line control is preserved, with all
authored tracks and other strings exact. Settled fixtures for both branches
and the two small tails in p101041 are added to the native suite.

The v10 tools are memory neutral. Low-zero floating constants omit their
redundant final ORI while preserving the relocation scanner contract.
Seed/clip/horizontal/socket helpers fit the original 1,580-byte leaf; the
1,732-byte core, 3,648-byte catalog span and 912-byte descriptor span retain
their original loaded sizes. The original relocation prefix and three-base
unselected-memory checks remain mandatory.

`tools/audit_bubble_corpus_042.py` examines 29,859 English indexed references
across 1,264 installed resources. Its static settled-phase model covers
27,120 standard pages, finding 25,928 feasible pages and 1,192 potential
fallback pages. It finds no newly infeasible pages from the larger-tail
rules. Dynamic controls and nonstandard shapes are counted separately.
Warnings do not establish actual visible overflow: field/battle geometry,
animation transforms, interpolation, reveal order and natural playback
remain unmodeled. This build fixes the reported Kogoro line, not every
warning in that audit. English-only evidence is stored in
work/ui/dialogue/0.1.42/corpus_audit.en.json.

Both installed sessions pass all 219 native cases with identical case
evidence; 198 use fitted geometry. The four new reported fixtures verify
sloping text clearance, larger outlined tails and exact original tips/rays.
All earlier word/name/control, layer-order, corner, integer/float fan,
repeat-draw and ABI checks still pass. Full ISO/archive hashes and nested
selected-resource readbacks are verified. All six earlier construction
coexistence checks pass. Three archive rows change from .41: the title and
p101050/051; 5,183 other rows remain exact. Reviewed title and menu captures
show v0.1.42. Normal playback of these conversations remains visually
unverified. No release is published.
