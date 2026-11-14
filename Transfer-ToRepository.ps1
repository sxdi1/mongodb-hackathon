param([string]$Destination = 'C:\Users\radhe\Desktop\projects\mongodb-hackathon')
$ErrorActionPreference = 'Stop'
$sourceRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$targetRoot = [System.IO.Path]::GetFullPath($Destination)
if ($sourceRoot -eq $targetRoot) { throw 'Source and destination are identical.' }
if (-not (Test-Path -LiteralPath $targetRoot -PathType Container)) { throw 'Open/create the intended repository directory first.' }
$files = Get-ChildItem -LiteralPath $sourceRoot -Recurse -Force -File | Where-Object { $_.FullName -notmatch '[\\/](__pycache__|\.pytest_cache|\.venv|\.git)[\\/]' -and $_.Name -notmatch '\.sqlite' }
# Preflight every destination; never overwrite an existing file, including .env.
foreach ($file in $files) {
    $relative = [System.IO.Path]::GetRelativePath($sourceRoot, $file.FullName)
    $targetFile = Join-Path $targetRoot $relative
    if (Test-Path -LiteralPath $targetFile) { throw "Destination already contains $relative. No files copied; merge manually." }
}
foreach ($file in $files) {
    $relative = [System.IO.Path]::GetRelativePath($sourceRoot, $file.FullName)
    $targetFile = Join-Path $targetRoot $relative
    New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($targetFile)) | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $targetFile
}
Write-Host 'Project transferred. The local .env was copied and is ignored by Git. No commits were created.'
Write-Host 'Review COMMIT_MESSAGES.md before staging explicit project files.'
