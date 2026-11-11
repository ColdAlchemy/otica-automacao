"""Regras de negócio: quem precisa de contato hoje. Funções puras (recebem 'hoje'), fáceis de testar."""
import datetime as dt
from dataclasses import dataclass

from .dados import VALIDADE_RECEITA_DIAS, OrdemServico


@dataclass(frozen=True)
class Alvo:
    tipo: str  # retirada | atraso | receita | aniversario
    os: OrdemServico
    detalhe: str = ""


def prontos_nao_retirados(ordens: list[OrdemServico], hoje: dt.date, dias: int = 3) -> list[Alvo]:
    """Pedido pronto e parado na loja há 'dias' ou mais."""
    saida = []
    for o in ordens:
        pronto = o.d("data_pronto")
        if o.status == "pronto" and pronto and (hoje - pronto).days >= dias:
            saida.append(Alvo("retirada", o, f"pronto há {(hoje - pronto).days} dias"))
    return saida


def atrasados(ordens: list[OrdemServico], hoje: dt.date) -> list[Alvo]:
    """Ainda em produção depois da data prometida: o cliente merece um aviso antes de reclamar."""
    saida = []
    for o in ordens:
        prometida = o.d("data_prometida")
        if o.status in ("pedido", "em_producao") and prometida and prometida < hoje:
            saida.append(Alvo("atraso", o, f"prometido para {prometida.isoformat()}"))
    return saida


def receitas_a_vencer(ordens: list[OrdemServico], hoje: dt.date, janela: int = 30) -> list[Alvo]:
    """Receita (do exame) que vence na janela e sem pedido mais novo do mesmo cliente."""
    ultimo: dict[str, OrdemServico] = {}
    for o in ordens:
        if o.status == "cancelado" or not o.data_receita:
            continue
        atual = ultimo.get(o.cliente)
        if atual is None or o.data_receita > atual.data_receita:
            ultimo[o.cliente] = o
    saida = []
    for o in ultimo.values():
        validade = o.d("data_receita") + dt.timedelta(days=VALIDADE_RECEITA_DIAS)
        if hoje <= validade <= hoje + dt.timedelta(days=janela):
            saida.append(Alvo("receita", o, f"receita vence em {validade.isoformat()}"))
    return sorted(saida, key=lambda a: a.os.cliente)


def aniversariantes(ordens: list[OrdemServico], hoje: dt.date) -> list[Alvo]:
    vistos, saida = set(), []
    for o in ordens:
        n = o.d("nascimento")
        if n and (n.month, n.day) == (hoje.month, hoje.day) and o.cliente not in vistos:
            vistos.add(o.cliente)
            saida.append(Alvo("aniversario", o))
    return saida


def todos_os_alvos(ordens: list[OrdemServico], hoje: dt.date) -> list[Alvo]:
    return (prontos_nao_retirados(ordens, hoje) + atrasados(ordens, hoje) + receitas_a_vencer(ordens, hoje) + aniversariantes(ordens, hoje))
