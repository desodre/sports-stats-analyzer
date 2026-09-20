# Hipótese futura — análise de partidas completas em vídeo

Ideia registrada em 19/09/2026 para a fase 7. Analisar os 90 minutos e acréscimos de
partidas anteriores para estudar estratégias de equipes e tendências observáveis de
jogadores e treinadores. Um vídeo curto de melhores momentos foi coletado em
20/09/2026; nenhuma partida completa foi coletada e nenhum modelo de vídeo foi
treinado ou incorporado às probabilidades.

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

## Piloto inicial com melhores momentos

Em 20/09/2026, foi identificado o [vídeo de melhores momentos de Corinthians 1 × 3
Fluminense](https://www.youtube.com/watch?v=78rS30sszUM), publicado pela ge tv para
a 28ª rodada do Brasileirão 2026. Os metadados indicam duração de 5min54. Uma
cópia local foi baixada para `data/videos/`, fora do Git. O arquivo tem 79.835.450
bytes e SHA-256 `563e060f576c379940ee75f74846242877490348614eb98b436b61371f8992f4`.
O [YouTube informa](https://support.google.com/youtube/answer/56100?hl=en) que não
oferece download dos vídeos enviados por outros usuários; uso e processamento do
material dependem dos direitos aplicáveis. Nenhum vídeo será distribuído pelo projeto.

Este vídeo pode testar a identificação de **eventos exibidos** e a ligação entre
instante do vídeo e relógio da partida. A seleção editorial impede medir cobertura
de todos os eventos, volume de passes, movimentação contínua, forma física ou fase
individual; tampouco permite concluir padrões de treinador a partir de um jogo.

### Protocolo com arquivo local

1. Registrar origem, licença/permissão, hash do arquivo, duração e partida. Manter
   vídeo e quadros fora do Git e dos dados de treino até definir sua licença.
2. Assistir aos 5min54 e marcar, por lance visível: segundo inicial/final do vídeo,
   minuto da partida se legível, tipo de evento, equipe, atleta apenas se confirmado,
   se é replay, evidência visual e confiança. Usar `desconhecido` para campos
   indetermináveis; replays não contam como segundo evento.
3. Rodar um primeiro detector de eventos sobre o mesmo arquivo e comparar sua
   saída com a anotação humana. Medir precisão dos eventos visíveis, erro de tempo
   com tolerância de cinco segundos e acerto de equipe/atleta somente nas linhas
   com identificação humana segura. Registrar falsos positivos e casos ignorados.
4. Conferir placar e eventos oficiais em fonte da partida. Separar divergência do
   modelo, edição do vídeo e discrepância da fonte. Publicar apenas tabela de
   anotações e métricas permitidas pela licença.

Formato mínimo de cada anotação: `video_start_s`, `video_end_s`, `match_clock`,
`event_type`, `team`, `player`, `is_replay`, `confidence`, `evidence`,
`review_status`. Este piloto responde se conseguimos reconhecer e conferir os
lances **selecionados**. A avaliação de estratégias e comportamento ao longo dos
90 minutos continua dependente de partidas completas.

### Download e primeira inspeção local

O comando `video-download` usa `yt-dlp[default]` com Node.js e FFmpeg. Restringe a
uma URL HTTPS de vídeo do YouTube, um item por vez e qualidade até 720p. Salva mídia
e proveniência mínima (URL, canal, duração, tamanho e hash) em `data/videos/`, que
está ignorado pelo Git. Não usa cookies ou login e permite retomar arquivo parcial.
O [guia do yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/EJS) explica a necessidade
de um runtime JavaScript e do componente EJS para extração atual do YouTube.

```sh
uv run sports-stats-analyzer video-download \
  --url 'https://www.youtube.com/watch?v=78rS30sszUM'
uv run sports-stats-analyzer video-frames \
  --path data/videos/78rS30sszUM.mp4 --every-s 5
```

O primeiro download foi concluído e `video-frames` gerou 71 JPEGs com horários
solicitados de 0 a 350 segundos e um manifesto JSON local. A duração medida por
FFprobe foi 353,521 s. Quadros de 0, 120, 200 e 300 s foram abertos e estão legíveis:
o placar exibido passa de 0–0 a 0–1, 1–1 e 1–2 nesses pontos amostrados. Os tempos
do vídeo não são tempos de jogo, e o vídeo contém cortes e replays. Esse exame
confirma acesso e decodificação, mas ainda não é detecção automática de eventos nem
anotação completa dos melhores momentos.

A [avaliação de SoccerNet e Metrica](video-dataset-feasibility.md) compara tarefas,
acesso, formatos, requisitos e o próximo teste de detecção local.
