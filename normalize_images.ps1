#!/usr/bin/env pwsh
# Decode percent-encoded image path segments, move files to decoded directories,
# update HTML files to reference decoded paths, and remove empty directories.

$repoRoot = Split-Path -Path $PSScriptRoot -Parent -ErrorAction SilentlyContinue
if (-not $repoRoot) { $repoRoot = "C:\Users\slick\dugnictravelsandexpeditions.com" }
$imagesRoot = Join-Path $repoRoot 'images'

Write-Host "Normalizing images under $imagesRoot"

function Decode-PathSegments($path) {
    $segments = $path -split '[\\/]'
    $decoded = @()
    foreach ($s in $segments) {
        if ($s -eq '') { continue }
        $decoded += [System.Uri]::UnescapeDataString($s)
    }
    return (Join-Path -Path $decoded)
}

# Move files to decoded path locations
Get-ChildItem -Path $imagesRoot -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
    $file = $_
    $rel = $file.FullName.Substring($repoRoot.Length).TrimStart('\', '/')
    $decodedRel = [System.Uri]::UnescapeDataString($rel)
    $target = Join-Path $repoRoot $decodedRel
    $targetDir = Split-Path $target -Parent
    if ($file.FullName -ieq $target) { return }
    if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
    try {
        Move-Item -Path $file.FullName -Destination $target -Force
        Write-Host "Moved: $($file.FullName) -> $target"
    } catch {
        Write-Warning "Failed to move $($file.FullName): $($_.Exception.Message)"
    }
}

# Update HTML files to replace percent-encoded references with decoded ones
Get-ChildItem -Path (Join-Path $repoRoot 'en') -Recurse -Include '*.html' -File -ErrorAction SilentlyContinue | ForEach-Object {
    $htmlFile = $_.FullName
    $orig = Get-Content -Raw -LiteralPath $htmlFile -ErrorAction SilentlyContinue
    if (-not $orig) { return }
    $decoded = [System.Uri]::UnescapeDataString($orig)
    if ($decoded -ne $orig) {
        Set-Content -LiteralPath $htmlFile -Value $decoded -Encoding utf8
        Write-Host "Updated HTML references in: $htmlFile"
    }
}

# Remove empty directories leftover (images only)
Get-ChildItem -Path $imagesRoot -Recurse -Directory -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object {
    if (-not (Get-ChildItem -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue)) {
        try { Remove-Item -LiteralPath $_.FullName -Force -Recurse -ErrorAction SilentlyContinue; Write-Host "Removed empty dir: $($_.FullName)" } catch {}
    }
}

Write-Host "Image normalization complete."
