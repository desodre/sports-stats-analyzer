# Arquitetura e decisões

## Stack

- Python 3.12+, uv e `uv.lock`: ambiente reprodutível.
- HTTPX: acesso síncrono à API com timeout e transporte simulado em testes.
- Pydantic Settings: ambiente e `.env`, com representação protegida do token.
- Typer: interface de coleta por terminal.
- SQLite da biblioteca padrão: armazenamento local de snapshots.
- pytest e Ruff: verificações de comportamento e padronização.

Implementado na fase 2: contratos Pydantic, tabelas normalizadas com revisões,
migração SQLite e indicadores descritivos. Fase 3 implementada com NumPy/SciPy,
modelos e avaliação temporal locais. Planejado: Streamlit para
o painel da fase 6. FastAPI e PostgreSQL só se o uso multiusuário justificar.
Não instalar antecipadamente uma stack de serviços distribuídos.

Fase 5: `markets.py` usa Decimal para odds e valores da carteira, CSV da biblioteca
padrão e persistência SQLite aditiva (migração 2). Previsões prospectivas guardam
parâmetros e revisões de treino; odds guardam observação e recebimento local.
Limites, reservas e liquidação da carteira virtual usam transações de escrita.
Nenhuma dependência adicional nem segunda API foi necessária.

## Fluxo atual

CLI valida argumentos → Settings carrega configuração → adaptador consulta API →
storage acrescenta snapshot SQLite → CLI informa ID. Falhas de coleta não são
persistidas como dados válidos. Toda resposta válida é preservada para reprocessamento.

O adaptador é específico da fonte; modelos estatísticos futuros consumirão o
modelo normalizado da fase 2, nunca o formato HTTP diretamente. Uma interface
comum entre provedores será extraída quando existir uma segunda fonte concreta.

## Contrato temporal

`fetched_at` marca quando o projeto recebeu a resposta, não quando a informação
ficou conhecida publicamente. Guardar futuramente também `provider_updated_at`,
`kickoff_at`, `prediction_at`, versão dos dados e versão do modelo.

Resultados históricos coletados hoje permitem experimentos retrospectivos com
limitações explícitas. Não comprovam que escalações, classificações ou correções
estavam disponíveis no horário de uma previsão antiga. Reconstruir classificações
e indicadores apenas com resultados anteriores ao corte; nunca usar a classificação
final de uma temporada como variável de uma partida dessa mesma temporada.

## Operação inicial

Uso local e sequencial. Limitação de requisições por instância, sem coordenação
entre processos. Não repetir automaticamente chamadas com falha. Na fase 6,
adicionar fila única, retries limitados com backoff e respeito aos cabeçalhos da API,
retenção, backup e monitoramento. SQLite é suficiente até evidência de necessidade
de concorrência de escrita ou serviço compartilhado.

Credenciais ficam no ambiente. Não registrar headers nem corpos de erro remotos.
Dados e `.env` são ignorados pelo Git. Licença de acesso não deve ser presumida
como autorização para redistribuir respostas brutas a usuários de um produto.
