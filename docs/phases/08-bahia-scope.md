# Fase 8 — Recorte Bahia e protocolo observacional

Estado: implementada e validada estruturalmente em 21/09/2026. A validação das
categorias comportamentais com vídeo autorizado continua na fase 10.

## Objetivo e dependências

Transformar a exploração ampla das fases anteriores em um programa longitudinal
centrado no Bahia. Depende da infraestrutura das fases 0–7, mas não depende da
contratação de uma nova fonte nem de um modelo de vídeo.

## Entregas planejadas

- [x] Registrar os identificadores canônicos do clube em cada fonte utilizada,
  sem fundir IDs apenas por semelhança de nome.
- [x] Definir temporadas, competições e limites temporais iniciais do estudo.
- [x] Selecionar dez partidas para o piloto, cobrindo casa/fora, diferentes resultados
  do placar e adversários com características distintas.
- [x] Definir perguntas observáveis para equipe, técnico e jogadores.
- [x] Criar taxonomia inicial de fases do jogo, ações, zonas, contexto e confiança.
- [x] Definir o contrato mínimo de uma evidência: partida, fonte, instante, entidade,
  observação, confiança, revisão e limite de interpretação.
- [x] Registrar disponibilidade, licença e restrições de cada fonte e vídeo.
- [x] Definir o contexto mínimo do adversário sem construir um perfil completo dele.

Artefatos: [`../bahia/scope.md`](../bahia/scope.md),
[`../bahia/pilot-2026.json`](../bahia/pilot-2026.json),
[`../bahia/taxonomy.md`](../bahia/taxonomy.md) e
[`../bahia/evidence-contract.md`](../bahia/evidence-contract.md).

## Critérios de aceite

O corpus-piloto possui dez partidas identificadas, fontes verificáveis e diversidade
de contexto documentada. Cada pergunta de pesquisa pode ser respondida por campos
observáveis; termos vagos como “mania”, “intensidade” ou “jogou mal” não entram sem
definição operacional. Nenhum vídeo é coletado ou redistribuído sem situação de uso
registrada.

## Verificação

Revisar manualmente a lista de partidas, IDs e fontes. Validar a taxonomia em duas
partidas contrastantes antes de congelar a primeira versão. Confirmar que uma
observação sempre pode apontar para sua evidência e que campos desconhecidos aceitam
valor ausente em vez de inferência.

Resultado: catálogo com dez partidas concluídas, cinco em casa/cinco fora e
distribuição 4–3–3 de vitória/empate/derrota. IDs `1777` e `61377` foram ligados por
23 partidas de 2026; o ID CBF histórico `20006` permanece não conciliado e `21878`
foi excluído como Bahia de Feira. O
[dry run](../experiments/bahia-phase-8-dry-run.md) validou o contrato em uma vitória
em casa e uma derrota fora sem inventar conteúdo tático. Testes automatizados
verificam cardinalidade, equilíbrio, IDs, URLs e campos obrigatórios do esquema.

## Fora do escopo

Perfis completos de adversários, comparação entre clubes, previsão de lucro,
diagnóstico médico, inferência de intenção e conclusões causais.
