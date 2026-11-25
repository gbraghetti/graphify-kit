"""Ferramentas do graphify-kit em cima do graph.json do Graphify.

Uso (sempre pelo Python do .venv do kit):
  python mapa.py blocos        <mapa> [--nomes ARQ]       lista os blocos (pra dar nome)
  python mapa.py aplicar-nomes <mapa> <nomes.txt>         grava os nomes no mapa e confere
  python mapa.py depende-de    <mapa> <arquivo|pasta>...  tudo de que isso depende, em cadeia
  python mapa.py quem-usa      <mapa> <arquivo> [--niveis N]
  python mapa.py ciclos        <mapa>                     ciclos de import de VALOR (sem os só de tipo)
  python mapa.py comparar      <mapa> <pasta-de-docs> [--padrao REGEX]
  python mapa.py foto          <pasta> <saida.json>       fotografa a pasta (pra provar que nada mudou)
  python mapa.py comparar-foto <pasta> <foto.json>
  python mapa.py autoteste     <mapa-do-exemplo>          usado pelo conferir.ps1

<mapa> é a pasta do mapa (a que tem graphify-out/ dentro), ex.: mapas/rocketseat.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

# O graph.json é SEM direção e SEM ligação repetida (directed: false,
# multigraph: false): se A importa B e B importa A, a ligação arquivo-arquivo
# fica uma só. Por isso a dependência sai de duas fontes (a ligação
# arquivo-arquivo e a arquivo-peça, "A importa a função x de B") e a direção
# vem do `source_file` da ligação (o arquivo onde ela foi escrita), nunca da
# ordem source/target.
IMPORT_RELATIONS = {"imports", "imports_from", "re_exports", "dynamic_import"}
VALOR_RELATIONS = {"calls", "re_exports", "dynamic_import", "inherits"}
TYPE_DECL = re.compile(r"^\s*(export\s+)?(declare\s+)?(interface|type)\s+\w+")
# Pastas pesadas que a foto não percorre (o Graphify também não lê).
FOTO_PULA = {"node_modules", ".next", ".turbo", ".venv", "__pycache__"}


# --------------------------------------------------------------------------
# Leitura do mapa
# --------------------------------------------------------------------------


class Mapa:
    def __init__(self, pasta: str):
        self.out = Path(pasta) / "graphify-out"
        g = json.loads((self.out / "graph.json").read_text(encoding="utf-8"))
        self.nodes: dict[str, dict] = {n["id"]: n for n in g["nodes"]}
        self.links: list[dict] = g.get("links") or g.get("edges") or []
        root_file = self.out / ".graphify_root"
        self.root = Path(root_file.read_text(encoding="utf-8").strip()) if root_file.exists() else None
        self._linhas: dict[str, list[str]] = {}

    def arquivo(self, node_id: str) -> str:
        return self.nodes.get(node_id, {}).get("source_file") or ""

    def eh_codigo(self, node_id: str) -> bool:
        n = self.nodes.get(node_id, {})
        f = n.get("source_file") or ""
        return n.get("file_type") == "code" and not f.endswith(".json")

    def linha(self, arquivo: str, loc: str | None) -> str:
        """Texto da linha `loc` ("L12") do arquivo, lido da pasta original."""
        if not self.root or not loc or not loc.startswith("L"):
            return ""
        if arquivo not in self._linhas:
            try:
                self._linhas[arquivo] = (self.root / arquivo).read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                self._linhas[arquivo] = []
        try:
            n = int(loc[1:].split("-")[0].split(":")[0])
        except ValueError:
            return ""
        linhas = self._linhas[arquivo]
        return linhas[n - 1] if 0 < n <= len(linhas) else ""

    def comando_import(self, arquivo: str, loc: str | None) -> str:
        """O import inteiro a partir da linha (pode ocupar várias linhas)."""
        if not self.root or not loc:
            return ""
        primeira = self.linha(arquivo, loc)
        partes = [primeira]
        try:
            n = int(loc[1:].split("-")[0].split(":")[0])
        except ValueError:
            return primeira
        linhas = self._linhas.get(arquivo, [])
        i = n
        while " from " not in " ".join(partes) and i < len(linhas) and i < n + 40:
            partes.append(linhas[i])
            i += 1
        return " ".join(p.strip() for p in partes)

    def origem(self, e: dict) -> str:
        """Arquivo onde a ligação foi escrita (quem importa / quem chama)."""
        return e.get("source_file") or self.arquivo(e["source"])

    def outra_ponta(self, e: dict) -> str | None:
        """Id da ponta que fica em OUTRO arquivo de código (o importado)."""
        origem = self.origem(e)
        for ponta in (e["target"], e["source"]):
            f = self.arquivo(ponta)
            if f and f != origem and self.eh_codigo(ponta):
                return ponta
        return None

    def deps_de_arquivo(self) -> dict[str, set[str]]:
        """arquivo -> arquivos de código que ele importa."""
        dep: dict[str, set[str]] = collections.defaultdict(set)
        for e in self.links:
            if e.get("relation") not in IMPORT_RELATIONS:
                continue
            ponta = self.outra_ponta(e)
            if ponta:
                dep[self.origem(e)].add(self.arquivo(ponta))
        return dep

    def blocos(self) -> dict[object, list[dict]]:
        by: dict[object, list[dict]] = collections.defaultdict(list)
        for n in self.nodes.values():
            by[n.get("community")].append(n)
        return by

    def grau(self) -> collections.Counter:
        c: collections.Counter = collections.Counter()
        for e in self.links:
            c[e["source"]] += 1
            c[e["target"]] += 1
        return c

    def nomes_atuais(self) -> dict[str, str]:
        f = self.out / ".graphify_labels.json"
        if not f.exists():
            return {}
        data = json.loads(f.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}


def chave_do_bloco(nos: list[dict], grau: collections.Counter) -> str:
    """Peça mais ligada do bloco: identifica o bloco mesmo se o número mudar."""
    return max(nos, key=lambda n: (grau[n["id"]], n["id"]))["id"]


# --------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------


def cmd_blocos(a: argparse.Namespace) -> None:
    m = Mapa(a.mapa)
    grau = m.grau()
    atuais = m.nomes_atuais()
    nossos = ler_nomes(a.nomes) if a.nomes else {}
    blocos = m.blocos()
    faltam = 0
    saida = open(a.saida, "w", encoding="utf-8") if a.saida else sys.stdout
    print("# chave | peças | projetos | pastas | peças principais | nome atual", file=saida)
    for cid in sorted(blocos, key=lambda c: (c is None, c if isinstance(c, int) else 0)):
        nos = blocos[cid]
        chave = chave_do_bloco(nos, grau)
        arquivos = [n.get("source_file") or "?" for n in nos]
        projetos = collections.Counter(f.split("/")[0] for f in arquivos)
        pastas = collections.Counter("/".join(f.split("/")[1:-1])[-45:] or "." for f in arquivos)
        top = [n["label"] for n in sorted(nos, key=lambda n: -grau[n["id"]])[:6]]
        nome = atuais.get(str(cid), "")
        marca = ""
        if chave not in nossos:
            marca = "   <-- falta nome"
            faltam += 1
        print(
            f"{chave} | {len(nos)} | {','.join(p for p, _ in projetos.most_common(2))} | "
            f"{';'.join(d for d, _ in pastas.most_common(2))} | {', '.join(top)} | {nome}{marca}",
            file=saida,
        )
    resumo = f"# {len(blocos)} blocos; {faltam} sem nome nosso"
    print(resumo, file=saida)
    if a.saida:
        saida.close()
        print(resumo.lstrip("# ") + f" (lista em {a.saida})")


def ler_nomes(arq: str) -> dict[str, str]:
    """Arquivo de nomes: uma linha por bloco, `chave|nome`. # = comentário."""
    nomes: dict[str, str] = {}
    p = Path(arq)
    if not p.exists():
        return nomes
    for linha in p.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "|" not in linha:
            continue
        chave, nome = linha.split("|", 1)
        nomes[chave.strip()] = nome.strip()
    return nomes


def cmd_aplicar_nomes(a: argparse.Namespace) -> None:
    nossos = ler_nomes(a.nomes)
    if not nossos:
        sys.exit(f"Nenhum nome em {a.nomes}")
    graphify = Path(sys.executable).with_name("graphify.exe")
    if not graphify.exists():
        graphify = Path(sys.executable).with_name("graphify")
    for rodada in (1, 2):
        m = Mapa(a.mapa)
        grau = m.grau()
        atuais = m.nomes_atuais()
        novos = dict(atuais)
        for cid, nos in m.blocos().items():
            chave = chave_do_bloco(nos, grau)
            if chave in nossos:
                novos[str(cid)] = nossos[chave]
        (m.out / ".graphify_labels.json").write_text(json.dumps(novos, ensure_ascii=False, indent=1), encoding="utf-8")
        # Os nomes valem pros blocos de AGORA: a assinatura velha sai e o
        # Graphify grava a nova no cluster-only.
        sig = m.out / ".graphify_labels.json.sig"
        if sig.exists():
            sig.unlink()
        env = dict(os.environ, GRAPHIFY_BACKEND="none", GRAPHIFY_QUERY_LOG_DISABLE="1")
        subprocess.run([str(graphify), "cluster-only", str(Path(a.mapa))], env=env, check=True,
                       stdout=subprocess.DEVNULL)
        # Confere: cada nome nosso está no bloco da sua chave?
        m = Mapa(a.mapa)
        grau = m.grau()
        atuais = m.nomes_atuais()
        certos = errados = 0
        for cid, nos in m.blocos().items():
            chave = chave_do_bloco(nos, grau)
            if chave in nossos:
                if atuais.get(str(cid)) == nossos[chave]:
                    certos += 1
                else:
                    errados += 1
        if errados == 0:
            break
    sumiram = len(nossos) - certos - errados
    print(f"Nomes aplicados: {certos} certos, {errados} fora do lugar, {sumiram} blocos que não existem mais.")
    if errados:
        sys.exit(1)


def cmd_depende_de(a: argparse.Namespace) -> None:
    m = Mapa(a.mapa)
    dep = m.deps_de_arquivo()
    todos = {m.arquivo(i) for i in m.nodes} - {""}
    inicio = sorted(f for f in todos if any(f == p or f.startswith(p.rstrip("/") + "/") for p in a.alvos))
    if not inicio:
        sys.exit("Nenhum arquivo do mapa bate com: " + ", ".join(a.alvos))
    visto = set(inicio)
    fila = list(inicio)
    while fila:
        f = fila.pop()
        for d in dep.get(f, ()):
            if d not in visto:
                visto.add(d)
                fila.append(d)
    for f in sorted(visto):
        print(("* " if f in inicio else "  ") + f)
    print(f"{len(visto)} arquivos ({len(inicio)} pedidos, marcados com *)")


def cmd_quem_usa(a: argparse.Namespace) -> None:
    m = Mapa(a.mapa)
    rev: dict[str, set[str]] = collections.defaultdict(set)
    for f, ds in m.deps_de_arquivo().items():
        for d in ds:
            rev[d].add(f)
    nivel = {a.alvo: 0}
    fila = [a.alvo]
    while fila:
        f = fila.pop(0)
        if nivel[f] >= a.niveis:
            continue
        for u in rev.get(f, ()):
            if u not in nivel:
                nivel[u] = nivel[f] + 1
                fila.append(u)
    if len(nivel) == 1:
        print(f"Ninguém importa {a.alvo} (confira o caminho: é relativo à pasta mapeada).")
        return
    por = collections.defaultdict(list)
    for f, n in nivel.items():
        if n:
            por[n].append(f)
    for n in sorted(por):
        print(f"nível {n} ({len(por[n])}):")
        for f in sorted(por[n]):
            print("  " + f)


def _par_so_de_tipo(m: Mapa, a_arq: str, b_arq: str) -> bool:
    """A importa de B só tipos? (import type, { type X } ou só interface/type)."""
    simbolos = 0
    for e in m.links:
        if m.origem(e) != a_arq:
            continue
        ponta = m.outra_ponta(e)
        if not ponta or m.arquivo(ponta) != b_arq:
            continue
        rel = e.get("relation")
        if rel in VALOR_RELATIONS:
            return False
        if rel != "imports":
            continue  # imports_from (arquivo-arquivo) e references (tipo) não decidem
        simbolos += 1
        comando = m.comando_import(a_arq, e.get("source_location"))
        if re.match(r"^\s*import\s+type\b", comando):
            continue
        alvo = m.nodes.get(ponta, {})
        nome = (alvo.get("label") or "").rstrip("()")
        if nome and re.search(r"\btype\s+" + re.escape(nome) + r"\b", comando):
            continue
        if TYPE_DECL.match(m.linha(b_arq, alvo.get("source_location"))):
            continue
        return False
    return simbolos > 0


def _componentes_fortes(grafo: dict[str, set[str]]) -> list[list[str]]:
    """Tarjan iterativo: grupos de arquivos que se importam em roda."""
    indice: dict[str, int] = {}
    baixo: dict[str, int] = {}
    na_pilha: set[str] = set()
    pilha: list[str] = []
    grupos: list[list[str]] = []
    contador = 0
    nos = set(grafo) | {d for ds in grafo.values() for d in ds}
    for raiz in sorted(nos):
        if raiz in indice:
            continue
        trabalho = [(raiz, iter(sorted(grafo.get(raiz, ()))))]
        indice[raiz] = baixo[raiz] = contador
        contador += 1
        pilha.append(raiz)
        na_pilha.add(raiz)
        while trabalho:
            v, filhos = trabalho[-1]
            avancou = False
            for w in filhos:
                if w not in indice:
                    indice[w] = baixo[w] = contador
                    contador += 1
                    pilha.append(w)
                    na_pilha.add(w)
                    trabalho.append((w, iter(sorted(grafo.get(w, ())))))
                    avancou = True
                    break
                if w in na_pilha:
                    baixo[v] = min(baixo[v], indice[w])
            if avancou:
                continue
            trabalho.pop()
            if trabalho:
                pai = trabalho[-1][0]
                baixo[pai] = min(baixo[pai], baixo[v])
            if baixo[v] == indice[v]:
                grupo = []
                while True:
                    w = pilha.pop()
                    na_pilha.discard(w)
                    grupo.append(w)
                    if w == v:
                        break
                if len(grupo) > 1:
                    grupos.append(sorted(grupo))
    return grupos


def calcular_ciclos(m: Mapa) -> tuple[list[list[str]], list[tuple[str, str]]]:
    dep = m.deps_de_arquivo()
    so_tipo: list[tuple[str, str]] = []
    valor: dict[str, set[str]] = collections.defaultdict(set)
    for a_arq, ds in dep.items():
        for b_arq in ds:
            if _par_so_de_tipo(m, a_arq, b_arq):
                so_tipo.append((a_arq, b_arq))
            else:
                valor[a_arq].add(b_arq)
    return _componentes_fortes(valor), so_tipo


def cmd_ciclos(a: argparse.Namespace) -> None:
    m = Mapa(a.mapa)
    grupos, so_tipo = calcular_ciclos(m)
    if not grupos:
        print("Nenhum ciclo de import de valor.")
    for g in grupos:
        print(f"Ciclo de {len(g)} arquivos (importam funções/valores em roda):")
        for f in g:
            print("  " + f)
    print(f"({len(so_tipo)} imports só de tipo ignorados: somem na compilação)")


def cmd_comparar(a: argparse.Namespace) -> None:
    m = Mapa(a.mapa)
    docs = "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in Path(a.docs).rglob("*.md")
    )
    padrao = re.compile(a.padrao)
    vistos: set[tuple[str, str]] = set()
    faltam = []
    total = 0
    for n in m.nodes.values():
        nome = (n.get("label") or "").rstrip("()")
        f = n.get("source_file") or ""
        if not f or nome.startswith("$") or re.search(r"(tsconfig|package|components)\.json$", f):
            continue
        if not padrao.search(nome) or (nome, f) in vistos:
            continue
        vistos.add((nome, f))
        total += 1
        curto = f.split("/", 1)[1] if "/" in f else f
        base = f.rsplit("/", 1)[-1].split(".")[0]
        if nome not in docs and curto not in docs and base not in docs:
            faltam.append((f.split("/")[0], nome, f))
    print(f"{total} peças procuradas; {len(faltam)} não aparecem em nenhum .md de {a.docs}")
    for p, nome, f in sorted(faltam):
        print(f"  {p:22} {nome:30} {f}")


def _fotografar(pasta: str) -> dict[str, list[int]]:
    foto: dict[str, list[int]] = {}
    raiz = Path(pasta)
    for atual, dirs, arqs in os.walk(raiz):
        rel = Path(atual).relative_to(raiz)
        # .git: só os ganchos interessam (é onde uma ferramenta instalaria algo)
        if rel.parts[:1] == (".git",) and rel.parts[:2] != (".git", "hooks"):
            dirs[:] = ["hooks"] if rel == Path(".git") and "hooks" in dirs else []
            continue
        dirs[:] = [d for d in dirs if d not in FOTO_PULA]
        for a in arqs:
            p = Path(atual) / a
            try:
                st = p.stat()
            except OSError:
                continue
            foto[str(p.relative_to(raiz)).replace("\\", "/")] = [st.st_size, int(st.st_mtime)]
    return foto


def cmd_foto(a: argparse.Namespace) -> None:
    foto = _fotografar(a.pasta)
    Path(a.saida).write_text(json.dumps(foto), encoding="utf-8")
    print(f"{len(foto)} arquivos fotografados")


def cmd_comparar_foto(a: argparse.Namespace) -> None:
    antes = json.loads(Path(a.foto).read_text(encoding="utf-8"))
    agora = _fotografar(a.pasta)
    novos = sorted(set(agora) - set(antes))
    sumidos = sorted(set(antes) - set(agora))
    mudados = sorted(f for f in set(agora) & set(antes) if agora[f] != antes[f])
    if not (novos or sumidos or mudados):
        print(f"Pasta intocada ({len(agora)} arquivos iguais).")
        return
    for titulo, lista in (("Novos", novos), ("Apagados", sumidos), ("Alterados", mudados)):
        for f in lista:
            print(f"{titulo}: {f}")
    sys.exit(1)


def cmd_autoteste(a: argparse.Namespace) -> None:
    m = Mapa(a.mapa)
    falhas: list[str] = []

    def confere(ok: bool, o_que: str) -> None:
        print(("  ok   " if ok else "  FALHOU ") + o_que)
        if not ok:
            falhas.append(o_que)

    arquivos = {m.arquivo(i) for i in m.nodes}
    confere("src/lista.tsx" in arquivos, "lê .tsx")
    dep = m.deps_de_arquivo()
    confere("src/total.ts" in dep.get("src/lista.tsx", set()), "lista.tsx importa total.ts")
    usa_total = {f for f, ds in dep.items() if "src/total.ts" in ds}
    confere(usa_total == {"src/lista.tsx", "src/soma.ts"}, f"quem usa total.ts = lista + soma (veio {sorted(usa_total)})")
    grupos, so_tipo = calcular_ciclos(m)
    confere(grupos == [["src/ida.ts", "src/volta.ts"]], f"um ciclo de valor: ida <-> volta (veio {grupos})")
    pares = {tuple(sorted(p)) for p in so_tipo}
    confere(("src/soma.ts", "src/total.ts") in pares, "ignora `import type` (soma -> total)")
    confere(("src/pessoa.ts", "src/saudacao.ts") in pares, "ignora interface importada sem `type` (saudacao -> pessoa)")
    if falhas:
        sys.exit(f"{len(falhas)} conferência(s) falharam: o Graphify mudou o formato do mapa.")
    print("Tudo certo.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("blocos"); x.add_argument("mapa"); x.add_argument("--nomes"); x.add_argument("--saida")
    x.set_defaults(f=cmd_blocos)
    x = s.add_parser("aplicar-nomes"); x.add_argument("mapa"); x.add_argument("nomes")
    x.set_defaults(f=cmd_aplicar_nomes)
    x = s.add_parser("depende-de"); x.add_argument("mapa"); x.add_argument("alvos", nargs="+")
    x.set_defaults(f=cmd_depende_de)
    x = s.add_parser("quem-usa"); x.add_argument("mapa"); x.add_argument("alvo")
    x.add_argument("--niveis", type=int, default=2); x.set_defaults(f=cmd_quem_usa)
    x = s.add_parser("ciclos"); x.add_argument("mapa"); x.set_defaults(f=cmd_ciclos)
    x = s.add_parser("comparar"); x.add_argument("mapa"); x.add_argument("docs")
    x.add_argument("--padrao", default=r"(^use[A-Z]\w+$|Mask|Input|Table|Format|format|Schema|schema)")
    x.set_defaults(f=cmd_comparar)
    x = s.add_parser("foto"); x.add_argument("pasta"); x.add_argument("saida"); x.set_defaults(f=cmd_foto)
    x = s.add_parser("comparar-foto"); x.add_argument("pasta"); x.add_argument("foto")
    x.set_defaults(f=cmd_comparar_foto)
    x = s.add_parser("autoteste"); x.add_argument("mapa"); x.set_defaults(f=cmd_autoteste)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
