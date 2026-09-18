# Validação da fase 5

Data: 17/09/2026, America/Manaus (18/09 em UTC).

## Verificação com dados reais

Coleta de BSA 2026 no snapshot 8: 380 partidas normalizadas sem rejeições.
Previsão prospectiva `0b1965c3fe3b47daabad88f99fbf1b30`, emitida em
`2026-09-18T01:06:09.197786+00:00`, para a partida 555011, CA Mineiro × Chapecoense AF,
com início registrado em `2026-09-19T19:00:00+00:00`.

Treino: 1.407 resultados observados anteriores, expansivo desde 2023.
Hash SHA-256 do treino:
`231427bfb7eec0b4da21bb9ca20c83455ad34572d7dab1d7033f25f700434408`.

Distribuição 1X2 emitida: mandante 0,672579, empate 0,191892, visitante 0,135530.
Essas são estimativas experimentais registradas, não recomendação ou garantia.
Sem cotação observada, não há cálculo de vantagem financeira real a reportar.
A validade operacional da previsão é 24 horas após a emissão; a reprodução atual
do comando gera nova previsão e novo horário, não altera esse registro histórico.

Carteira real do projeto após validação: zero cotações, zero apostas abertas ou
liquidadas, saldo virtual 100 unidades, ROI nulo. Nenhuma odd foi inventada para
essa partida e nenhuma aposta foi enviada para uma casa.

## Testes automatizados

92 testes passaram, incluindo 27 adicionados para esta fase. Usam bancos temporários
e dados explicitamente sintéticos; não se misturam à carteira local.

Cobertura: odds inválidas, mercados e linhas incompatíveis, fuso ausente, CSV,
importação atômica, duplicatas e conflitos, EV, margem completa/incompleta,
cotação futura/vencida, previsão prospectiva, abstenção por cenário de estresse,
partidas diferentes, limites de exposição, aposta única, regras de anulação,
prorrogação sem placar regulamentar, mudanças de agenda e liquidação idempotente.

Uma sequência sintética de 20 apostas exercita geração de previsão, registro de
cotação, reserva de saldo, observação posterior de resultado e liquidação. Verifica
ROI e reprodutibilidade do bootstrap. Seu retorno é determinado pelos dados de teste
e não é evidência de rentabilidade do modelo.

Ainda falta acompanhar decisões com odds reais e quantidade suficiente de partidas.
O [protocolo da carteira](../paper-trading.md) define validade, limites, liquidação
e as limitações dos intervalos de incerteza.
