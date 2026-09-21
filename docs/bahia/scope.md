# Escopo longitudinal do Bahia

Versão: `bahia-scope-v1`. Decisão registrada em 21/09/2026.

## Unidade de análise

O foco é o **Esporte Clube Bahia**. A unidade primária é uma partida do Bahia; atleta,
comissão técnica, ação e padrão são entidades subordinadas a partidas observadas. O
adversário entra somente como contexto necessário para interpretar aquela partida.

O piloto usa dez partidas concluídas da Série A brasileira de 2026, entre 28/01 e
30/05. A amostra foi estratificada por mando e resultado: cinco jogos em casa, cinco
fora, quatro vitórias, três empates e três derrotas. O objetivo é validar o método,
não estimar a frequência anual definitiva de comportamentos.

O catálogo verificável está em [`pilot-2026.json`](pilot-2026.json).

## Identidade entre fontes

| Fonte | ID | Nome observado | Decisão |
| --- | ---: | --- | --- |
| football-data.org | `1777` | `EC Bahia` | ID do foco no corpus BSA 2026 |
| CBF | `61377` | `Bahia` | ID atual do foco; vínculo candidato sustentado por 23 partidas de 2026 |
| CBF | `20006` | `Esporte Clube Bahia` | ID histórico de 2023; relação com `61377` não presumida |
| CBF | `21878` | `Bahia de Feira` | Clube diferente; explicitamente excluído |

O vínculo `61377 ↔ 1777` é forte para o piloto, mas continua registrado como
`candidate_by_fixture_linkage`, não como identidade universal. IDs de atletas e
comissão técnica ainda não fazem parte desta decisão.

## Partidas do piloto

| Data UTC | Mando | Partida | Resultado do Bahia | football-data | CBF | Motivo de seleção |
| --- | --- | --- | --- | ---: | ---: | --- |
| 28/01 | Fora | Corinthians 1–2 Bahia | Vitória | `554743` | `831892` | vitória fora |
| 05/02 | Casa | Bahia 1–1 Fluminense | Empate | `554751` | `831907` | empate em casa |
| 18/03 | Casa | Bahia 2–0 RB Bragantino | Vitória | `554802` | `831957` | vitória sem sofrer gol |
| 22/03 | Fora | Remo 4–1 Bahia | Derrota | `554816` | `831968` | derrota de margem alta |
| 05/04 | Casa | Bahia 1–2 Palmeiras | Derrota | `554831` | `831988` | derrota em casa |
| 11/04 | Fora | Mirassol 1–2 Bahia | Vitória | `554846` | `831994` | vitória fora por um gol |
| 25/04 | Casa | Bahia 2–2 Santos | Empate | `554862` | `832018` | empate com quatro gols |
| 03/05 | Fora | São Paulo 2–2 Bahia | Empate | `554878` | `832022` | empate fora com quatro gols |
| 25/05 | Fora | Coritiba 3–2 Bahia | Derrota | `554901` | `832057` | derrota fora com cinco gols |
| 30/05 | Casa | Bahia 2–1 Botafogo | Vitória | `554911` | `832068` | vitória em casa por um gol |

Resultado final e mando são fatos disponíveis nas fontes estruturadas. As etiquetas
não descrevem progressão do placar, formação ou comportamento tático; isso exige
evidência adicional da fase 10.

## Perguntas observáveis

### Equipe

1. Por quais zonas o Bahia inicia e progride quando a jogada está observável?
2. Que ações antecedem entradas no terço final e finalizações?
3. Como a estrutura observada muda entre posse, perda, recuperação e bola parada?
4. Quais comportamentos se repetem por mando e estado do placar?
5. Em quais contextos o Bahia pressiona, recua ou interrompe a progressão adversária?

### Jogadores

1. Em quais zonas e funções cada jogador é observado recebendo e executando ações?
2. Qual ação escolhe depois de receber em contextos comparáveis?
3. Com quais companheiros forma sequências recorrentes de progressão ou criação?
4. Como seu papel observável muda por posição, formação, placar ou entrada como reserva?
5. Quais exemplos contradizem um padrão candidato?

### Comissão técnica

1. Quão estáveis são escalação, estrutura e papéis entre partidas?
2. Quando ocorrem substituições e quais mudanças observáveis as acompanham?
3. Como a equipe reage, em campo, a vantagem, desvantagem ou inferioridade numérica?
4. Quais padrões persistem e quais mudam entre períodos de comissão técnica?

Essas perguntas descrevem o que pode ser observado. Não autorizam inferir intenção,
instrução privada, personalidade, condição médica ou causalidade.

## Contexto mínimo do adversário

Para cada partida, registrar apenas: identidade, mando, placar/estado do placar,
estrutura observada quando necessária, número de jogadores, pressão ou bloco apenas
nos lances que sustentam uma observação do Bahia e eventos que alteram o contexto.
Não criar perfil longitudinal do adversário nesta trilha.
