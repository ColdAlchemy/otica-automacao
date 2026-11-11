"""Rascunhos de mensagem para revisão humana. NADA é enviado: o resultado é uma lista para a pessoa conferir.

O redator é uma interface: o padrão é por modelos de texto (offline, determinístico); o outro usa a API da Anthropic.
Toda mensagem, venha de onde vier, passa por `validar`: se o texto de uma IA sair do padrão, volta para o modelo de texto.
"""
import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Callable, Protocol

from .regras import Alvo

LIMITE = 320
RODAPE = "Para não receber mais mensagens, responda SAIR."

MODELOS = {
    "retirada": "Olá, {nome}! Seu pedido ({produto}) está pronto e te esperando na loja. Quando puder, passe para retirar.",
    "atraso": "Olá, {nome}! Seu pedido ({produto}) está levando um pouco mais que o combinado. Avisaremos assim que ficar pronto. Obrigado pela paciência!",
    "receita": "Olá, {nome}! A receita do seu último exame está perto de vencer. Quer agendar um novo exame de vista?",
    "aniversario": "Feliz aniversário, {nome}! Desejamos um ano com muita saúde e boa visão.",
}


@dataclass(frozen=True)
class Rascunho:
    os_id: int
    cliente: str
    telefone: str
    tipo: str
    texto: str
    origem: str  # modelo | ia | modelo (ia reprovada)


def primeiro_nome(cliente: str) -> str:
    return cliente.split()[0]


def validar(texto: str) -> list[str]:
    """Regras que toda mensagem precisa cumprir antes de chegar a uma pessoa."""
    problemas = []
    if len(texto) > LIMITE:
        problemas.append(f"passa de {LIMITE} caracteres")
    if "R$" in texto or "http" in texto.lower():
        problemas.append("traz valor em dinheiro ou link")
    if "SAIR" not in texto:
        problemas.append("sem a opção de sair")
    return problemas


class Redator(Protocol):
    def escrever(self, alvo: Alvo) -> str: ...


class RedatorModelo:
    def escrever(self, alvo: Alvo) -> str:
        base = MODELOS[alvo.tipo].format(nome=primeiro_nome(alvo.os.cliente), produto=alvo.os.produto)
        return f"{base} {RODAPE}"


def _post_urllib(url: str, cabecalhos: dict, corpo: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), headers=cabecalhos, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:  # pragma: no cover - rede real
        return json.loads(r.read())


class RedatorAnthropic:
    """Pede à IA um texto mais natural. Só recebe o primeiro nome, o tipo e o produto (nunca telefone ou valor)."""

    def __init__(self, chave: str | None = None, modelo: str | None = None, post: Callable = _post_urllib):
        self.chave = chave or os.environ.get("ANTHROPIC_API_KEY", "")
        self.modelo = modelo or os.environ.get("OTICA_MODELO", "claude-haiku-5-5")
        self.post = post
        if not self.chave:
            raise ValueError("Defina ANTHROPIC_API_KEY para usar o redator com IA.")

    def escrever(self, alvo: Alvo) -> str:
        pedido = (
            f"Escreva uma mensagem curta e simpática de WhatsApp, em português, de uma ótica para {primeiro_nome(alvo.os.cliente)}. "
            f"Assunto: {alvo.tipo} (produto: {alvo.os.produto}). Não cite valores nem links. Termine com: {RODAPE}"
        )
        r = self.post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": self.chave, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            {"model": self.modelo, "max_tokens": 200, "messages": [{"role": "user", "content": pedido}]},
        )
        return "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text").strip()


def gerar_rascunhos(alvos: list[Alvo], redator: Redator | None = None) -> list[Rascunho]:
    redator = redator or RedatorModelo()
    fallback = RedatorModelo()
    saida = []
    for a in alvos:
        texto, origem = redator.escrever(a), "modelo" if isinstance(redator, RedatorModelo) else "ia"
        if validar(texto):
            texto, origem = fallback.escrever(a), "modelo (ia reprovada)" if origem == "ia" else "modelo"
        saida.append(Rascunho(a.os.id, a.os.cliente, a.os.telefone, a.tipo, texto, origem))
    return saida
