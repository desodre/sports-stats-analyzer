# Validação estrutural da fase 8 — Bahia

Data: 21/09/2026. Esta validação usa apenas metadados e resultados já armazenados;
não contém anotação tática nem afirmações derivadas de vídeo.

## Casos contrastantes

Foram usados dois extremos do piloto:

- `554802` / CBF `831957`: Bahia 2–0 RB Bragantino, em casa, vitória sem sofrer gol;
- `554816` / CBF `831968`: Remo 4–1 Bahia, fora, derrota por três gols.

Nos dois casos, o contrato representa IDs, mando, resultado e fonte sem preencher
jogador, fase, ação, zona, relógio ou estrutura. Esses campos permanecem `null` ou
`unknown`. Assim, o esquema não força conteúdo comportamental inexistente.

## Verificações

- IDs do foco: football-data.org `1777`, CBF `61377`.
- Os dois jogos possuem vínculo entre IDs de partida dos provedores.
- O resultado é convertido para a perspectiva do Bahia sem depender do mando.
- Fato observado e interpretação são campos separados.
- Fonte sem licença de redistribuição confirmada não recebe estado `permitted`.
- Replay, jogador, relógio, fase, ação e zona aceitam estado desconhecido.
- Oponente é contexto da partida e não ganha perfil longitudinal.

## Decisão

O contrato e a taxonomia `v1` estão aptos para iniciar o catálogo da fase 9 e a
anotação manual da fase 10. A validação é estrutural: categorias comportamentais
devem ser revistas novamente nas duas primeiras partidas com vídeo autorizado.
