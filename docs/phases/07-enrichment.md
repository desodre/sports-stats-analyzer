# Fase 7 — Notícias e enriquecimento futuro

Estado: iniciada a coleta exploratória de súmulas e páginas de clubes CBF; enriquecimento estatístico
e integração ao modelo continuam pendentes.
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
- [ ] Concluir todas as abas de todos os clubes e auditar cobertura/duplicidades.
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
