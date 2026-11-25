<#
.SYNOPSIS
Dá nome aos blocos de um mapa (sem IA do Graphify).

.DESCRIPTION
Sem -Aplicar: gera nomes/<Nome>.blocos.txt, a lista dos blocos com a chave,
as pastas e as peças principais de cada um (os que ainda não têm nome nosso
vêm marcados com "<-- falta nome").

Com -Aplicar: lê nomes/<Nome>.txt (uma linha por bloco, "chave|nome"), grava
os nomes no mapa e confere que cada um caiu no bloco certo.

A chave é a peça mais ligada do bloco, então o nome continua valendo mesmo
se o Graphify renumerar os blocos.

.EXAMPLE
./nomear.ps1 -Nome rocketseat            # gera a lista
./nomear.ps1 -Nome rocketseat -Aplicar   # aplica os nomes escritos
#>
param(
    [Parameter(Mandatory)] [string] $Nome,
    [switch] $Aplicar
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_comum.ps1')

$mapa = Get-KitMapa $Nome
New-Item -ItemType Directory -Force $KitNomes | Out-Null
$arquivo = Join-Path $KitNomes "$Nome.txt"

if ($Aplicar) {
    if (-not (Test-Path $arquivo)) { throw "Não existe $arquivo (formato: chave|nome, uma linha por bloco)." }
    Invoke-KitMapa aplicar-nomes $mapa $arquivo
}

$lista = Join-Path $KitNomes "$Nome.blocos.txt"
Invoke-KitMapa blocos $mapa --nomes $arquivo --saida $lista
if (-not $Aplicar) {
    Write-Host "Escreva os nomes em $arquivo (chave|nome) e rode: ./nomear.ps1 -Nome $Nome -Aplicar"
}
