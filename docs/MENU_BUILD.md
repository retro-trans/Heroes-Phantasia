# Local menu/font test builds — 0.1.6

The current local opening test is `work/output/0.1.6-opening-vwf-4x-candidate/Heroes-Phantasia-0.1.6-opening-vwf-4x-candidate.iso`. It retains the five verified English menu labels and all 96 supported 4x-source glyphs. Thirteen loaded hooks, every packed glyph pixel/lookup entry and the compact bubble catalog passed checks, with 76 actual menu uploads/sprites. Evidence is `association_candidate_menu_trace.en.json` and `association_candidate_menu_validation.en.json` under `work/ui/runtime`. Use `tools/verify_menu_build.py --association-fix` for the matching running candidate.

The selected opening dialogue record now passes display QA on both pages and restores Japanese fallback afterward. The complete English game remains unfinished; see `DIALOGUE_BUILD.md`. Earlier versioned candidates remain separate and reproducible.

## Earlier 0.1.3 result

The latest local opening candidate is `work/output/0.1.3-opening-vwf-4x-candidate/Heroes-Phantasia-0.1.3-opening-vwf-4x-candidate.iso`. It retains the five verified English menu labels and full 96-glyph 4×-source bank. Twelve loaded hook sites and all glyph pixels/lookup entries passed checks; `speaker_candidate_menu_trace.en.json` records 76 actual menu uploads/sprites, and `speaker_candidate_menu_validation.en.json` records this limited verification. Run `tools/verify_menu_build.py --speaker-labels` for the matching candidate. The opening record's body and speaker also render, but its bubble layout fails QA; see `DIALOGUE_BUILD.md`. The menu verification does not imply a playable English game.

## Earlier 0.1.1 full Latin bank

The latest local font-test ISO is `work/output/0.1.1-menu-full-vwf-4x-candidate/Heroes-Phantasia-0.1.1-menu-full-vwf-4x-candidate.iso`. It cold-boots with the same five English menu labels and all 96 supported Latin glyphs loaded in compact 64×64 T4 slots. The static payload is 328,336 bytes; loaded high-resolution pixel data is 196,608 bytes. Six hook sites, the font descriptor, all menu pointers/strings and the complete high-resolution bank/lookup passed live checks. A second 76-draw trace confirms 64×64 upload/pitch, 64×64 source and 16×16 destination sizes. The Japanese Options screen remained readable. Evidence is `cold_boot_full_font_menu.png`, `cold_boot_full_font_trace.en.json`, `cold_boot_full_font_validation.en.json` and `cold_boot_full_font_options.png` under `work/ui/runtime`.

Run `tools/build_menu_patch.py --full-4x` to preview this version, then `--write --iso` after reviewing the output. `tools/verify_menu_build.py --full-4x` and `tools/trace_vwf_4x.py --build-manifest work/output/0.1.1-menu-full-vwf-4x-candidate/manifest.en.json` verify a matching running candidate; both require separate `--write` to save evidence. The default builder still produces the byte-identical 0.1.0 candidate described below. The original ISO is unchanged.

This is still a five-label menu test. Individual rendering of all 96 glyphs, dialogue translations, every font/measurement path, gameplay/save/load/battles, native hardware and increased emulator internal resolution remain unverified. The separately rebuilt dialogue archive in `DIALOGUE_BUILD.md` is not included in this font-test ISO.

## Earlier 0.1.0 menu subset

The local candidate in `work/output/0.1.0-menu-vwf-4x-candidate/` cold-boots in the isolated PPSSPP v1.20.4 interpreter/software session. Its executable installs the font during resident-resource initialization. No debugger writes or save-state injection installed the cold-boot patch. All five relocated English menu labels rendered with proportional advances; 76 actual glyph uploads and sprites confirmed 64×64 source rectangles drawn into 16×16 destinations. Output was captured at native 480×272.

This build translates only New Game, Load, Options, Gallery and Data Install. It contains no translated dialogue. Japanese Options remains readable. Complete gameplay, battle transitions, save/load progress, all font and measurement paths, ruby, wrapping, broader high-resolution coverage and increased emulator internal resolution remain to be tested. Native PSP hardware compatibility is unverified.

The original ISO and decrypted executable remain unchanged. The candidate's EBOOT is a plain decrypted PRX, with SHA-256 `64e18adc27557d42f6733e4636054e3b29c81d4a0b4e28011330469ddf2f45df`. Its new third load segment starts at module `0x16f9b00` and contains a 221,840-byte payload. Six hook sites include the resident initializer's call at `0x4c0ec`; five menu pointer words point into new storage. The original BSS is preserved. Both relocation program and section views include the original 71,807 records plus 23 new records. Independent checks exercised signed HI/LO carry and jump reconstruction at several load addresses.

The bank is reconstructed deterministically from the extracted resident resource: original 230 glyph records/pixels plus 96 native Latin glyphs and 22 menu-focused 4x glyphs. This reconstruction exactly matches the original live font snapshot hash. The startup wrapper calls the original initializer, then installs the new resident descriptor while preserving its return behavior. Reloads can reinstall the same static bank. General reload/gameplay regression coverage remains pending.

Run `tools/build_menu_patch.py` to inspect the candidate, then `--write --iso` after reviewing the output. The copied ISO appends EBOOT and updates its directory extent/length and volume size. Independent ISO inventory confirmed the file's extent and bytes. `tools/trace_vwf_4x.py --build-manifest <manifest> --output <trace>` measures runtime draws without installing a patch; review its default output before `--write`. `tools/verify_menu_build.py` checks the live hooks, descriptor, menu pointers, strings and saved cold-boot trace; it writes evidence only with `--write`.

Evidence is `work/ui/runtime/cold_boot_menu_candidate.png`, `cold_boot_menu_vwf_4x_trace.en.json`, `cold_boot_options_fallback.png` and `cold_boot_menu_validation.en.json`. The output manifest records the candidate hash and limited verification scope. This is a local test build, with no GitHub release.
