# otica-automacao — a rotina de contato com clientes de uma ótica, automatizada, com painel

Automação em Python (só biblioteca padrão) que lê as **ordens de serviço** de uma ótica, decide **quem precisa de contato hoje**, escreve **rascunhos de mensagem para uma pessoa revisar** e gera um **painel HTML** com os indicadores do negócio.

> Desenvolvido por mim com o auxílio do Claude Code. Eu defini o escopo, revisei e estudei o código; o guia `docs/ESTUDO.md` explica cada parte. Surgiu da minha realidade como proprietário de uma ótica, mas **todos os dados, nomes e telefones deste repositório são fictícios** e o projeto **não está ligado ao sistema da minha loja**.

**Painel de exemplo:** https://coldalchemy.github.io/otica-automacao/

## Para que serve (em termos simples)
Em uma ótica, muita gente some depois de fazer o pedido: o óculos fica pronto e ninguém avisa, o pedido atrasa e o cliente só descobre quando liga, a receita vence e a pessoa não lembra de renovar. Quem cuida da loja não tem tempo de olhar planilha todo dia. Esta automação **olha as ordens todo dia por você** e entrega uma lista pronta: "estes 6 pedidos estão prontos esperando retirada, estes 3 estão atrasados, estas 2 receitas vencem em 30 dias, estes 2 clientes fazem aniversário hoje", cada um com **uma mensagem já escrita**. A pessoa só confere e envia. O painel mostra vendas por mês, ticket médio, tempo de produção e cancelamentos.

## O que ela faz
| Regra | Quando dispara |
|---|---|
| Retirada | pedido **pronto** parado na loja há 3 dias ou mais |
| Atraso | pedido ainda **em produção** depois da data prometida |
| Receita | a receita do exame vence nos próximos 30 dias e o cliente não tem pedido mais novo |
| Aniversário | o cliente faz aniversário hoje |

Cada alvo vira um **rascunho** em `data/rascunhos.csv`, com a coluna `aprovado` vazia. **Nada é enviado.**

## Cuidados de projeto
- **Humano no laço:** a automação prepara, a pessoa aprova e envia.
- **Toda mensagem é validada**, venha de modelo de texto ou de IA: até 320 caracteres, sem valores em dinheiro, sem links e com a opção de sair ("responda SAIR"). Uma mensagem de IA reprovada volta para o modelo de texto.
- **A IA só recebe o necessário:** primeiro nome, tipo de contato e produto. Nunca telefone, valor ou sobrenome (há teste para isso).
- **O painel não expõe dados pessoais:** só números e exemplos de texto.
- **Regras como funções puras** (recebem "hoje"), o que as torna fáceis de testar sem mexer no relógio.

## Uso
```bash
python -m otica gerar-dados      # recria data/ordens.csv (fictício, determinístico)
python -m otica resumo           # indicadores no terminal
python -m otica rotina           # decide quem contatar e grava os rascunhos
python -m otica painel           # grava docs/index.html
python -m unittest               # 27 testes, sem rede
```
`rotina --com-ia` usa a API da Anthropic para redigir (exige `ANTHROPIC_API_KEY`). **Nenhuma dependência.** Testado no Python 3.14 (a sintaxe exige 3.10 ou mais novo). Para usar seus próprios dados, aponte `--csv` para um arquivo com as mesmas colunas de `data/ordens.csv`.

## Sobre a economia de tempo
A rotina e o painel mostram uma **estimativa** de minutos poupados, calculada com a **suposição** de 2 minutos para escrever e conferir cada mensagem à mão. **É uma estimativa, não uma medição**: eu não medi isso em uma loja real. Se a suposição for outra, o número muda (ela é a constante `MINUTOS_POR_MENSAGEM_MANUAL` em `kpis.py`).

## O que tem dentro
| Módulo | Papel |
|---|---|
| `dados.py` | gerador determinístico de ordens fictícias; leitura e gravação de CSV com validação |
| `regras.py` | as quatro regras de contato |
| `mensagens.py` | redator por modelos de texto, redator com IA (testado só com HTTP simulado) e validação |
| `kpis.py` | vendas por mês e produto, ticket médio, tempo de produção, atraso, cancelamento |
| `painel.py` | HTML estático, sem JavaScript, com tema claro/escuro e leitura em celular |

## Limitações
- Dados fictícios e gerados por regras simples: os números do painel não representam nenhuma loja real.
- Não envia mensagens (de propósito) e não se integra a WhatsApp, e-mail nem a um sistema de gestão.
- O redator com IA foi testado só com HTTP simulado, não contra a API real.
- Uma pessoa só é "aniversariante" se o CSV tiver a data de nascimento; em produção, esse dado pessoal exigiria consentimento e cuidado com a LGPD.
