# Retro Trans release packaging

Follow the [Retro Trans release standard](https://github.com/retro-trans/retro-trans-tools/blob/main/docs/RELEASE_STANDARD.md), using stable game ID `heroes-phantasia`, platform `PSP`, language `en`, edition `English` and repository `retro-trans/Heroes-Phantasia`.

The first public version is **0.1.45**, reproducing the exact reviewed local candidate. Its full patch takes only the original Japanese ISO; earlier local builds are not public upgrade sources. Read the release notes for actual testing coverage.

The authorized **0.1.50** release uses `tools/package_release_050.py --source-commit <full-commit>` (add `--write` after reviewing the dry plan), with Retro Trans Tools pinned to `540a61cb6bb50a6ec8f2a52bc4e89a25226c9061` under `work/source/release_050/retro-trans-tools`. It builds a full patch from the original and an upgrade from the exact published 0.1.45 ISO. Both must decode to the reviewed 0.1.50 ISO, SHA-256 `fa420a494942817a7498615716b8b43bbc5ff4a817abb3cdb4354a90e89df8b8`. Package and catalog verification do not replace gameplay testing.

`tools/package_release.py --source-commit <full-commit>` previews exact inputs and the packaging plan. Add `--write` after reviewing it. The wrapper uses a verified pinned Retro Trans checkout under ignored `work/source/release_045/retro-trans-tools`; it hashes both ISOs, builds xdelta, decodes it into a temporary target and verifies the entire result. The canonical output contains only the patch, `BUILD-MANIFEST.json`, `VALIDATION.json` and `SHA256SUMS.txt`. Private paths and complete game binaries are excluded.

Before committing, run `tools/strip_jp.py`, then `tools/audit_public_sources.py` against the staged index. Publish the source commit, create a draft release, upload the patch, validation and checksums, and upload the manifest last. Verify every uploaded size/hash before publishing. Never overwrite a published asset.

After publishing, run the Retro Trans Tools **Refresh patch catalog** workflow with `repository=retro-trans/Heroes-Phantasia`. Check that the scoped validation succeeds and the manifest appears in the public catalog. Verify original-to-latest, each advertised upgrade source and the current-version no-op. Release packaging proves byte reproduction; it does not replace gameplay testing.
