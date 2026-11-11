import datetime as dt
import io
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path

from otica.cli import RAIZ, main
from otica.dados import OrdemServico, carregar_csv, gerar, gravar_csv
from otica.kpis import calcular, estimativa_de_tempo, meses_anteriores
from otica.mensagens import LIMITE, RedatorAnthropic, RedatorModelo, gerar_rascunhos, validar
from otica.painel import brl, gerar_html
from otica.regras import Alvo, aniversariantes, atrasados, prontos_nao_retirados, receitas_a_vencer, todos_os_alvos

HOJE = dt.date(2026, 11, 10)


def os_(id=1, cliente="Ana Silva", produto="óculos de grau", status="pronto", pedido="2026-10-01", prometida="2026-10-08",
        pronto="2026-10-08", entrega="", receita="2026-09-30", nascimento="1990-05-05", valor=500.0):
    return OrdemServico(id, cliente, "(99) 90000-0000", nascimento, produto, valor, pedido, prometida, pronto, entrega, status, receita)


class DadosTest(unittest.TestCase):
    def test_deterministico(self):
        self.assertEqual(gerar(60, 3), gerar(60, 3))
        self.assertNotEqual(gerar(60, 3), gerar(60, 4))

    def test_csv_ida_e_volta(self):
        ordens = gerar(50, 2)
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "o.csv"
            gravar_csv(ordens, c)
            self.assertEqual(carregar_csv(c), ordens)

    def test_csv_invalido(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "o.csv"
            c.write_text("id,cliente\n1,Ana\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "colunas faltando"):
                carregar_csv(c)
            c.write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                carregar_csv(c)

    def test_status_invalido_e_recusado(self):
        cab = "id,cliente,telefone,nascimento,produto,valor,data_pedido,data_prometida,data_pronto,data_entrega,status,data_receita\n"
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "o.csv"
            c.write_text(cab + "7,Ana Silva,(99) 90000-0000,1990-05-05,conserto,50,2026-11-01,2026-11-03,,,sumiu,\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "status inválido na ordem 7"):
                carregar_csv(c)

    def test_dados_de_exemplo_cobrem_todos_os_tipos(self):
        ordens = carregar_csv(RAIZ / "data" / "ordens.csv")
        c = Counter(a.tipo for a in todos_os_alvos(ordens, HOJE))
        for tipo in ("retirada", "atraso", "receita", "aniversario"):
            self.assertGreater(c[tipo], 0, tipo)


class RegrasTest(unittest.TestCase):
    def test_pronto_nao_retirado_respeita_o_prazo(self):
        self.assertEqual(len(prontos_nao_retirados([os_(pronto="2026-11-05")], HOJE)), 1)
        self.assertEqual(prontos_nao_retirados([os_(pronto="2026-11-09")], HOJE), [])  # pronto há 1 dia: ainda cedo
        self.assertEqual(prontos_nao_retirados([os_(status="entregue", pronto="2026-11-01")], HOJE), [])

    def test_atrasado(self):
        a = atrasados([os_(status="em_producao", prometida="2026-11-05", pronto="")], HOJE)
        self.assertEqual(len(a), 1)
        self.assertEqual(atrasados([os_(status="em_producao", prometida="2026-11-12", pronto="")], HOJE), [])
        self.assertEqual(atrasados([os_(status="entregue", prometida="2026-10-01")], HOJE), [])

    def test_receita_a_vencer_considera_so_a_mais_recente(self):
        antiga = os_(1, receita="2025-11-20")  # vence 2026-11-20: dentro da janela
        nova = os_(2, receita="2026-09-01")    # mesma cliente, receita mais nova: não precisa de aviso
        self.assertEqual(len(receitas_a_vencer([antiga], HOJE)), 1)
        self.assertEqual(receitas_a_vencer([antiga, nova], HOJE), [])

    def test_receita_fora_da_janela_ou_ja_vencida(self):
        self.assertEqual(receitas_a_vencer([os_(receita="2026-06-01")], HOJE), [])
        self.assertEqual(receitas_a_vencer([os_(receita="2025-10-01")], HOJE), [])  # venceu em 2026-10-01

    def test_cancelada_e_sem_receita_sao_ignoradas(self):
        self.assertEqual(receitas_a_vencer([os_(status="cancelado", receita="2025-11-20")], HOJE), [])
        self.assertEqual(receitas_a_vencer([os_(receita="")], HOJE), [])

    def test_aniversariante_sem_duplicar_cliente(self):
        ordens = [os_(1, nascimento="1990-11-10"), os_(2, nascimento="1990-11-10"), os_(3, "Bia Lima", nascimento="1991-11-11")]
        self.assertEqual([a.os.cliente for a in aniversariantes(ordens, HOJE)], ["Ana Silva"])


class MensagensTest(unittest.TestCase):
    def alvo(self, tipo="retirada"):
        return Alvo(tipo, os_())

    def test_modelo_usa_primeiro_nome_e_passa_na_validacao(self):
        for tipo in ("retirada", "atraso", "receita", "aniversario"):
            texto = RedatorModelo().escrever(self.alvo(tipo))
            self.assertTrue(texto.startswith(("Olá, Ana!", "Feliz aniversário, Ana!")), texto)
            self.assertEqual(validar(texto), [], texto)

    def test_nao_vaza_dados_sensiveis(self):
        texto = RedatorModelo().escrever(Alvo("retirada", os_(valor=999.99)))
        self.assertNotIn("999", texto)
        self.assertNotIn("(99)", texto)
        self.assertNotIn("Silva", texto)

    def test_validar_detecta_problemas(self):
        self.assertTrue(validar("x" * (LIMITE + 1) + " SAIR"))
        self.assertTrue(any("dinheiro" in p for p in validar("Pague R$ 10. SAIR")))
        self.assertTrue(any("link" in p for p in validar("veja http://x.com SAIR")))
        self.assertTrue(any("sair" in p for p in validar("Olá!")))

    def test_ia_reprovada_volta_para_o_modelo(self):
        class Safado:
            def escrever(self, alvo):
                return "Compre agora por R$ 10 em http://golpe.com"
        r = gerar_rascunhos([self.alvo()], Safado())
        self.assertEqual(r[0].origem, "modelo (ia reprovada)")
        self.assertEqual(validar(r[0].texto), [])

    def test_anthropic_envia_so_o_necessario_e_valida_o_retorno(self):
        enviados = []
        def post(url, cab, corpo):
            enviados.append(corpo)
            return {"content": [{"type": "text", "text": "Oi Ana, seu pedido chegou! Para não receber mais mensagens, responda SAIR."}]}
        red = RedatorAnthropic(chave="k", modelo="m", post=post)
        r = gerar_rascunhos([self.alvo()], red)
        corpo = str(enviados[0])
        self.assertIn("Ana", corpo)
        self.assertNotIn("Silva", corpo)
        self.assertNotIn("(99)", corpo)
        self.assertNotIn("500", corpo)
        self.assertEqual(r[0].origem, "ia")

    def test_anthropic_reprovada_cai_no_modelo(self):
        red = RedatorAnthropic(chave="k", post=lambda *a: {"content": [{"type": "text", "text": "Pague R$ 50 agora"}]})
        r = gerar_rascunhos([self.alvo()], red)
        self.assertEqual(r[0].origem, "modelo (ia reprovada)")

    def test_exige_chave(self):
        import os
        antigo = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with self.assertRaises(ValueError):
                RedatorAnthropic(chave="")
        finally:
            if antigo:
                os.environ["ANTHROPIC_API_KEY"] = antigo


class KpisTest(unittest.TestCase):
    def test_meses(self):
        m = meses_anteriores(dt.date(2026, 2, 10), 4)
        self.assertEqual(m, ["2025-11", "2025-12", "2026-01", "2026-02"])

    def test_calculos_a_mao(self):
        ordens = [
            os_(1, valor=100.0, status="entregue", pedido="2026-11-01", prometida="2026-11-05", pronto="2026-11-04"),
            os_(2, valor=300.0, status="entregue", pedido="2026-11-02", prometida="2026-11-05", pronto="2026-11-08"),
            os_(3, valor=999.0, status="cancelado", pedido="2026-11-03", prometida="2026-11-05", pronto=""),
        ]
        k = calcular(ordens, HOJE)
        self.assertEqual(k["faturamento"], 400.0)
        self.assertEqual(k["ticket_medio"], 200.0)
        self.assertEqual(k["tempo_medio_producao_dias"], 4.5)  # (3 + 6) / 2

    def test_taxa_de_atraso_e_cancelamento(self):
        ordens = [
            os_(1, status="entregue", pedido="2026-11-01", prometida="2026-11-05", pronto="2026-11-04"),
            os_(2, status="entregue", pedido="2026-11-02", prometida="2026-11-05", pronto="2026-11-08"),
            os_(3, status="cancelado", pronto=""),
            os_(4, status="em_producao", pronto=""),
        ]
        k = calcular(ordens, HOJE)
        self.assertEqual(k["taxa_atraso"], 0.5)
        self.assertEqual(k["taxa_cancelamento"], 0.25)
        self.assertEqual(k["funil"]["cancelado"], 1)

    def test_estimativa_declara_a_suposicao(self):
        e = estimativa_de_tempo(10)
        self.assertEqual(e["minutos"], 20)
        self.assertEqual(e["suposicao_min_por_mensagem"], 2)


class PainelECliTest(unittest.TestCase):
    def test_brl(self):
        self.assertEqual(brl(1234567.5), "R$ 1.234.567,50")

    def test_painel_nao_expoe_dados_pessoais(self):
        ordens = carregar_csv(RAIZ / "data" / "ordens.csv")
        alvos = todos_os_alvos(ordens, HOJE)
        r = gerar_rascunhos(alvos)
        html = gerar_html(calcular(ordens, HOJE), dict(Counter(a.tipo for a in alvos)), r, HOJE, estimativa_de_tempo(len(r)))
        for o in ordens[:30]:
            self.assertNotIn(o.telefone, html)
        self.assertIn("Dados fictícios", html)
        self.assertIn('lang="pt-BR"', html)
        self.assertNotIn("<script", html)

    def test_cli_rotina_grava_rascunhos_sem_aprovar_nada(self):
        with tempfile.TemporaryDirectory() as d:
            saida = Path(d) / "r.csv"
            buf = io.StringIO()
            with redirect_stdout(buf):
                main(["rotina", "--saida", str(saida)])
            linhas = saida.read_text(encoding="utf-8").splitlines()
            self.assertTrue(linhas[0].endswith("aprovado"))
            self.assertTrue(all(l.endswith(",") for l in linhas[1:]))  # 'aprovado' vazio: nada enviado
            self.assertIn("nada foi enviado", buf.getvalue())

    def test_cli_resumo_e_painel(self):
        with tempfile.TemporaryDirectory() as d:
            buf = io.StringIO()
            with redirect_stdout(buf):
                main(["resumo"])
                main(["painel", "--saida", str(Path(d) / "p" / "index.html")])
            self.assertIn("ordens", buf.getvalue())
            self.assertTrue((Path(d) / "p" / "index.html").exists())

    def test_dados_gravados_batem_com_o_gerador(self):
        self.assertEqual(carregar_csv(RAIZ / "data" / "ordens.csv"), gerar())


if __name__ == "__main__":
    unittest.main()
