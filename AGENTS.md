** Organize folder like this **
work - work folder
    output - contains the file for testing (iso, zip, etc...)
    glossary - contains the one or many json files for glossary
    ui - contains screenshot of actual UI element ingame with label on screenshot if possible, contains files (json,py,...) describe the coordinate, width and height, id and other attributes
    translation/<language code> - contains the target translation of ui element or dialogues or anything that need translation
docs - documents
tools - any tools help with translation
incoming - outside files that need agent to look into

** SOME RULES **
- Avoid contains extensive Japanese scripts (UI elements is fine)
- Identified each build with version 0.x.y (start at 0.1.0)
- Always write change log
- If user told you to remember anything write it down here, make sure to ask user if the new one conflict with old one
- Do not create or publish a GitHub release until the user explicitly requests a release for that build. Translation and local builds do not imply release permission.
- Be conscious of subscription limit before creating sub-agents
- Consider using https://github.com/nationalsecurityagency/ghidra if applicable

** REMEMBER **
- Speech-bubble tails should point to the speaker's lips. Use reviewed portrait landmarks and scene placement when correcting them; resizing the English text box must preserve the intended speaker anchor. Record scoped fixes and unverified scenes instead of claiming automatic mouth tracking.
- Both protagonists' default surname, given name and epithet must use Latin characters in the English build, including the values restored by Restore Defaults. Preserve custom player input and validate the name-entry/storage limits before changing the defaults.
- Show the current build version above `github.com/retro-trans` in the bottom-right corner of the title screen. Update the displayed version for every new local build. Use `tools/build_local.py` so the title stamp and build manifest share the same version; older candidate builders are historical preparation tools.
- Create a variable-width font (VWF) for the English translation. Use 4x resolution if technically possible; confirm the game's font/rendering limits before choosing an implementation.
- Every new github release must work with [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools).
- Japanese script text must never be committed to git. Keeping it in local working files is fine: `.gitignore` covers `work/source/` and the translation working files. Commit only the `*.en.json` copies written by `tools/strip_jp.py` (run it before committing). Names and UI terms in Japanese are allowed.
