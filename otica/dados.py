"""Ordens de serviço FICTÍCIAS de uma ótica, geradas de forma determinística, e leitura/gravação em CSV."""
import csv
import datetime as dt
import random
from dataclasses import dataclass, fields
from pathlib import Path

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Hugo", "Isabela", "João", "Karina", "Lucas", "Marina", "Nicolas", "Olívia", "Paulo", "Rita", "Samuel", "Tânia", "Vitor"]
SOBRENOMES = ["Silva", "Souza", "Costa", "Oliveira", "Pereira", "Lima", "Ribeiro", "Almeida", "Rocha", "Barros", "Cardoso", "Nunes"]
PRODUTOS = {"óculos de grau": (280, 1200), "óculos de sol": (150, 800), "lentes de contato": (120, 420), "conserto": (30, 120)}
STATUS = ["pedido", "em_producao", "pronto", "entregue", "cancelado"]
VALIDADE_RECEITA_DIAS = 365


@dataclass
class OrdemServico:
    id: int
    cliente: str
    telefone: str
    nascimento: str
    produto: str
    valor: float
    data_pedido: str
    data_prometida: str
    data_pronto: str
    data_entrega: str
    status: str
    data_receita: str

    def d(self, campo: str) -> dt.date | None:
        v = getattr(self, campo)
        return dt.date.fromisoformat(v) if v else None


def gerar(n: int = 240, semente: int = 10, hoje: dt.date = dt.date(2026, 11, 10)) -> list[OrdemServico]:
    rng = random.Random(semente)
    clientes = []
    for i in range(max(20, n // 2)):
        nome = f"{rng.choice(NOMES)} {rng.choice(SOBRENOMES)}"
        tel = f"(99) 9{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}"  # número fictício
        nasc = dt.date(rng.randint(1955, 2005), rng.randint(1, 12), rng.randint(1, 28))
        if i < 2:  # dois aniversariantes na data de referência, para a demonstração
            nasc = dt.date(rng.randint(1960, 2000), hoje.month, hoje.day)
        clientes.append((nome, tel, nasc))
    ordens: list[OrdemServico] = []
    for i in range(1, n + 1):
        nome, tel, nasc = rng.choice(clientes)
        produto = rng.choice(list(PRODUTOS))
        valor = round(rng.uniform(*PRODUTOS[produto]), 2)
        recente = rng.random() < 0.12  # parte dos pedidos é de poucos dias atrás
        pedido = hoje - dt.timedelta(days=rng.randint(0, 12) if recente else rng.randint(0, 360))
        producao = rng.randint(2, 9) if produto != "conserto" else rng.randint(1, 3)
        prometida = pedido + dt.timedelta(days=producao + rng.randint(0, 2))
        receita = pedido - dt.timedelta(days=rng.randint(0, 10)) if produto in ("óculos de grau", "lentes de contato") else None
        atraso = rng.choice([0, 0, 0, 0, 0, 0, 0, 1, 2, 5])
        pronto = pedido + dt.timedelta(days=producao + atraso)
        entrega, status, data_pronto = None, "", None
        if rng.random() < 0.04:
            status = "cancelado"
        elif pronto > hoje:
            status = "pedido" if (hoje - pedido).days <= 1 else "em_producao"
        else:
            data_pronto = pronto
            retirada = pronto + dt.timedelta(days=rng.choice([0, 1, 2, 3, 5, 9]))
            if retirada <= hoje and rng.random() < 0.985:
                status, entrega = "entregue", retirada
            else:
                status = "pronto"
        ordens.append(OrdemServico(
            i, nome, tel, nasc.isoformat(), produto, valor, pedido.isoformat(), prometida.isoformat(),
            data_pronto.isoformat() if data_pronto else "", entrega.isoformat() if entrega else "", status,
            receita.isoformat() if receita else "",
        ))
    return sorted(ordens, key=lambda o: o.id)


def gravar_csv(ordens: list[OrdemServico], caminho: str | Path) -> None:
    campos = [f.name for f in fields(OrdemServico)]
    with Path(caminho).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        for o in ordens:
            w.writerow({c: getattr(o, c) for c in campos})


def carregar_csv(caminho: str | Path) -> list[OrdemServico]:
    with Path(caminho).open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        raise ValueError("CSV sem ordens de serviço")
    faltando = {f.name for f in fields(OrdemServico)} - set(linhas[0])
    if faltando:
        raise ValueError("colunas faltando no CSV: " + ", ".join(sorted(faltando)))
    saida = []
    for l in linhas:
        if l["status"] not in STATUS:
            raise ValueError(f"status inválido na ordem {l['id']}: {l['status']}")
        saida.append(OrdemServico(int(l["id"]), l["cliente"], l["telefone"], l["nascimento"], l["produto"], float(l["valor"]),
                                  l["data_pedido"], l["data_prometida"], l["data_pronto"], l["data_entrega"], l["status"], l["data_receita"]))
    return saida
