# Fase 0 — Fundação

Estado: implementada.

## Objetivo e dependências

Criar um projeto Python reproduzível com uv. Depende de Python 3.12+ e uv instalado.

## Entregas e implementação

- [x] Projeto criado com `uv init --package`, layout `src` e CLI instalável.
- [x] Dependências de execução e desenvolvimento separadas; lockfile versionável.
- [x] Configuração por `.env` e ambiente; token representado como segredo.
- [x] Exclusão de ambiente, cache, dados locais e credenciais do Git.
- [x] README, arquitetura e planos por fase.

Arquivos: `pyproject.toml`, `uv.lock`, `.python-version`, `.env.example`,
`.gitignore`, `src/sports_stats_analyzer/config.py`.

## Critérios de aceite

`uv sync --locked`, `uv run sports-stats-analyzer --help`, `uv run pytest`,
`uv run ruff check .` e `uv run ruff format --check .` devem concluir sem falhas.
Não exige chave de API para instalar, exibir ajuda ou executar testes.

Verificação local em 17/09/2026: instalação com lockfile e ajuda da CLI aprovadas;
14 testes passaram; lint e verificação de formatação aprovados.

## Limites

Sem deploy, servidor web ou CI nesta fase. Os testes automatizados locais serão a
base do pipeline da fase 6.
