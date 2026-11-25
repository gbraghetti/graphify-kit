# graphify-kit

Um jeito nosso de usar o [Graphify](https://github.com/Graphify-Labs/graphify)
(mapa de "quem importa quem" de um código), **sem ele se meter em nada**:
não escreve na pasta mapeada, não instala ganchos nem skill no Claude Code,
não usa IA e não manda nada pra fora da máquina.

O Graphify original não é modificado: o kit instala uma versão travada dele
num ambiente isolado e põe em volta os scripts e as escolhas abaixo.

## Por que um kit e não uma cópia do Graphify

Tudo o que queríamos diferente é **jeito de usar**, não código:

| O que queríamos | Como o kit faz |
|---|---|
| Não interferir na leitura do código | Nunca roda `graphify install` (é ele que põe skill, ganchos e o modo strict) |
| Nada escrito no projeto | Mapa sempre em `mapas/<nome>/` (opção `--out`); a pasta é fotografada antes e depois |
| Sem IA, nada sai da máquina | `GRAPHIFY_BACKEND=none` (só a leitura do código, local e de graça) |
| Não quebrar com versão nova | Versão travada em `versao.txt` + autoteste (`conferir.ps1`) |
| Blocos com nome em português | `nomear.ps1`: o Claude (ou você) escreve os nomes, sem a IA do Graphify |
| Ciclo de import sem alarme falso | `consultar.ps1 -Pergunta ciclos` ignora os imports só de tipo |
| Desinstalar "como se nunca tivesse existido" | `limpar.ps1` apaga e procura sobras |

O Graphify lança versão quase todo dia; uma cópia do código exigiria comparar
centenas de arquivos a cada atualização pra trocar zero linhas nossas, e as
correções de segurança chegariam atrasadas.

## Precisa de

- Windows + PowerShell 7
- Python 3.11 ou mais novo (`python` no PATH)

Nada mais: o `.venv` é criado na primeira vez que um script roda.

## Uso

```powershell
# 1. Montar o mapa de uma pasta (de novo = incremental)
./montar.ps1 -Pasta J:\workspace\development\rocketseat -Nome rocketseat
./montar.ps1 -Pasta C:\workspace_c\next-projects\suaparte-project -Nome suaparte

# 2. Perguntar
./consultar.ps1 -Nome suaparte -Pergunta quem-usa   -Alvo src/lib/live-events.ts
./consultar.ps1 -Nome suaparte -Pergunta depende-de -Alvo src/lib/live-events.ts, src/components/live-refresh
./consultar.ps1 -Nome suaparte -Pergunta ciclos
./consultar.ps1 -Nome suaparte -Pergunta explicar   -Alvo groupAdminContext
./consultar.ps1 -Nome rocketseat -Pergunta comparar -Alvo J:\workspace\development\rocketseat\_project-analysis
./consultar.ps1 -Nome rocketseat -Pergunta relatorio

# 3. Dar nome aos blocos
./nomear.ps1 -Nome rocketseat            # gera nomes/rocketseat.blocos.txt
#   escrever nomes/rocketseat.txt: uma linha "chave|nome" por bloco
./nomear.ps1 -Nome rocketseat -Aplicar

# 4. Desinstalar
./limpar.ps1                # apaga Graphify e mapas; guarda os nomes
./limpar.ps1 -ApagarNomes   # apaga tudo
```

Caminhos de arquivo nas perguntas são relativos à pasta mapeada, com barra
normal (`src/lib/viewer.ts`).

O que cada pergunta responde:

| Pergunta | Responde | Quando vale |
|---|---|---|
| `depende-de` | Tudo de que um arquivo/pasta depende, em cadeia | Levar uma peça pra outro projeto sem esquecer nada |
| `quem-usa` | Quem importa um arquivo, por nível | "Se eu mexer nisso, o que mais quebra?" |
| `ciclos` | Arquivos que se importam em roda (só valores) | Antes de refatorar; erros de `undefined` ao carregar |
| `comparar` | Peças que nenhum `.md` da pasta de docs cita | Achar o que falta numa documentação/análise |
| `explicar` / `caminho` | Uma peça e suas ligações / o caminho entre duas | Entender um pedaço que não se conhece |

## Os nomes dos blocos

O Graphify agrupa o código em blocos. Sem IA, cada bloco ganha o nome da sua
peça principal (ex.: `CyclesContext.tsx`). Pra ter nomes de verdade
("ignite-timer · Ciclos (reducer + Context)"):

1. `./nomear.ps1 -Nome X` lista os blocos em `nomes/X.blocos.txt` (chave,
   pastas, peças principais).
2. Os nomes vão em `nomes/X.txt`, uma linha `chave|nome` por bloco. A
   **chave** é a peça mais ligada do bloco, então o nome continua valendo
   se o Graphify renumerar os blocos.
3. `./nomear.ps1 -Nome X -Aplicar` grava e confere que cada nome caiu no
   bloco certo.

Depois disso o `montar.ps1` reaplica os nomes sozinho a cada reconstrução.
Bloco novo, ou que mudou demais, aparece na lista marcado com
`<-- falta nome`. Pasta que não muda (ex.: `rocketseat`) = nomear uma vez só.

## Atualizar o Graphify

Sem calendário: quando sair uma versão que interesse (correção de
segurança, linguagem nova) ou antes de voltar a usar depois de muito tempo.

1. Ler as notas da versão nova: <https://github.com/Graphify-Labs/graphify/releases>.
   Atenção a "AST cache schema" (a 1ª montagem depois relê tudo) e a
   mudanças no `graph.json`.
2. Trocar o número em `versao.txt`.
3. `./conferir.ps1`: reinstala a versão e roda o autoteste no `exemplo/`
   (`.tsx`, dependências, "quem usa", ciclos só de tipo, pasta intocada).
4. Passou: anotar no `HISTORICO.md` e remontar os mapas. Falhou: voltar o
   `versao.txt` pra anterior e rodar `./conferir.ps1` de novo.

Copiar o código do Graphify só faria sentido se um dia precisássemos de algo
que ele não deixa configurar; mesmo assim, o melhor caminho é mandar a
mudança pro projeto original.

## O que tem aqui

```
montar.ps1        monta/atualiza um mapa (foto antes e depois da pasta)
consultar.ps1     as perguntas
nomear.ps1        lista blocos / aplica nomes
conferir.ps1      autoteste da versão travada
limpar.ps1        desinstala e procura sobras
_comum.ps1        caminhos, versão, variáveis (sem IA, sem log)
versao.txt        a versão do Graphify em uso
HISTORICO.md      versões testadas
ferramentas/
  mapa.py         as ferramentas em cima do graph.json
exemplo/          projetinho com respostas conhecidas (autoteste)
mapas/            (não vai pro git) os mapas
nomes/            (não vai pro git) os nomes dos blocos
.venv/            (não vai pro git) o Graphify
```

## Cuidados conhecidos (versão 0.9.119)

- Arquivos sem símbolos (ex.: `main.tsx` que só monta o app) aparecem como
  "yielded no symbols": normal.
- Pacotes com o mesmo nome em projetos diferentes viram uma peça só (ex.:
  `react-dom`): útil pra ver quem usa qual versão, mas não é ligação entre
  os projetos.
- Os ciclos que o próprio relatório do Graphify (`GRAPH_REPORT.md`) lista
  incluem os só de tipo; use `consultar.ps1 -Pergunta ciclos`.
- Em 21/11/2026 a 0.9.115 corrigiu uma falha do Windows (vazamento de
  credencial de rede ao indexar). Não usar versões abaixo dela.
