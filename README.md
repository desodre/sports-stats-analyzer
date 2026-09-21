# Sports Stats Analyzer

Projeto Python para análise estatística de futebol, com probabilidades auditáveis,
validação temporal e comunicação de incerteza. Fonte inicial de partidas:
[football-data.org](https://www.football-data.org/). A coleta experimental de
súmulas da CBF é separada e ainda não alimenta o modelo.

O foco de desenvolvimento a partir da fase 8 é o **Esporte Clube Bahia**. A nova
trilha constrói um corpus longitudinal de partidas, perfis observáveis de jogadores
e padrões da equipe e do técnico antes de expandir a análise para outros clubes.
Adversários entram somente como contexto das partidas do Bahia nesta etapa.

## Estado atual

Fases 0–3 implementadas: ambiente uv, coleta, normalização, indicadores, modelos
estatísticos e avaliação temporal. Dados reais: 1.140 partidas de BSA 2023–2025.
Teste retrospectivo favorável ao Poisson para 1X2; não comprova rentabilidade.
Não há execução de apostas em casas.

Fase 5 disponível: previsões prospectivas pela CLI, odds manuais/CSV, avaliação de EV
e carteira virtual. A The Odds API pode fornecer odds 1X2 atuais após confirmação
manual do vínculo com uma partida. Rentabilidade não validada;
uma [amostra real](docs/experiments/the-odds-api-feasibility-2026.md) trouxe 69
cotações de 23 casas para uma partida, sem aposta virtual registrada.

Fase 4: coleta e relatórios de contexto disponíveis. A auditoria acessou elenco e
perfil de jogador, mas não encontrou escalações/eventos nas partidas expandidas de
BSA 2025. Impacto individual e minutos permanecem adiados, sem alterar o modelo.

Fase 7 encerrou a exploração ampla inicial e preservou seus dados como referência.
As [fases 8–14](docs/roadmap.md) implementam o recorte Bahia: protocolo, corpus,
anotação de partidas, perfis de jogadores, estratégia, dossiê e critérios para uma
futura expansão comparativa. A fase 8 está implementada, a fase 9 está em andamento
e as fases 10–14 permanecem planejadas.

A fase 8 já definiu os IDs do Bahia entre fontes, dez partidas da Série A 2026,
perguntas observáveis, taxonomia e contrato de evidência. Consulte o
[escopo do Bahia](docs/bahia/scope.md). Vídeos permanecem apenas como candidatos
até que origem e direitos sejam registrados.

A fase 9 começou com o catálogo de uma transmissão completa de Remo x Bahia e com
as [perguntas de produto do Bahia](docs/bahia/research-questions.md). A mídia não foi
baixada e sua disponibilidade pública não foi tratada como permissão de uso.

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
a cota é compartilhada pelo token. Na fase 6, processos que usam o mesmo diretório
`SPORTS_RATE_LIMIT_DIR` coordenam requisições via lock por credencial.
Erros de rede, autenticação, cobertura e limite encerram o comando com código 1;
parâmetros inválidos usam código 2. `collect` faz uma tentativa; `update-data` faz até três
para falhas transitórias, respeitando backoff e cota.

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

## Jogadores e escalações

```bash
uv run sports-stats-analyzer collect-context team 1776
uv run sports-stats-analyzer collect-context person 171241
uv run sports-stats-analyzer collect-context match 534938
uv run sports-stats-analyzer collect matches --competition BSA --season 2025 --unfold
uv run sports-stats-analyzer context-coverage --competition BSA --season 2025
uv run sports-stats-analyzer squad-report 1776 --before 2026-09-18T01:00:00Z
uv run sports-stats-analyzer player-report 171241 --before 2026-09-18T01:00:00Z
uv run sports-stats-analyzer context-report 534938 --before 2026-09-18T01:00:00Z
```

Use corte posterior à coleta desejada; os horários acima reproduzem a auditoria inicial.
Os relatórios são locais e não exigem nova coleta. Respeite a cota ao executar consultas.
`--unfold` solicita detalhes, sem conceder permissões além das disponíveis na conta.
Elenco não é escalação; informações faltantes não comprovam desfalques. Minutos,
métricas por 90 e ajustes de probabilidade permanecem nulos nesta entrega.

Consulte a [auditoria de contexto](docs/experiments/context-coverage-bsa.md) para os
dados encontrados, os limites e os itens adiados à fase 7.

## Súmulas da CBF

Para baixar uma súmula conhecida, sem token de API:

```bash
uv run sports-stats-analyzer cbf-collect --url https://conteudo.cbf.com.br/sumulas/2026/142269se.pdf
```

Também é possível passar uma página de jogo das competições nacionais masculinas
selecionadas com `--url` ou várias URLs
em `--urls-file` (uma por linha). A descoberta automática de todos os jogos ainda
não foi implementada. Páginas e PDFs compartilham um limite conservador de uma
requisição a cada 15,1 segundos, no máximo vinte em qualquer período de cinco minutos.
Arquivos válidos ficam em `data/cbf/`, ignorados pelo Git; metadados e hash ficam
em `cbf_sumulas` no SQLite. Reexecução pula PDFs já armazenados, salvo `--refresh`.
Veja [coleta e limitações](docs/cbf-collection.md) antes de processar lotes maiores.

O comando `cbf-teams` coleta os índices e as abas públicas dos clubes de Série A–D
e Copa do Brasil, por temporada. Preserva o HTML bruto e extrai atletas listados,
histórico de partidas e estatísticas agregadas, sem misturar esses dados com o modelo:

```bash
SPORTS_CBF_CA_BUNDLE=data/cbf/certs/sectigo-ov-bundle.crt \
  uv run sports-stats-analyzer cbf-teams --season 2026 --max-requests 20
uv run sports-stats-analyzer cbf-team-coverage --season 2026
uv run sports-stats-analyzer cbf-team-audit --season 2026
```

Repita o primeiro comando para continuar de onde parou. Veja no procedimento da
coleta como obter o pacote público de certificados exigido pelo domínio da CBF.
A [auditoria de 2026](docs/experiments/cbf-2026-audit.md) registra a cobertura,
a revisão dos HTML e a identidade que ainda exige conciliação. A proposta de analisar
[partidas completas em vídeo](docs/experiments/full-match-video.md) foi guardada
como pesquisa futura, sem alterar as previsões atuais. O
[piloto local de vídeo](docs/experiments/full-match-video.md) documenta o download
de um vídeo de melhores momentos e a extração de quadros para revisão; nenhuma
variável de vídeo entrou no modelo.

Após revisar os HTML de 2026, os índices de 2023–2025 foram coletados. A rotina
`sh scripts/collect_cbf_history.sh` coleta as abas desses anos sequencialmente e
audita cada temporada antes de avançar. A coleta leva várias horas e pode ser
retomada após interrupção. Para catalogar URLs de jogos já observados:

```bash
uv run sports-stats-analyzer cbf-match-urls --season 2026 \
  --urls-file data/cbf/match-urls-2026.txt
```

O [catálogo de 2026](docs/experiments/cbf-2026-match-catalog.md) mediu 1.508 URLs
distintas; não comprova calendário completo ou disponibilidade de todas as súmulas.
Com Poppler instalado, `cbf-sumula-extract ID` lê uma súmula local e retorna
escalações, substituições e minutos nominais. O
[piloto de dois PDFs](docs/experiments/cbf-sumula-pilot.md) descreve a validação e
as limitações; os dados extraídos ainda não alimentam previsões.
`cbf-team-links --season 2026` propõe vínculos de clubes da Série A com IDs BSA,
usando jogos observados; o [estudo local](docs/experiments/cbf-bsa-2026-links.md)
documenta 20 candidatos e uma divergência de horário, sem fusão de cadastros.
O [inventário da fase 7](docs/experiments/phase-7-gap-inventory.md) prioriza as
lacunas de dados e as verificações necessárias antes de escolher uma nova fonte.

## Cotações e carteira virtual

```bash
uv run sports-stats-analyzer forecast ID_DA_PARTIDA
uv run sports-stats-analyzer odds-import data/odds.csv
uv run sports-stats-analyzer odds-events ID_DA_PARTIDA
uv run sports-stats-analyzer odds-fetch ID_DA_PARTIDA ID_DO_EVENTO --confirm-match
uv run sports-stats-analyzer odds-assess ID_DA_COTACAO ID_DA_PREVISAO
uv run sports-stats-analyzer paper-bet ID_DA_COTACAO ID_DA_PREVISAO
uv run sports-stats-analyzer paper-settle
uv run sports-stats-analyzer paper-wallet
```

Substitua os IDs pelos valores do banco e retornados pelos comandos. Antes de
prever ou liquidar, atualize e normalize resultados/agenda. O comando `odds-add`
também aceita observação manual; consulte `--help` e o [template CSV](examples/odds-template.csv).
Para usar a The Odds API, configure `THE_ODDS_API_KEY` no `.env` local. Confira
times e horário em `odds-events` antes de confirmar `odds-fetch`; o comando importa
apenas odds recentes e não cria apostas. Veja as [regras](docs/paper-trading.md).

Somente odds observadas nos últimos 15 minutos; previsões novas e prospectivas.
Carteira começa com 100 unidades virtuais, aposta fixa de uma unidade, exposição
máxima de cinco e uma aposta por partida. Inicialmente apenas 1X2/BSA é elegível.
Sem apostas liquidadas, ROI é nulo. Não há acesso a casas ou movimentação de dinheiro.

Leia as [regras da carteira](docs/paper-trading.md) e a [validação da fase 5](docs/experiments/phase-5-validation.md).

## Painel e operação

```bash
uv run sports-stats-analyzer dashboard
```

Abra `http://127.0.0.1:8501`. Painel local com partidas, times, previsões, carteira e
qualidade. Atualizações e previsões exigem ação explícita; não há apostas automáticas.
Os locks operacionais requerem Linux/macOS (testado em Linux).

```bash
uv run sports-stats-analyzer update-data --competition BSA --season 2026
uv run sports-stats-analyzer health --competition BSA --season 2026
uv run sports-stats-analyzer backup
```

Restauração exige destino novo. Veja [operação, backups e agendamento](docs/operations.md).
O workflow de CI do GitHub executa a mesma rotina em pushes e pull requests. A primeira
execução remota depende do próximo push; publicação/deploy continuam fora do escopo.

## Verificar

Rotina completa, também utilizável por um runner de CI futuro:

```bash
sh scripts/check.sh
```

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
