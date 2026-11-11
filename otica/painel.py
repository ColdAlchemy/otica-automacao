"""Painel HTML estático e autocontido (sem JavaScript). Não lista nomes nem telefones: só números e exemplos."""
import datetime as dt
from html import escape

from .mensagens import Rascunho

CSS = """
:root{--fundo:#f6f7f4;--cartao:#fff;--tinta:#1c2420;--suave:#58645d;--linha:#dde2dc;--acento:#17624a;--barra:#cfe3da;--aviso:#8a5a00}
@media (prefers-color-scheme:dark){:root{--fundo:#101512;--cartao:#171e1a;--tinta:#e6ece8;--suave:#a0aca5;--linha:#27322c;--acento:#6fd1ad;--barra:#1f3a2f;--aviso:#e0b45c}}
*{box-sizing:border-box}body{margin:0;background:var(--fundo);color:var(--tinta);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:64rem;margin:0 auto;padding:1.5rem 1rem 4rem}
h1{font-size:1.6rem;margin:0}h2{font-size:1.1rem;margin:2rem 0 .75rem}p.sub{color:var(--suave);margin:.25rem 0 1.25rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));gap:.75rem}
.card{background:var(--cartao);border:1px solid var(--linha);border-radius:10px;padding:.8rem 1rem}
.card b{display:block;font-size:1.35rem;white-space:nowrap}.card span{color:var(--suave);font-size:.85rem}
table{width:100%;border-collapse:collapse;background:var(--cartao);border:1px solid var(--linha);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:.5rem .7rem;border-bottom:1px solid var(--linha);font-size:.92rem}th{color:var(--suave);font-weight:600}
td:nth-child(2) .bar{min-width:6rem}td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.bar{height:.7rem;background:var(--barra);border-radius:3px;min-width:2px}.bar i{display:block;height:100%;background:var(--acento);border-radius:3px}
.rolagem{overflow-x:auto}.nota{color:var(--aviso);font-size:.88rem}
blockquote{margin:.4rem 0;padding:.5rem .8rem;border-left:3px solid var(--acento);background:var(--cartao)}
footer{margin-top:2.5rem;color:var(--suave);font-size:.85rem}
"""


def brl(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _barra(valor: float, maximo: float) -> str:
    pct = 0 if maximo == 0 else valor / maximo * 100
    return f'<div class="bar" aria-hidden="true"><i style="width:{pct:.0f}%"></i></div>'


def gerar_html(k: dict, alvos_por_tipo: dict[str, int], rascunhos: list[Rascunho], hoje: dt.date, tempo: dict) -> str:
    maxmes = max((v for _, v in k["vendas_mensais"]), default=0)
    linhas_mes = "".join(
        f"<tr><td>{m}</td><td>{_barra(v, maxmes)}</td><td class='n'>{brl(v)}</td></tr>" for m, v in k["vendas_mensais"]
    )
    maxprod = max((v for _, v in k["por_produto"]), default=0)
    linhas_prod = "".join(
        f"<tr><td>{escape(p)}</td><td>{_barra(v, maxprod)}</td><td class='n'>{brl(v)}</td></tr>" for p, v in k["por_produto"]
    )
    funil = "".join(f"<tr><td>{escape(s.replace('_', ' '))}</td><td class='n'>{n}</td></tr>" for s, n in k["funil"].items())
    rotulos = {"retirada": "Pedidos prontos esperando retirada", "atraso": "Pedidos atrasados", "receita": "Receitas vencendo em 30 dias", "aniversario": "Aniversariantes do dia"}
    contatos = "".join(f"<tr><td>{rotulos[t]}</td><td class='n'>{alvos_por_tipo.get(t, 0)}</td></tr>" for t in rotulos)
    exemplos, vistos = "", set()
    for r in rascunhos:
        if r.tipo not in vistos and len(vistos) < 4:
            vistos.add(r.tipo)
            exemplos += f"<blockquote><small>{rotulos[r.tipo]}</small><br>{escape(r.texto)}</blockquote>"
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Painel da ótica (dados fictícios)</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>Painel da ótica</h1>
<p class="sub">Dados fictícios · posição em {hoje.strftime('%d/%m/%Y')} · gerado por <code>python -m otica painel</code></p>

<div class="cards">
<div class="card"><b>{k['ordens']}</b><span>ordens de serviço</span></div>
<div class="card"><b>{brl(k['faturamento'])}</b><span>vendas (sem canceladas)</span></div>
<div class="card"><b>{brl(k['ticket_medio'])}</b><span>ticket médio</span></div>
<div class="card"><b>{k['tempo_medio_producao_dias']:.1f} dias</b><span>produção até ficar pronto</span></div>
<div class="card"><b>{k['taxa_atraso'] * 100:.0f}%</b><span>prontos depois do prometido</span></div>
<div class="card"><b>{k['taxa_cancelamento'] * 100:.0f}%</b><span>cancelamentos</span></div>
</div>

<h2>Vendas por mês</h2>
<div class="rolagem"><table><thead><tr><th>mês</th><th></th><th>vendas</th></tr></thead><tbody>{linhas_mes}</tbody></table></div>

<h2>Vendas por produto</h2>
<div class="rolagem"><table><thead><tr><th>produto</th><th></th><th>vendas</th></tr></thead><tbody>{linhas_prod}</tbody></table></div>

<h2>Situação das ordens</h2>
<table><thead><tr><th>status</th><th>ordens</th></tr></thead><tbody>{funil}</tbody></table>

<h2>Quem precisa de contato hoje</h2>
<table><thead><tr><th>motivo</th><th>clientes</th></tr></thead><tbody>{contatos}</tbody></table>
<p class="nota">A automação só prepara <b>rascunhos</b> para uma pessoa revisar; nada é enviado sozinho. Estimativa de tempo (sob a suposição de {tempo['suposicao_min_por_mensagem']} min por mensagem escrita à mão): {tempo['rascunhos']} rascunhos ≈ {tempo['minutos']} min poupados hoje. É uma estimativa, não uma medição.</p>
<h2>Exemplos de rascunho</h2>
{exemplos}

<footer>Projeto de portfólio com dados e nomes fictícios. Sem JavaScript e sem recursos externos.</footer>
</main>
</body>
</html>
"""
