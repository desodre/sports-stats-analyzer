# Protocolo estatístico da fase 3

## Objetivo e limites

Testar qualidade preditiva de probabilidades pré-jogo para uma competição.
Mercado primário: 1X2, na ordem mandante/empate/visitante. Mercados secundários:
mais de 2,5 gols e ambas marcam. Sem odds, ROI, apostas executadas ou promessa de lucro.

O comando `evaluate` interpreta os anos informados como **anos civis UTC**;
não usa o ano de início da temporada do provedor para cortar datas. Isso funciona
para o experimento BSA. Competições com temporada cruzando anos precisam de cortes
adequados, disponíveis via `ExperimentConfig` com datetimes explícitos na API Python.

## Dados e cronologia

Revisões normalizadas, resultados finalizados, times identificados e placar de
90 minutos disponível. Prorrogação e pênaltis nunca substituem o placar regulamentar.
Cobertura reportada é sobre essas partidas elegíveis, não todos os eventos da fonte.

Treino inicial anterior à validação; validação anterior ao teste final. Cada período
avança em blocos de sete dias ancorados no início do período. No começo de cada bloco,
reajustar parâmetros com todos os resultados desde `train_start`, cujo início ocorreu
mais de três horas antes do corte. Jogos simultâneos e do próprio bloco não entram
no treino. O buffer de três horas é uma aproximação, não evidência da hora de conclusão.

O treino cresce com o tempo. Durante o teste final, resultados de blocos anteriores
podem entrar no treino dos blocos seguintes, mas a escolha de hiperparâmetros permanece
congelada. Não há divisão aleatória entre treino e teste nem seleção pelo resultado final.

No modo padrão, o treino consulta revisões observadas até cada corte e exige que
os times e a data da partida já fossem conhecidos. Sem isso, abstém-se.
Com `--retrospective`, revisões atuais são usadas para uma simulação histórica.
Os resultados de 2023–2025 coletados em 2026 permitem esse segundo modo; não demonstram
como a API, correções e informações estavam disponíveis em cada data passada.

## Modelos

Baseline: frequências anteriores de mandante/empate/visitante, com um pseudocontador
por classe. Nos mercados binários, um pseudocontador para cada resultado.

Poisson independente:

```text
log(lambda_mandante) = intercepto + mando + ataque_mandante + defesa_visitante
log(lambda_visitante) = intercepto + ataque_visitante + defesa_mandante
```

Defesa positiva representa maior propensão a sofrer gols. Ajuste por máxima
verossimilhança penalizada, usando L-BFGS-B e gradiente analítico. Penalidade L2
aplicada a ataque/defesa; não ao intercepto e mando. Limites numéricos: intercepto
[-3, 3], mando e forças [-2, 2]. Não existe xG, notícia ou escalação como variável aqui.

O experimento compara penalidades 1 e 10 e rho em {0, -0,1, +0,1}. Para rho diferente
de zero, a matriz recebe a correção de placares baixos Dixon–Coles nos resultados
0–0, 0–1, 1–0 e 1–1. Trata-se de correção **após** o ajuste Poisson: não implementa
estimação conjunta de rho nem ponderação por recência do modelo original completo.

A matriz de placares cresce até massa omitida inferior a 1e-10 e é renormalizada.
Taxas fora de (0, 10], fatores de correção não positivos ou falha do otimizador
causam abstenção. Mínimos padrão: 100 jogos no treino e cinco aparições de cada time.
Times promovidos sem histórico suficiente não recebem forças inventadas.

## Seleção e métricas

Escolher a menor log loss 1X2 na validação, usando a interseção dos jogos previstos
pelos seis candidatos. Exigir ao menos 50 jogos e 80% de cobertura nessa interseção.
Levar ao teste apenas o vencedor e o melhor Poisson sem correção como referência
secundária, se forem diferentes. Não trocar de vencedor depois de olhar o teste.

Reportar log loss, Brier e calibração para os três mercados. Brier 1X2 é a soma dos
erros quadráticos nas três classes (escala 0–2); Brier binário é `(p-y)^2` (0–1).
Log loss recorta probabilidades em 1e-15 para estabilidade. Valores menores são melhores.
Calibração: cinco faixas fixas de probabilidade por classe, com contagem, probabilidade
média e frequência observada. ECE é a média dos desvios absolutos ponderados por
contagem e por classe. Faixas pouco povoadas exigem cautela.

Comparar modelo e baseline exatamente nos mesmos jogos. Mostrar também baseline
em todos os jogos em que o treino permitiu estimá-lo e as razões de abstenção do modelo.
Intervalo de 95% da diferença de log loss: bootstrap pareado de blocos semanais,
2.000 reamostragens, semente 42, ponderando pelo número de jogos. Valor negativo
favorece o modelo. É uma aproximação; não captura toda dependência entre times e semanas.

## Regra exploratória de decisão

Definida antes da execução de BSA 2025, aplica-se somente ao mercado 1X2:

- Pelo menos 100 previsões e cobertura de 80% no teste.
- Limite superior do intervalo da diferença de log loss abaixo de zero.
- ECE não piora mais de 0,02 em relação ao baseline.
- Diferença média de log loss negativa nas duas metades cronológicas do teste.

Se todos passarem, registrar `candidate_for_prospective_validation`; caso contrário,
`baseline_retained`. A tolerância de ECE é uma regra exploratória do projeto, não
um padrão universal de boa calibração. Não há promoção automática ou validação
financeira. Mercados secundários não herdam a conclusão do mercado primário.

## Rastreabilidade

Cada execução grava JSON exclusivo em `data/experiments/`, com UUID, horário,
configuração, versões de modelo/features/dependências, hash do código e hash dos
registros finais no recorte. Cada bloco inclui parâmetros ajustados, hash do treino,
IDs das revisões e corte. Cada previsão referencia seu bloco e snapshot do resultado.
Os snapshots no SQLite são necessários para reproduzir o treino exato.

O hash do conjunto final não substitui os hashes dos treinos: no modo observado,
eles podem usar versões anteriores. Identificador e horário da execução mudam;
métricas devem se repetir no mesmo ambiente com dados, código e parâmetros idênticos.
Artefatos completos e dados permanecem locais; o resumo do experimento é versionado.

## Referências

- [Artigo original Dixon e Coles, 1997](https://www.research.lancs.ac.uk/portal/en/publications/modelling-association-football-scores-and-inefficiencies-in-the-football-betting-market%28d16276a2-d6e0-483b-a708-1d29663f1992%29.html)
- [Artigo sobre a correção dos quatro placares baixos](https://arxiv.org/abs/2307.02139)
- [SciPy: distribuição Poisson](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.poisson.html)
- [SciPy: otimizador L-BFGS-B](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html)
