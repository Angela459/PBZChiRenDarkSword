param([Parameter(Mandatory=$true)][string]$ModRoot, [string]$InstallVersion = 'v1.1')
$ErrorActionPreference = 'Stop'
$modFolder = (Resolve-Path -LiteralPath $ModRoot).Path.TrimEnd('\', '/')
$gameFolder = [IO.Path]::GetFullPath((Join-Path $modFolder '../../../../../'))
$menuFolder = Join-Path $gameFolder 'ProjectPBZ/Content/JavaScript/PBZModsMenu'
if (-not (Test-Path -LiteralPath (Join-Path $menuFolder 'bootstrap.js'))) { exit 0 }
$id = 'PBZChiRenDarkSword'
$entryFolder = Join-Path $menuFolder "Mods/$id"
[IO.Directory]::CreateDirectory($entryFolder) | Out-Null
$utf8 = New-Object Text.UTF8Encoding($false)
$source = [IO.File]::ReadAllText((Join-Path $modFolder 'Menu/main.js'))
$installed = $source.Replace('const MOD_ROOT = null;', ('const MOD_ROOT = ' + (ConvertTo-Json -InputObject $modFolder -Compress) + ';'))
$entryPath = Join-Path $entryFolder 'main.js'
if (-not (Test-Path -LiteralPath $entryPath) -or [IO.File]::ReadAllText($entryPath) -ne $installed) {
    [IO.File]::WriteAllText($entryPath, $installed, $utf8)
}
$discoveredPath = Join-Path $menuFolder 'discovered.txt'
if (Test-Path -LiteralPath $discoveredPath) {
    $manifest = [IO.File]::ReadAllText($discoveredPath) | ConvertFrom-Json
} else {
    $manifest = [pscustomobject]@{ version=1; mods=@([pscustomobject]@{ id='PBZModsMenu'; entry='PBZModsMenu/Mods/PBZModsMenu/main'; enabled=$true }) }
}
$manifest.mods = @($manifest.mods | Where-Object { $_.id -ne 'PBZChiRenAudioReplace' })
if (-not (@($manifest.mods | Where-Object { $_.id -eq $id }).Count)) {
    $manifest.mods = @($manifest.mods) + @([pscustomobject]@{ id=$id; entry="PBZModsMenu/Mods/$id/main"; enabled=$true })
}
[IO.File]::WriteAllText($discoveredPath, ($manifest | ConvertTo-Json -Depth 8) + "`r`n", $utf8)
[IO.File]::WriteAllText((Join-Path $modFolder 'Menu/install-version.txt'), $InstallVersion + "`r`n", $utf8)
