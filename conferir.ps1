<#
.SYNOPSIS
Autoteste: confere se a versão do Graphify em versao.txt ainda serve pro kit.

.DESCRIPTION
Monta do zero o mapa do projeto exemplo/ (respostas conhecidas) e confere
.tsx, dependências, "quem usa" e o filtro de ciclos só de tipo. Também
confere que a pasta exemplo/ não foi tocada. Rodar sempre depois de trocar
a versão em versao.txt.

.EXAMPLE
./conferir.ps1
#>
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_comum.ps1')

Install-KitAmbiente
$exemplo = Join-Path $Kit 'exemplo'
$mapa = Join-Path $KitMapas '_exemplo'
if (Test-Path $mapa) { Remove-Item -Recurse -Force $mapa -Confirm:$false }
New-Item -ItemType Directory -Force $mapa | Out-Null

$foto = Join-Path $mapa 'foto-da-pasta.json'
Invoke-KitMapa foto $exemplo $foto
Invoke-KitGraphify extract $exemplo --out $mapa | Out-Null
Invoke-KitGraphify cluster-only $mapa | Out-Null
Write-Host "Autoteste do graphifyy $KitVersao"
Invoke-KitMapa autoteste $mapa
Invoke-KitMapa comparar-foto $exemplo $foto
Write-Host "graphifyy $KitVersao passou. Anote no HISTORICO.md."
