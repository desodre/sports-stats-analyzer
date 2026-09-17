# Sports Stats Analyzer

Projeto Python para análise estatística de futebol, com probabilidades auditáveis,
validação temporal e comunicação de incerteza. Fonte inicial exclusiva:
[football-data.org](https://www.football-data.org/).

## Estado atual

Fases 0–3 implementadas: ambiente uv, coleta, normalização, indicadores, modelos
estatísticos e avaliação temporal. Dados reais: 1.140 partidas de BSA 2023–2025.
Teste retrospectivo favorável ao Poisson para 1X2; não comprova rentabilidade.
Ainda não há serviço de previsões, painel ou execução de apostas.

## Iniciar

Requer Python 3.12+ e uv.

```bash
uv sync --locked
cp .env.example .env
```

Edite `.env` e preencha `FOOTBALL_DATA_API_TOKEN` com o token da sua conta.
Não compartilhe esse arquivo nem coloque o token no código.

```bash
uv run sports-stats-analyzer --help
uv run sports-stats-analyzer collect competitions
uv run sports-stats-analyzer collect matches --competition BSA --season 2025
uv run sports-stats-analyzer collect teams --competition BSA --season 2025
uv run sports-stats-analyzer collect standings --competition BSA --season 2025
```

`BSA` é um exemplo configurável; cobertura e temporadas acessíveis dependem da
conta. `season` representa o ano de início da temporada. Sem esse argumento,
a API usa a temporada corrente. Listar competições não garante acesso aos seus dados.

Cada coleta bem-sucedida acrescenta um snapshot em `data/sports.db`, com fonte,
endpoint, filtros, horário UTC de recebimento e resposta JSON. Não armazena o token.
Repetir a coleta preserva o histórico; `normalize` processa snapshots pendentes e
mantém revisões das entidades vinculadas a cada coleta.
Consultar os snapshots com qualquer cliente SQLite:

```sql
SELECT id, provider, endpoint, fetched_at FROM snapshots ORDER BY id DESC;
```

O cliente espaça requisições dentro da mesma instância. Evite coletas concorrentes:
a cota é compartilhada pelo token e ainda não existe coordenação entre processos.
Erros de rede, autenticação, cobertura e limite encerram o comando com código 1;
parâmetros inválidos usam código 2. Não há repetição automática nesta fase.

## Normalizar e analisar

```bash
uv run sports-stats-analyzer normalize
uv run sports-stats-analyzer quality --competition BSA --season 2025
uv run sports-stats-analyzer team-report 1776 --before 2025-12-01T00:00:00Z --competition BSA --season 2025 --window 5 --retrospective
```

`1776` é o ID do São Paulo no provedor. Relatórios são JSON no terminal.
`normalize` cria a migração automaticamente e registra inválidos em quarentena.
`quality` detalha as partidas por temporada; as rejeições listadas são globais,
inclusive fora dos filtros. Classificações permanecem apenas nos snapshots brutos.

Por padrão, `team-report` usa revisões observadas até `--before`. Dados de 2025
coletados em 2026 não aparecem com corte em 2025. `--retrospective` permite exploração
com revisões atuais; não comprova informação disponível na época nem backtest auditável.

Somente resultados finalizados com placar regulamentar e início mais de três horas
antes do corte entram nos indicadores. Esse buffer não comprova a hora de encerramento.
Casa/fora subdividem a mesma janela recente. Intervalo desde a última partida considera
apenas os jogos do recorte, não descanso físico nem outras competições.
Amostra pequena é sinalizada e médias sem jogos permanecem nulas.

## Testar o modelo

Após coletar e normalizar as três temporadas:

```bash
uv run sports-stats-analyzer collect matches --competition BSA --season 2023
uv run sports-stats-analyzer collect matches --competition BSA --season 2024
uv run sports-stats-analyzer collect matches --competition BSA --season 2025
uv run sports-stats-analyzer normalize
uv run sports-stats-analyzer evaluate --competition BSA --train-season 2023 --validation-season 2024 --test-season 2025 --retrospective
```

Se as temporadas já foram coletadas, execute apenas `evaluate`. Respeite a cota entre
comandos de coleta. A avaliação é local e não consulta a API. Os parâmetros de ano
delimitam anos civis UTC; veja o protocolo para temporadas que cruzam anos.

O comando seleciona parâmetros em 2024 e testa em 2025 com treino atualizado em
blocos semanais. Salva parâmetros, previsões, métricas e rastreabilidade em um JSON
exclusivo em `data/experiments/`. O terminal informa o caminho e a conclusão.
Sem `--retrospective`, dados devem ter sido observados antes dos cortes históricos;
as coletas atuais não atendem a esse requisito para 2023–2025.

Leia o [protocolo](docs/model-protocol.md) e o [resultado inicial](docs/experiments/bsa-2025.md).
O mercado de gols não melhorou no experimento. A conclusão favorável de 1X2 não
se estende a todos os mercados nem implica vantagem em relação às odds das casas.

## Verificar

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Organização

- `src/sports_stats_analyzer/`: implementação organizada por responsabilidade.
- `tests/`: contratos HTTP simulados, CLI e persistência.
- `docs/phases/`: plano e registro de implementação de cada fase.
- `docs/architecture.md`: decisões técnicas e regras de dados.
- `docs/data-source.md`: cobertura e limitações da fonte inicial.
- `data/`: armazenamento local ignorado pelo Git.

Comece pelo [roteiro por fases](docs/roadmap.md). Os planos separam entregas,
dependências, verificações e itens ainda não implementados. Nenhuma estimativa
de probabilidade constitui garantia de acerto ou lucro.
