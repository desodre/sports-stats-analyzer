# Roteiro de implementação

## Escopo

As fases 0–7 construíram e testaram uma base genérica para futebol pré-jogo,
rastreabilidade, modelagem, mercado e exploração de fontes. A partir da fase 8,
o produto concentra a análise longitudinal no **Esporte Clube Bahia**. O objetivo
é obter profundidade antes de escala: partidas do Bahia, jogadores, padrões
coletivos e decisões do técnico. Adversários entram apenas como contexto necessário.

Python continua como stack principal e uv gerencia ambiente, dependências e
lockfile. A The Odds API e o modelo Poisson permanecem disponíveis, mas validação
financeira, novas fontes amplas e expansão para todos os clubes deixam de disputar
prioridade com o corpus do Bahia.

| Fase | Entrega | Estado |
| --- | --- | --- |
| [0 — Fundação](phases/00-foundation.md) | Pacote, configuração e ferramentas | Implementada |
| [1 — Coleta](phases/01-ingestion.md) | API v4, CLI e snapshots | Implementada; validada com BSA 2025 |
| [2 — Dados analíticos](phases/02-analytics.md) | Normalização, qualidade e indicadores temporais | Implementada e validada |
| [3 — Probabilidades](phases/03-models.md) | Baselines, Poisson e avaliação temporal | Implementada; experimento BSA 2023–2025 concluído |
| [4 — Escalações e contexto](phases/04-context.md) | Auditoria, elencos e contexto observado | Implementada no escopo disponível; efeitos individuais adiados |
| [5 — Avaliação de mercados](phases/05-markets.md) | Cotações manuais/API, valor esperado e carteira virtual prospectiva | Implementada; API validada em uma rodada, rentabilidade não validada |
| [6 — Produto e operação](phases/06-product.md) | Painel local, atualização, monitoramento e backup | Implementada; CI remota validada |
| [7 — Enriquecimento](phases/07-enrichment.md) | Auditoria CBF e estudo de novas fontes | Exploração ampla encerrada; acervo preservado |
| [8 — Recorte Bahia](phases/08-bahia-scope.md) | Identidade, perguntas, protocolo e corpus-piloto | Planejada; Bahia selecionado |
| [9 — Corpus longitudinal](phases/09-bahia-corpus.md) | Partidas, escalações, súmulas, vídeos e proveniência | Planejada |
| [10 — Análise de partidas](phases/10-bahia-match-analysis.md) | Anotação estruturada e validação da extração | Planejada |
| [11 — Perfis de jogadores](phases/11-bahia-player-profiles.md) | Padrões individuais contextualizados | Planejada |
| [12 — Equipe e técnico](phases/12-bahia-team-strategy.md) | Padrões coletivos, formações e decisões técnicas | Planejada |
| [13 — Dossiê Bahia](phases/13-bahia-dossier.md) | Produto consultável com evidências e incerteza | Planejada |
| [14 — Expansão comparativa](phases/14-comparative-expansion.md) | Critérios e contrato para incluir outros clubes | Bloqueada pelas fases 8–13 |

## Ordem e decisões

As fases 0–7 permanecem como fundação e evidência exploratória. O novo caminho
crítico é 8 → 9 → 10 → 11/12 → 13 → 14. As fases 11 e 12 podem evoluir em paralelo
após o corpus e o protocolo de anotação estarem verificados. A fase 14 não começa
antes de o método funcionar de ponta a ponta para o Bahia.

Novas coletas amplas, contratação de provedores, odds históricas, xG, notícias e
análise de todos os clubes ficam suspensas, salvo quando resolverem uma lacuna
concreta do corpus do Bahia. Vídeo só entra com origem, direitos, hash, partida e
limites de uso registrados.

Não estimamos prazos antes de confirmar competição, histórico acessível e cobertura.
Coleta ampliada para BSA 2023–2025: 1.140 resultados. Fase 3 concluída com evidência
favorável para 1X2 em teste retrospectivo, sem comprovação financeira. Próximo marco
do roteiro: decisões da fase 7 sobre enriquecimento, caso necessário. Painel local,
atualização, backup e workflow de CI para GitHub foram entregues. A fase 7 começou
com coleta CBF e auditoria automatizada de 2026; a revisão dirigida dos HTML confirmou
o conteúdo vazio de um dos IDs do Ituano e preservou a ambiguidade. A coleta histórica
de 2023–2025 foi concluída localmente: 2023 preservou três abas indisponíveis e as
auditorias registraram alertas de conteúdo para revisão, sem bloquear o novo recorte.
O catálogo local encontrou 1.508 URLs distintas de jogos de 2026. A análise de partidas
completas em vídeo foi registrada como hipótese
futura, condicionada a direitos de uso, qualidade da extração e validação temporal.
Dois PDFs locais passaram por extração piloto de escalações e substituições; 20
vínculos candidatos de clubes entre CBF/Série A e football-data.org/BSA foram
apoiados por 267 jogos, com uma divergência de horário preservada. Nenhum desses
dados altera o modelo.
O inventário de lacunas da fase 7 foi priorizado; não há seleção de segunda fonte
sem verificar acesso, cobertura histórica e condições de uso.
Um teste limitado com token local confirmou que a Série A brasileira não está
entre as sete ligas acessíveis nesta conta SportMonks; nenhuma partida foi consultada.
A fase 5 entregou previsões prospectivas,
odds manuais/CSV, importação opcional da The Odds API e carteira virtual. A
[verificação com chave real](experiments/the-odds-api-feasibility-2026.md) encontrou
cinco jogos BSA na agenda e importou 69 cotações de um deles; nenhuma aposta
virtual foi registrada e não há evidência de rentabilidade.
A auditoria da fase 4 encontrou
perfis/elenco, mas não escalações e eventos para BSA 2025; efeitos individuais passam
para a nova trilha do Bahia quando houver cobertura suficiente. Validar previsões
prospectivamente antes de qualquer conclusão de lucro.

Decisão de 21/09/2026: interromper a expansão horizontal e concentrar novas
implementações no Bahia. O primeiro marco é a fase 8: definir identidade entre
fontes, perguntas observáveis, taxonomia e dez partidas para o corpus-piloto.

## Regra de conclusão

Uma fase só passa a concluída quando seus critérios foram verificados e o registro
de implementação aponta arquivos, comandos, limitações e evidências. Um plano não
representa funcionalidade entregue. Os módulos são organizados por responsabilidade;
o vínculo com as fases é documentado, evitando duplicar código em pastas por fase.

Mudanças de probabilidade precisam de avaliação temporal. Valor esperado positivo
estimado não substitui a incerteza do modelo. Dados ausentes devem permanecer ausentes,
e o produto deve poder responder “dados insuficientes” ou “sem vantagem demonstrada”.
