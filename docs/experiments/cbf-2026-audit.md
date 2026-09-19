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

## Revisão dirigida dos HTML armazenados — 19/09/2026

O índice da Série C contém os dois IDs, ambos em SP: `20281` (“Ituano”) e `64742`
(“ITUANO FC”). Foram conferidos os HTML das páginas 162–164 e 192–194 e repetida a
extração local com `parse_detail`; os seis resultados coincidem com o JSON salvo.
A página 162 tem somente o cabeçalho da tabela, sem atletas; a 163 não contém links
de jogos; a 164 mostra `Jogos disputados: 0` e traços nas demais métricas. A 192
contém 30 atletas listados, a 193 contém 19 links de jogos e a 194 informa 19 jogos,
6 vitórias, 4 empates e 9 derrotas. Portanto, o vazio de `20281` consta no HTML
recebido, não resulta de perda na extração local. Os nomes e a UF sugerem cadastro
duplicado ou antigo, mas estas páginas não provam a relação jurídica entre IDs.
Ambos permanecem distintos, sem conciliação automática.

Também foram revisadas as três abas dos seguintes exemplos, um por competição:

| Competição | ID | Páginas | Atletas | Jogos | Métricas |
| --- | ---: | --- | ---: | ---: | ---: |
| Copa do Brasil | 20001 | 6–8 | 44 | 4 | 8 |
| Série A | 20001 | 18–20 | 40 | 27 | 9 |
| Série B | 20010 | 15–17 | 49 | 28 | 9 |
| Série C | 64742 | 192–194 | 30 | 19 | 9 |
| Série D | 20029 | 12–14 | 13 | 10 | 7 |

As 15 extrações reproduziram o JSON salvo. Em cada histórico, a quantidade de links
de jogos no HTML coincidiu com a de cartões extraídos. Essa amostra confirma a
extração dessas páginas, não a veracidade dos dados publicados pela CBF nem todos
os 854 HTML. A coleta histórica pode prosseguir com os IDs separados; uma futura
conciliação requer fonte independente ou evidência explícita da CBF.
