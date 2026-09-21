# Perguntas de produto para o Bahia

Versão: `bahia-research-questions-v1`. Perguntas registradas em 21/09/2026 e
traduzidas para respostas verificáveis. Elas orientam o corpus sem autorizar
preenchimento de lacunas por inferência.

## Q1 — Como está a temporada atual do Bahia?

Resposta-alvo: fotografia datada da Série A 2026 com posição e pontos quando houver
snapshot de classificação, campanha, gols, forma recente, desempenho em casa/fora,
força dos adversários enfrentados e cobertura das fontes. Outras competições só
entram quando possuírem o mesmo nível de rastreabilidade.

Toda resposta deve informar `as_of`, competição, número de partidas, fontes e campos
ausentes. “Boa” ou “ruim” deve ser consequência de critérios explícitos, não opinião.

## Q2 — Quais são as chances de ganhar os próximos jogos?

Resposta-alvo: probabilidades de vitória, empate e derrota para cada próximo jogo,
com data de geração, versão do modelo, dados disponíveis naquele instante, intervalo
ou sinalização de incerteza e comparação com baselines. Adiamento, mando desconhecido
ou amostra insuficiente devem impedir falsa precisão.

Esta pergunta reutiliza as fases 3 e 5, agora filtradas para o Bahia. Probabilidade
não é certeza nem recomendação de aposta, e dados publicados depois da partida não
podem participar da previsão.

## Q3 — Como o Bahia joga contra Flamengo, Palmeiras e adversários semelhantes?

Resposta-alvo: comparação observacional de saída, progressão, criação, pressão,
transições, bola parada e mudanças por placar/mando nas partidas com cobertura
suficiente. Exemplos e contraexemplos devem apontar para instantes revisáveis.

Flamengo e Palmeiras formam o primeiro recorte solicitado. “Maiores recursos” é uma
hipótese de contexto: só pode ser usada como variável se houver medida, fonte e data
para recursos financeiros ou valor de elenco. O nome do adversário, sozinho, não
prova superioridade de recursos nem explica causalmente o comportamento do Bahia.

## Q4 — Quais são as métricas dos atletas e quem possui perfil semelhante?

Resposta-alvo: ficha atual de cada atleta com posição e função observadas, minutos,
amostra, disponibilidade das métricas, ações por 90 quando o denominador for válido,
contexto e incerteza. A similaridade deve usar apenas métricas comparáveis e declarar
população, temporada, competição, posição/função, minutos mínimos, distância e fonte.

O foco continua sendo o Bahia. Atletas externos entram como referências limitadas de
comparação, não como novos dossiês de clubes. Enquanto não houver cobertura homogênea
entre jogadores, o sistema responde `dados insuficientes` em vez de produzir um
ranking enganoso.

## Ordem de implementação

1. Q1: corpus e consultas da fase 9.
2. Q2: aplicação Bahia dos modelos e previsões já existentes.
3. Q3: anotações da fase 10 e síntese coletiva da fase 12.
4. Q4: identidades e minutos da fase 9, perfis da fase 11 e fonte comparável limitada.
