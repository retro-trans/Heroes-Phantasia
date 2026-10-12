# Four-times English glyph feasibility

This began as a read-only disassembly audit of the decrypted executable identified in `prx_relocation.md`. The parent has since tested native and 4x-source menu rendering. **The live 4x test verified 64×64 source regions drawn into 16×16 screen rectangles**, with unchanged proportional advances. The output capture remains native 480×272. See the live evidence below; the original static candidates and estimates remain recorded for comparison.

The later 0.1.1 font-test ISO cold-boots with a compact 64×64 T4 slot bank containing all 96 supported Latin glyphs. Its 328,336-byte static payload fits the observed module load; every loaded slot/lookup matches the candidate, and a 76-draw menu trace verifies 64×64 upload/pitch and unchanged 16×16 destinations. This resolves the earlier full-repertoire allocation problem for the static menu bank. Dialogue font coverage, all-glyph rendering and increased internal resolution remain unverified; see `VWF.md` and `MENU_BUILD.md`.

All code addresses below are module-relative; add the observed load base for runtime addresses. File offsets for these code sites equal module address plus `0xc0`.

## Upload arguments and texture state

`0xea45c` is the reviewed glyph renderer. Its three branches upload a selected glyph through `0x1b7e1c`, at calls `0xea540`, `0xea5ec`, and `0xea688`. Original arguments are:

| Register | Meaning | Original value |
| --- | --- | --- |
| `$a0` | Mipmap level | 0 |
| `$a1` | Texture width | 32 |
| `$a2` | Texture height input | 24 |
| `$a3` | Texture buffer width/pitch in pixels | 32 |
| `$t0` | Selected glyph pointer | Font base + selected slot × 384 |

`0x1b7e1c–0x1b7e98` emits GE texture buffer width (`0xa8+level`), texture address (`0xa0+level`), texture size (`0xb8+level`), and flush (`0xcb`). PSP `clz` instructions at `0x1b7e2c` and `0x1b7e54`, followed by subtraction from 31, compute **floor(log2(height))** and **floor(log2(width))**. Thus the original 32×24 input configures a 32×16 texture; 128×96 would configure 128×64, not 128×96. This matches the exponent encoding in [PSPSDK's texture-image routine](https://github.com/pspdev/pspsdk/blob/master/src/gu/sceGuTexImage.c). Use explicit power-of-two dimensions for the new path.

At `0xea694–0xea6a4`, the renderer calls `0x1b7d28` with `(4,4,0,1)`. Its worker `0x1b8ca8` emits GE texture mode `0xc2` and format `0xc3`: T4, maximum mip index 4, multiclut off, swizzle on, as confirmed by [PSPSDK's texture-mode routine](https://github.com/pspdev/pspsdk/blob/master/src/gu/sceGuTexMode.c). Palette setup remains through `0xe9264` and `0x1b7f3c`.

Original T4 pitch 32 means 16 bytes per row. With one 16-byte block across, PSP swizzle happens to be identical to linear storage. A 128-pixel pitch means 64 bytes per row and **four blocks across**, so a new glyph must be swizzled in 16-byte × 8-row blocks. Merely enlarging the old packed bitmap is insufficient.

## Source rectangle versus destination rectangle

The original draw call at `0xea6e4` targets `0xd7fc`. Its arguments are `(context,x,y,u,v,width,height)` in `$a0,$a1,$a2,$a3,$t0,$t1,$t2`. It writes two 10-byte vertices: `(u,v,x,y,z)` and `(u+width,v+height,x+abs(width),y+abs(height),z)`. Texture extent and screen extent are therefore coupled. Setting its width/height to 64 would enlarge the label to 64×64 on screen.

The adjacent existing routine **`0xd8e4` separates those extents**:

| Argument | Location |
| --- | --- |
| Context | `$a0` |
| Screen x/y | `$a1/$a2` |
| Destination width/height | `$a3/$t0` |
| Texture u/v | `$t1/$t2` |
| Source width | `$t3` |
| Source height | Caller stack `+0` |

It reads the ninth argument at its adjusted stack `+0x30` (`0xd92c`). Vertex writes at `0xd93c–0xd978` independently produce UV end `(u+source_width,v+source_height)` and screen end `(x+destination_width,y+destination_height)`. Both routines call `0x1b7810` with primitive 6, vertex type `0x00800102`, two vertices: a 2D sprite with 16-bit UV and positions. [PSPSDK's declarations](https://github.com/pspdev/pspsdk/blob/master/src/gu/pspgu.h) confirm those constants.

For an English glyph, the tested call is `0xd8e4(context,x,y,16,16,0,0,64,64)`. It samples 64×64 source pixels while retaining a 16×16 logical sprite. Keep independently measured VWF pen advances in logical pixels; multiplying the pen advance by four would change layout. Static stores and the subsequent live trace agree; the rendered five-label menu was visually reviewed.

## Candidate English path

Use a separate owned high-resolution Latin bank and branch on the already validated English glyph range. Bind only English glyphs with upload arguments `(0,128,64,128,pointer)` and draw through `0xd8e4`; retain the original 32×24 upload, lookup, draw, and advance path for Japanese. A 128×64 T4 slot is 4,096 bytes and covers the required 64×64 UV rectangle. This is sufficient for a four-times version of the original sampled 16×16 area; the original extra padded rows do not need proportional allocation. If preserving the entire 32×24 source slot is desired, use 128×128 power-of-two storage (8,192 bytes), with the 128×96 content zero-padded.

For 96 Latin slots, the 128×64 bank costs 393,216 bytes. Replacing 96 native slots in the reported 130,704-byte proof payload produces approximately **487,056 bytes**, before new hook code/alignment. A 128×128 bank raises that estimate to 880,272 bytes. The earlier `0x23000` allocation cannot hold either; allocate a new sufficiently sized heap chunk and handle failure before installing hooks.

Verify active minification/magnification filters: `0x1b7d64` emits the filter register and has both nearest and linear callers elsewhere. The glyph renderer itself does not set a filter. To avoid sampling undefined higher mip levels during 4:1 reduction, an English branch can explicitly use mip index 0 with a non-mipmap filter and restore the expected state afterward. Palette, swizzle, texture mode, buffer pitch, and source/destination extents must all be correct before visual testing. Keep the bank alive until queued GPU work has completed; restore hooks/state before freeing it.

Individual 128×64 or 128×128 textures fit the PSP texture-size limits. This per-glyph path avoids the large-page problem documented in `font_format.md`. The extra source detail may be more visible at increased emulator rendering resolution; a native 480×272 frame still displays a 16×16 destination. Crispness, baseline, edge padding, filter choice, performance, Japanese fallback, and complete rollback need live screenshots and traces before claiming four-times support.

## Read-only review of proposed live hooks

The parent proposed three coordinated hooks; static review found no inherent register-flow conflict:

- At `0xea5c4`, the overwritten instructions are `move $t0,$a1` and `ori $s5,$zero,0`. Before clearing `$s5`, its table entry contains the character code. For English codes 32–126 and the separately assigned code 128, select slots 0–94 or 95 in a separate 4,096-byte bank, set upload arguments `(0,128,64,128,pointer)`, set `$t1=0`, `$s5=-1`, `$s6=0`, and jump to `0xea5ec`. **The zero `$t1` is necessary** because retained delay-slot instruction `0xea5f0` adds `$t1` to the pointer. Japanese fallback must replay both overwritten instructions and resume at `0xea5cc`; its range test must preserve the original `$a1` until that fallback decision.
- Replace the call at `0xea6a0` with a wrapper that changes maximum mip index `$a1` to zero only when `$s5=-1`, then tail-jumps to `0x1b7d28`. The retained delay slot at `0xea6a4` establishes swizzle `$a3=1`; the tail jump must preserve the return address supplied by the original call. Upload, texture-mode, and palette routines do not clobber the saved `$s5` marker.
- Replace the call at `0xea6e4` with a wrapper that uses `0xd8e4` only for the English marker and otherwise tail-jumps to `0xd7fc`. The retained `0xea6e8` delay slot finishes constructing the draw context address `0x127a628`; do not overwrite it. An English frame of `0x20` bytes can save return address at `+0x1c` and place ninth argument 64 at `+0`. Supply destination extents from `$s3/$s4`, UV origin zero, and source extents 64/64, then restore stack and return address after the call. Original Japanese arguments must survive the fallback branch and its delay slot. Pen advances remain the native logical VWF values.

The existing palette path `0xe9264` remains structurally valid because texture format stays T4 and the new bank uses the same 0–15 palette indices. This establishes compatibility of the call path, not visual proof of the new alpha/color result.

The state-preparation routine `0xe8da4` sets nearest/nearest through `0x1b7d64(0,0)` at `0xe8e20`. A different routine, `0xe8e54`, sets linear-mipmap-linear/linear through `(7,1)` at `0xe8e78`. Consequently the font renderer cannot be said to have an unconditional nearest, non-mipmap default. Record the actual active filter for the live test or explicitly manage and restore it. Marker branches should use safe delay slots, and every hook must be restored before the owned bank is freed after GPU completion. This review did not install or execute any hook.

## Live menu experiment

The root implemented and tested the reviewed wrappers in `tools/live_vwf.py --scale 4`. The full 96-glyph allocation of 536,576 bytes failed cleanly before any patch. A subset of 22 high-resolution glyphs, including the menu repertoire and experimental accent, succeeded: payload 221,840 bytes, owned game-heap block 233,472 bytes at 0x09efe010. A 129-byte lookup maps eligible codes to compact slots; unknown slots retain native glyphs. Upload, mode and draw hooks are 136, 24 and 76 bytes and passed independent instruction/branch review.

`main_menu_vwf_4x_trace.en.json` verifies 76 real glyph uploads and sprites: mip 0, width/pitch 128, height 64, source extent 64×64, destination 16×16, and all five English labels at their original logical positions. The visually reviewed screenshot is `main_menu_vwf_4x.png`. Japanese Options remained readable in `options_fallback_4x.png`. Maximum mip level zero is explicit; inherited filter state was not measured. Output is native 480×272, so higher emulator internal resolution and performance remain untested.

The root validated every installed change and payload hash, restored all seven change ranges, waited two display frames and freed the allocation. `main_menu_restored_after_4x.png` confirms the original menu resumed. No ISO or executable file was patched. This establishes a reversible 4x-source menu proof; full repertoire memory planning, all font/measurement paths and persistent cold-boot integration remain required.
