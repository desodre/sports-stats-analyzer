# Catálogo local de URLs de jogos CBF — 2026

Executado em 19/09/2026 a partir dos HTML/JSON de clubes já armazenados, sem rede:

```bash
uv run sports-stats-analyzer cbf-match-urls --season 2026 \
  --urls-file data/cbf/match-urls-2026.txt
```

| Competição | Históricos / clubes indexados | Cartões | URLs distintas | Em dois históricos | Em um histórico |
| --- | ---: | ---: | ---: | ---: | ---: |
| Copa do Brasil | 126 / 126 | 300 | 150 | 150 | 0 |
| Série A | 20 / 20 | 534 | 267 | 267 | 0 |
| Série B | 20 / 20 | 565 | 283 | 282 | 1 |
| Série C | 21 / 21 | 396 | 198 | 198 | 0 |
| Série D | 96 / 96 | 1.220 | 610 | 610 | 0 |
| **Total** | **283 / 283** | **3.015** | **1.508** | **1.507** | **1** |

Nenhuma URL inválida ou contradição de equipes/placar foi encontrada entre cartões
do mesmo jogo. O único cartão sem par é o jogo `833170`, Ceará x Grêmio Novorizontino,
na Série B, observado na página 112. Os históricos dos dois clubes foram coletados
em 19/09/2026 por volta de 05:34–05:39 UTC. Não há evidência suficiente para dizer
por que a página do Ceará não contém esse cartão; a URL foi preservada e o caso
permanece sinalizado pela contagem de referências únicas.

O denominador é o conjunto de páginas de clubes do banco, não uma tabela oficial de
jogos esperados. Históricos podem mudar com o tempo; estes totais descrevem as
observações locais, não garantem calendário completo nem PDFs disponíveis.
