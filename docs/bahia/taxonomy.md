# Taxonomia observacional do Bahia

Versão: `bahia-taxonomy-v1`. Esta taxonomia organiza observações; não transforma
interpretação em fato nem substitui revisão humana.

## Orientação e zonas

Normalizar a direção de ataque do Bahia da esquerda para a direita. Quando a câmera
ou a origem não permitir localizar a ação, usar `unknown`.

O campo usa nove zonas básicas: terços `defensive`, `middle`, `attacking`, cruzados
com corredores `left`, `central`, `right`. Área defensiva e área ofensiva podem ser
marcadas adicionalmente. Coordenadas contínuas são opcionais e exigem método de
calibração registrado.

## Fases do jogo

| Valor | Definição operacional |
| --- | --- |
| `attacking_build_up` | Bahia em posse buscando sair do primeiro terço organizado |
| `attacking_progression` | Posse tentando avançar entre primeiro e último terço |
| `attacking_final_third` | Posse controlada ou ação ofensiva no último terço |
| `attacking_set_piece` | Reinício ofensivo com bola parada |
| `defensive_high_block` | Bahia sem posse com primeira linha pressionando alto |
| `defensive_mid_block` | Bahia sem posse organizado predominantemente no terço médio |
| `defensive_low_block` | Bahia sem posse organizado próximo da própria área |
| `defensive_set_piece` | Reinício adversário com bola parada |
| `transition_attack` | Intervalo entre recuperação e estabilização da posse/ataque |
| `transition_defence` | Intervalo entre perda e reorganização defensiva |
| `stoppage` | Bola parada, atendimento, revisão ou interrupção sem fase ativa |
| `unknown` | Evidência insuficiente para classificar |

## Ações

Valores iniciais: `receive`, `pass`, `cross`, `carry`, `dribble`, `shot`, `header`,
`pressure`, `duel`, `interception`, `recovery`, `block`, `clearance`, `foul`,
`restart`, `substitution_effect`, `off_ball_run`, `shape_change`, `other`, `unknown`.

Subtipos não devem ser inferidos sem definição. Por exemplo, um passe só recebe a
marca `progressive` quando o método e a informação espacial necessária estiverem
registrados; “passe inteligente” não é categoria observável.

## Contexto obrigatório

- `venue_role`: `home`, `away` ou `neutral`;
- `score_state`: `leading`, `drawing`, `trailing` ou `unknown`;
- `period`: `first_half`, `second_half`, `extra_time`, `shootout` ou `unknown`;
- `player_state`: `equal`, `bahia_superior`, `bahia_inferior` ou `unknown`;
- formação declarada e estrutura observada em campos separados;
- posição nominal e função observada em campos separados;
- adversário apenas no contexto da partida.

## Confiança e revisão

| Confiança | Uso |
| --- | --- |
| `high` | fato claramente visível ou coincidente em fontes independentes |
| `medium` | observação provável, mas com câmera, identidade ou instante parcialmente limitados |
| `low` | hipótese útil para revisão, nunca para agregação padrão |
| `unknown` | confiança ainda não avaliada |

Estados de revisão: `unreviewed`, `reviewed`, `disputed`, `rejected`. Divergências
são preservadas; revisão não apaga a observação original.

## Linguagem de padrões

- **Observação isolada:** uma ocorrência rastreável.
- **Padrão candidato:** pelo menos cinco ocorrências em três partidas, com denominador
  e contextos registrados; permanece hipótese descritiva.
- **Padrão recorrente:** regra específica pré-registrada para a métrica, revisada em
  amostra ampliada e acompanhada de contraexemplos.
- **Dados insuficientes:** cobertura, denominador ou diversidade de contexto não
  sustentam a síntese.

O limiar de candidato reduz narrativas baseadas em um único jogo, mas não demonstra
estabilidade, causalidade ou capacidade preditiva.
