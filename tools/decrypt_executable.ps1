param([switch]$Execute)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$upstreamRoot = Join-Path $projectRoot 'work/source/third_party/pspdecrypt'
$inputFile = Join-Path $projectRoot 'work/source/PSP_GAME/SYSDIR/EBOOT.BIN'
$outputFile = Join-Path $projectRoot 'work/source/PSP_GAME/SYSDIR/EBOOT.decrypted.elf'
$revision = 'c156627db7634d395c380c0a9589130f603307fc'
Write-Output "Plan: use John-K/pspdecrypt revision $revision under ignored work/source."
Write-Output "Compile bundled libkirk + PrxDecrypter with the local ELF-only driver."
Write-Output "Read $inputFile; write $outputFile; refuse an existing output."
if (-not $Execute) { Write-Output 'Dry run: add -Execute after reviewing this plan.'; return }
if (Test-Path -LiteralPath $outputFile) { throw 'Output exists; preserving it.' }
if (-not (Test-Path -LiteralPath $upstreamRoot)) {
    & git clone https://github.com/John-K/pspdecrypt.git $upstreamRoot
    if ($LASTEXITCODE -ne 0) { throw 'Source download failed.' }
}
& git -C $upstreamRoot checkout --detach $revision
if ($LASTEXITCODE -ne 0) { throw 'Could not select documented upstream revision.' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'decrypt_prx.cpp') -Destination (Join-Path $upstreamRoot 'decrypt_game.cpp')
Push-Location $upstreamRoot
try {
    $cSources = Get-ChildItem -LiteralPath (Join-Path $upstreamRoot 'libkirk') -Filter '*.c' | ForEach-Object FullName
    & gcc -O2 -c $cSources
    if ($LASTEXITCODE -ne 0) { throw 'libkirk compile failed.' }
    $objectFiles = Get-ChildItem -LiteralPath $upstreamRoot -Filter '*.o' | ForEach-Object FullName
    & g++ -std=c++11 -O2 -o decrypt_game.exe decrypt_game.cpp PrxDecrypter.cpp $objectFiles
    if ($LASTEXITCODE -ne 0) { throw 'Decrypter compile failed.' }
    & (Join-Path $upstreamRoot 'decrypt_game.exe') $inputFile $outputFile
    if ($LASTEXITCODE -ne 0) { throw 'Decryption or ELF verification failed.' }
} finally { Pop-Location }
