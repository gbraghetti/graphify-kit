<#
.SYNOPSIS
Monta (ou atualiza) o mapa de uma pasta, sem escrever nada dentro dela.

.DESCRIPTION
O mapa vai pra mapas/<Nome>/. Antes e depois, a pasta é fotografada: se
qualquer arquivo dela mudar, o script para com erro. Rodar de novo é
incremental (só relê o que mudou). Se existir nomes/<Nome>.txt, os nomes
dos blocos são aplicados no fim.

.EXAMPLE
./montar.ps1 -Pasta J:\workspace\development\rocketseat -Nome rocketseat

.EXAMPLE
./montar.ps1 -Pasta C:\workspace_c\next-projects\suaparte-project -Nome suaparte -Excluir e2e
#>
param(
    [Parameter(Mandatory)] [string] $Pasta,
    [Parameter(Mandatory)] [ValidatePattern('^[\w.-]+$')] [string] $Nome,
    [string[]] $Excluir = @()
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_comum.ps1')

Install-KitAmbiente
$Pasta = (Resolve-Path $Pasta).Path
$mapa = Join-Path $KitMapas $Nome
New-Item -ItemType Directory -Force $mapa | Out-Null

$foto = Join-Path $mapa 'foto-da-pasta.json'
Invoke-KitMapa foto $Pasta $foto

$argumentos = @('extract', $Pasta, '--out', $mapa)
foreach ($e in $KitExcluirPadrao + $Excluir) { $argumentos += @('--exclude', $e) }
$inicio = Get-Date
Invoke-KitGraphify @argumentos
Invoke-KitGraphify cluster-only $mapa

$nomes = Join-Path $KitNomes "$Nome.txt"
if (Test-Path $nomes) { Invoke-KitMapa aplicar-nomes $mapa $nomes }

Invoke-KitMapa comparar-foto $Pasta $foto
$segundos = [int]((Get-Date) - $inicio).TotalSeconds
$out = Join-Path $mapa 'graphify-out'
Write-Host ""
Write-Host "Mapa '$Nome' pronto em $segundos s."
Write-Host "  Relatório: $(Join-Path $out 'GRAPH_REPORT.md')"
Write-Host "  Navegar:   $(Join-Path $out 'graph.html')"
