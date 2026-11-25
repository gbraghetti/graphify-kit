# Projeto de exemplo do autoteste

Arquivos pequenos com respostas conhecidas. O `conferir.ps1` monta o mapa
desta pasta e confere que o Graphify (e o `mapa.py`) continuam enxergando:

- `lista.tsx` importa `total.ts` (lê `.tsx`);
- `ida.ts` ⇄ `volta.ts`: ciclo **de valor** (funções), tem que aparecer;
- `soma.ts` → `total.ts` com `import type`: tipo, não conta como ciclo;
- `saudacao.ts` → `pessoa.ts` importando só uma `interface` sem a palavra
  `type`: também é só tipo, o ciclo `pessoa` ⇄ `saudacao` não conta.

Não mexer sem atualizar o `autoteste` em `ferramentas/mapa.py`.
