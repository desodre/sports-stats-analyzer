# Contrato de evidência do Bahia

Versão: `bahia-evidence-v1`. O formato validável está em
[`evidence.schema.json`](evidence.schema.json).

## Princípio

Uma síntese só é auditável quando pode ser percorrida até uma observação, uma partida
e uma fonte. O contrato separa fato bruto, interpretação e limitação. Campos que não
podem ser observados ficam nulos ou recebem `unknown`; não são completados por palpite.

## Campos mínimos

| Grupo | Campos |
| --- | --- |
| Identidade | `schema_version`, `observation_id`, IDs da partida |
| Fonte | tipo, URI/localizador, horário de coleta, direitos e hash quando houver arquivo |
| Tempo | segundo do vídeo, relógio da partida, período e indicador de replay |
| Contexto | mando, placar, número de jogadores, fase e zona |
| Entidades | time foco, jogador e adversário quando identificáveis |
| Conteúdo | ação, fato observado, interpretação separada |
| Qualidade | confiança, estado de revisão, limitações |

## Estados de direitos

- `unreviewed`: acesso localizado, condições ainda não avaliadas;
- `local_analysis_only`: uso restrito à análise local, sem redistribuição;
- `permitted`: uso pretendido confirmado e registrado;
- `restricted`: uso possível com limitações adicionais;
- `prohibited`: fonte não deve ser usada no fluxo.

Disponibilidade pública não implica `permitted`.

## Matriz inicial de fontes

| Fonte | Uso no piloto | Estado inicial | Restrição operacional |
| --- | --- | --- | --- |
| football-data.org | metadados e resultados | `restricted` | acesso e redistribuição dependem da conta/termos; snapshots locais |
| páginas de jogos CBF | identidade e referência oficial da partida | `local_analysis_only` | preservar URL e coleta; não presumir licença de redistribuição |
| súmulas CBF | escalação, substituições e minutos pós-jogo | `local_analysis_only` | documento pós-jogo; não usar como informação pré-jogo sem horário comprovado |
| vídeo localizado na web | metadados e candidato a evidência | `unreviewed` | não baixar automaticamente; revisar direitos caso a caso |
| vídeo fornecido pelo usuário | análise quando autorizado | `unreviewed` | usuário informa origem/direito; mídia fora do Git e de exportações |

## Regras de uso

1. Hash é obrigatório para arquivo local usado como evidência.
2. URI não prova conteúdo, licença ou permanência.
3. Relógio do vídeo e relógio da partida são campos distintos.
4. Replay referencia o evento original e não conta como nova ocorrência.
5. Interpretação nunca substitui `observed_fact`.
6. Agregações padrão usam somente `reviewed` com confiança `high` ou `medium`.
7. `low`, `disputed` e `unknown` permanecem consultáveis, mas fora de métricas padrão.
8. Exportações não incorporam mídia sem permissão explícita.
