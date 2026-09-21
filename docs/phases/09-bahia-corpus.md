# Fase 9 — Corpus longitudinal do Bahia

Estado: planejada. Depende da fase 8.

## Objetivo

Reunir dados rastreáveis das partidas do Bahia sem exigir cobertura equivalente dos
demais clubes. Começar pelas dez partidas do piloto e ampliar somente após medir
completude, custo de revisão e direitos de uso.

## Entregas planejadas

- [ ] Catalogar partida, competição, rodada, estádio, mando, adversário, placar,
  estado e horários observados.
- [ ] Coletar escalações, banco, substituições, cartões e eventos onde disponíveis.
- [ ] Vincular súmula, páginas oficiais, snapshots de provedores e mídia à partida.
- [ ] Registrar elenco e comissão técnica como observações temporais, não como
  atributos permanentes.
- [ ] Preservar arquivos brutos, hashes, origem, horário de coleta e revisões.
- [ ] Registrar vídeo por metadados e direitos; manter mídia fora do Git.
- [ ] Medir completude por partida, campo e fonte.
- [ ] Separar informação conhecida antes do jogo de documentos publicados depois.

## Critérios de aceite

As dez partidas do piloto possuem identidade única, proveniência reproduzível e
relatório de completude. Ausência, indisponibilidade e não aplicabilidade são estados
distintos. Nenhum dado pós-jogo é apresentado como evidência pré-jogo.

## Verificação

Testar deduplicação, revisões, integridade por hash, horários, partidas adiadas e
conflitos entre fontes. Conferir manualmente pelo menos duas partidas e todos os
casos de identidade ambígua. Dados locais, vídeos e credenciais permanecem ignorados
pelo Git.

## Limites

Um catálogo disponível na web não comprova licença, estabilidade ou cobertura.
Oponente é armazenado como contexto da partida do Bahia; sua análise longitudinal
completa pertence à fase 14.
