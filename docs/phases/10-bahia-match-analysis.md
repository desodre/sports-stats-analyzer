# Fase 10 — Anotação e análise de partidas do Bahia

Estado: planejada. Depende das fases 8 e 9.

## Objetivo

Converter vídeo, súmula e eventos em uma linha do tempo estruturada que permita
observar comportamentos recorrentes sem confundir edição, replay, ausência de imagem
ou interpretação humana com fatos confirmados.

## Entregas planejadas

- [ ] Implementar esquema de anotação com instante do vídeo e da partida, fase do
  jogo, zona, equipe, jogador, ação, resultado, evidência, confiança e revisão.
- [ ] Marcar cortes, replays, câmera sem cobertura e identidade desconhecida.
- [ ] Anotar manualmente duas partidas para validar vocabulário e esforço.
- [ ] Concluir as dez partidas do piloto com protocolo versionado.
- [ ] Criar métricas de cobertura, concordância de revisão e taxa de campos incertos.
- [ ] Avaliar automação somente contra a anotação humana revisada.
- [ ] Ligar eventos observados a súmulas sem tratar uma fonte como verdade absoluta.

## Critérios de aceite

Cada anotação é rastreável até uma evidência e distingue observação de interpretação.
Replays não duplicam eventos. O sistema consegue responder “não observável” e
“jogador desconhecido”. Mudanças na taxonomia geram nova versão, sem reescrever
silenciosamente análises anteriores.

## Verificação

Reanotar uma amostra sem consultar o primeiro resultado e medir divergências.
Revisar todos os eventos de baixa confiança. Para qualquer detector automático,
reportar precisão, erros temporais, duplicatas e cobertura apenas dos lances visíveis;
não extrapolar recall para a partida inteira quando o vídeo for de melhores momentos.

## Fora do escopo

Rastreamento físico confiável a partir de câmera incompleta, diagnóstico de fadiga,
identificação facial, intenção psicológica e treinamento de modelo de vídeo sem
direitos e conjunto de avaliação adequados.
