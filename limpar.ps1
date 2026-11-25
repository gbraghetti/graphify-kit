<#
.SYNOPSIS
Desinstala o Graphify do kit e confere que nada ficou pra trás.

.DESCRIPTION
Apaga o .venv (o Graphify inteiro mora nele) e os mapas. Os nomes dos
blocos (nomes/) ficam, a não ser com -ApagarNomes: com eles, montar de novo
recupera os mesmos nomes.

Depois procura sobras nos lugares onde o Graphify instalaria algo se fosse
usado do jeito padrão (skill, ganchos, servidor MCP, caches, comando no
PATH) e nas pastas que foram mapeadas.

.EXAMPLE
./limpar.ps1
./limpar.ps1 -ApagarNomes
#>
param([switch] $ApagarNomes)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_comum.ps1')

# As pastas mapeadas, antes de apagar os mapas
$raizes = @()
if (Test-Path $KitMapas) {
    $raizes = Get-ChildItem $KitMapas -Directory | ForEach-Object {
        $r = Join-Path $_.FullName 'graphify-out\.graphify_root'
        if (Test-Path $r) { (Get-Content $r -Raw).Trim() }
    } | Sort-Object -Unique
}

foreach ($p in @($KitVenv, $KitMapas) + $(if ($ApagarNomes) { $KitNomes } else { @() })) {
    if (Test-Path $p) {
        Remove-Item -Recurse -Force $p -Confirm:$false
        Write-Host "Apagado: $p"
    }
}

$sobras = @()
foreach ($cmd in 'graphify', 'graphify-mcp') {
    $c = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($c) { $sobras += "Comando '$cmd' no PATH: $($c.Source)" }
}
$lugares = @(
    (Join-Path $HOME '.graphify'),
    (Join-Path $HOME '.cache\graphify-queries.log'),
    (Join-Path $HOME '.claude\skills\graphify'),
    (Join-Path $env:LOCALAPPDATA 'graphify')
)
foreach ($l in $lugares) { if (Test-Path $l) { $sobras += "Existe: $l" } }
$cache = Join-Path $HOME '.cache'
if (Test-Path $cache) {
    Get-ChildItem $cache -Filter 'graphify*' -ErrorAction SilentlyContinue | ForEach-Object { $sobras += "Existe: $($_.FullName)" }
}
$claudeJson = Join-Path $HOME '.claude.json'
if ((Test-Path $claudeJson) -and (Select-String -Path $claudeJson -Pattern '"graphify' -Quiet)) {
    $sobras += "Servidor MCP 'graphify' registrado no Claude Code ($claudeJson): claude mcp remove graphify"
}
foreach ($r in $raizes) {
    foreach ($f in 'graphify-out', '.graphifyignore', '.graphifyrc') {
        $p = Join-Path $r $f
        if (Test-Path $p) { $sobras += "Na pasta mapeada: $p" }
    }
    $hooks = Join-Path $r '.git\hooks'
    if (Test-Path $hooks) {
        Get-ChildItem $hooks -File | Where-Object { $_.Extension -ne '.sample' } |
            Where-Object { Select-String -Path $_.FullName -Pattern 'graphify' -Quiet } |
            ForEach-Object { $sobras += "Gancho de git com graphify: $($_.FullName)" }
    }
}

Write-Host ""
if ($sobras.Count -eq 0) {
    Write-Host "Nada do Graphify ficou na máquina (conferido também em: $($raizes -join ', '))."
} else {
    Write-Host "Sobras encontradas (não apaguei, confira):"
    $sobras | ForEach-Object { Write-Host "  $_" }
    exit 1
}
