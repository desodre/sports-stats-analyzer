# Fase 7 — Notícias e enriquecimento futuro

Estado: adiada por decisão de usar somente football-data.org inicialmente.
Depende de lacunas demonstradas pelas fases anteriores e escolha futura de fontes.

## Plano de decisão

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
Nenhuma segunda API, modelo de linguagem ou assinatura foi implementada nesta entrega.
