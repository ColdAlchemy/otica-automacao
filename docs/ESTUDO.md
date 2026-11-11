# Guia de estudo — otica-automacao

## 1. Roteiro de leitura
1. `otica/dados.py`: o formato das ordens e como o gerador cria dados verossímeis.
2. `otica/regras.py`: as quatro regras (funções puras).
3. `otica/mensagens.py`: rascunhos, validação e o redator com IA.
4. `otica/kpis.py`: indicadores e a estimativa de tempo.
5. `otica/painel.py`: HTML estático.
6. `tests/test_otica.py`: os cálculos feitos à mão.

## 2. Conceitos
**Automação de rotina.** Transformar uma tarefa que alguém faz olhando planilha em um passo repetível e confiável.

**Função pura.** Dá sempre o mesmo resultado para a mesma entrada e não depende de relógio nem de arquivo. As regras recebem `hoje` como parâmetro, então o teste fixa a data e o resultado é previsível.

**Humano no laço.** A automação prepara e uma pessoa decide. Aqui a coluna `aprovado` fica vazia: nada é enviado sozinho.

**Validação da saída de uma IA.** Texto gerado por IA pode sair fora do padrão (valor, link, texto longo). Valide antes de usar e tenha um plano B (aqui, o modelo de texto).

**Minimização de dados.** A IA recebe só o primeiro nome, o tipo e o produto. Quanto menos dado pessoal sai do seu sistema, menor o risco.

**Dados sintéticos e determinismo.** Com semente fixa, o gerador sempre produz o mesmo CSV, e um teste garante que o arquivo versionado é igual ao gerado.

**Estimativa × medição.** "Economiza X horas" só vale se você mediu. Aqui é uma estimativa sob uma suposição declarada (2 min por mensagem), e o projeto diz isso.

**LGPD (noções).** Telefone e data de nascimento são dados pessoais: exigem base legal, consentimento para marketing e a opção de sair.

## 3. Perguntas prováveis (treine em voz alta)
- *Isso economiza quantas horas de verdade?* Não medi. É uma estimativa com uma suposição declarada; numa loja real eu mediria antes e depois.
- *Está em uso na sua ótica?* Não: é um projeto de portfólio com dados fictícios, inspirado na minha rotina.
- *Por que não enviar as mensagens sozinho?* Porque um erro vira mensagem errada para um cliente de verdade. Uma pessoa revisa e envia.
- *Como você evita que a IA mande algo indevido?* Ela recebe poucos dados, e todo texto passa por validação; se reprovar, usa o modelo de texto.
- *Por que as regras recebem `hoje`?* Para testar sem depender da data do computador.
- *Como você integraria isso a um sistema real?* Lendo o banco do ERP em vez do CSV e enviando por uma API de mensagens, mantendo a aprovação humana.

## 4. Exercícios
1. Crie uma quinta regra: clientes sem pedido há 12 meses ("sentimos sua falta").
2. Mude o prazo da retirada de 3 para 7 dias e veja o efeito nos rascunhos.
3. Escreva um teste para uma ordem sem `data_prometida`. O que o código faz hoje?
4. Adicione o indicador "taxa de retirada em até 3 dias" ao painel.
5. Troque o CSV por uma leitura de SQLite mantendo as regras iguais.

## 5. O que dizer sobre a sua experiência (sem exagerar)
"Construí uma automação que lê ordens de serviço, aplica regras de contato com clientes, gera rascunhos de mensagem para revisão humana e produz um painel de indicadores. Usei dados fictícios, a economia de tempo é uma estimativa com suposição declarada, e desenvolvi com o auxílio do Claude Code, estudando o código." Não diga que "automatizou a minha loja" nem que "economizou N horas": não foi medido nem está em uso.
