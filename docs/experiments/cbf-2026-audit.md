# Auditoria inicial das páginas de clubes CBF — 2026

Executada em 19/09/2026 sobre o banco local, sem novas requisições à CBF. Reproduzir:

```bash
uv run sports-stats-analyzer cbf-team-audit --season 2026
```

O comando lê índices, abas e HTML armazenados, confere hashes, cobertura por clube,
estrutura básica dos dados, soma de vitórias/empates/derrotas e referências de jogos.
Também aponta nomes parecidos na mesma competição e UF, preservando todos os IDs.
Usa a observação mais recente de cada aba para a checagem semântica e verifica a
integridade de todos os arquivos registrados, inclusive revisões anteriores.

## Resultado observado

- 283 participações de clubes em cinco competições, 849 abas e cinco índices.
- 854 arquivos HTML presentes e com SHA-256 correspondente ao banco.
- Todas as 849 abas previstas presentes; 847 com lista ou métricas não vazias.
- 8.434 linhas de atletas listados e 3.015 cartões de partidas extraídos, contados
  por página de clube. São ocorrências, não atletas ou jogos únicos. Todos os 3.015
  cartões têm IDs de equipes e placares no conteúdo estruturado.
- Nenhum conflito de nome/UF para o mesmo ID entre competições.
- Um candidato de identidade na Série C/SP: `20281` (“Ituano”) e `64742`
  (“ITUANO FC”). O ID `20281` tem listas vazias nas abas de atletas e histórico;
  a aba de estatísticas contém apenas parte dos resultados esperados. Páginas
  registradas: 162, 163 e 164. Não houve fusão nem descarte.

As listas vazias podem representar conteúdo vazio do site ou falha de extração;
o relatório não distingue as causas sem revisão do HTML e da fonte. Igualdade de
nome normalizado e UF é somente um indício de identidade, não confirmação.
O comando não valida se cada atleta, placar ou estatística corresponde ao mundo real,
nem identifica todos os apelidos possíveis. IDs diferentes de clubes com mesmo nome
em UFs diferentes não são tratados como duplicatas.

## Próxima revisão

Conferir manualmente o índice e as três páginas dos IDs `20281` e `64742`, registrar
se há alias, cadastro obsoleto ou dois registros válidos, e revisar amostras de
atletas/jogos/estatísticas das cinco competições. Só então concluir a auditoria de
identidades e iniciar a coleta histórica de 2023–2025 planejada para a fase 7.
