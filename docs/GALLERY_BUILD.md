# Selected gallery prose build — 0.1.7

The local candidate cold-boots and displays the full English Red Shield dictionary prose using the shared variable-width 4x glyph bank. All wording is retained. Top, middle and bottom scroll positions pass visual review and exact glyph/position checks; the next Japanese dictionary entry retains its original font and spacing. Gallery headings/navigation are still Japanese. This is one tested prose entry, not a complete translated game.

The fresh ISO is `work/output/0.1.7-gallery-vwf-4x-candidate/Heroes-Phantasia-0.1.7-gallery-vwf-4x-candidate.iso`. Original inputs and earlier candidates remain unchanged. No commit or release was created.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| ISO | 1,831,995,392 | `1175e0bf020b8456a883bb7b377956afa1f86a807c96e0100b6f91e9d1a32f1a` |
| EBOOT.BIN | 6,182,448 | `8d310d47f903d2dfdcb86d8ba63ced77b06a1d80aa4590c255b50c26ecdc0bf1` |
| HP.CPK | 410,791,936 | `45c570c3af50ede5462766a953216d27ca930be8b376bbab601affbf66ed26be` |
| GgHelp000.bin | 41,024 | `ea886a95b1b932a33dc9c581c491a14e0950c9139a35686993ec87972bc6ccaf` |

The executable is byte-identical to 0.1.6. The archive keeps its selected opening resource and replaces only `menu/Gallery/dic/GgHelp000.bin` with the complete current English target, translation ID `51ccd5f7a174a1d8e041`. Its prose grows from 328 to 450 encoded bytes; the original packed font and charset stay intact. The packager verifies all archive metadata and untouched bytes, all ISO inventory entries and untouched bytes, both selected ISO extraction hashes and final size. Opening QA evidence is inherited from 0.1.6; it was not rerun on 0.1.7.

The dictionary body viewport is [4,72,330,154], with seven 22px-spaced visible rows and a 45-glyph line capacity. Six English spaces become additional line breaks in the rebuilt resource. Their reversible offset ledger proves that wrapping changes no wording and leaves every original control at its original encoded offset. The resulting body has 15 physical lines, including one preserved blank line, and 434 visible characters. Maximum conservative glyph extent is 304px; maximum line length is 43 glyphs. Captured output is 480x272. The 4x refers to 64x64 source glyphs drawn into 16x16 rectangles; increased emulator internal resolution remains unverified.

Proof: `work/ui/runtime/gallery_candidate_validation.en.json`. It combines three reviewed screenshots, 1,536 actual English glyph draws, and 32 native regression draws. Each English glyph's character, proportional origin, upload pointer and source/destination rectangle match the rebuilt target and bank. Each nonempty line is observed completely, and the top-position spacing accounts for the blank line. Read-only live checks match the full shared font bank, lookup table, integer advance table and gallery route/cursor hooks to the executable. The native regression matches the following GgHelp001 resource's entire original font, each uploaded glyph and D7FC rectangle arguments, preserving 13px advances.

![Top scroll position](../work/ui/runtime/gallery_candidate_top.png)

![Middle scroll position](../work/ui/runtime/gallery_candidate_middle.png)

![Bottom scroll position](../work/ui/runtime/gallery_candidate_bottom.png)

## Reproduce

Use the repository's Python runtime. Every writer defaults to preview; inspect that output before adding `--write`. Rebuild/package writers require fresh outputs and will reject overwriting this candidate.

```text
python tools/rebuild_gallery.py menu/Gallery/dic/GgHelp000.bin work/translation/en/batch_0008.en.json --wrap-width 330 --wrap-glyph-limit 45 --output work/output/0.1.7-gallery-candidate/GgHelp000.bin
python tools/audit_gallery_layout.py --width 330 --glyph-limit 45 --output work/ui/vwf/gallery_layout_coverage.en.json
python tools/append_cpk.py --replace fld/talk/f101010.bin=work/output/0.1.1-dialogue-candidate/assets/selected/fld/talk/f101010.bin --replace menu/Gallery/dic/GgHelp000.bin=work/output/0.1.7-gallery-candidate/GgHelp000.bin --output work/output/0.1.7-gallery-candidate/HP.CPK
python tools/build_gallery_patch.py
```

The archive append step between rebuilding and packaging retains `fld/talk/f101010.bin` and inserts the rebuilt gallery resource; its selected paths/hashes are recorded in `work/output/0.1.7-gallery-candidate/HP.CPK.manifest.en.json`. Do not replace the original archive.

Launch the isolated software-renderer PPSSPP against this ISO, load its system data, enter Gallery/BLOOD+ and select Red Shield. At scroll offsets 0, 4 and 8, capture the native framebuffer with `tools/capture_frame.py` and collect 512 draws per position with `tools/trace_dialogue_vwf_4x.py --gallery`. Pass the candidate `--build-manifest` and a fresh output path to each tool. Review saved captures and record the reviewed hashes and corresponding scroll positions before validation. Switch to the next original Japanese entry and run `tools/trace_native_gallery.py` for 32 draws; capture/review it too. These probes use temporary breakpoints and leave the CPU running; they do not patch text/font/executable memory.

```text
python tools/verify_gallery_build.py
```

That command rechecks the selected resource, current English export, saved traces/captures, ISO/archive hashes and live font/hooks. `--write --output <fresh English-only proof path>` saves the reviewed proof and links it in the candidate manifest. This verifies selected prose only. Other dictionary entries, profile/quest/tutorial layouts, native symbols, ruby, runtime substitutions, headings, save/load, battles, both protagonists and native hardware still need work. The structural audit prepares 80 of 82 drafted gallery prose targets at the selected dimensions; it does not certify their display layouts.
