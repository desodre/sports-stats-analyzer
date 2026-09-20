# Viabilidade do FBref para dados do futebol brasileiro

Avaliação em 19/09/2026 para a fase 7. Nenhum dado do FBref foi incorporado ao
banco ou ao modelo.

## Cobertura e utilidade observadas

A [página do Brasil](https://fbref.com/en/country/BRA/Brazil-Football) lista
Série A e Série B masculinas de 2014 a 2026 e Série A1 feminina de 2019 a 2026.
Páginas indexadas da [Série A de 2025](https://fbref.com/en/comps/24/2025/2025-Serie-A-Stats)
mostram minutos, titularidades, gols, assistências e cartões por equipe e
jogador. Há [chutes e chutes no alvo por equipe](https://fbref.com/en/comps/24/2025/shooting/2025-Serie-A-Stats),
[estatísticas individuais de chutes](https://fbref.com/en/squads/639950ae/2025/c24/Flamengo-Stats-Serie-A)
e [chutes por partida](https://fbref.com/en/squads/639950ae/2025/matchlogs/c24/shooting/Flamengo-Match-Logs-Serie-A).
Isso poderia ajudar a auditar minutos da CBF e testar variáveis históricas de
finalização, desde que houvesse acesso e direito de uso adequados.

Essas páginas são agregações por temporada, equipe, jogador ou partida. A
amostra **não** demonstra um feed de cada passe, posição do atleta a cada
segundo, escalação conhecida antes do jogo, lesões ou odds com horário de
observação. Dados publicados depois da partida só serviriam como variáveis de
partidas *anteriores* ao corte temporal de uma previsão.

## Limites de dados, acesso e uso

- Em [20/01/2026, a Sports Reference anunciou](https://www.sports-reference.com/blog/2026/01/fbref-stathead-data-update/)
  a remoção dos dados avançados fornecidos por um parceiro. Informou que
  continuaria a disponibilizar dados básicos históricos. Na página indexada de
  [passes da Série A de 2025](https://fbref.com/en/comps/24/2025/passing/2025-Serie-A-Stats),
  colunas como passes completos/tentados e passes chave aparecem sem valores em
  linhas observadas. Cabeçalhos ou resultados antigos de busca não comprovam
  disponibilidade atual de passes detalhados, xG ou pressão.
- Uma requisição `HEAD` à página do Brasil, feita deste ambiente, recebeu
  `HTTP 403` com `cf-mitigated: challenge`. Também não foi possível abrir a
  página diretamente com a ferramenta de navegação. Não foi feita tentativa de
  contornar a proteção. As observações de conteúdo acima vêm de páginas do
  próprio FBref indexadas recentemente; não validam um coletor funcional nem a
  completude dos dados.
- A [política de tráfego automatizado](https://www.sports-reference.com/bot-traffic.html)
  informa bloqueio acima de dez requisições por minuto no FBref e ausência de
  API pública. Esse limite não é uma licença de coleta. Os
  [termos de uso](https://www.sports-reference.com/termsofuse.html) restringem
  automação que prejudique o acesso, bases que substituam o serviço e uso de
  conteúdo para modelos de IA ou métodos de aprendizado de máquina preditivos.
  Qualquer uso em um modelo ou produto precisa de avaliação dos termos e
  autorização compatível antes de uma integração.

## Decisão

Não implementar raspagem ou adaptador FBref nesta fase. O valor potencial está
em minutos e métricas básicas de chutes, mas o acesso automatizado não foi
obtido, os dados avançados foram removidos e os termos exigem cautela para o
uso pretendido. Prosseguir com a auditoria da CBF e buscar uma fonte com acesso
e permissão verificáveis para eventos, métricas avançadas e odds históricas.
Reabrir a avaliação somente com uma via de acesso autorizada, direitos de uso
confirmados e uma amostra que comprove cobertura nas temporadas necessárias.
