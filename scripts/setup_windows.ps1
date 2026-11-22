<#
 CUTAWAY studio setup for Windows (PowerShell). Safe by default: it only CHECKS what is installed.
   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1            # check only
   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -Install   # offers to install missing tools
With -Install it asks Y/N before EACH program and uses winget (built into Windows 10/11). Nothing is
installed without your answer. Each install is several hundred MB: with an HDD, install one at a time.
The winget package IDs below are the usual ones; the script first runs "winget show" so you can see the
real name/publisher before confirming. If an ID is wrong, install from the official site instead (docs\TOOLS.md).
#>
param([switch]$Install)
$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Test-Cmd($n) { return [bool](Get-Command $n -ErrorAction SilentlyContinue) }
Write-Host "== CUTAWAY studio check ==" -ForegroundColor Cyan
if (-not (Test-Cmd python)) { Write-Host "Python not found. Install Python 3.10+ from python.org, then re-run." -ForegroundColor Yellow }
else {
  python --version
  Write-Host "Python packages (pillow, pyyaml, numpy):"
  python -m pip install --user -r requirements.txt   # small, pure-Python; safe
  python -m studio.doctor
}

if ($Install) {
  if (-not (Test-Cmd winget)) { Write-Host "winget not found; use the manual links in docs\TOOLS.md" -ForegroundColor Yellow; exit 1 }
  $tools = @(
    @{ key="blender";    id="BlenderFoundation.Blender"; name="Blender (3D, free)" },
    @{ key="freecadcmd"; id="FreeCAD.FreeCAD";           name="FreeCAD (CAD, free)" },
    @{ key="kdenlive";   id="KDE.Kdenlive";              name="Kdenlive (video editor, free)" }
  )
  foreach ($t in $tools) {
    $found = python -c "from studio.paths import find_tool; print(find_tool('$($t.key)') or '')"
    if ($found) { Write-Host "$($t.name): already found at $found" -ForegroundColor Green; continue }
    Write-Host "`n$($t.name) is missing." -ForegroundColor Yellow
    winget show --id $t.id --exact
    $a = Read-Host "Install $($t.name) now with winget? (y/N)"
    if ($a -match '^(y|yes)$') { winget install --id $t.id --exact --source winget }
    else { Write-Host "Skipped." }
  }
  Write-Host "`nRe-run without -Install (or: python -m studio.doctor) to see what was found."
}
Write-Host "`nOptional: Ollama (local Qwen) from https://ollama.com ; then: ollama pull qwen2.5:7b"
