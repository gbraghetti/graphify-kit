# Peças comuns dos scripts do kit (carregado com ". _comum.ps1").

$Kit = $PSScriptRoot
$KitVenv = Join-Path $Kit '.venv'
$KitPython = Join-Path $KitVenv 'Scripts\python.exe'
$KitGraphifyExe = Join-Path $KitVenv 'Scripts\graphify.exe'
$KitMapas = Join-Path $Kit 'mapas'
$KitNomes = Join-Path $Kit 'nomes'
$KitFerramenta = Join-Path $Kit 'ferramentas\mapa.py'
$KitVersao = (Get-Content (Join-Path $Kit 'versao.txt') -TotalCount 1).Trim()

# Sem IA (nada sai da máquina) e sem log de consultas no perfil do usuário.
$env:GRAPHIFY_BACKEND = 'none'
$env:GRAPHIFY_QUERY_LOG_DISABLE = '1'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'

# Pastas que nunca entram no mapa (além do .gitignore de cada projeto e do
# node_modules, que o Graphify já pula).
$KitExcluirPadrao = @('.next', 'dist', 'build', 'coverage', '.turbo', '.velite')

function Install-KitAmbiente {
    if (-not (Test-Path $KitPython)) {
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            throw 'Python não encontrado. Instale o Python 3.11 ou mais novo.'
        }
        $v = & python -c "import sys; print('%d.%d' % sys.version_info[:2])"
        if ([version]$v -lt [version]'3.11') {
            throw "Python $v encontrado; o Graphify pede 3.11 ou mais novo."
        }
        Write-Host "Criando o ambiente isolado em $KitVenv"
        & python -m venv $KitVenv
        if ($LASTEXITCODE) { throw 'Falhou ao criar o .venv' }
    }
    $atual = & $KitPython -c "import importlib.metadata as m`ntry: print(m.version('graphifyy'))`nexcept Exception: print('')"
    if ($atual -ne $KitVersao) {
        Write-Host "Instalando graphifyy $KitVersao (estava: '$atual')"
        & $KitPython -m pip install --quiet --disable-pip-version-check "graphifyy[sql]==$KitVersao"
        if ($LASTEXITCODE) { throw 'Falhou ao instalar o Graphify' }
    }
}

function Invoke-KitGraphify {
    & $KitGraphifyExe @args
    if ($LASTEXITCODE) { throw "graphify $($args[0]) falhou (código $LASTEXITCODE)" }
}

function Invoke-KitMapa {
    & $KitPython $KitFerramenta @args
    if ($LASTEXITCODE) { throw "mapa.py $($args[0]) falhou (código $LASTEXITCODE)" }
}

function Get-KitMapa([string]$Nome) {
    $mapa = Join-Path $KitMapas $Nome
    if (-not (Test-Path (Join-Path $mapa 'graphify-out\graph.json'))) {
        throw "Não existe o mapa '$Nome'. Monte antes: ./montar.ps1 -Pasta <pasta> -Nome $Nome"
    }
    return $mapa
}
