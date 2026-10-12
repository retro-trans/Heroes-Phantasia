# PRX storage and relocation plan

Audit of original `work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf`, SHA-256 `03db593abe2febc5886c04ac4c9c4c8d6010359e66f403e8e8f54466770e15c1`; that source remains unchanged. The dedicated appended-load-segment approach has since been implemented in `tools/build_menu_patch.py` and cold-booted as a local 0.1.0 menu-test ISO. Its 221,840-byte payload and 23 added relocations were checked independently; actual loaded hooks, descriptor, pointers and menu draws passed. Full gameplay and native PSP compatibility remain untested. Historical audit alternatives below retain their original limitations; see `MENU_BUILD.md` for current evidence.

## Exact existing layout

ELF32, little-endian MIPS, type `0xffa0` (PSP PRX), flags `0x10a23001`. Entry is module-relative `0x127214`. File length is `0x508865`. ELF header size is 52; the three 32-byte program headers start at file `0x34`. There are 55 40-byte section headers at `0x47bbc4`; section-name index is 54, but names are stripped, so use indices/types rather than names.

| PH index/type | File offset | Module address | File size | Memory size | Flags/alignment |
| --- | --- | --- | --- | --- | --- |
| 0, `PT_LOAD` | `0xc0` | `0` | `0x47af58` | `0x47af58` | RWX / `0x40` |
| 1, `PT_LOAD` | `0x47b040` | `0x47af58` | `0x7ac` | `0x127eb74` | RW / `0x40` |
| 2, `PT_PSPREL1`, `0x700000a0` | `0x47c45c` | `0` | `0x8c3f8` | `0` | 0 / `0x10` |

Initialized segment 1 ends at module `0x47b704`. The original allocation ends at `0x16f9acc`: its zero-fill span is `0x127e3c8` bytes. Section 51 is `SHT_NOBITS` at module `0x47b740`, size `0x127e38c`; the preceding 60 bytes are alignment padding. **The BSS belongs to the game, even when currently zero.** Zero-filled buffers or file gaps are not approved storage caves.

PH0 `p_paddr=0x294958` points to the **file offset** of the PSP module-info record; its module address is `0x294898`. Keep that special locator unchanged. Module name is `hp_proj`, attributes 0, version bytes 1/1, GP 0, export range `0x2946b0–0x2946c0`, import range `0x2946c8–0x294894`. Preserve these and entry unless a separately verified startup hook needs changes. The [PSPSDK generator](https://github.com/pspdev/pspsdk/blob/master/tools/psp-prxgen.c) confirms the module-info locator convention.

## Relocation schema and counts

The file has ordinary PSP REL1 records, not compressed REL2: 71,807 entries of eight bytes, `<u32 r_offset,u32 r_info>`. Here `r_info & 0xff` is type; bits 8–15 select the segment containing the patch, bits 16–23 select the segment whose loaded base is added, and bits 24–31 are zero. `r_offset` is relative to the patch segment. The [PPSSPP loader implementation](https://github.com/hrydgard/ppsspp/blob/master/Core/ELF/ElfReader.cpp) is the primary reference used to check these meanings.

| Type | Count | Application |
| --- | --- | --- |
| 2, `R_MIPS_32` | 11,031 | Absolute pointer word |
| 4, `R_MIPS_26` | 42,192 | `j` / `jal` target |
| 5, `R_MIPS_HI16` | 7,892 | High immediate, paired with following low relocation |
| 6, `R_MIPS_LO16` | 10,692 | Low immediate |

71,597 patch segment 0 (offsets `0x10–0x47af20`); 210 patch segment 1 (`0–0x7a8`). Target bases are segment 0 for 66,568 records and segment 1 for 5,239. HI/LO counts differ, so do not assume a one-to-one pair or arbitrarily sort the records. Preserve existing order and signed-low carry behavior.

Ten existing `SHT_PSPREL` sections divide this same contiguous relocation payload: indices 2, 28, 32, 35, 37, 40, 42, 44, 48, and 50, with respectively 61,272 / 1 / 69 / 4 / 6 / 5,205 / 5,036 / 4 / 57 / 153 records. Their sum exactly matches the program-header count. A builder must enumerate and validate these headers. Section-relocation processing and segment-relocation processing must agree; updating only the program-header relocation blob would omit new relocations in a loader that uses the section headers.

## Deterministic appended-segment approach

1. Validate the input hash, headers, section spans, every relocation target, and expected original hook instructions before building. Preserve load segments 0/1 and all original module addresses.
2. The current PH table ends at `0x94`. Four PH entries end at `0xb4`, before original payload `0xc0`, so one extra entry fits without moving that payload. Put the new `PT_LOAD` at PH index 2 and move the original REL1 PH descriptor to index 3; old records only reference 0/1 and keep those indices.
3. Place new storage at module `align_up(0x16f9acc,0x40)=0x16f9b00`. Its first appended file position can be `align_up(0x508865,0x40)=0x508880`. Use an initialized, aligned, bounded payload for English pointers/text, Latin font data/metrics, and any renderer trampoline. Use RWX only if that segment contains code; a data-only segment needs RW. Set `p_filesz <= p_memsz`, and keep initialized data out of original BSS.
4. Use offsets relative to the new segment for its self-pointers. Add `R_MIPS_32` records targeting segment 2 where absolute pointers are needed. For hooks into new code, change or replace the old relocation at that exact site; never let an old base-0 relocation run on a target already rebased for segment 2. New HI/LO pairs must use correct signed-low rounding, consistent segment IDs, and stable order. Jumps require the same 256 MiB region at runtime; otherwise use an absolute register jump and verified delay-slot handling. Avoid new GP-relative references.
5. Rebuild a contiguous REL1 blob containing all original records (with deliberate hook changes) plus new records. Preserve old relocation section group boundaries/order, update their file offsets, add an allocated section for the new payload and a PSP relocation section for its new records, then append a rebuilt section-header table and update `e_shoff/e_shnum`. Keep existing section indices, links, and module-info locator valid. The relocation PH must cover the complete rebuilt blob. Update `e_phnum` to 4; leave entry unchanged.
6. Parse the proposed result independently, simulate relocations at multiple candidate load bases, and compare unchanged original sites with the original loader result. Then test actual allocation, cold boot, imports, dialogue, menus, battle transitions, saves, wrapping/centering, and font rendering. The larger module consumes additional user memory and may reduce the game's heap, so size must be bounded and observed in-game.

Appending bytes without a load segment does not load them. Growing segment 0 would overlap segment 1; moving segment 1 would invalidate untracked relationships. Growing segment 1's file size past its current initialized bytes would materialize the entire large BSS before any safe tail payload. The separate segment is therefore the least intrusive structural candidate. A verified game allocator/file-loading hook is another option for large assets, but its ownership, lifetime, and failure handling must be established first.

These steps concern the decrypted PRX. Repacking an encrypted PSP header or shipping a plain test ELF is a separate, loader-specific build decision; do not retain stale encrypted-header segment sizes/signatures. No compatibility with native PSP loading has yet been demonstrated by this audit.

## Isolated live allocation route

The game already imports all three required partition-memory functions. The `SysMemUserForUser` descriptor is module `0x2947b8` (file `0x294878`). Its 20-byte layout is `<u32 name,u16 version,u16 flags,u8 length_words,u8 variable_count,u16 function_count,u32 nid_table,u32 stub_table>`. Values are name `0x2949a0`, version `0x11`, flags `0x4000`, length 5 words, zero variables, **six functions**, NID table module `0x294c40`, stubs module `0x29430c`. The length byte 5 is not the function count.

| Function | NID | Callable loaded stub, module-relative | NID file offset |
| --- | --- | --- | --- |
| `sceKernelAllocPartitionMemory` | `0x237dbd4f` | `0x294324` | `0x294d0c` |
| `sceKernelGetBlockHeadAddr` | `0x9d9a5ba1` | `0x294334` | `0x294d14` |
| `sceKernelFreePartitionMemory` | `0xb6d61d02` | `0x294314` | `0x294d04` |

These associations agree with the [PSPSDK import definitions](https://github.com/pspdev/pspsdk/blob/master/src/user/SysMemUserForUser.S). Add the observed module load base to stub addresses; do not call the unlinked `jr ra; nop` placeholders in the on-disk ELF.

The game wrapper beginning at module `0x127864` calls allocate at `0x1278c4`, checks its returned UID, then calls get-head at `0x1278dc`. It requests user partition 2, allocation type 3, size from its heap configuration, name literal `UserSbrk` at module `0x2f3d14`, and fifth argument `0x1000` in register `$t0`. It stores the UID at `0x11f470c`, the current/end/base pointers at `0x11f4700/0x11f4708/0x11f4704`, and subsequently serves allocations by moving those pointers. Its free routine starts at `0x127b38`, calls free at `0x127b64`, and clears the heap UID. Calling either wrapper would alter the game's shared heap state.

For the isolated VWF experiment, call the loaded imports directly: allocate with `$a0=2`, `$a1` pointing to a valid immutable name string, `$a2=1` (High), `$a3=0x23000`, and `$t0=0`; save the returned positive UID in experiment-owned state. Pass that UID in `$a0` to get-head, and validate the returned range before writing. Save/restore the interrupted thread's registers and return context. Restore every hook/pointer before passing the saved UID to free, and never free the game's `UserSbrk` UID. The API contracts, including High=1 and UID-to-base conversion, are documented in [PSPSDK's memory header](https://github.com/pspdev/pspsdk/blob/master/src/user/pspsysmem.h). Allocation failure must abort the experiment without installing hooks. This route is statically verified; the audit did not invoke it or allocate emulator memory.

## Game heap allocation fallback

The parent experiment reported a `0x23000` partition allocation failing with `0x800200d9`, with registers/scratch restored and no hooks installed. This is consistent with user RAM already being reserved by the game, but that cause has not been proven. The executable has a regular heap allocation/free pair above `UserSbrk`, suitable for requesting an owned chunk from the game's reserved heap:

| Routine | Module-relative address | File offset | Calling convention |
| --- | --- | --- | --- |
| Public malloc wrapper | `0x12815c` | `0x12821c` | `$a0=byte size`; `$v0=pointer`, or zero on failure |
| Public free wrapper | `0x128180` | `0x128240` | `$a0=original malloc pointer`; no useful return value established |
| Reentrant malloc implementation | `0x12cb28` | `0x12cbe8` | `$a0=reent`, `$a1=size` |
| Reentrant free implementation | `0x12d15c` | `0x12d21c` | `$a0=reent`, `$a1=pointer` |

Both public wrappers move their sole argument into `$a1` and fetch `$a0` from the shared reentrancy pointer at module `0x471a3c` (original value `0x471750`), then call the matching implementation. The allocator manages size-tagged, split/coalesced chunks and free bins at module `0x471a78`; it rounds chunk sizes to multiples of 16. Its growth routine `0x12c840` calls `0x12ea3c`, which calls the already traced `UserSbrk` at `0x127864`. At `0x12d148`, successful malloc returns the selected chunk address plus eight bytes; at `0x12d110–0x12d118`, failure unlocks and returns zero. Free starts by handling null and locating the header eight bytes before the passed pointer, then merges adjacent free chunks.

The higher game wrapper at `0x1a3400` calls public malloc at `0x1a340c`, but invokes `0x1a4a3c` on allocation failure; its behavior should not be used for the experiment. Call `base+0x12815c` directly with size `0x23000`. A nonzero validated pointer is a new owned heap allocation, not a block UID. Keep that exact pointer in experiment-owned state and eventually pass it to `base+0x128180`; never use partition-free on it. If a separately aligned interior pointer is used for textures, retain and free the original allocation pointer.

Heap lock `0x12d7e0` calls the imported interrupt-suspend stub at `0x29439c`, increments nesting at module `0x11f48b4`, and saves the first interrupt mask at `0x11f48b8`. Unlock `0x12d81c` decrements nesting and resumes interrupts through `0x2943bc` when it reaches zero. Inject only from a verified idle context outside heap routines with this nesting count zero: interrupt suspension does not make an interrupted, half-updated heap safe for recursive allocation. Preserve the interrupted registers/stack/return context, validate ownership and bounds, and restore hooks/pointers before freeing the allocation. This fallback is supported by static disassembly only; no allocator was called during this audit.

## Persistent startup candidate and segment-relative records

An appended third load segment is structurally supported by the loader, but **does not fit inside unused original BSS**. The allocation span must grow to include its new end. At observed module base `0x08804000`, the original end is `0x09efdacc`; the proposed aligned segment starts at `0x09efdb00`. No live memory availability or native PSP load success is established here. The original `UserSbrk` configuration word at module `0x302840` is `0x200`: its shift by ten requests a fixed 512 KiB heap. Adding a large initialized font bank to the module can compete with that reservation. A small appended code/state segment plus an owned game-malloc font allocation is therefore a better candidate than storing the whole high-resolution bank in the new load segment. Embedded bank bytes still cost loaded memory; loading them dynamically from a separate asset avoids that cost.

For a conventional third `PT_LOAD` at PH index 2, ordinary REL1 records use these exact `r_info` values (offset always relative to the segment being patched):

| Patch | `r_info` | Stored addend before loader relocation |
| --- | --- | --- |
| Original code jumps to new segment | `0x00020004` | New target's offset **within segment 2**, encoded as J/JAL target divided by four |
| New code calls original segment 0 | `0x00000204` | Original module-relative target divided by four |
| New pointer word targets original segment 0 | `0x00000202` | Original module-relative address |
| New pointer word targets segment 2 | `0x00020202` | Offset within segment 2 |

Replace the existing relocation at a patched original call, rather than adding another record that relocates the same instruction twice. HI/LO records use the same segment-byte scheme with type 5/6 and paired signed-low carry. PC-relative branches do not need base relocation. Live hook bytes containing absolute `0x08.../0x09...` addresses cannot simply be copied into a persistent PRX.

The resident-bank initializer at module `0xea204` has one direct call, **`0x4c0ec`**, file `0x4c1ac`. Its existing REL1 record is index 7,565, currently `(r_offset=0x4c0ec,r_info=4)`, in the original text relocation section. That record can target a wrapper in segment 2 by changing its target-base byte and storing the wrapper's segment-local offset. Preserve call delay slot `0x4c0f0`, `move $t2,$v0`.

The calling loader-state routine starts at `0x4bf84`. It obtains the font manager via `0xe928c` at `0x4c03c`, saves it in `$s0`, obtains resource IDs 8–13 through `0x8d080`, then passes manager/font/charset pointers to `0xea204`. That initializer constructs descriptors at manager `+4/+8/+0xc`, assigns pixel pointers, builds lookup tables, and initializes the palette. A wrapper can save the incoming manager and caller return address, call the original initializer first, validate manager `+4` and its count/table/pixels, then allocate and prepare the translation bank. Return to **`0x4c0f4`** with the original call result/register contract preserved; startup continues through `0xeb8e0` and `0xeb930`. This is a structurally suitable point after bank readiness and before the loader reports completion, not a live-verified startup hook.

Frequency is controlled by the loader object's signed halfword at `+0x32`: state 0 starts loading and sets 1; state 1 polls readiness through `0x8cf08`, sets 2 before the initializer, and installs the resident bank; state 2 reports completion without repeating initialization. The containing routine is polled through its direct caller at `0x4c304`. The hook consequently runs once per successful loader-object cycle, **not necessarily once per process**: resets or reloads can repeat it. Guard against an already translated descriptor, record original descriptor generation/table/pixel addresses, and handle teardown/reload ownership before reusing or freeing the allocated font. The much more widely called getter `0xe928c` is not an equivalent once-only readiness hook.

## Static candidate audit and PPSSPP boot routes

`tools/build_menu_patch.py` uses another valid REL1 representation: all address addends are absolute **module-relative** values, including `0x16f9b00 + payload_offset`, and their target-base byte remains zero. The new records' patch segment is 2; this selects the write location independently from the target segment. Existing original call/menu relocations therefore remain target-0 records. This differs from the segment-local addends in the example table above and must not be mixed with them. Independent read-only checks of the 23 added records passed HI/ADDIU signed-low carry and J-region reconstruction at bases `0x08804000`, `0x08808000`, and `0x08810000`. Payload size was 221,840 bytes. Static disassembly confirms `0xea204` consumes its seven arguments from registers A0–T2, without incoming stack arguments; the wrapper's additional 32-byte frame does not shift an argument. These checks do not establish successful cold boot or available RAM.

The current [PPSSPP command-line implementation](https://github.com/hrydgard/ppsspp/blob/master/Core/CmdLine.cpp) declares `--mount`/`-m` for the **Headless** mode only. `--root` maps `host0:/` and does not replace the UMD mount. Avoid assuming GUI `PPSSPPWindows64.exe --mount=... patched.elf` will mount the original game disc. The [file detector](https://github.com/hrydgard/ppsspp/blob/master/Core/Loaders.cpp) recognizes a directory containing `PSP_GAME` as `PSP_DISC_DIRECTORY`; [MountGameISO and Load_PSP_ISO](https://github.com/hrydgard/ppsspp/blob/master/Core/PSPLoaders.cpp) then mount it through `VirtualDiscFileSystem` as `umd0:`, `umd1:`, `umd:`, and `disc0:`. Thus a separate complete staged disc tree with patched `PSP_GAME/SYSDIR/EBOOT.BIN` can be passed as the GUI boot path. A separate copied ISO with the patched EBOOT extent/length is the closer equivalent to the original game's sector-backed disc.

The disc loader accepts ELF magic in EBOOT.BIN, so a decrypted candidate need not be re-encrypted for this PPSSPP test. Do not place an original backup at an alternative boot name such as `EBOOT.OLD`: PPSSPP can select that file instead of the candidate. Existing installed `PBOOT.PBP` game updates can also override the disc executable. These routes are supported by current upstream source; behavior of the installed PPSSPP version still requires the parent's isolated cold-boot check. No emulator was accessed during this audit.
