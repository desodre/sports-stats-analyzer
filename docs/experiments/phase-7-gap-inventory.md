# Inventário de lacunas e prioridade da fase 7

Revisão em 20/09/2026. A ordem abaixo prioriza testes que podem mudar uma decisão
do produto. “Cobertura não verificada” significa que a existência de um campo em
um catálogo público não comprova disponibilidade na assinatura nem na temporada
necessária. The Odds API foi integrada apenas para odds atuais; nenhuma nova fonte
de estatísticas alimenta o modelo.

| Prioridade | Lacuna e benefício testável | Cobertura observada / a medir | Custo e licença antes de integrar |
| --- | --- | --- | --- |
| 0 | Escalações e minutos pós-jogo: medir qualidade da extração e usar somente partidas anteriores ao corte de previsão | Football-data.org BSA 2025: escalações/eventos ausentes em 381 observações; CBF: dois PDFs piloto extraídos, histórico 2023–2025 em coleta | CBF já autorizada para coleta local; distribuição dos documentos ou dados derivados não foi liberada. Custo operacional da cota é alto |
| 1 | Odds históricas: testar retorno e incerteza da carteira com cotações realmente observadas | 69 odds atuais de uma partida coletadas em 20/09; histórico e resultados da carteira ainda ausentes | The Odds API anuncia histórico apenas em plano pago; cobertura efetiva ainda não testada. Termos publicados permitem armazenamento e análise, mas não revenda do feed bruto. Não inferir lucro de EV estimado |
| 1 | Escalações, substituições e eventos por partida: avaliar impacto incremental em log loss, Brier e calibração | CBF dá evidência pós-jogo; pré-jogo e disponibilidade temporal ausentes. Cobertura SportMonks/BSA 2023–2026 não testada nesta conta | Acesso depende de assinatura/temporada; contrato e permissão de uso precisam ser conferidos |
| 2 | xG e pressão: agregar partidas anteriores, ajustar por contexto e comparar com Poisson | Nenhuma série local; cobertura histórica e definição de métrica desconhecidas | Pode exigir complementos pagos; preço e licença efetivos devem ser confirmados antes de buscar dados |
| 3 | Notícias e lesões: medir cobertura, antecedência, contradições e eventual ganho incremental | Nenhuma série local de fatos com publicação verificável; elenco não indica disponibilidade | Notícias podem exigir produto adicional e licença de texto; sem fonte contratada |
| 3 | Vídeo de partidas: avaliar eventos e tendências táticas só após piloto de qualidade | Sem vídeos ou direitos definidos | Licença, armazenamento e revisão humana ainda desconhecidos |

## Fonte candidata para verificação de cobertura

A documentação da SportMonks descreve `lineups`, `events`, `sidelined`, `odds`,
`xGFixture` e `pressure` em partidas, mas recomenda conferir dinamicamente as
ligas e recursos habilitados na **conta específica**. A página pública de Série A
anuncia dados históricos com profundidade variável; isso não demonstra cobertura
de todos os campos em 2023–2026. Um teste limitado deve primeiro consultar recursos
da assinatura e uma amostra de jogos, sem incorporar dados ao modelo.
[Recursos por liga](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/data-features-per-league),
[includes de partidas](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures),
[página pública da Série A](https://www.sportmonks.com/football-api/serie-a-api-brazil/).

O preço público de entrada é anunciado a partir de **€29/mês**; xG/pressão,
notícias e arquivo histórico aparecem como complementos com cobrança própria.
Isso não é uma cotação para esta conta nem comprova acesso à Série A ou às
temporadas necessárias. A síntese pública de permissões permite construir e
mostrar dados em produto, mas condiciona revenda do feed bruto a aprovação escrita;
os termos contratuais específicos prevalecem.
[Planos e complementos](https://www.sportmonks.com/football-api/plans-pricing/),
[uso permitido](https://www.sportmonks.com/integrity-support/).

## Decisão atual

Concluir e auditar a coleta CBF já iniciada, medir cobertura real de súmulas e
revisar vínculos de atletas antes de experimentar efeitos individuais. Para odds,
confirmar primeiro que existe histórico com horários de observação e direito de
uso; a carteira prospectiva atual não supre essa lacuna. SportMonks foi avaliada
como candidata, sem ser escolhida como fonte do produto. O teste de cobertura
depende de acesso à liga, às temporadas e aos recursos necessários; nenhuma
credencial deve entrar no Git ou em logs.

O [teste autorizado com token local](sportmonks-account-coverage-2026.md) retornou
sete ligas na conta, sem a Série A brasileira (ID 648), e a consulta direta à liga
não trouxe dados. A cobertura de partidas não pôde ser medida. A fonte continua
inviável para integração com esta credencial, sem contratação.

A [avaliação do FBref](fbref-brazil-feasibility.md) encontrou minutos e chutes
básicos potencialmente úteis, mas acesso automatizado bloqueado neste ambiente,
remoção dos dados avançados em 2026 e restrições de uso relevantes para o modelo.
Não integrar nem tratar FBref como fonte de passes detalhados, xG ou eventos até
existirem acesso autorizado, direitos confirmados e amostra de cobertura atual.

A [verificação da The Odds API](the-odds-api-feasibility-2026.md) demonstrou acesso
a odds atuais 1X2 de BSA nesta conta, mas o plano gratuito não inclui histórico.
A lacuna de odds históricas com horário verificável para backtest financeiro
permanece aberta; a carteira atual segue prospectiva.

Uma nova variável só pode alterar probabilidades após comparação temporal com o
protocolo da fase 3 e análise de cobertura. As súmulas coletadas depois dos jogos
não comprovam informação pré-jogo em backtests históricos.
