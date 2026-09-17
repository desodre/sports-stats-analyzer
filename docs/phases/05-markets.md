# Fase 5 — Cotações, valor esperado e simulação

Estado: planejada. Depende da fase 3 validada; fase 4 é opcional.

## Implementações

- [ ] Aceitar odds decimais por entrada manual ou CSV, sem integrar outra API.
- [ ] Exigir partida, mercado, seleção, linha, casa, horário e origem da observação.
- [ ] Validar odds finitas maiores que 1 e recusar registros incompatíveis ou vencidos.
- [ ] Calcular probabilidade implícita e remover margem com método documentado
      apenas quando existir conjunto completo de resultados mutuamente exclusivos.
- [ ] Calcular `EV = p * odd - 1` para mercados sem devolução; tratar liquidação
      e regras próprias antes de suportar outros mercados.
- [ ] Comparar vantagem estimada com incerteza e qualidade dos dados; permitir abstenção.
- [ ] Simular aposta unitária fixa com saldo virtual, retorno e queda máxima acumulada.
- [ ] Expor tamanho da amostra e intervalos de incerteza; não usar taxa de acerto isolada.

Módulos previstos: `markets/`, `backtesting/`. Sem execução automática de apostas,
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
