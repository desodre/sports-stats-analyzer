# Contexto para continuidade pelo celular

Atualizado em 18/09/2026, fuso America/Manaus.

Este arquivo reúne o contexto relevante da conversa, o estado do repositório, as
conclusões sobre a fase 4 e a auditoria da Sportmonks. Ele deve permitir continuar o
trabalho em uma nova sessão sem depender do histórico do chat.

> Segurança: o valor de `SPORTMONKS_API_TOKEN` não está registrado aqui. O token já
> está no `.env` local e nunca deve ser exibido, enviado ao Git ou incluído em logs.

## Objetivo atual

Completar o que ficou pendente na fase 4 — jogadores, escalações e contexto — usando
dados da Sportmonks quando a cobertura do football-data.org for insuficiente.

A solicitação que motivou esta análise foi:

1. Continuar a implementação do último plano.
2. Analisar o que deixou de ser implementado na quarta fase.
3. Identificar quais dados faltaram e como adquiri-los.
4. Avaliar a Sportmonks API v3, localizar os endpoints necessários e verificar sua
   viabilidade para o projeto.

## Regras de trabalho do repositório

O `AGENTS.md` determina que, ao concluir uma implementação:

1. Executar as verificações apropriadas.
2. Atualizar a documentação e o estado da fase correspondente.
3. Revisar o diff e criar um commit Git descritivo apenas com mudanças pertinentes.
4. Informar o hash do commit e os resultados das verificações.

Não versionar credenciais, `.env`, ambientes virtuais, caches ou dados locais. Não
fazer push sem solicitação explícita.

## Estado atual do projeto

- Branch: `main`.
- Último commit antes deste handoff: `e556929` (`feat: implement phase 6 dashboard
  and operations`).
- O branch local estava um commit à frente de `origin/main` no início da análise.
- Existe uma mudança local preexistente em `.env.example` adicionando
  `SPORTMONKS_API_TOKEN=`. Ela não foi criada durante a auditoria e deve ser
  preservada.
- O `.env` local contém `SPORTMONKS_API_TOKEN`; seu valor não foi exposto.
- A integração Sportmonks ainda **não foi implementada** no código. Foram feitas
  somente análise documental e chamadas autenticadas de leitura.

Arquivos mais relevantes:

- `docs/phases/04-context.md`: estado formal da fase 4.
- `docs/experiments/context-coverage-bsa.md`: auditoria da fonte inicial.
- `docs/phases/07-enrichment.md`: itens adiados e regras para uma segunda fonte.
- `docs/data-source.md`: contrato atual com football-data.org.
- `docs/model-protocol.md`: protocolo temporal dos modelos.
- `docs/roadmap.md`: estado das fases.

## O que a fase 4 já implementou

A fase 4 criou a infraestrutura de contexto sobre a fonte inicial:

- Auditoria de pessoas, escalações e substituições.
- Coleta de detalhes de partidas, equipes e pessoas.
- Separação entre elenco observado e onze jogadores reportados.
- Preservação de snapshots e primeira observação do conjunto de onze jogadores.
- Relatórios `context-coverage`, `context-report`, `squad-report` e
  `player-report`.
- Corte temporal dos relatórios para evitar o uso de observações posteriores.
- Tratamento separado de campos ausentes, nulos, vazios, parciais e inválidos.

Comandos existentes:

```bash
uv run sports-stats-analyzer collect-context
uv run sports-stats-analyzer context-coverage --competition BSA --season 2025
uv run sports-stats-analyzer context-report 534938 --before 2026-09-18T01:00:00Z
uv run sports-stats-analyzer squad-report 1776 --before 2026-09-18T01:00:00Z
uv run sports-stats-analyzer player-report 171241 --before 2026-09-18T01:00:00Z
```

## O que ficou pendente na fase 4

Quatro entregas estatísticas ficaram sem implementação:

1. Calcular minutos e métricas por posição/per 90.
2. Regularizar efeitos individuais para amostras pequenas e força dos adversários.
3. Comparar cenários de escalação sem penalidades percentuais arbitrárias.
4. Medir a contribuição incremental das variáveis de jogadores por avaliação
   temporal.

Esses itens foram formalmente transferidos para a fase 7 porque a fonte inicial não
forneceu evidência suficiente para implementá-los corretamente.

## Por que esses itens ficaram pendentes

A auditoria do football-data.org sobre BSA 2025 encontrou:

- 380 partidas coletadas com expansão solicitada.
- 381 observações detalhadas/expandidas ao contar uma consulta adicional.
- Nenhuma escalação ou banco nas 381 observações.
- Nenhuma substituição, gol individual ou cartão nas 381 observações.
- Um elenco atual de 46 jogadores para o São Paulo.
- Um perfil individual acessível, mas sem minutos ou desempenho por partida.

Um elenco observado em 2026 não prova quem jogou uma partida de 2025. Sem minutos,
escalações históricas e eventos individuais não seria possível calcular métricas por
90, atribuir efeito a jogadores ou testar cenários sem inventar informação.

## Dados necessários para completar a fase 4

### Obrigatórios

- Escalação titular e banco por partida.
- Minutos jogados por jogador e partida.
- Posição e posição detalhada do jogador na partida.
- Substituições com minuto, jogador que saiu e jogador que entrou.
- IDs estáveis para partidas, equipes, temporadas e jogadores.
- Formação e confirmação da escalação, quando disponíveis.
- Data/hora em que cada observação foi coletada.

### Importantes para maior qualidade

- Lesões e suspensões com intervalo de validade.
- Elencos históricos por equipe e temporada.
- Transferências para reconstruir vínculos históricos.
- Eventos da partida e períodos/acréscimos para validar minutos.
- Escalações prováveis antes da confirmação oficial.

### Produzidos internamente, não comprados da API

- Mapeamento de IDs entre Sportmonks e football-data.org.
- Histórico das diferentes versões observadas antes do jogo.
- Features sem vazamento temporal.
- Efeitos regularizados de jogadores.
- Ajuste por força do adversário, mando e tamanho da amostra.
- Cenários quantitativos e avaliação incremental do modelo.

## Resultado da análise da Sportmonks

### Veredito

A Sportmonks é **tecnicamente viável**, mas a adoção está condicionada à habilitação
da Série A brasileira na assinatura e a uma auditoria de cobertura de BSA 2023–2025.

O token local é válido e dá acesso a numerosos recursos de futebol, incluindo
fixtures, jogadores, temporadas, elencos e transferências. Porém, `GET /v3/my/leagues`
mostrou apenas ligas como:

- Superliga da Dinamarca (`271`).
- Premiership da Escócia (`501`).
- Premiership Play-Offs (`513`).
- Superliga Play-offs (`1659`).

A Série A brasileira, identificada na Sportmonks como liga `648`, não está habilitada
na assinatura atual. Por isso ainda não foi possível medir diretamente a completude
do Brasileirão.

### Validação prática feita com o token

Para confirmar a estrutura dos dados, foi usada a Premiership escocesa, que está
habilitada. Na partida concluída `19700206`, Falkirk x Rangers, temporada 2025/26, uma
consulta de fixture retornou:

- 2 participantes.
- 40 registros de escalação/titulares e banco.
- 21 eventos.
- 2 formações.
- 2 registros de desfalque.
- 2 períodos.
- 10 metadados.
- Formação 4-2-3-1 para as duas equipes.
- `lineup_confirmed = true` no metadado `type_id = 572`.
- Lesões com jogador, equipe, início, fim e jogos perdidos.
- Posição geral, posição detalhada, número e campo da formação por jogador.
- Eventos com `participant_id`, `player_id`, `related_player_id`, minuto e tipo.

Um filtro sobre os detalhes de escalação retornou 64 registros não nulos:

- `type_id = 119`: `MINUTES_PLAYED`.
- `type_id = 118`: `RATING`.
- O valor fica dentro de `details[].data.value`, não diretamente em
  `details[].value`.

Isso comprova que a API consegue fornecer os dados necessários para minutos e
métricas por jogador em pelo menos uma liga coberta.

### Teste de uma partida futura

Na partida futura `19722784`, St. Johnstone x Falkirk, prevista para 19/09/2026:

- A fixture normal respondeu HTTP 200.
- `lineups` ainda estava vazio cerca de um dia antes do jogo.
- `lineup_confirmed` estava `false`.
- Formações estavam presentes.
- O include `expectedLineups` retornou HTTP 403.

Conclusão: escalações confirmadas normais estão disponíveis quando publicadas, mas
escalações previstas são um produto premium não habilitado no token atual.

## Endpoints necessários

Base URL:

```text
https://api.sportmonks.com/v3
```

### Descoberta e assinatura

```text
GET /my/resources
GET /my/leagues
GET /football/leagues/648?include=country;seasons;currentSeason
```

### Temporadas, calendário e partidas

```text
GET /football/schedules/seasons/{season_id}
GET /football/fixtures/{fixture_id}
GET /football/fixtures/date/{date}
GET /football/fixtures/between/{start_date}/{end_date}
GET /football/fixtures/latest
```

Para obter o contexto essencial de uma partida:

```text
include=participants;state;periods;metadata;formations;lineups.player;lineups.type;lineups.position;lineups.detailedPosition;lineups.details.type;events.type;sidelined.sideline
```

Para restringir os detalhes da escalação a minutos e rating:

```text
filters=lineupdetailTypes:119,118
```

Observação: a documentação menciona em um ponto uma rota de fixtures por temporada,
mas a chamada correspondente retornou 404 durante o teste. A rota comprovadamente
funcional para obter IDs de jogos de uma temporada foi:

```text
GET /football/schedules/seasons/{season_id}
```

Depois disso, cada fixture pode ser buscada pelo ID com os includes necessários.

### Elencos e transferências

```text
GET /football/squads/teams/{team_id}
GET /football/squads/seasons/{season_id}/teams/{team_id}
GET /football/transfers/teams/{team_id}
GET /football/transfers/players/{player_id}
```

Includes úteis para elencos:

```text
include=player;position;detailedPosition;transfer
```

### Escalações previstas, opcional

```text
GET /football/fixtures/{fixture_id}?include=expectedLineups
GET /football/expected-lineups/teams/{team_id}
GET /football/expected-lineups/players/{player_id}
```

O include usa IDs compartilhados com jogadores/equipes/fixtures. Os tipos informados
pela Sportmonks são:

- `77614`: titular previsto.
- `77615`: candidato.

## Como adquirir o acesso que falta

1. Entrar no painel MySportmonks.
2. Adicionar a Série A brasileira, liga `648`, à seleção do plano.
3. Consultar novamente `/v3/my/leagues` para confirmar a habilitação.
4. Consultar a liga `648` com temporadas e verificar 2023, 2024 e 2025.
5. Se 2023 não estiver disponível, habilitar o add-on de dados históricos.

Na consulta feita em 18/09/2026, a página oficial de preços informava:

- Starter a partir de €29/mês ou €24/mês no pagamento anual.
- Escolha de até 5 ligas.
- 2.000 chamadas por entidade por hora.
- Teste de 14 dias.
- Histórico com mais de três temporadas como add-on de pagamento único, a partir de
  €29.

O add-on Expected Lineups estava anunciado somente para Growth e Pro:

- €159/mês no pagamento anual.
- €199/mês no pagamento mensal.

Ele não é necessário para a primeira implementação. Escalações confirmadas, elencos,
desfalques e histórico de utilização são suficientes para completar o núcleo da fase
4. Podemos reconsiderar as previsões premium somente se uma avaliação temporal
demonstrar benefício.

## Auditoria obrigatória depois de habilitar a liga 648

Antes de construir o adaptador completo, executar uma auditoria estratificada sobre
2023, 2024 e 2025. Idealmente consultar todos os jogos; para um primeiro gate, usar ao
menos 30 partidas por temporada, distribuídas entre rodadas e clubes.

Medir por temporada:

- Total de fixtures.
- Percentual com titulares e banco.
- Percentual com `MINUTES_PLAYED` não nulo.
- Percentual com posições detalhadas.
- Percentual com eventos/substituições.
- Percentual com `lineup_confirmed` observável.
- Percentual com desfalques.
- Consistência dos IDs de jogadores e equipes.
- Divergências de data, mandante, visitante e placar contra football-data.org.

Gate recomendado:

- Pelo menos 95% das partidas com escalação.
- Pelo menos 90% dos jogadores escalados com minutos válidos.
- Substituições e posições suficientemente completas para validar os minutos.
- IDs estáveis ao longo das três temporadas.
- Nenhuma divergência material e sistemática em resultados.

Se a cobertura ficar abaixo desses valores, manter os dados apenas como contexto
informativo e não ativar efeitos individuais no modelo.

## Arquitetura recomendada para a integração

Não substituir imediatamente o football-data.org. Adicionar Sportmonks como segunda
fonte, com rastreabilidade explícita.

### Componentes

1. `SportmonksClient` com autenticação por `SPORTMONKS_API_TOKEN`.
2. Rate limiter independente por provedor/token/entidade.
3. Armazenamento dos payloads brutos antes da normalização.
4. Adaptador Sportmonks para fixtures, lineups, eventos, sidelined, squads e
   transfers.
5. Tabelas de identidade externa; nunca conciliar jogadores apenas pelo nome.
6. Tabelas normalizadas de escalação, participação, evento e indisponibilidade.
7. Snapshots com `fetched_at` local para reconstruir o que era conhecido antes do
   kickoff.
8. Relatório de cobertura Sportmonks equivalente ao relatório existente da fase 4.

### Cuidados obrigatórios

- Não misturar IDs numéricos de provedores diferentes.
- Não assumir que elenco significa disponibilidade ou escalação.
- Não inferir minutos somente a partir da presença na escalação se a estatística ou
  eventos contradisserem isso.
- Não usar uma observação coletada após o kickoff em uma previsão pré-jogo.
- Não transformar ausências em zero.
- Preservar revisões e correções do provedor.
- Verificar os termos de licença antes de reter payloads indefinidamente ou usar os
  dados para treinamento/modelagem.
- Tratar HTTP 429 usando o `rate_limit` da resposta e retry com espera limitada.
- Cachear tipos, estados e outros dados de referência.

## Sequência de implementação sugerida

### Etapa 1 — desbloquear e auditar

- [ ] Habilitar liga `648` na conta Sportmonks.
- [ ] Confirmar acesso às temporadas 2023–2025.
- [ ] Rodar auditoria pequena de cobertura.
- [ ] Decidir se é necessário comprar o histórico de 2023.
- [ ] Registrar o resultado em `docs/experiments/`.

### Etapa 2 — infraestrutura do provedor

- [ ] Adicionar configuração Sportmonks sem expor credenciais.
- [ ] Implementar cliente HTTP, paginação, includes, retries e rate limit por entidade.
- [ ] Adicionar fixtures de teste gravadas e sanitizadas.
- [ ] Preservar snapshots brutos e metadados da consulta.

### Etapa 3 — normalização e identidade

- [ ] Criar migrações para IDs externos por provedor.
- [ ] Normalizar jogadores, escalações, banco, minutos, posições, eventos e
  indisponibilidades.
- [ ] Implementar reconciliação assistida entre equipes/partidas dos dois provedores.
- [ ] Exigir revisão para jogadores ambíguos; não casar apenas por nome.

### Etapa 4 — completar as estatísticas adiadas

- [ ] Calcular minutos e estatísticas por 90 somente com denominadores válidos.
- [ ] Estimar efeitos de jogadores com shrinkage/regularização.
- [ ] Ajustar por adversário, mando e contexto da partida.
- [ ] Produzir cenários rotulados, sem penalidades arbitrárias.
- [ ] Comparar o modelo básico e o modelo com jogadores no mesmo protocolo temporal.
- [ ] Ativar `model_context_enabled` apenas se houver melhoria fora da amostra.

### Etapa 5 — documentação e entrega

- [ ] Atualizar `docs/phases/04-context.md` e `docs/phases/07-enrichment.md`.
- [ ] Atualizar `docs/data-source.md`, arquitetura e operações.
- [ ] Registrar cobertura, limitações, custo e licença.
- [ ] Rodar testes, lint e formatação.
- [ ] Revisar o diff e criar commit descritivo.

## Referências oficiais consultadas

- [Sportmonks API v3](https://docs.sportmonks.com/v3)
- [Fixtures](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures)
- [Fixture por ID](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures/get-fixture-by-id)
- [Lineups e formações](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/lineups-and-formations)
- [Include de lineups](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/includes/lineups)
- [Eventos](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/includes/events)
- [Tipos de estatística de jogador](https://docs.sportmonks.com/v3/definitions/types/statistics/player-statistics)
- [Calendários por temporada](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/season-schedule/schedules)
- [Elencos](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/team-squads)
- [Transferências](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/transfers)
- [Expected Lineups](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/premium-expected-lineups)
- [Rate limits](https://docs.sportmonks.com/v3/api/rate-limit)
- [Planos e preços](https://www.sportmonks.com/football-api/plans-pricing/)
- [Produto Expected Lineups](https://www.sportmonks.com/football-api/expected-lineups-api/)

## Próxima ação recomendada

Habilitar a Série A `648` no painel da Sportmonks e então pedir:

> Continue a partir de `CONTEXTO_CONTINUIDADE.md`. Confirme que a liga 648 está
> disponível no token, audite a cobertura de BSA 2023–2025 e registre as evidências.
> Não implemente o modelo de jogadores até a auditoria passar pelos critérios de
> cobertura documentados.

Se a liga já tiver sido habilitada, a próxima sessão pode iniciar diretamente pela
auditoria autenticada. Se ainda não tiver sido habilitada, não há como validar o
Brasileirão além da documentação comercial e dos testes realizados em outra liga.
