# Fase 6 — Painel e operação

Estado: planejada. Depende da fase 3; mostrar módulos das fases 4 e 5 apenas quando prontos.

## Implementações

- [ ] Criar painel Python com Streamlit: agenda, partida, times e histórico de previsões.
- [ ] Exibir probabilidade, incerteza, fontes, horário e limitações em campos separados.
- [ ] Exibir qualidade e desatualização dos dados e estados de abstenção.
- [ ] Adicionar tarefas de atualização sequenciais com retries limitados e backoff.
- [ ] Respeitar cabeçalhos de cota e coordenar processos que usam a mesma credencial.
- [ ] Adicionar logs sem segredos, saúde das coletas e métricas de drift/calibração.
- [ ] Automatizar testes/lint em CI; definir backup, restauração, migrações e retenção.
- [ ] Reavaliar autenticação, licença e banco se houver decisão de publicar para terceiros.

Módulos previstos: `dashboard/`, `jobs/`; configuração de CI apenas no provedor
de repositório escolhido. Sem pressupor cloud, domínio ou conta de hospedagem.

## Critérios de aceite

Usuário consegue explicar de onde veio uma previsão e quando ela foi produzida.
Falha da API não apaga dados existentes e aparece como desatualização. Restauração
de backup testada. Nenhum token aparece na interface ou logs. Painel distingue
resultado observado, estimativa e simulação. Atualização não excede cotas por concorrência.

## Verificação

Testes de fluxo com dados simulados e indisponibilidade da API; teste de restauração;
inspeção do painel para nulos, partidas adiadas, previsão ausente e dados antigos.
