# Fase 3 — Probabilidades e validação

Estado: planejada. Depende de qualidade e histórico suficientes na fase 2.

## Implementações

- [ ] Criar baseline de frequências por competição e mando, treinado apenas no passado.
- [ ] Ajustar Poisson com forças ofensiva/defensiva, mando e regularização.
- [ ] Derivar 1X2, total de gols 2,5 e ambas marcam de uma distribuição de placares.
- [ ] Controlar massa truncada da distribuição e garantir probabilidades consistentes.
- [ ] Comparar Dixon–Coles como experimento, condicionado a ganho fora da amostra.
- [ ] Criar validação walk-forward, com ajuste de hiperparâmetros apenas no treino.
- [ ] Medir log loss, Brier score e calibração; quantificar incerteza das comparações.
- [ ] Versionar modelo, features, corte, janela e conjunto de dados de cada previsão.
- [ ] Definir abstenção para dados insuficientes ou entradas fora do domínio treinado.

Dependências candidatas: NumPy, SciPy, pandas e scikit-learn, adicionadas com uv
quando utilizadas. Módulos previstos: `features/`, `models/`, `evaluation/`.

## Critérios de aceite

Experimento reproduzível com períodos de treino, validação e teste separados.
Probabilidades finitas entre 0 e 1; 1X2 soma 1 dentro de tolerância documentada.
Publicar comparação com baseline e limitações mesmo que o modelo não melhore.
Somente promover modelo cuja melhoria e calibração sejam sustentadas pelo teste;
caso contrário, manter baseline e registrar ausência de evidência.

## Verificação

Testar probabilidades, simetria sem mando, equipes novas e ausência de vazamento.
Incluir verificações contra dados posteriores ao horário da previsão. Backtest de
resultados não valida notícias ou escalações históricas sem evidência temporal.
Esta fase não declara rentabilidade: ainda não há histórico de odds adequado.
