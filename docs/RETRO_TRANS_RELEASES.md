# Retro Trans release packaging

Follow the [Retro Trans release standard](https://github.com/retro-trans/retro-trans-tools/blob/main/docs/RELEASE_STANDARD.md), using stable game ID `heroes-phantasia`, platform `PSP`, language `en`, edition `English` and repository `retro-trans/Heroes-Phantasia`.

The first public version is **0.1.45**, reproducing the exact reviewed local candidate. Its full patch takes only the original Japanese ISO; earlier local builds are not public upgrade sources. Read the release notes for actual testing coverage.

`tools/package_release.py --source-commit <full-commit>` previews exact inputs and the packaging plan. Add `--write` after reviewing it. The wrapper uses a verified pinned Retro Trans checkout under ignored `work/source/release_045/retro-trans-tools`; it hashes both ISOs, builds xdelta, decodes it into a temporary target and verifies the entire result. The canonical output contains only the patch, `BUILD-MANIFEST.json`, `VALIDATION.json` and `SHA256SUMS.txt`. Private paths and complete game binaries are excluded.

Before committing, run `tools/strip_jp.py`, then `tools/audit_public_sources.py` against the staged index. Publish the source commit, create a draft release, upload the patch, validation and checksums, and upload the manifest last. Verify every uploaded size/hash before publishing. Never overwrite a published asset.

After publishing, run the Retro Trans Tools **Refresh patch catalog** workflow with `repository=retro-trans/Heroes-Phantasia`. Check that the scoped validation succeeds and the manifest appears in the public catalog. Verify the original-to-0.1.45 route and current-version no-op. Release packaging proves byte reproduction; it does not replace gameplay testing.
