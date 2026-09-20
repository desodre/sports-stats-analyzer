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
modelos e avaliação temporal locais. Fase 6: Streamlit para painel local, operações
SQLite e monitoramento. FastAPI e PostgreSQL só se o uso multiusuário justificar.
Não instalar antecipadamente uma stack de serviços distribuídos.

Fase 5: `markets.py` usa Decimal para odds e valores da carteira, CSV da biblioteca
padrão e persistência SQLite aditiva (migração 2). Previsões prospectivas guardam
parâmetros e revisões de treino; odds guardam observação e recebimento local.
Limites, reservas e liquidação da carteira virtual usam transações de escrita.
A fonte inicial de partidas permanece football-data.org. O adaptador opcional da
The Odds API usa HTTPX já presente: lista eventos e importa apenas odds 1X2 atuais
após confirmação manual do vínculo com uma partida local. As cotações normalizadas
guardam casa, horário de atualização e origem; a resposta bruta de odds não é
armazenada como snapshot de partidas. A chave fica no `.env` local.

Fase 7 mantém a CBF isolada do modelo: `cbf_team_pages` guarda HTML por hash e
observações de clubes; `cbf_matches.py` cataloga URLs com proveniência por página;
`cbf_sumulas.py` lê apenas PDFs locais com hash verificado. A extração posicional
usa `pdftotext` (Poppler) instalado opcionalmente e recusa layouts desconhecidos.
IDs CBF ainda não são reconciliados com os IDs da fonte inicial.
`cbf_identity.py` produz candidatos de vínculo entre clubes da Série A e BSA com
votos e partidas de suporte; nenhuma tabela normalizada ou previsão consome esses
candidatos automaticamente.

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

Uso local. Fase 6 adicionou lock por banco para atualização, lock por credencial
para requisições, retries limitados no job, headers de cota, backup e monitoramento.
Coordenação exige o mesmo diretório de locks e não cobre outras máquinas.
SQLite é suficiente até evidência de necessidade
de concorrência de escrita ou serviço compartilhado.

Credenciais ficam no ambiente. Não registrar headers nem corpos de erro remotos.
Dados e `.env` são ignorados pelo Git. Licença de acesso não deve ser presumida
como autorização para redistribuir respostas brutas a usuários de um produto.
