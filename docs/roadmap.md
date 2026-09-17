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
| [3 — Probabilidades](phases/03-models.md) | Baselines, Poisson e avaliação temporal | Planejada |
| [4 — Escalações e contexto](phases/04-context.md) | Disponibilidade de jogadores e cenários | Planejada; condicionada à cobertura |
| [5 — Avaliação de mercados](phases/05-markets.md) | Cotações informadas, valor esperado e simulação | Planejada |
| [6 — Produto e operação](phases/06-product.md) | Painel, atualização e observabilidade | Planejada |
| [7 — Enriquecimento](phases/07-enrichment.md) | Notícias e dados avançados de fontes futuras | Adiada |

## Ordem e decisões

Executar 0 → 1 → 2 → 3. A fase 4 depende de dados com cobertura comprovada;
se indisponíveis, as fases 5 e 6 podem usar apenas o modelo básico, com a limitação
explícita. A fase 5 depende da validação da fase 3; a fase 7 exige nova decisão
sobre necessidade, custo, licença e provedor.

Não estimamos prazos antes de confirmar competição, histórico acessível e cobertura.
Coleta e qualidade verificadas em BSA 2025: 380 resultados e 20 equipes. O próximo
marco é a fase 3: baseline e Poisson com avaliação temporal. Uma temporada permite
um experimento inicial; acesso a temporadas adicionais e janela de treino/teste
ainda precisam ser avaliados para medir estabilidade.

## Regra de conclusão

Uma fase só passa a concluída quando seus critérios foram verificados e o registro
de implementação aponta arquivos, comandos, limitações e evidências. Um plano não
representa funcionalidade entregue. Os módulos são organizados por responsabilidade;
o vínculo com as fases é documentado, evitando duplicar código em pastas por fase.

Mudanças de probabilidade precisam de avaliação temporal. Valor esperado positivo
estimado não substitui a incerteza do modelo. Dados ausentes devem permanecer ausentes,
e o produto deve poder responder “dados insuficientes” ou “sem vantagem demonstrada”.
