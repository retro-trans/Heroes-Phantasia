param(
    [Parameter(Mandatory=$true)][string]$Frames,
    [Parameter(Mandatory=$true)][string]$Output,
    [switch]$Write,
    [int]$Limit = 0,
    [double]$Scale = 2
)
# Run with WindowsPowerShell5.1. Recognition is local; Japanese output must stay
# inside ignored work/source. A dry run lists inputs without recognizing/writing.
$ErrorActionPreference = 'Stop'
$frameRoot = (Resolve-Path -LiteralPath $Frames).Path
$sourceRoot = [IO.Path]::GetFullPath((Join-Path (Get-Location) 'work/source'))
$outputPath = [IO.Path]::GetFullPath($Output)
if (-not $outputPath.StartsWith($sourceRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'OCR source output must stay in ignored work/source.' }
if ($Scale -le 0) { throw 'Scale must be positive.' }
$images = @(Get-ChildItem -LiteralPath $frameRoot -Filter 'frame*.png' | Sort-Object Name)
if ($Limit -gt 0) { $images = @($images | Select-Object -First $Limit) }
if ($images.Count -eq 0) { throw 'No frame PNGs.' }
if (-not $Write) {
    [pscustomobject]@{ mode='dry'; frames=$images.Count; first=$images[0].FullName; last=$images[-1].FullName; output=$outputPath; source_scale=$Scale; recognition_verified=$false } | ConvertTo-Json
    exit
}
if (Test-Path -LiteralPath $outputPath) { throw 'Refuse existing output.' }
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
function Await-WinRT($Operation, [Type]$ResultType) {
    $task = $asTask.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}
$language = New-Object Windows.Globalization.Language 'ja'
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
if ($null -eq $engine) { throw 'Japanese OCR recognizer unavailable.' }
$rows = New-Object System.Collections.Generic.List[object]
foreach ($image in $images) {
    $file = Await-WinRT ([Windows.Storage.StorageFile]::GetFileFromPathAsync($image.FullName)) ([Windows.Storage.StorageFile])
    $stream = Await-WinRT ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    try {
        $decoder = Await-WinRT ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await-WinRT ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        try {
            $result = Await-WinRT ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            $lines = @($result.Lines | ForEach-Object {
                $line = $_
                $words = @($line.Words | ForEach-Object { [pscustomobject]@{ text=$_.Text; x=$_.BoundingRect.X/$Scale; y=$_.BoundingRect.Y/$Scale; width=$_.BoundingRect.Width/$Scale; height=$_.BoundingRect.Height/$Scale } })
                [pscustomobject]@{ text=$line.Text; words=$words }
            })
            $rows.Add([pscustomobject]@{ frame=$image.Name; frame_sha256=(Get-FileHash -LiteralPath $image.FullName -Algorithm SHA256).Hash.ToLowerInvariant(); source_scale=$Scale; text=$result.Text; lines=$lines; human_verified=$false })
        } finally { $bitmap.Dispose() }
    } finally { $stream.Dispose() }
    if ($rows.Count % 25 -eq 0) { Write-Host ('Recognized '+$rows.Count+'/'+$images.Count+' local frames; unverified.') }
}
$report = [pscustomobject]@{ schema_version=1; status='local_ocr_source_candidates_not_verified_transcript'; recognizer_language='ja'; frame_count=$rows.Count; frames=$rows }
[IO.File]::WriteAllText($outputPath, ($report | ConvertTo-Json -Depth 12), (New-Object System.Text.UTF8Encoding($false)))
Write-Host ('Wrote ignored OCR candidates: '+$outputPath)
