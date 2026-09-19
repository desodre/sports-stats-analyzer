# Roteiro de implementação

## Escopo

Futebol pré-jogo, inicialmente uma competição com histórico suficiente e disponível
na conta football-data.org. BSA é o exemplo da CLI, não uma restrição do produto.
Python é a stack principal; uv gerencia ambiente, dependências e lockfile.
Nenhuma segunda API será integrada nesta etapa.

| Fase | Entrega | Estado |
| --- | --- | --- |
| [0 — Fundação](phases/00-foundation.md) | Pacote, configuração e ferramentas | Implementada |
| [1 — Coleta](phases/01-ingestion.md) | API v4, CLI e snapshots | Implementada; validada com BSA 2025 |
| [2 — Dados analíticos](phases/02-analytics.md) | Normalização, qualidade e indicadores temporais | Implementada e validada |
| [3 — Probabilidades](phases/03-models.md) | Baselines, Poisson e avaliação temporal | Implementada; experimento BSA 2023–2025 concluído |
| [4 — Escalações e contexto](phases/04-context.md) | Auditoria, elencos e contexto observado | Implementada no escopo disponível; efeitos individuais adiados |
| [5 — Avaliação de mercados](phases/05-markets.md) | Cotações, valor esperado e carteira virtual prospectiva | Implementada; rentabilidade ainda não validada |
| [6 — Produto e operação](phases/06-product.md) | Painel local, atualização, monitoramento e backup | Implementada; primeira CI remota depende de push |
| [7 — Enriquecimento](phases/07-enrichment.md) | Auditoria CBF e estudo de novas fontes | Em andamento; revisão dirigida de 2026 concluída, identidade ambígua preservada |

## Ordem e decisões

Executar 0 → 1 → 2 → 3. A fase 4 depende de dados com cobertura comprovada;
se indisponíveis, as fases 5 e 6 podem usar apenas o modelo básico, com a limitação
explícita. A fase 5 depende da validação da fase 3; a fase 7 exige nova decisão
sobre necessidade, custo, licença e provedor.

Não estimamos prazos antes de confirmar competição, histórico acessível e cobertura.
Coleta ampliada para BSA 2023–2025: 1.140 resultados. Fase 3 concluída com evidência
favorável para 1X2 em teste retrospectivo, sem comprovação financeira. Próximo marco
do roteiro: decisões da fase 7 sobre enriquecimento, caso necessário. Painel local,
atualização, backup e workflow de CI para GitHub foram entregues. A fase 7 começou
com coleta CBF e auditoria automatizada de 2026; a revisão dirigida dos HTML confirmou
o conteúdo vazio de um dos IDs do Ituano e preservou a ambiguidade. A coleta histórica
teve os 15 índices coletados e a rotina sequencial de abas foi iniciada. O catálogo
local encontrou 1.508 URLs distintas de jogos de 2026. A análise de partidas
completas em vídeo foi registrada como hipótese
futura, condicionada a direitos de uso, qualidade da extração e validação temporal.
Dois PDFs locais passaram por extração piloto de escalações e substituições; 20
vínculos candidatos de clubes entre CBF/Série A e football-data.org/BSA foram
apoiados por 267 jogos, com uma divergência de horário preservada. Nenhum desses
dados altera o modelo.
A fase 5 entregou previsões prospectivas,
odds manuais/CSV e carteira virtual, ainda sem apostas reais observadas.
A auditoria da fase 4 encontrou
perfis/elenco, mas não escalações e eventos para BSA 2025; efeitos individuais passam
para a fase 7. Validar previsões prospectivamente antes de qualquer conclusão de lucro.

## Regra de conclusão

Uma fase só passa a concluída quando seus critérios foram verificados e o registro
de implementação aponta arquivos, comandos, limitações e evidências. Um plano não
representa funcionalidade entregue. Os módulos são organizados por responsabilidade;
o vínculo com as fases é documentado, evitando duplicar código em pastas por fase.

Mudanças de probabilidade precisam de avaliação temporal. Valor esperado positivo
estimado não substitui a incerteza do modelo. Dados ausentes devem permanecer ausentes,
e o produto deve poder responder “dados insuficientes” ou “sem vantagem demonstrada”.
