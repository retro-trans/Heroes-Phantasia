# Speech bubble lip references

Version 0.1.31 corrects the Princess Serish shot containing “Who will accompany you?” in both protagonist variants. The preceding horizontal fit scaled every X coordinate, including the tail. In this shot it placed the outline tip near (200.5,104), above and left of the mouth.

The original phase animation ends at bubble shape 8 and center (369,99). The Serish portrait ends at (222,148). Her visually reviewed mouth landmark is approximately (117,114) in the 192×256 portrait, relative to pivot (96,128). This gives local (21,-14) and screen (243,134), consistent with the supplied screenshot at twice the PSP frame dimensions.

The new helper changes only tip vertex 6 in the outline and both fill banks. The outline ends at (243,134); the fill tips retain native border offsets (+3.5,-1) and (-3.5,+1). The fitted box, text, nameplate, source control bytes and other vertices retain the inherited behavior. Geometry regenerates from the original template each frame.

The correction requires the exact body bytes, shape 8, final native center (369,99), stationary unit scale and zero rotation. Other lines, other positions, Japanese fallback and animated geometry retain the existing hook. This is a reviewed scene landmark, not automatic face detection or a general repair for every speech bubble. It also does not introduce upward growth or automatic wrapping.

`tools/prepare_serish_tail_compact.py` validates the frozen input, old hooks, typed relocations, font metadata and three loader bases before writing new assets. It reuses the obsolete pre-0.1.27 geometry slot, adds no loaded memory, and removes six obsolete HI/LO relocations. Three capture instructions use existing no-op slots in the active geometry helper; its final jump visits the guarded leaf before the native continuation. The original text/box behavior is preserved.

`tools/check_serish_tail_live.py` compares the inherited 0.1.29 instructions with the installed correction in the isolated PSP debugger, including negative cases and the register/stack ABI. Its synthetic window tests are separate from natural story playback; consult `work/ui/dialogue/0.1.31/tail_native_instruction.en.json` for current results. `tools/verify_serish_tail_build.py` checks the finished executable, selected archive records, nested title bytes and reviewed native title captures.

The larger 0.1.30 candidate passed nine instruction checks but stalled during the opening movie in the tested session. Its additional loaded memory is a suspected cause, not a proven kernel-allocation failure. It remains an interim candidate; the 0.1.31 implementation restores the 0.1.29 module footprint.

All 152 templates have been audited for later placement work: 120 standard tails, 15 stars, 15 rounded shapes and 2 rectangles. Standard families 3+10n through 10+10n have tip indices 1 through 8, with adjacent bases. A future general solution needs reviewed portrait landmarks and current scene transforms; the native bubble structure has no independent mouth coordinate.
