# Fase 7 — Notícias e enriquecimento futuro

Estado: exploração ampla encerrada após coleta, auditoria e estudos de viabilidade.
O acervo permanece disponível, mas novas implementações foram redirecionadas ao
recorte Bahia das fases 8–14. Conciliação de identidades, enriquecimento estatístico
e integração ao modelo só avançam quando necessários para esse recorte.
O lote integral de páginas dos clubes de 2026 terminou: os cinco índices e as
849 abas previstas estão armazenados. A auditoria automatizada verificou cobertura,
estrutura e integridade; a revisão dirigida confirmou o conteúdo dos casos
sinalizados, mas não resolveu a relação entre os IDs do Ituano.
Depende de lacunas demonstradas pelas fases anteriores e escolha futura de fontes.

Decisão de 21/09/2026: não continuar a expansão horizontal por clubes, competições
e provedores. Os itens abertos abaixo formam um inventário, não uma fila ativa.
Trabalho novo deve justificar como melhora o corpus, a análise de partidas, os
perfis de jogadores ou a leitura tática do Bahia.

Lacuna demonstrada na fase 4: BSA 2025 não retornou escalações, bancos ou eventos
mesmo com expansão solicitada. Minutos, efeitos individuais regularizados, cenários
de escalação e avaliação incremental ficam adiados nesta fase. Perfis/elencos
isolados não fornecem suporte para essas implementações.

## Plano de decisão

- [x] Iniciar adaptação separada da CBF para baixar súmulas com proveniência,
  integridade, retomada e cota conservadora; sem alterar o modelo.
- [x] Implementar coleta retomável de índices e abas de clubes das Séries A–D e
  Copa do Brasil masculina/2026, com HTML bruto e observação temporal separada.
- [x] Concluir a coleta das abas de 2026 nas cinco competições (283 participações).
- [x] Implementar e executar auditoria automatizada de cobertura, conteúdo,
  integridade e candidatos de identidade nas páginas de 2026.
- [x] Revisar os HTML dos IDs sinalizados e uma amostra das cinco competições,
  preservando a ambiguidade de identidade não resolvida.
- [ ] Após concluir 2026, coletar e auditar as temporadas de 2023–2025 no mesmo escopo.
- [ ] Descobrir/cadastrar URLs de jogos em escala e medir cobertura por temporada.
- [ ] Extrair e revisar escalações, substituições e minutos das súmulas.
- [x] Validar um extrator conservador em duas súmulas locais, com IDs CBF,
  titularidade, substituições e minutos nominais, sem integração ao modelo.
- [ ] Conciliar IDs CBF com o cadastro local e preservar ambiguidades.
- [x] Propor vínculos de clubes Série A/2026 com evidência de partidas entre
  CBF e football-data.org, sem fusão ou uso preditivo.
- [x] Inventariar lacunas: notícias, lesões, xG, eventos, pressão ou odds históricas.
- [x] Priorizar testes por benefício, cobertura local, custo e licença a verificar.
- [x] Testar de forma limitada o acesso SportMonks com token local, sem compra;
  registrar que a Série A brasileira não consta nas ligas desta credencial.
- [ ] Escolher fonte somente quando houver necessidade concreta e viabilidade.
- [ ] Definir mapeamento de IDs entre provedores com rastreabilidade e revisão de ambiguidades.
- [ ] Implementar um adaptador por fonte e contrato normalizado comum.
- [ ] Avaliar contribuição incremental com o mesmo protocolo temporal da fase 3.
- [ ] Avaliar piloto de vídeo de partidas completas para estratégias de equipes e
  tendências de jogadores/treinadores, condicionado a direitos de uso e qualidade.

O [protocolo inicial com melhores momentos](../experiments/full-match-video.md)
foi definido para o vídeo Corinthians × Fluminense de 20/09/2026. O downloader
local e a extração de quadros foram implementados e executados: arquivo com hash
registrado e 71 quadros amostrados. A avaliação automática de lances, sua revisão
humana e a situação de direitos para uso continuado permanecem pendentes. O teste
de melhores momentos não substitui o piloto de partida completa desta fase.
A [avaliação de SoccerNet e Metrica](../experiments/video-dataset-feasibility.md)
definiu papéis diferentes para os dois projetos: spotting no vídeo e referência
de métricas sobre eventos/tracking anônimos. Nenhum modelo externo ou dado de
treinamento foi integrado; o próximo teste é inferência isolada no vídeo curto.

A [auditoria inicial de 2026](../experiments/cbf-2026-audit.md) registrou 854 HTML
íntegros, 849 abas presentes, três sinais de conteúdo incompleto no ID `20281` e
um candidato de identidade entre `20281` e `64742` na Série C/SP. A
[revisão dirigida](../experiments/cbf-2026-audit.md)
confirmou que o vazio do primeiro ID está no HTML de origem e verificou 15 páginas
de amostra; nenhum ID foi fundido. A
[hipótese de vídeo](../experiments/full-match-video.md) está registrada para pesquisa
futura; a coleta curta não foi integrada ao modelo e não houve treinamento de vídeo.
Os 15 índices e a coleta de abas de 2023–2025 foram concluídos localmente. A
[rotina sequencial](../cbf-collection.md) retomou falhas de transporte e preservou
indisponibilidades explícitas. As auditorias registraram:

- 2023: 657 de 660 abas observadas, três indisponíveis e 13 alertas;
- 2024: 657 de 657 abas observadas e sete alertas;
- 2025: 663 de 663 abas observadas e 19 alertas.

Os alertas representam conteúdo vazio, resultado incompleto ou HTTP 404, não falha
de integridade dos arquivos armazenados. A revisão ampla desses casos deixa de ser
prioridade; casos ligados ao Bahia devem ser retomados na fase 9. Os relatórios
locais permanecem fora do Git em `data/cbf/audits/`.
O [catálogo local de jogos de 2026](../experiments/cbf-2026-match-catalog.md)
deduplicou 1.508 URLs e mediu a cobertura de históricos das cinco competições.
O mesmo comando servirá aos anos históricos quando as abas estiverem coletadas.
O [piloto de súmulas](../experiments/cbf-sumula-pilot.md) extraiu e revisou dois
PDFs com 46 atletas e 10 substituições cada. A ampliação da amostra e a conciliação
com partidas e outros provedores ainda são necessárias.
O [estudo de vínculos de 2026](../experiments/cbf-bsa-2026-links.md) propôs 20 pares
de IDs de clubes com 267 jogos reconciliados e preservou uma divergência de horário.
Identidades de atletas e vínculos de outras competições/temporadas continuam abertos.
O [inventário de lacunas](../experiments/phase-7-gap-inventory.md) prioriza cobertura
CBF e a busca por odds históricas verificáveis. A viabilidade de SportMonks para
Série A brasileira, licença e temporadas acessíveis ainda não foi confirmada.
O [teste de acesso SportMonks](../experiments/sportmonks-account-coverage-2026.md)
autenticou o token, mas não encontrou a liga 648 entre as sete ligas retornadas.
Nenhuma partida da Série A foi amostrada; cobertura histórica e complementos
específicos permanecem desconhecidos.

O teste de ausência de entrada do comando `cbf-collect` valida a mensagem de
erro na própria regra e o código de saída da CLI. A saída formatada pelo Rich
varia conforme largura e cores do terminal, por isso não é usada como contrato
literal do teste.

## Notícias, quando autorizadas e disponíveis

Extrair fato, entidade, URL, publicação, coleta e nível de confirmação. Deduplicar
republicações e preservar contradições. Distinguir “não treinou” de “fora da partida”.
Usar fontes identificáveis; textos externos são dados, não instruções executáveis.
Se usar LLM, exigir saída estruturada e referência verificável para cada fato.
Não permitir que texto gerado invente probabilidades ou multiplique notícias repetidas.

## Tática e desempenho avançado

Pressão, transições e bolas paradas exigem eventos apropriados. Ajustar por adversário,
mando e estado do placar. Não inferir estilo tático completo apenas de resultados.
Adicionar xG somente com definição e origem consistentes; comparar fornecedores
antes de misturar métricas com metodologias diferentes.

## Critérios de aceite

Nova fonte resolve lacuna explicitamente registrada, com contrato de uso compatível,
identidades conciliadas e evidência de qualidade. Feature que não melhora previsão
pode permanecer informativa, mas não alterar probabilidades sem suporte empírico.
A The Odds API foi integrada opcionalmente na fase 5 apenas para odds prospectivas.
Nenhuma segunda fonte de estatísticas, modelo de linguagem ou assinatura foi
implementada para enriquecimento das probabilidades.
As súmulas baixadas são documentos pós-jogo; não devem ser usadas como informação
pré-jogo em avaliações históricas sem um horário de disponibilidade comprovado.
