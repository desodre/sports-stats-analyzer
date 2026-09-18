# Fase 4 — Jogadores, escalações e contexto

Estado: auditoria e contexto observável implementados; modelagem de impacto adiada
por cobertura insuficiente na amostra da fonte inicial.
Depende das fases 2 e 3; não exige introduzir outra API.

## Implementações

- [x] Auditar pessoas, escalações e substituições na conta e competição utilizadas.
- [x] Estender adaptador para detalhes de partidas, equipes e pessoas e expansão de listas.
- [x] Separar elenco observado e onze jogadores reportados; não inferir provável/confirmada.
- [x] Preservar observações e primeira observação do conjunto de onze jogadores reportado.
- [ ] Calcular minutos e métricas por posição somente onde existirem dados suficientes.
- [ ] Aplicar regularização a amostras pequenas e considerar qualidade dos adversários.
- [ ] Comparar cenários de escalação sem atribuir penalidades percentuais arbitrárias.
- [ ] Medir contribuição incremental ao modelo básico por avaliação temporal.

Implementação: `context.py`, extensão de `providers/football_data.py` e CLI.
Comandos: `collect-context`, `context-coverage`, `context-report`, `squad-report`,
`player-report` e `collect matches --unfold`. Módulo simples substitui pastas previstas.
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

## Resultado e itens adiados

Auditoria real em 17/09/2026 no fuso America/Manaus (18/09 em UTC): BSA 2025,
380 partidas com expansão solicitada, mais um detalhe de partida. Nenhuma das 381
observações detalhadas incluiu escalação, banco, substituições, gols individuais
ou cartões. Elenco do São Paulo retornou 46 jogadores; um perfil individual foi acessível.
Isso comprova a limitação dessa amostra, não identifica por si só o plano contratado.

Os quatro itens estatísticos não marcados acima passam para a fase 7: minutos e
métricas por posição, regularização de efeitos individuais, cenários e avaliação
incremental. Não há suporte para estimá-los nem para comparar modelo com/sem jogadores.
Nenhuma penalidade arbitrária foi adicionada ao Poisson e nenhuma nova API foi integrada.

Snapshots guardam observações completas; relatórios de contexto consultam diretamente
esses registros com corte temporal, sem nova migração. O normalizador das fases 1–2
processa a lista de partidas expandida e ignora detalhes de pessoa/equipe/partida,
que continuam disponíveis em bruto para contexto. `_unfold` nos filtros persistidos
é metadado local de requisição, não parâmetro enviado à API.

Uma lista posterior sem detalhes não apaga a última observação detalhada: relatório
mostra separadamente a evidência de contexto e o status mais recente. Nova observação
detalhada vazia/nula é respeitada. Os timestamps são observações locais, não publicação
ou confirmação oficial. Elenco é retrato da fonte, não comprovação de vínculo ou aptidão.

Ver [auditoria detalhada](../experiments/context-coverage-bsa.md).
Verificação: 65 testes aprovados, incluindo 15 novos de contexto; lint e formato aprovados.
