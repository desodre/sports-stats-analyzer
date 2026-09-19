# Candidatos de vínculo entre clubes CBF e football-data.org — Série A/2026

Relatório local executado em 19/09/2026, sem rede ou alteração de cadastros:

```bash
uv run sports-stats-analyzer cbf-team-links --season 2026 \
  --report-file data/cbf/team-links-2026.json
```

Foram usados os históricos CBF mais recentes dos 20 clubes da Série A e a última
revisão de cada partida BSA em `matches`. Ambos os conjuntos têm 267 jogos
finalizados observados até a coleta. O horário UTC de football-data.org foi
convertido para `America/Sao_Paulo`; o horário textual da CBF foi interpretado nesse
mesmo fuso para comparação. Essa convenção precisa ser reavaliada se outras
competições ou temporadas tiverem horários em fusos distintos.

Primeiro, data, horário e placar geraram votos para os IDs de mandante e visitante
quando havia uma única partida candidata. Cada vínculo exigiu pelo menos três votos,
vantagem de três votos sobre a segunda opção e unicidade do ID de destino. Depois,
os pares de equipes propostos, a data e o placar permitiram reconciliar **267/267**
jogos de forma unívoca. O relatório preserva os IDs de todos os jogos que sustentam
cada voto e os pares de partidas reconciliadas. Os **20 vínculos são candidatos**;
nenhum ID foi fundido nem passou a alimentar o modelo.

Há uma divergência de horário: CBF `832039` (Remo x Palmeiras) informa
10/05/2026 às 16:00, enquanto football-data.org `554887` informa 17:40 no fuso
acima; data, equipes e placar 1 x 1 coincidem. Por isso, a votação preliminar por
horário registrou um voto espúrio para Remo → `1766` (Atlético Mineiro) e Palmeiras
→ `1770` (Botafogo). Os vínculos apoiados pelos demais jogos são Remo `20022` →
`4287` (24 votos) e Palmeiras `20002` → `1769` (23 votos). Ambos têm um voto
conflitante preservado no JSON. A checagem final por equipes/data/placar identificou
o par de partidas correto sem ignorar a divergência temporal.

O relatório demonstra consistência entre esses resultados observados e oferece
proveniência para revisão. Não prova identidade de atletas, disponibilidade pré-jogo,
nem a completude dos calendários das fontes. Os dados CBF foram recebidos depois de
vários jogos; não podem ser usados retrospectivamente como se fossem conhecidos
antes de cada partida.
