# Fase 2 — Dados normalizados e indicadores

Estado: implementada e validada com BSA 2025 em 17/09/2026.

## Implementações

- [x] Modelos tipados para competição, temporada, equipe e partida.
- [x] Migração versionada, tabelas normalizadas e vínculo ao snapshot.
- [x] Identidade `(provider, external_id)` e reprocessamento idempotente.
- [x] Revisões consultáveis por instante de observação.
- [x] Validação de IDs, horários UTC, status e placares regulamentares.
- [x] Separação de finalizadas, adiadas, canceladas, atribuídas e incompletas.
- [x] Relatório por competição, temporada e campo.
- [x] Forma recente, gols, mando e intervalo entre partidas com corte temporal.
- [x] Amostra insuficiente explícita para equipes sem histórico, incluindo promovidos.

Arquivos implementados no pacote: `domain.py`, `repository.py` (inclui migração 1),
`normalization.py`, `analytics.py` e extensões da CLI. Módulos simples substituem
as pastas previstas enquanto o volume de código é pequeno.
Comandos disponíveis: `normalize`, `quality`, `team-report`.

## Critérios de aceite

Reprocessar o mesmo snapshot não duplica entidades; nova versão preserva a anterior.
Placar desconhecido permanece nulo. Partidas de copa não misturam gols de prorrogação
com mercados de 90 minutos. Indicadores de uma partida nunca usam essa própria partida
nem resultados posteriores. Relatório expõe amostra, janela e campos ausentes.

## Verificação

Fixtures de jogo futuro, adiado, finalizado, corrigido e com prorrogação. Testar
reprocessamento, transações e corte temporal com partidas em ambos os lados do corte.
Inspecionar distribuição e completude dos dados reais antes da fase 3.

## Evidências e limitações

27 testes aprovados: 14 de coleta e 13 da fase 2. Lint e formatação aprovados.
Dados reais: 380 partidas finalizadas, 20 equipes, 380 resultados elegíveis, zero
rejeições e zero lacunas nos IDs, gols, duração e atualização do provedor.
Jogos de 29/03/2025 a 07/12/2025, observados em 17/09/2026.

Registros inválidos ficam em quarentena com índice e motivo, preservando o payload
no snapshot. Estrutura de coleção inválida causa rollback da execução. Classificações
não são normalizadas em features para evitar incorporar rankings finais ao passado.

Modo padrão usa revisões observadas até o corte. `--retrospective` usa revisões
atuais para exploração histórica, sem comprovar disponibilidade na época. Ambos
excluem partidas com início a menos de três horas do corte; esse buffer não substitui
a hora real de encerramento. O protocolo da fase 3 deverá considerar essa limitação.

O intervalo desde último jogo é restrito aos jogos disponíveis no recorte; não mede
descanso físico. Equipes sem histórico retornam amostra vazia e médias nulas.
Dados completos nessa temporada ainda não demonstram viabilidade preditiva ou financeira.
