# Cotações e carteira virtual — política paper-v1

Esta implementação acompanha decisões prospectivas em saldo virtual. Não integra
casas de apostas, não movimenta dinheiro e não importa resultados financeiros do
experimento retrospectivo da fase 3. Fonte esportiva continua sendo football-data.org.

## Fluxo de uso

1. Atualize e normalize resultados e agenda de BSA.
2. Gere uma previsão para uma partida futura com `forecast`.
3. Registre cotações reais recentes com `odds-add` ou `odds-import`.
4. Compare usando `odds-assess`, no horário atual.
5. Se desejar acompanhar uma decisão elegível, registre-a com `paper-bet`.
6. Após atualizar os resultados, execute `paper-settle` e consulte `paper-wallet`.

```bash
uv run sports-stats-analyzer collect matches --competition BSA --season 2026
uv run sports-stats-analyzer normalize
uv run sports-stats-analyzer forecast ID_DA_PARTIDA
uv run sports-stats-analyzer odds-import data/odds.csv
uv run sports-stats-analyzer odds-assess ID_DA_COTACAO ID_DA_PREVISAO
uv run sports-stats-analyzer paper-bet ID_DA_COTACAO ID_DA_PREVISAO
uv run sports-stats-analyzer paper-settle
uv run sports-stats-analyzer paper-wallet
```

Substitua os IDs pelos retornados pelos comandos. Não execute os placeholders
literalmente. `forecast`, `odds-assess` e `paper-bet` usam o relógio atual, sem opção
de retroagir decisões. `paper-settle` usa resultados já observados e normalizados;
ele não consulta a rede. Coletar dados posteriores não altera uma previsão já gravada.

## Previsão prospectiva

`forecast` aceita apenas BSA, status SCHEDULED/TIMED, antes do início, com agenda
observada nas últimas 24 horas. Usa Poisson com penalidade 10, rho 0, treinamento
expansivo desde 01/01/2023, somente resultados observados no momento da emissão
e com início mais de três horas antes dela. Exige 100 jogos no treino, cinco por
equipe e pelo menos um resultado da competição nos últimos 45 dias.

Modelo permanece experimental. A referência de 45 dias é uma regra operacional
de atualização, não garantia de cobertura completa. Elencos e notícias não alteram
as probabilidades. Falta de dados ou partidas já iniciadas causam abstenção/erro.
O snapshot da agenda, parâmetros, versões, hash do treino e IDs das revisões são
persistidos junto com a previsão. Esta não é uma importação de previsões históricas.

## Cotação manual e CSV

O [template](../examples/odds-template.csv) contém apenas o cabeçalho, sem odds fictícias:

```text
match_id,market,selection,line,odds,bookmaker,observed_at,source
```

| Campo | Contrato |
| --- | --- |
| match_id | ID positivo da partida normalizada na football-data.org |
| market | `1x2`, `total_goals` ou `btts` |
| selection | `home/draw/away`, `over/under` ou `yes/no`, respectivamente |
| line | `2.5` apenas para `total_goals`; vazio nos outros mercados |
| odds | Decimal com ponto; maior que 1 e no máximo 1000; não aceita NaN/infinito |
| bookmaker | Identificação da casa, não vazia |
| observed_at | Horário real da observação, ISO 8601 com fuso |
| source | Origem identificável, como URL ou registro da consulta |

CSV UTF-8, separador vírgula, exatamente essas oito colunas; ordem flexível.
Importação é transacional: um registro inválido rejeita o lote inteiro.
Uma cotação repetida não duplica registros. Mesma partida/mercado/seleção/linha/
casa/horário/origem com odd diferente é conflito, não atualização silenciosa.

Exemplo de comando manual, com valores a substituir por uma observação verdadeira:

```bash
uv run sports-stats-analyzer odds-add --match-id ID_DA_PARTIDA --market 1x2 --selection home --odds ODD_OBSERVADA --bookmaker CASA --observed-at HORARIO_ISO_COM_FUSO --source ORIGEM
```

O horário informado deve estar nos últimos 15 minutos e não pode estar no futuro.
O horário de recebimento local também é salvo. Só importar odds de partida ainda
não iniciada. Odds antigas não ganham validade trocando sua data; a origem manual
não tem verificação externa automática de autenticidade.

## Avaliação e abstenção

As previsões e odds precisam existir no momento atual da decisão. Uma cotação pode
ter sido observada depois da previsão: a comparação é feita **agora**, nunca retroage
ao horário da previsão. A previsão tem validade operacional de 24 horas; a cotação,
15 minutos. Mudança de horário/equipes, partida iniciada e agenda antiga invalidam a avaliação.

Para cada seleção:

```text
probabilidade implícita = 1 / odd
EV por unidade = p × odd − 1
p no cenário de estresse = max(0, p − 0.05)
```

Exemplo aritmético: p=0,60 e odd=1,80 resultam em EV=0,08. O cenário de estresse
reduz cinco pontos percentuais. Não é intervalo de confiança nem estimativa do erro
do modelo; `uncertainty_interval` permanece nulo. Ele apenas testa sensibilidade.

Elegibilidade virtual exige EV pontual de pelo menos 0,02 e EV estressado positivo.
Esses limiares são regras exploratórias fixas. Resultado pode ser `abstain`, com motivos,
ou `eligible_virtual`; o segundo não significa aposta segura ou execução automática.
Somente 1X2 em BSA é elegível para a carteira. Mercados de gols/ambas marcam podem ser
importados e examinados, mas se abstêm por falta de validação específica.

Remoção de margem usa normalização proporcional de `1/odd`, exclusivamente quando
há todas as seleções mutuamente exclusivas com mesma casa, partida, mercado, linha,
origem e horário. Não combina as melhores odds de casas/horários diferentes.
Mercado incompleto retorna `fair_market=null`. Probabilidades normalizadas não são
probabilidades verdadeiras garantidas; overround negativo é reportado como tal.

## Regras da carteira virtual

- Saldo inicial: 100 unidades. Cada aposta: uma unidade, sem reinvestimento variável.
- Máximo reservado em apostas abertas: cinco unidades. Saldo livre precisa cobrir a unidade.
- Uma aposta por partida durante toda a carteira, inclusive após anulação; evita
  duplicidade e exposição a múltiplos mercados correlacionados do mesmo jogo.
- Carteira única local; não há reset, depósito ou ajuste retroativo de estratégia.
- O registro guarda previsão, cotação, avaliação, política e horário da decisão.

Saldo realizado = 100 + resultados liquidados. Saldo disponível = realizado menos
unidades reservadas em apostas abertas. Verificação de duplicidade/exposição e
inserção usam transação SQLite com bloqueio de escrita.

## Liquidação

Regras próprias da simulação, não uma reprodução das regras de qualquer casa:

| Situação observada | Tratamento |
| --- | --- |
| Finalizada, placar regulamentar conhecido, início há mais de três horas | Vitória ou derrota em 1X2 |
| POSTPONED, CANCELLED ou AWARDED | Anulada, unidade liberada, lucro zero |
| Alteração de horário, mandante ou visitante | Anulada |
| SUSPENDED sem alteração de agenda/equipes | Permanece aberta |
| Finalizada sem placar regulamentar conhecido | Permanece aberta |

Prorrogação e disputa de pênaltis não substituem o placar regulamentar. Vitória
gera `odd − 1` de lucro, derrota gera −1; valores são arredondados a duas casas
com ROUND_HALF_UP. Não modelamos taxas, comissão, tributação ou limites de casas.
Rodar novamente não duplica liquidação. Correções posteriores da fonte não reescrevem
liquidações; o snapshot utilizado fica registrado para auditoria.

## Retorno e incerteza

ROI usa apenas apostas ganhas/perdidas, excluindo abertas e anuladas. Sem apostas
liquidadas, ROI é nulo. Maior queda é medida no saldo **realizado**, em ordem de
liquidação; liquidações simultâneas são agregadas. Não equivale a marcação a mercado
de posições abertas nem à sequência histórica de resultados se a atualização foi tardia.

Intervalo de 95% de ROI só aparece a partir de 20 apostas liquidadas: bootstrap
exploratório por partida, 2.000 amostras, semente 42. Não contempla toda dependência
entre times, temporadas e decisões nem garante robustez com apenas 20 apostas.
Não produz intervalo para a probabilidade de cada aposta.

Persistência: migração 2 aditiva, tabelas `market_quotes`, `paper_forecasts` e
`paper_bets` no SQLite local. Nenhuma credencial, cotação ou carteira é versionada.
