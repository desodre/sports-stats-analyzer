# Fase 1 — Coleta e rastreabilidade

Estado: implementada e validada com coleta autenticada de BSA 2025.
Depende da fase 0 e, para coleta real, de uma conta football-data.org.

## Entregas e implementação

- [x] Cliente v4 com autenticação, timeout e espaçamento entre requisições.
- [x] CLI para competições, partidas, equipes e classificação.
- [x] Filtro de temporada explícito.
- [x] Tratamento de rede, autenticação, cobertura, limite e JSON inválido.
- [x] Snapshots SQLite com fonte, endpoint, filtros e horário UTC.
- [x] Preservação de respostas anteriores, valores nulos e payload original em JSON.
- [x] Testes locais com transporte HTTP simulado, sem consumir cota.

Arquivos: `providers/football_data.py`, `storage.py`, `cli.py` dentro do pacote;
testes em `tests/test_ingestion.py`.

## Aceite e validação real

1. Executar a suíte local de testes e verificações de estilo.
2. Configurar token localmente, sem compartilhá-lo em mensagens ou commits.
3. Coletar competições e escolher uma competição acessível.
4. Coletar partidas de uma temporada acessível; consultar o snapshot no SQLite.
5. Confirmar que nova coleta gera novo ID e preserva a anterior.
6. Registrar competição, temporada, campos presentes, contagem e data da validação.

Validação real em 17/09/2026: BSA 2025 com 380 partidas, snapshot 1. O acesso foi
validado diretamente; listagem de competições não foi necessária. Preservação de
revisões coberta por testes locais. Tabelas analíticas foram adicionadas na fase 2;
descoberta automática da cobertura e retries continuam fora desta fase.

Evidência local em 17/09/2026: 14 testes aprovados, incluindo contrato HTTP,
respostas inválidas, erros HTTP, preservação de snapshots, CLI e espaçamento de chamadas.

## Próxima passagem

Entregar snapshots reais à fase 2 e medir o histórico disponível. Não interpretar
uma resposta vazia como prova de inexistência de jogos sem revisar os filtros.
