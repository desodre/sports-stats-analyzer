# Teste limitado da conta SportMonks

Executado em 19/09/2026, com autorização para consultas de leitura e token local.
Foram feitas seis requisições HTTPS à API v3, com `Authorization` no cabeçalho,
sem gravar respostas brutas ou credenciais e sem contratar serviços.

| Consulta | Observação |
| --- | --- |
| `GET /v3/my/leagues` (duas vezes) | HTTP 200; sete ligas: 271, 501, 513, 1659, 2153, 2155, 2160. Nenhuma é a Série A brasileira. |
| `GET /v3/football/leagues/648` (duas vezes) | HTTP 200, mas sem campo `data`; mensagem de ausência de resultado ou acesso. |
| `GET /v3/my/enrichments` | HTTP 200; 48 itens gerais, incluindo acesso a escalações, eventos, estatísticas e odds. A lista não demonstra disponibilidade na liga 648. |
| `GET /v3/my/resources` | HTTP 200; 124 recursos listados. |

O [ID 648](https://www.sportmonks.com/faq/) é o da Série A brasileira na
documentação pública. A [API My Leagues](https://docs.sportmonks.com/v3/core-api/my-sportmonks/get-my-leagues)
descreve as ligas da assinatura; a [documentação de cobertura](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/data-features-per-league)
recomenda usar os recursos da conta como referência. A API aceitou o token,
mas esta credencial não mostrou acesso à liga desejada. Como não foi possível
obter uma temporada ou uma partida da Série A, **nenhuma cobertura de escalações,
eventos, xG, pressão, odds ou histórico da competição foi medida**.

Decisão: não selecionar SportMonks como segunda fonte com a credencial atual.
Retomar o teste somente se uma credencial já autorizada passar a listar a liga
648; verificar temporadas e partidas antes de construir um adaptador. Nenhum
dado deste teste entrou no banco ou no modelo.
