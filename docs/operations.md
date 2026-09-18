# Painel e operação local

## Iniciar o painel

```bash
uv sync --locked
uv run sports-stats-analyzer dashboard
```

Abra `http://127.0.0.1:8501`. Para outra porta, use `--port 8502`.
O servidor escuta somente em localhost, não abre o navegador automaticamente e
desabilita a telemetria de uso do Streamlit. Encerre com Ctrl+C.
O mecanismo de bloqueio desta versão usa `fcntl`: suportado em Linux/macOS,
testado em Linux. Publicação para terceiros, autenticação e Windows não foram implementados.

O painel tem quatro áreas:

- Partidas: filtros, status/placar observado, forma recente dos times e contexto disponível.
- Previsões: histórico, probabilidades e origem; incerteza individual não estimada.
- Carteira virtual: saldo, exposição, ROI, decisões e liquidações de todas as partidas.
- Operação: atualização explícita, idade dos dados, falhas, qualidade, monitoramento e backup.

Atualizar e registrar previsão exigem clique explícito. Abrir/recarregar páginas
não coleta dados nem cria apostas. Forma dos times é calculada no momento atual e
rotulada assim, não como reconstrução histórica pré-jogo. A carteira é global;
os filtros de competição/temporada não recortam seu saldo.

Odds, avaliação de EV, entrada e liquidação da carteira continuam disponíveis pela
CLI da fase 5. Esta versão do painel não inclui formulário de odds ou botão de aposta.
Não há execução real em casas de apostas. O painel trata erros conhecidos sem
mostrar configurações, headers, tokens ou corpos de erro da API.

## Atualização e coordenação

```bash
uv run sports-stats-analyzer update-data --competition BSA --season 2026
uv run sports-stats-analyzer health --competition BSA --season 2026
```

`update-data` coleta as partidas e normaliza snapshots pendentes. Mantém a fonte
bruta se a normalização falhar. Registra início, fim, competição, temporada,
status e classe do erro em `operation_runs`, sem conteúdo remoto ou credenciais.
Falha retorna exit code 1. Registro `running` pode indicar interrupção do processo;
o lock do sistema é liberado ao sair, mesmo quando o processo é interrompido.

Um bloqueio por banco impede atualizações simultâneas. Cada requisição real também
usa um bloqueio por hash da credencial em `SPORTS_RATE_LIMIT_DIR`, padrão
`data/.rate-limits`. Para vários projetos/processos usando a mesma credencial,
configure o **mesmo diretório absoluto** nessa variável. O token não é salvo no lock.
Essa coordenação é local, não alcança outras máquinas ou programas que ignoram o lock.

O bloqueio cobre espaçamento e requisição HTTP. São respeitados `Retry-After`
(segundos/data HTTP) e `X-RequestCounter-Reset` quando não há requisições disponíveis
ou ocorre 429. Esperas acima de 60 segundos ficam registradas no lock e encerram a
tentativa para ser repetida mais tarde. Não apagar locks para tentar contornar cotas.

Atualização faz no máximo três tentativas para falha de rede, HTTP 429 e HTTP 5xx,
com backoff de 1 e 2 segundos, além da espera pela cota. HTTP 401/403/404 e resposta
JSON inválida não são repetidos. Comandos `collect`/`collect-context` continuam com
uma tentativa, mas compartilham a coordenação de cota. Transporte HTTP simulado
usa apenas o espaçamento em memória, sem arquivos de cota.

`health` avalia a idade de coletas com competição e temporada explícitas; não usa
uma coleta de outra temporada para mascarar dados antigos. Frescor (limiar de 24h)
e qualidade são conceitos diferentes: uma resposta recente pode estar vazia ou
incompleta. Quarentena global e última falha são reportadas separadamente.

## Agendamento

`update-data` é um job de execução única, apropriado para cron ou systemd timer.
Nenhum agendamento foi instalado na máquina nesta entrega. Execute no diretório do
projeto, com caminho absoluto para uv e acesso ao mesmo `.env` e diretório de cota.
Uma frequência horária é um ponto de partida operacional; ajustar à cobertura e cota.
O job não gera previsões, liquida apostas ou escolhe odds automaticamente.

## Monitoramento do modelo

O painel avalia previsões prospectivas com resultado conhecido: uma por partida,
última emitida antes do início, desde que horário e equipes correspondam. Exibe
log loss, Brier e faixas de calibração. Menos de 20 previsões recebe aviso de amostra
insuficiente; acima disso, o acompanhamento ainda é exploratório.

O diagnóstico de mudança de distribuição compara média de gols nos últimos 90 dias
com os 90 anteriores, exigindo 30 jogos em cada janela. Diferença absoluta acima de
0,5 gol gera `watch`. É uma regra descritiva, não teste estatístico formal de drift.
Não há retreinamento ou promoção automática baseada nesses indicadores.

## Backup, restauração e retenção

```bash
uv run sports-stats-analyzer backup
uv run sports-stats-analyzer restore CAMINHO_DO_BACKUP data/restores/novo-banco.db
```

Substitua o caminho do backup pelo retornado pelo primeiro comando. A cópia usa a
API de backup do SQLite, incluindo dados, previsões, cotações, carteira e registros
operacionais. Verifica integridade da origem e da cópia. Não copia `.env`, arquivos
de cota ou artefatos JSON de `data/experiments/`.

Restaurar exige destino novo: nunca sobrescreve banco ativo ou arquivo existente.
Inspecione o banco restaurado e, para passar a usá-lo, ajuste `SPORTS_DATABASE_PATH`
manualmente. Preserve o anterior. Mudanças de schema seguem migrações aditivas;
faça backup antes de alterações futuras. Não há downgrade automático.

Retenção inicial: preservar snapshots, previsões e carteira para auditoria; manter
backups diários por pelo menos 30 dias e uma cópia adicional antes de mudar schema.
Artefatos de experimentos devem ser copiados separadamente junto com o banco usado.
Não existe exclusão automática. A revisão de espaço/arquivamento é manual;
esta implementação não remove dados ou backups do usuário.

## Verificações e CI

```bash
sh scripts/check.sh
```

Instala com lockfile, executa lint, formatação e testes, interrompendo na primeira
falha. Testes usam dados sintéticos, não dependem de token ou rede e incluem AppTest,
concorrência, indisponibilidade da fonte e restauração.

O workflow `.github/workflows/ci.yml` executa esse script no GitHub Actions em pushes
e pull requests, com permissões somente de leitura e actions fixadas por commit. A
primeira execução remota ocorrerá somente após push; esta implementação não faz push.
Sem deploy, cloud, publicação ou revisão de licença para redistribuição.
