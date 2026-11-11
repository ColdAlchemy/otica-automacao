"""Linha de comando: gerar-dados, rotina, resumo e painel."""
import argparse
import csv
import datetime as dt
import sys
from collections import Counter
from pathlib import Path

from .dados import carregar_csv, gerar, gravar_csv
from .kpis import calcular, estimativa_de_tempo
from .mensagens import RedatorAnthropic, gerar_rascunhos
from .painel import brl, gerar_html
from .regras import todos_os_alvos

RAIZ = Path(__file__).resolve().parent.parent


def _hoje(texto: str | None) -> dt.date:
    return dt.date.fromisoformat(texto) if texto else dt.date(2026, 11, 10)


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    pai = argparse.ArgumentParser(add_help=False)
    pai.add_argument("--csv", default=str(RAIZ / "data" / "ordens.csv"))
    pai.add_argument("--hoje", help="data de hoje (AAAA-MM-DD); padrão 2026-11-10, a data dos dados de exemplo")
    ap = argparse.ArgumentParser(prog="otica", description="Rotina de contato com clientes e painel de uma ótica (dados fictícios).")
    sub = ap.add_subparsers(dest="comando", required=True)
    g = sub.add_parser("gerar-dados", help="gera o CSV fictício")
    g.add_argument("--n", type=int, default=240)
    g.add_argument("--saida", default=str(RAIZ / "data" / "ordens.csv"))
    r = sub.add_parser("rotina", parents=[pai], help="decide quem contatar e grava rascunhos para revisão")
    r.add_argument("--saida", default=str(RAIZ / "data" / "rascunhos.csv"))
    r.add_argument("--com-ia", action="store_true", help="usa a API da Anthropic para redigir (exige ANTHROPIC_API_KEY)")
    sub.add_parser("resumo", parents=[pai], help="mostra os indicadores")
    p = sub.add_parser("painel", parents=[pai], help="gera o painel HTML")
    p.add_argument("--saida", default=str(RAIZ / "docs" / "index.html"))
    args = ap.parse_args(argv)

    if args.comando == "gerar-dados":
        destino = Path(args.saida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        ordens = gerar(args.n)
        gravar_csv(ordens, destino)
        print(f"{len(ordens)} ordens fictícias gravadas em {destino}")
        return 0

    hoje = _hoje(args.hoje)
    ordens = carregar_csv(args.csv)
    alvos = todos_os_alvos(ordens, hoje)

    if args.comando == "resumo":
        k = calcular(ordens, hoje)
        print(f"{k['ordens']} ordens · vendas {brl(k['faturamento'])} · ticket médio {brl(k['ticket_medio'])}")
        print(f"produção média {k['tempo_medio_producao_dias']} dias · atraso {k['taxa_atraso']:.1%} · cancelamento {k['taxa_cancelamento']:.1%}")
        print("situação:", ", ".join(f"{s} {n}" for s, n in k["funil"].items()))
    elif args.comando == "rotina":
        redator = RedatorAnthropic() if args.com_ia else None
        rascunhos = gerar_rascunhos(alvos, redator)
        destino = Path(args.saida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["os_id", "cliente", "telefone", "tipo", "texto", "origem", "aprovado"])
            for x in rascunhos:
                w.writerow([x.os_id, x.cliente, x.telefone, x.tipo, x.texto, x.origem, ""])
        por_tipo = Counter(a.tipo for a in alvos)
        print(f"Hoje ({hoje.isoformat()}): " + ", ".join(f"{t} {n}" for t, n in sorted(por_tipo.items())) or "ninguém para contatar")
        t = estimativa_de_tempo(len(rascunhos))
        print(f"{len(rascunhos)} rascunhos gravados em {destino} (coluna 'aprovado' vazia: nada foi enviado).")
        print(f"Estimativa (suposição de {t['suposicao_min_por_mensagem']} min por mensagem escrita à mão): ≈ {t['minutos']} min poupados.")
    elif args.comando == "painel":
        k = calcular(ordens, hoje)
        rascunhos = gerar_rascunhos(alvos)
        html = gerar_html(k, dict(Counter(a.tipo for a in alvos)), rascunhos, hoje, estimativa_de_tempo(len(rascunhos)))
        destino = Path(args.saida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(html, encoding="utf-8")
        print("Painel gravado em", destino)
    return 0
