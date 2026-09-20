# Viabilidade — SoccerNet e Metrica para análise de vídeo

Avaliação em 20/09/2026, após baixar o vídeo de 5min54 de Corinthians × Fluminense
e extrair 71 quadros a cada 5 segundos. O MP4 local tem 1280 × 720, 30 quadros/s
e 10.605 quadros. Nenhum modelo de detecção de ações foi executado.

## Comparação para o projeto

| Fonte | O que entrega | Serve para nosso vídeo? | Decisão |
| --- | --- | --- | --- |
| [SoccerNet Action Spotting](https://www.soccer-net.org/tasks/action-spotting) | 500 jogos completos de transmissão, 17 classes com um instante por ação, rótulos e características extraídas | Sim, como referência e possível detector de gols, chutes, faltas, cartões e substituições; **não** inclui passes | Testar inferência de um modelo pré-treinado em ambiente isolado, com avaliação restrita aos lances exibidos |
| [SoccerNet Ball Action Spotting](https://www.soccer-net.org/tasks/ball-action-spotting) | 7 jogos de transmissão, 12 ações densas incluindo passe, condução, cruzamento e chute, tolerância de 1 s | Mais próximo de passes visíveis, mas um vídeo de melhores momentos não fornece todos os passes nem rastreamento contínuo | Considerar depois do piloto de ações esparsas e somente com amostragem temporal adequada |
| [Metrica sample-data](https://github.com/metrica-sports/sample-data) | 3 jogos anônimos com eventos e posições de atletas/bola sincronizados | Não se liga ao Corinthians × Fluminense: não há vídeo correspondente no repositório nem nomes reais | Usar como referência para esquema e cálculos de passes, movimento e tática, sem misturar identidades |

## Evidência observada

- O [repositório SoccerNet de spotting](https://github.com/SoccerNet/sn-spotting)
  fornece rótulos, exemplos e baselines. O [CALF](https://github.com/SoccerNet/sn-spotting/tree/main/Benchmarks/CALF)
  documenta inferência em vídeo externo e pesos pré-treinados, mas seu procedimento
  cita Python 3.8, PyTorch 1.6, TensorFlow 2.3 e OpenCV 3.4. Isso pede ambiente
  separado e verificação de compatibilidade antes de instalar no projeto.
- A [FAQ SoccerNet](https://www.soccer-net.org/faq) limita o conjunto de dados a
  pesquisa não comercial. Os vídeos brutos do Action Spotting estão em
  [repositório com acesso controlado e NDA](https://huggingface.co/datasets/SoccerNet/SoccerNet_raw_HQ);
  rótulos e características estão listados como públicos no
  [pacote oficial](https://github.com/SoccerNet/SoccerNet). Os vídeos do
  [Ball Action Spotting 2024](https://huggingface.co/datasets/SoccerNet/SN-BAS-2024)
  aparecem como públicos, mas o conjunto completo tem 19,3 GB.
- O [baseline de Ball Action Spotting 2024](https://github.com/recokick/ball-action-spotting)
  foi preparado para NVIDIA RTX 3080/CUDA. Este PC mostra GPU AMD Radeon RX 6600,
  15 GiB de RAM e cerca de 8,6 GiB livres no disco; portanto, copiar o ambiente
  inteiro ou baixar os 19,3 GB não é um primeiro teste apropriado.
- O [README da Metrica](https://github.com/metrica-sports/sample-data) descreve
  dois jogos em CSV e um terceiro em formato EPTS/JSON; dados são anônimos,
  coordenadas vão de 0 a 1 em campo de 105 × 68 m e eventos/tracking são
  sincronizados. A inspeção do CSV público de eventos do jogo 1 encontrou 1.745
  linhas, incluindo 799 `PASS`, 24 `SHOT` e 4 `CARD`. O tracking do mesmo jogo
  tem quadros em 0,04 e 0,08 s, compatíveis com 25 quadros/s, com posições de
  atletas e bola. Os dois CSV de tracking somam cerca de 65,6 MB.
- O README da Metrica convida a experimentar e pede atribuição em uso público,
  porém o repositório não apresenta arquivo `LICENSE` nem licença declarada nos
  [metadados do GitHub](https://api.github.com/repos/metrica-sports/sample-data).
  O escopo de redistribuição e uso em produto precisa ser esclarecido com a fonte.

## Consequências para o piloto Corinthians × Fluminense

Os 71 quadros extraídos a cada 5 s são suficientes para conferir decodificação,
placar e alguns lances, mas insuficientes para localizar ações com tolerância de
1–5 s ou identificar passes individuais. O próximo teste de spotting deve ler o
MP4 contínuo e manter a correspondência entre segundo do arquivo, relógio da
partida, cortes e replays. Uma amostra a 2 quadros/s teria cerca de 708 quadros;
Ball Action Spotting requer uma sequência temporal muito mais densa.

1. Isolar o baseline do SoccerNet e verificar se seus pesos e extração de
   características executam no hardware disponível, sem alterar o modelo Poisson.
2. Rodar apenas o vídeo de 5min54 e revisar manualmente predições de gol,
   finalização, cartão e substituição. Medir precisão, tempo e duplicatas de replay;
   não estimar recall da partida inteira a partir dos melhores momentos.
3. Em paralelo, validar importação de eventos/tracking Metrica e cálculos de
   passes e movimento em `Sample_Game_1`, preservando anonimização e licença.
4. Avaliar passes no vídeo e tendências individuais somente após fonte de partida
   completa, direitos adequados, amostragem densa e identificação confiável.

Nenhuma das duas fontes fornece diretamente desempenho por segundo dos atletas do
Fluminense nesta partida. Os dados da Metrica servem como exemplo de **saída** que
um sistema de rastreamento poderia gerar; SoccerNet serve como referência de
**detecção de eventos** em vídeo.
