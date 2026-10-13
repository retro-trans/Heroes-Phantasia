param([switch]$Write)
$env:PYTHONPATH='tools;work/source/analysis_packages'
$env:PYTHONIOENCODING='utf-8'
$taskPython='C:/Users/Binh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$taskArguments=@('tools/build_local.py',
 '--base-manifest','work/output/0.1.50-title-credit-vwf-4x-candidate/manifest.en.json',
 '--archive','work/output/0.1.51-ui-dialogue-assets/HP.CPK',
 '--executable','work/output/0.1.51-ui-dialogue-assets/EBOOT.BIN',
 '--executable-report','work/output/0.1.51-ui-dialogue-assets/executable.en.json',
 '--prologue-movie','work/output/0.1.23-prologue-candidate/HPMOVE03.PMF',
 '--prologue-proof','work/output/0.1.23-prologue-candidate/HPMOVE03.PMF.en.json',
 '--prologue-proof-sha256','75b5efc82806a85fb1390d3dd6138f2f08b6aa1f77d2043b33a2f9462b4b34c9',
 '--prologue-movie-sha256','c2f6dbaa03b713c42ffad7e60c66f8664ea6d1def5bd82513fd75adb076d5946')
if ($Write) {$taskArguments+='--write'}
& $taskPython @taskArguments
exit $LASTEXITCODE
