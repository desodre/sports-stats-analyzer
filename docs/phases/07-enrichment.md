# Fase 7 — Notícias e enriquecimento futuro

Estado: coleta exploratória, auditoria automatizada e revisão dirigida das páginas
de clubes CBF de 2026 concluídas. Conciliação definitiva de identidades,
enriquecimento estatístico e integração ao modelo continuam pendentes.
O lote integral de páginas dos clubes de 2026 terminou: os cinco índices e as
849 abas previstas estão armazenados. A auditoria automatizada verificou cobertura,
estrutura e integridade; a revisão dirigida confirmou o conteúdo dos casos
sinalizados, mas não resolveu a relação entre os IDs do Ituano.
Depende de lacunas demonstradas pelas fases anteriores e escolha futura de fontes.

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
- [ ] Conciliar IDs CBF com o cadastro local e preservar ambiguidades.
- [ ] Inventariar lacunas: notícias, lesões, xG, eventos, pressão ou odds históricas.
- [ ] Priorizar cada lacuna por benefício testável, cobertura, custo e licença.
- [ ] Escolher fonte somente quando houver necessidade concreta e viabilidade.
- [ ] Definir mapeamento de IDs entre provedores com rastreabilidade e revisão de ambiguidades.
- [ ] Implementar um adaptador por fonte e contrato normalizado comum.
- [ ] Avaliar contribuição incremental com o mesmo protocolo temporal da fase 3.
- [ ] Avaliar piloto de vídeo de partidas completas para estratégias de equipes e
  tendências de jogadores/treinadores, condicionado a direitos de uso e qualidade.

A [auditoria inicial de 2026](../experiments/cbf-2026-audit.md) registrou 854 HTML
íntegros, 849 abas presentes, três sinais de conteúdo incompleto no ID `20281` e
um candidato de identidade entre `20281` e `64742` na Série C/SP. A
[revisão dirigida](../experiments/cbf-2026-audit.md)
confirmou que o vazio do primeiro ID está no HTML de origem e verificou 15 páginas
de amostra; nenhum ID foi fundido. A
[hipótese de vídeo](../experiments/full-match-video.md) está registrada para pesquisa
futura; não há ingestão ou treinamento de vídeo nesta etapa.

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
Nenhuma segunda API paga, modelo de linguagem ou assinatura foi implementada.
As súmulas baixadas são documentos pós-jogo; não devem ser usadas como informação
pré-jogo em avaliações históricas sem um horário de disponibilidade comprovado.
