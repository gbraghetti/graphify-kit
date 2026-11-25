<#
.SYNOPSIS
Pergunta coisas a um mapa já montado.

.DESCRIPTION
Perguntas:
  depende-de  tudo de que um arquivo (ou pasta) depende, em cadeia
  quem-usa    quem importa um arquivo, por nível (-Niveis, padrão 2)
  ciclos      ciclos de import de VALOR (os só de tipo ficam de fora)
  comparar    peças (hooks, schemas, inputs, tabelas…) que não aparecem
              em nenhum .md de uma pasta de documentação
  explicar    uma peça e as ligações dela (graphify explain)
  caminho     o caminho entre duas peças (graphify path)
  relatorio   onde estão o relatório e o mapa navegável

Caminhos de arquivo são relativos à pasta mapeada, com barra normal:
src/lib/viewer.ts

.EXAMPLE
./consultar.ps1 -Nome suaparte -Pergunta quem-usa -Alvo src/lib/live-events.ts
./consultar.ps1 -Nome suaparte -Pergunta depende-de -Alvo src/lib/live-events.ts, src/components/live-refresh
./consultar.ps1 -Nome rocketseat -Pergunta comparar -Alvo J:\workspace\development\rocketseat\_project-analysis
./consultar.ps1 -Nome suaparte -Pergunta explicar -Alvo groupAdminContext
#>
param(
    [Parameter(Mandatory)] [string] $Nome,
    [Parameter(Mandatory)]
    [ValidateSet('depende-de', 'quem-usa', 'ciclos', 'comparar', 'explicar', 'caminho', 'relatorio')]
    [string] $Pergunta,
    [string[]] $Alvo = @(),
    [int] $Niveis = 2
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_comum.ps1')

$mapa = Get-KitMapa $Nome
$grafo = Join-Path $mapa 'graphify-out\graph.json'

function Assert-KitAlvo([int]$Quantos) {
    if ($Alvo.Count -lt $Quantos) { throw "A pergunta '$Pergunta' precisa de $Quantos -Alvo." }
}

switch ($Pergunta) {
    'depende-de' { Assert-KitAlvo 1; Invoke-KitMapa depende-de $mapa @Alvo }
    'quem-usa' { Assert-KitAlvo 1; Invoke-KitMapa quem-usa $mapa $Alvo[0] --niveis $Niveis }
    'ciclos' { Invoke-KitMapa ciclos $mapa }
    'comparar' { Assert-KitAlvo 1; Invoke-KitMapa comparar $mapa $Alvo[0] }
    'explicar' { Assert-KitAlvo 1; Invoke-KitGraphify explain $Alvo[0] --graph $grafo }
    'caminho' { Assert-KitAlvo 2; Invoke-KitGraphify path $Alvo[0] $Alvo[1] --graph $grafo }
    'relatorio' {
        $out = Join-Path $mapa 'graphify-out'
        Write-Host "Relatório: $(Join-Path $out 'GRAPH_REPORT.md')"
        Write-Host "Navegar:   $(Join-Path $out 'graph.html')"
    }
}
