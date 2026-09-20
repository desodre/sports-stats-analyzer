# Fonte inicial: football-data.org

Documentação consultada em 17/09/2026. Revalidar limites e cobertura ao ativar a conta.

## Contrato utilizado

Base: `https://api.football-data.org/v4/`; autenticação pelo header `X-Auth-Token`.

| Recurso | Endpoint implementado | Uso |
| --- | --- | --- |
| Competições | `/competitions` | Descobrir códigos e competições |
| Partidas | `/competitions/{code}/matches` | Calendário, status e placares |
| Equipes | `/competitions/{code}/teams` | Equipes da temporada |
| Classificação | `/competitions/{code}/standings` | Inspeção contextual; evitar vazamento temporal |
| Detalhe de partida | `/matches/{id}` | Auditoria de escalações e eventos |
| Detalhe de equipe | `/teams/{id}` | Elenco observado, sem inferir escalação |
| Pessoa | `/persons/{id}` | Perfil e equipe reportados no momento da coleta |

Filtros implementados: `season` nos três subrecursos de competição. Não se presume
que todas as temporadas ou competições estejam incluídas no plano contratado.

## Limites e semântica

A documentação de políticas informa 10 requisições/minuto para clientes gratuitos;
o padrão local é 10, configurável. O header `X-RequestCounter-Reset` informa o tempo
para reiniciar a cota. Na versão inicial, HTTP 429 interrompe a coleta com orientação
para aguardar. Na fase 6, o job repete até três vezes falhas transitórias e processos
que compartilham `SPORTS_RATE_LIMIT_DIR` coordenam cota por credencial. Não cobre outras
máquinas ou aplicativos externos que não usam esse lock.

`null` e listas vazias são respostas válidas. Nunca transformar placar ausente em
zero. Elenco não é escalação confirmada. Listagens podem ocultar detalhes por padrão;
headers `X-Unfold-*` controlam expansão, mas não concedem acesso fora do plano.

## Matriz de capacidade

| Informação | Decisão inicial |
| --- | --- |
| Resultados e calendário | Coletar e medir completude |
| Equipes e classificação | Coletar; registrar data de observação |
| Escalações, substituições e estatísticas individuais | Verificar plano e partida antes da fase 4 |
| Odds | Não assumir acesso; entrada manual/CSV planejada na fase 5 |
| xG, pressão, eventos táticos detalhados | Fora do escopo inicial; avaliar lacunas na fase 7 |
| Notícias e lesões contextualizadas | Fora do escopo inicial; outra fonte somente no futuro |

## Referências oficiais

- [Quickstart e recursos](https://www.football-data.org/documentation/quickstart)
- [Referência v4](https://docs.football-data.org/general/v4/index.html)
- [Políticas, valores nulos e limites](https://docs.football-data.org/general/v4/policies.html)
- [Filtros, códigos e headers](https://docs.football-data.org/general/v4/lookup_tables.html)
- [Planos e recursos comerciais](https://www.football-data.org/pricing)

As capacidades acima distinguem implementação local de disponibilidade comercial.
Chamadas autenticadas confirmaram acesso a BSA 2023, 2024 e 2025 em 17/09/2026:
380 partidas por temporada (1.140 no total). Auditoria da fase 4 confirmou detalhes
de equipe/pessoa, mas não obteve escalações/eventos mesmo expandindo BSA 2025.
Veja [evidências da cobertura](experiments/context-coverage-bsa.md).

Na fase 5, BSA 2026 também foi coletado (380 partidas, snapshot 8) para gerar uma
previsão prospectiva. Cotações podem vir de entrada manual/CSV ou da The Odds API,
integrada separadamente para 1X2 atual. A
[verificação real](experiments/the-odds-api-feasibility-2026.md) importou 69 odds
de uma partida; isso não altera a fonte de jogos ou as probabilidades do modelo.
