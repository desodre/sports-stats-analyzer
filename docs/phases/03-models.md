# Fase 3 — Probabilidades e validação

Estado: implementada e testada com BSA 2023–2025. Resultado promissor apenas para
avançar à validação prospectiva de 1X2; não demonstra rentabilidade.

## Implementações

- [x] Baseline de frequências por competição e resultado relativo ao mando.
- [x] Poisson com forças ofensiva/defensiva, mando e regularização.
- [x] 1X2, total de gols 2,5 e ambas marcam derivados da distribuição de placares.
- [x] Massa truncada controlada e probabilidades consistentes.
- [x] Experimento com correção Dixon–Coles pós-ajuste; não selecionada na validação.
- [x] Walk-forward; hiperparâmetros escolhidos na validação e congelados no teste.
- [x] Log loss, Brier, calibração e bootstrap pareado por bloco temporal.
- [x] Versões, parâmetros, hashes, revisões e corte de cada previsão no artefato.
- [x] Abstenção por pouca amostra, equipe nova ou taxa/otimização inválida.

Dependências adicionadas via uv: NumPy e SciPy. Implementação em `models.py`,
`metrics.py`, `evaluation.py` e CLI; módulos simples em vez de pastas ainda desnecessárias.
Comando disponível: `evaluate`. Esta fase produz artefatos de experimentos, não
um serviço de previsões nem recomendações de apostas.

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

## Evidências

50 testes aprovados, incluindo 23 novos para modelos e avaliação temporal.
Coletadas três temporadas com 380 partidas cada. Na validação de 2024, 361 jogos
comuns aos candidatos; no teste de 2025, 365 previsões e 15 abstenções.

Ver [protocolo](../model-protocol.md) para fórmulas, cortes, critérios e limitações;
ver [resultado de BSA 2025](../experiments/bsa-2025.md) para métricas e conclusão.
O período 2025 já foi consultado: não reutilizá-lo como teste intocado ao ajustar
novos modelos. Próximas hipóteses exigem novo período reservado ou validação prospectiva.
