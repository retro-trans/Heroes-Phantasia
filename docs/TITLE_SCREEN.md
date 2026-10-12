# Title credit and build version

Every new local ISO must display its version above `github.com/retro-trans` at the bottom right of the title screen. `build.json` is the single source for both the displayed version and the build manifest. Increment its `0.x.y` version before each build.

Use `tools/build_local.py` from the repository root. It previews by default; read the proposed stamp and build metadata before adding `--write`. It rejects a version that is not newer than its base or any existing local ISO manifest, and never overwrites an existing versioned build. The older menu, opening and gallery builders remain historical preparation tools; package any future executable/archive changes through this entry point before testing or distributing a new build.

The default base is the 0.1.7 gallery/VWF candidate. `--base-manifest` selects another candidate; `--executable` and `--archive` supply newly prepared translation/font assets. A custom `--executable` requires `--executable-report`: its version, executable hash and byte length must match the selected build configuration and input. The title resource is always regenerated from the untouched original, so a later build replaces the previous version instead of layering another stamp over it. This tool creates local outputs only.

The 0.1.11 setup candidate was packaged with the following inputs from the repository root. `build.json` selected 0.1.11 before its first packaging; an already written version cannot be rebuilt or overwritten. Future builds need a fresh version and an executable report with that same version. Inspect the preview before adding `--write`.

```powershell
python tools/build_local.py --base-manifest work/output/0.1.10-title-credit-vwf-4x-candidate/manifest.en.json --executable work/output/0.1.11-setup-assets/EBOOT.BIN --executable-report work/output/0.1.11-setup-assets/setup_patch.en.json --dialogue-report work/output/0.1.9-setup-assets/opening.en.json
```

See [SETUP_BUILD.md](SETUP_BUILD.md) for the setup/keyboard changes, completed scoped checks and remaining limitations. A preparation report supplies asset metadata; it does not certify in-game display. The latest title/main-menu proof is `work/ui/title/0.1.11/validation.en.json`; both captures show v0.1.11 above the credit. Its stamp-region mean channel error is 1.97/255 and maximum 9/255.

The original title texture is the 480×272 background in `menu/TitleMenu_Data.bin`, beginning at `0x13710`. It uses an unchanged 256-color RGBA palette and CI8 pixels swizzled in 16-byte by eight-row blocks. Only pixel indices covered by the text/shadow change. Headers, layout, the palette, uncovered pixels and every other texture in the resource remain byte-exact. The shared title/menu background keeps the stamp when the main menu appears.

The stamp uses Roboto Condensed, sampled at 4× size then reduced to a 9px logical font. The existing palette supplies warm white text and a dark shadow. Its credit line is 81×9px at (391,255); version 0.1.8 is 23×7px at (449,245). Both align to x=472, with an eight-pixel right/bottom margin. Longer version numbers align to the same right edge. This is a native title texture stamp; the inherited VWF implementation is unchanged. Font licensing is recorded in `work/ui/vwf/Roboto-LICENSE.txt`.

Background previews and the coordinate record are stored under `work/ui/title/<version>/`. Cold-boot screenshots and their separate validation record establish actual title/menu display, rather than relying on a mockup. Archive/ISO packaging verifies every unrelated metadata field, every original byte outside the planned metadata edits, both selected ISO extractions and final lengths. Broader gameplay and translation coverage retain the base candidate's limitations.

## Verified local build 0.1.8 — 2026-10-11

The title and main menu were visually checked after a fresh launch in the isolated PPSSPP interpreter/software-renderer session. The stamp region in each native RGBA5551 screenshot agrees with the generated background: average RGB channel error 1.99/255, maximum 9/255, consistent with framebuffer rounding. The Start prompt remains unobstructed and opens the five English menu labels. A second fresh launch reached the same title/menu and preserved the stamp. System data was loaded from the existing isolated test save; no save was written.

- Title: `work/ui/title/0.1.8/title.png`
- Main menu: `work/ui/title/0.1.8/menu.png`
- Repeat launch: `work/ui/title/0.1.8/repeat_title.png` and `repeat_menu.png`
- Reviewed validation: `work/ui/title/0.1.8/validation.en.json`
- ISO: `work/output/0.1.8-title-credit-vwf-4x-candidate/Heroes-Phantasia-0.1.8-title-credit-vwf-4x-candidate.iso`
- ISO SHA256: `e56cdaee8b2724472f4f90731fef5438acfd9d442b7d8c92dfc017475e8e2109`

An early startup probe saw only the `balloon` loader module, so the title capture was deferred. Startup logs contain a 327,936-byte contiguous-allocation error; the controlled repeat nevertheless loads `hp_proj` and reaches the title/menu. No memory patch or save-state injection was applied. This evidence establishes the displayed credit and menu transition, rather than universal startup/native-hardware compatibility.

`tools/verify_title_build.py` rechecks the generated resource, archive and ISO extractions and capture-region agreement. Preview its report, inspect the images, then supply their SHA256 values with `--reviewed-title-sha256` and `--reviewed-menu-sha256` before `--write`. A next-version generation check produced `v0.1.9` with the same credit/right alignment. A duplicate 0.1.8 build is rejected before writing.
