# Hipótese futura — análise de partidas completas em vídeo

Ideia registrada em 19/09/2026 para a fase 7. Analisar os 90 minutos e acréscimos de
partidas anteriores para estudar estratégias de equipes e tendências observáveis de
jogadores e treinadores. É um plano de pesquisa: nenhum vídeo foi coletado e nenhum
modelo de vídeo foi treinado ou incorporado às probabilidades.

## Perguntas de pesquisa

- Equipes: criação de chances, progressão, transições, bolas paradas, pressão e
  mudanças de organização conforme adversário, mando, placar e expulsões.
- Jogadores: escolhas recorrentes de passe, condução, finalização, posicionamento
  e resposta a situações similares, condicionadas por função e tempo em campo.
- Treinadores: padrões observáveis de substituição, mudanças de formação e ajustes
  táticos ao longo de várias partidas. Um lance isolado não define uma tendência.

## Dados e método propostos

1. Confirmar direito de acesso, processamento, armazenamento e eventual publicação
   dos vídeos. Registrar fonte, competição, partida, câmera, hash e horários.
2. Fazer piloto de detecção de eventos com marcação de tempo, equipe, jogador quando
   verificável e confiança. Revisar manualmente uma amostra; medir erros e cobertura.
3. Só depois avaliar rastreamento e posição em campo. Transmissões cortam parte do
   gramado, replays e jogadores fora do quadro; câmera tática pode ampliar cobertura.
4. Agregar tendências de partidas **anteriores** ao instante da previsão, com
   amostra, contexto e qualidade da extração. Dados do próprio jogo servem para
   análise posterior ou modelo ao vivo, nunca para prever seu pré-jogo.
5. Comparar novas variáveis com o Poisson atual no protocolo temporal da fase 3,
   medindo log loss, Brier, calibração e cobertura. Manter a informação apenas
   descritiva se não houver ganho confiável.

O [SoccerNet](https://www.soccer-net.org/tasks/action-spotting) oferece tarefas de
detecção de eventos e vídeos para pesquisa; sua [FAQ](https://www.soccer-net.org/faq)
informa restrições de uso comercial dos vídeos. A fonte de vídeo para partidas
brasileiras e seus direitos ainda precisam ser definidos. Súmulas CBF podem ajudar
na checagem de eventos e participantes, respeitando a disponibilidade pós-jogo.
