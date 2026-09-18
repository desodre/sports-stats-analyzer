# Fase 5 — Cotações, valor esperado e simulação

Estado: implementada e testada. Fluxo prospectivo disponível; validação financeira
real pendente de cotações e resultados observados, sem histórico fabricado.

## Implementações

- [x] Odds decimais por entrada manual ou CSV, sem outra API.
- [x] Partida, mercado, seleção, linha, casa, horário e origem obrigatórios.
- [x] Validação de odds, compatibilidade e validade temporal.
- [x] Probabilidade implícita e normalização proporcional da margem
      apenas quando existir conjunto completo de resultados mutuamente exclusivos.
- [x] `EV = p * odd - 1` para mercados sem devolução; regras de liquidação
      e regras próprias antes de suportar outros mercados.
- [x] EV com cenário de sensibilidade e qualidade dos dados; abstenção explícita.
- [x] Aposta unitária fixa, saldo virtual, retorno e queda máxima realizada.
- [x] Tamanho da amostra e IC exploratório do ROI a partir de 20 apostas liquidadas.

Implementação: `markets.py` e comandos CLI, com migração 2 aditiva.
Previsões prospectivas são geradas e persistidas localmente com dados observados;
não se importam previsões retrospectivas para a carteira. Sem execução automática de apostas,
integração com casas, múltiplas ou mecanismos para recuperar perdas.

## Critérios de aceite

Exemplo verificável: p=0,60 e odd=1,80 implica EV estimado de 0,08 por unidade.
Não comparar uma previsão antiga com cotação ainda indisponível naquela data.
Sem odds históricas confiáveis, avaliar prospectivamente com carteira virtual;
não declarar ROI retrospectivo. Tratar anuladas e adiadas conforme regras registradas.

## Verificação

Testar aritmética, arredondamento, entradas inválidas, margem com mercado incompleto,
liquidação e cronologia. Avaliar limites de exposição e duplicidade de registros.
Resultado positivo de simulação não constitui promessa de retorno futuro.

## Entrega e verificações

92 testes aprovados, incluindo 27 da fase 5: importação atômica, deduplicação,
cronologia, margem incompleta, EV, abstenção, exposição, anulação, liquidação
idempotente e sequência prospectiva sintética de 20 apostas. Lint e formato aprovados.

BSA 2026 coletado e normalizado (380 partidas). Uma previsão prospectiva real foi
registrada para a partida 555011 com 1.407 resultados anteriores no treino.
Não foram fornecidas odds reais: a carteira do projeto permanece com zero cotações,
zero apostas, saldo virtual 100 e ROI nulo. Os testes sintéticos são isolados em bancos temporários.

O cenário conservador de probabilidade não é um intervalo de confiança. A incerteza
da probabilidade individual permanece não estimada. Elegibilidade virtual não
comprova rentabilidade. Somente 1X2/BSA pode gerar aposta virtual nesta versão.

Ver [regras e comandos](../paper-trading.md), [template CSV](../../examples/odds-template.csv)
e [evidência da validação](../experiments/phase-5-validation.md).
