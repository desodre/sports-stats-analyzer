# Fase 6 — Painel e operação

Estado: implementada. A CI remota foi validada em `main`; publicação continua
condicionada a uma decisão de infraestrutura. Depende das fases anteriores.

## Implementações

- [x] Painel Streamlit: agenda, partida, times, previsões e carteira virtual.
- [x] Probabilidade, fontes, horário, limitações e incerteza não estimada explícita.
- [x] Qualidade, desatualização, ausência de dados e abstenção.
- [x] Job de atualização sequencial com até três tentativas e backoff.
- [x] Headers de cota e bloqueio local compartilhado por credencial/diretório.
- [x] Registros sem segredos, saúde, calibração e diagnóstico descritivo de distribuição.
- [x] Backup consistente, restauração sem sobrescrita e política de retenção.
- [x] Script único de verificações reproduzíveis (`scripts/check.sh`).
- [x] Configurar CI no GitHub para executar o script em pushes e pull requests.
- [ ] Reavaliar autenticação, licença e banco se houver decisão de publicar para terceiros.

Implementação: `dashboard.py`, `operations.py`, `monitoring.py`, `providers/rate_limit.py`
e CLI. Módulos simples substituem pastas enquanto o tamanho permite.
Configuração de CI apenas no provedor
de repositório escolhido. Sem pressupor cloud, domínio ou conta de hospedagem.

## Critérios de aceite

Usuário consegue explicar de onde veio uma previsão e quando ela foi produzida.
Falha da API não apaga dados existentes e aparece como desatualização. Restauração
de backup testada. Nenhum token aparece na interface ou logs. Painel distingue
resultado observado, estimativa e simulação. Atualização não excede cotas por concorrência.

## Verificação

Testes de fluxo com dados simulados e indisponibilidade da API; teste de restauração;
inspeção do painel para nulos, partidas adiadas, previsão ausente e dados antigos.

## Evidências e limites

104 testes aprovados. AppTest verificou banco ausente, partida adiada e sem placar,
previsão ausente, abstenção, falha de atualização e navegação. Navegação com dados
reais também passou nas quatro áreas. Servidor local respondeu HTTP 200 e health `ok`;
foi encerrado após a verificação. Não houve inspeção visual por screenshot.

Atualização real `d09e1dc2de6b4f38bc571732f041d083`: snapshot 9, BSA 2026, 380 registros
normalizados, zero rejeições. Backup `data/backups/20260918T012257Z-8a4ec34d.db`
restaurado em `data/restores/phase6-verified.db`; ambos com integridade `ok`.

Teste de processos comprovou espera pelo estado de cota compartilhada; testes de
retry verificaram limite de tentativas, reset de cota e ausência de repetição em 403.
Workflow de CI configurado em `.github/workflows/ci.yml`, com actions fixadas por SHA,
permissão somente de leitura e execução do mesmo script local. A execução remota do
commit `2534c11` concluiu com sucesso em 21/09/2026. Cron/timer não instalado.
Autenticação e publicação não implementadas: painel restrito a localhost por padrão.
Drift é diagnóstico por média, não teste formal; não há promoção automática do modelo.

Ver [operação local](../operations.md) para comandos e limites.
