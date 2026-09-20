# Viabilidade da The Odds API para BSA/1X2

Verificação em 20/09/2026, entre 02:58 e 03:00 UTC. Chave lida do `.env` local,
sem registrá-la neste relatório, no Git ou no SQLite. Escopo: eventos futuros da
Série A brasileira, odds pré-jogo 1X2 e carteira virtual prospectiva.

## Acesso e cobertura observada

- `odds-events 555014` autenticou e retornou Grêmio × Palmeiras para
  `2026-09-20T14:00:00Z`, igual ao horário da partida local. Os nomes locais são
  `Grêmio FBPA` e `SE Palmeiras`; o vínculo foi conferido manualmente.
- A lista da API continha 15 eventos BSA. Os cinco jogos locais futuros de
  20/09/2026 apareceram com os mesmos horários e pares de clubes: Grêmio ×
  Palmeiras, Corinthians × Fluminense, Vitória × Cruzeiro, Flamengo × Bragantino
  e Atletico Paranaense × Bahia. Essa é uma amostra de uma rodada, não medida de
  cobertura de toda a temporada.
- `odds-fetch 555014 a0f1cb8a1ea9cd2193aa4c39ebf2d103 --region eu
  --confirm-match` importou 69 cotações 1X2 completas de 23 casas, três seleções
  por casa. Nenhuma casa foi descartada por atraso ou mercado incompleto nessa
  resposta. Os horários de atualização das odds importadas ficaram entre
  `02:57:46Z` e `02:58:56Z`; o importador preservou esses horários.
- A resposta de quota após o teste mostrou 499 créditos restantes, um usado e
  custo zero na última consulta de eventos. O provedor documenta que `/events`
  não consome crédito e que uma consulta de odds por evento com um mercado e uma
  região custa um crédito. [Documentação da API](https://the-odds-api.com/liveapi/guides/v4/).

## Fluxo prospectivo e integridade

O snapshot 10 da atualização `d77499cd3676403e90451e463bd71880` normalizou 380
partidas, sem rejeições. `forecast 555014` registrou a previsão prospectiva
`a6f25cbdd716480da2e12d2c3ae85a64` antes do início do jogo. `odds-assess`
avaliou uma cotação importada e devolveu `abstain` por
vantagem insuficiente no cenário de sensibilidade. `paper-wallet` permaneceu com
100 unidades, zero apostas e ROI nulo. Nenhuma aposta foi executada ou simulada
na carteira durante o teste.

O `.env` é ignorado pelo Git. Uma consulta local às 69 cotações confirmou zero
ocorrências da chave nos payloads armazenados. O evento e a casa aparecem no campo
`source`, sem credencial. A chave usada neste teste havia sido compartilhada na
conversa e deve ser substituída no painel do provedor para uso contínuo.

## Decisão e limites

**Viável para coletar odds prospectivas 1X2 da BSA nesta conta e nesta amostra.**
Continuar com confirmação manual de identidade, pois os nomes dos clubes diferem
entre fontes e partidas podem ter o mesmo horário. As odds precisam ter atualização
de até 15 minutos para entrar no fluxo atual; a cobertura e a disponibilidade de
casas devem ser acompanhadas em mais rodadas.

O plano gratuito anunciado oferece 500 créditos mensais, sem acesso a odds
históricas; [planos e limites](https://the-odds-api.com/). Odds históricas exigem
plano pago e ainda não foram consultadas. Não há base para backtest financeiro ou
conclusão de rentabilidade com esta amostra. Os
[termos publicados](https://the-odds-api.com/terms-and-conditions.html) permitem
armazenamento e uso analítico, mas proíbem redistribuir o feed bruto como produto.

## Verificações

Comandos reais: `odds-events`, `odds-fetch`, `update-data`, `forecast`,
`odds-assess` e `paper-wallet`. `sh scripts/check.sh` passou com lint, formato e
145 testes. Os dados locais e a chave permanecem fora do Git.
