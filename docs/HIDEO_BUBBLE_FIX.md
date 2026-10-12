# Ryudock dialogue layout — 0.1.27

The supplied snowy-scene screenshot shows the second Ryudock record running off the left edge. Its Latin Hideo pronunciation annotation was outside the accepted measurement and geometry scope, so the native Japanese width calculation remained active. The first sentence also retained an uneven Japanese line division.

The replacement hooks accept the exact `0F 32 48 69 64 65 6F 0F` annotation. They measure the body with the existing integer VWF advances and skip the already rendered reading when computing body width. Original ruby markers, the span digit, reading, speaker names, record boundaries, and wording remain intact. Other annotations retain the inherited fallback. Geometry retains its stationary, unit-scale, unrotated, centered and one-to-four-line guards.

The two English records have the same words with new line boundaries. Both `phase/bin/p101010.bin` and `phase/bin/p101011.bin` receive the correction. Each keeps all 19 reference IDs, all other row bytes, and its nontext suffix. The Hideo sentence's first line measures 182 native pixels, rather than the fallback's 377 pixels for its 29 body glyphs. Its pronunciation remains a small annotation above the name.

The new code extends the existing loaded helper segment by 2,804 bytes and adds ten relocation records. Existing loaded segments, inherited helper bytes and relocation records remain unchanged except the two entry jumps. Three section-driven load models, eight emitted measurement cases, eleven inherited measurement regression cases and nine emitted geometry scanner cases pass. Incorrect readings, changed digits, truncation and probe limits keep native fallback.

Installation checks compare the generated executable with the build and its ISO entry, read back both story resources, confirm all 5,183 other archive rows remain unchanged, and retain the English prologue movie. The title asset is the third changed row, for version 0.1.27.

An isolated ordinary boot reaches the title, menu, Latin male setup defaults, intro movies and English opening Keroro dialogue. A debugger breakpoint observes execution of the new geometry entry during that opening scene. This is startup and opening regression evidence; the exact snowy Ryudock scene, simultaneous bubble placement and its ruby annotation still require a gameplay capture. No full-game or native-hardware verification is claimed.

Sources and evidence: `tools/fix_hideo_bubble.py`, `tools/fix_ryudock_lines.py`, `tools/check_hideo_geometry.py`, `tools/verify_hideo_build.py`, and `work/ui/dialogue/0.1.27/validation.en.json`.
