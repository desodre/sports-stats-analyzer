# Fase 4 — Jogadores, escalações e contexto

Estado: planejada e condicionada à cobertura da fonte inicial.
Depende das fases 2 e 3; não exige introduzir outra API.

## Implementações

- [ ] Auditar disponibilidade real de pessoas, escalações e substituições por plano.
- [ ] Estender o adaptador somente para recursos acessíveis e necessários.
- [ ] Diferenciar elenco cadastrado, escalação provável e escalação confirmada.
- [ ] Preservar horário em que cada escalação passou a ser observada.
- [ ] Calcular minutos e métricas por posição somente onde existirem dados suficientes.
- [ ] Aplicar regularização a amostras pequenas e considerar qualidade dos adversários.
- [ ] Comparar cenários de escalação sem atribuir penalidades percentuais arbitrárias.
- [ ] Medir contribuição incremental ao modelo básico por avaliação temporal.

Módulos previstos: `context/lineups.py`, `analytics/players.py` e extensões do provider.
Formação declarada não comprova comportamento tático. Notícias, lesões não documentadas,
xG e pressão detalhada permanecem fora desta fase quando não disponíveis na fonte.

## Critérios de aceite

Relatório de disponibilidade distingue ausência real de ausência de cobertura.
Sem minutos confiáveis, não apresentar estatísticas por 90 minutos. Sem escalação
confirmada, rotular cenários. Modelo básico continua utilizável sem esses campos.
Ativar ajustes apenas quando avaliação temporal sustentar seu benefício.

## Verificação

Fixtures de jogador transferido, elenco sem escalação, substituição e campo nulo.
Comparar modelo com/sem variáveis de jogadores no mesmo conjunto de partidas.
Se cobertura insuficiente, registrar a limitação e adiar itens para a fase 7.
