# Piloto de extração de súmulas CBF

Executado em 19/09/2026 sobre os dois PDFs locais já registrados em `cbf_sumulas`.
O comando verifica o SHA-256 antes de ler o PDF e usa `pdftotext` (Poppler) para
extrair posições de palavras. Nenhum documento foi alterado.

```bash
uv run sports-stats-analyzer cbf-sumula-extract 1
uv run sports-stats-analyzer cbf-sumula-extract 2
```

| ID | Jogo | Data | Duração nominal | Atletas | Substituições | Soma de minutos por equipe |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | Bahia x Remo | 14/09/2026 | 101 | 46 | 10 | 1.111 |
| 2 | Fortaleza x Mirassol | 24/08/2025 | 104 | 46 | 10 | 1.144 |

Cada PDF apresenta 11 titulares e 12 reservas por equipe, com cinco trocas por
equipe. As somas correspondem a 11 vezes a duração nominal. As páginas 1 e 3 do
PDF de 2026 foram renderizadas e conferidas visualmente: IDs e papéis estão na
tabela de atletas, enquanto tempo, equipe e camisas constam da tabela de
substituições. O resultado estruturado liga cada troca aos IDs CBF pela camisa.

Os nomes no PDF são truncados visualmente; o extrator não os usa para conciliar
atletas. Minutos são **nominais**, calculados a partir dos acréscimos de cada tempo
e dos instantes das substituições, não uma medição de tempo efetivo de bola em jogo.
A publicação é preservada como texto local, sem supor fuso horário. O extrator
recusa documentos com expulsões, cronologia incompleta, três páginas fora do
layout A4 esperado, IDs duplicados ou substituições sem atleta correspondente.
Outros layouts e casos excepcionais exigem revisão e testes com mais PDFs.

Esses são documentos pós-jogo e não alimentam previsões. Ainda faltam coleta
ampliada, mapeamento entre URL de jogo e PDF, conciliação de IDs com outros
provedores e verificação de cobertura/erros em amostra maior.
