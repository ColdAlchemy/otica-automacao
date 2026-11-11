"""Indicadores calculados em código puro a partir das ordens de serviço."""
import datetime as dt
from collections import Counter, defaultdict

from .dados import STATUS, OrdemServico


def meses_anteriores(hoje: dt.date, n: int = 12) -> list[str]:
    """Os últimos n meses, do mais antigo ao atual, como 'AAAA-MM'."""
    ano, mes, saida = hoje.year, hoje.month, []
    for _ in range(n):
        saida.append(f"{ano:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return saida[::-1]


def calcular(ordens: list[OrdemServico], hoje: dt.date) -> dict:
    validas = [o for o in ordens if o.status != "cancelado"]
    por_mes: dict[str, float] = defaultdict(float)
    for o in validas:
        por_mes[o.data_pedido[:7]] += o.valor
    meses = meses_anteriores(hoje)
    vendas_mensais = [(m, round(por_mes.get(m, 0.0), 2)) for m in meses]

    tempos = [(o.d("data_pronto") - o.d("data_pedido")).days for o in validas if o.data_pronto]
    com_pronto = [o for o in validas if o.data_pronto]
    atrasadas = [o for o in com_pronto if o.d("data_pronto") > o.d("data_prometida")]
    por_produto: dict[str, float] = defaultdict(float)
    for o in validas:
        por_produto[o.produto] += o.valor
    funil = Counter(o.status for o in ordens)
    total = sum(o.valor for o in validas)
    return {
        "ordens": len(ordens),
        "faturamento": round(total, 2),
        "ticket_medio": round(total / len(validas), 2) if validas else 0.0,
        "tempo_medio_producao_dias": round(sum(tempos) / len(tempos), 1) if tempos else 0.0,
        "taxa_atraso": round(len(atrasadas) / len(com_pronto), 3) if com_pronto else 0.0,
        "taxa_cancelamento": round((len(ordens) - len(validas)) / len(ordens), 3) if ordens else 0.0,
        "vendas_mensais": vendas_mensais,
        "por_produto": sorted(((p, round(v, 2)) for p, v in por_produto.items()), key=lambda x: -x[1]),
        "funil": {s: funil.get(s, 0) for s in STATUS},
    }


MINUTOS_POR_MENSAGEM_MANUAL = 2  # SUPOSIÇÃO: tempo de escrever e conferir uma mensagem na mão


def estimativa_de_tempo(n_rascunhos: int) -> dict:
    """Estimativa (não medição): minutos de escrita manual que os rascunhos poupam, sob a suposição acima."""
    return {"rascunhos": n_rascunhos, "minutos": n_rascunhos * MINUTOS_POR_MENSAGEM_MANUAL, "suposicao_min_por_mensagem": MINUTOS_POR_MENSAGEM_MANUAL}
