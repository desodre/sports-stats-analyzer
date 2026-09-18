# Auditoria de contexto — BSA

Realizada em 17/09/2026, America/Manaus; registros UTC de 18/09/2026.
Fonte exclusiva: football-data.org v4. Não foi consultada uma segunda API.

## Evidências

| Snapshot | Consulta | Resultado |
| --- | --- | --- |
| 4 | `/matches/534938`, headers de expansão | Detalhe acessível; escalações e eventos ausentes |
| 5 | `/teams/1776` | Elenco com 46 jogadores informado pelo provedor |
| 6 | `/competitions/BSA/matches?season=2025`, headers de expansão | 380 partidas; escalações e eventos ausentes |
| 7 | `/persons/171241` | Perfil de Carlos Coronel acessível, com posição e equipe informada |

Headers solicitados: `X-Unfold-Lineups`, `X-Unfold-Subs`, `X-Unfold-Goals`,
`X-Unfold-Bookings`, todos `true`. A auditoria separa respostas com expansão/detalhe
das listas originais que poderiam ocultar campos por padrão.

Nas 381 observações detalhadas/expandidas, referentes a 380 partidas distintas:

- `homeTeam.lineup`, `awayTeam.lineup`, bancos: ausentes em 381/381.
- `substitutions`, `goals`, `bookings`: ausentes em 381/381.
- Perfil consultado contém identificação, posição e equipe informada; não contém
  histórico de minutos e desempenho individual.

As repetições da mesma partida são contadas como observações, não jogos adicionais.
O elenco foi observado em 2026 e não pode representar a escalação das partidas de 2025.
A ausência de campos nessa amostra não demonstra que a API inteira não os oferece,
nem permite atribuir a causa a um plano comercial específico.

## Decisão

Disponibilizar coleta, perfil e elenco com fonte e data; exibir campos ausentes e
contexto histórico observado. Manter `model_context_enabled=false`, minutos e métricas
por 90 minutos nulos. Perfil, posição e presença no elenco não medem desempenho.

Não calcular efeitos individuais, cenários quantitativos ou ajustes de probabilidades
sem dados e validação. Esses itens ficam na fase 7. A fase 5 pode prosseguir com o
modelo básico e entrada manual/CSV de odds, conforme o roteiro.

## Reproduzir os relatórios locais

```bash
uv run sports-stats-analyzer context-coverage --competition BSA --season 2025
uv run sports-stats-analyzer context-report 534938 --before 2026-09-18T01:00:00Z
uv run sports-stats-analyzer squad-report 1776 --before 2026-09-18T01:00:00Z
uv run sports-stats-analyzer player-report 171241 --before 2026-09-18T01:00:00Z
```

O corte acima é posterior às coletas desta auditoria. Novas coletas exigem um corte
adequado; usar um horário anterior retorna o estado observado naquela ocasião.
Os relatórios são JSON. Dados e credenciais permanecem fora do Git.

## Interpretação de escalações

`missing`, `null`, `empty` e `invalid` são estados diferentes. Nenhum comprova
desfalque, ausência de eventos ou suspensão. Lista parcial recebe `partial`.
Onze IDs únicos recebem `reported_starting_xi`, sem alegar confirmação independente;
duplicidade ou jogador simultaneamente no banco e entre titulares invalida o conjunto.
Formação declarada não equivale a comportamento tático medido.

`first_observed_xi_at` indica a primeira observação do conjunto de titulares informado,
não o momento oficial de divulgação. `observed_before_kickoff` informa se a resposta
selecionada foi coletada antes da partida. O relatório não incorpora esse contexto
às previsões da fase 3.

## Referências oficiais

- [Recurso Team](https://docs.football-data.org/general/v4/team.html)
- [Recurso Person](https://docs.football-data.org/general/v4/person.html)
- [Políticas de expansão e semântica de elencos](https://docs.football-data.org/general/v4/policies.html)
