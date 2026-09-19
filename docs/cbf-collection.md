# Coleta inicial de súmulas CBF

Estado em 19/09/2026: coletores retomáveis para Série A–D e Copa do Brasil masculina.
A autorização de
raspagem foi informada pelo responsável pelo projeto. O comando aceita URLs de
páginas de jogo em `www.cbf.com.br` ou PDFs de súmula em `conteudo.cbf.com.br`;
não usa token, API interna, navegador automatizado ou fontes de terceiros.

```bash
uv run sports-stats-analyzer cbf-collect \
  --url https://conteudo.cbf.com.br/sumulas/2026/142269se.pdf \
  --max-documents 1
uv run sports-stats-analyzer cbf-collect --urls-file data/cbf-urls.txt --max-documents 20
```

O arquivo de entrada usa uma URL por linha e permite comentários com `#` no início.
Uma página de jogo exige duas requisições: HTML e PDF. O limite conta **todas** as
requisições à CBF, inclusive falhas; há pelo menos 15,1 segundos entre inícios de
requisições. Isso garante até vinte acessos em qualquer janela de cinco minutos e
evita rajadas. O timestamp é gravado antes do acesso em
`SPORTS_RATE_LIMIT_DIR/cbf-public.lock`. Processos nesta máquina devem usar o mesmo
diretório; outras máquinas ou ferramentas externas não compartilham a cota.
Não remova o lock para antecipar a coleta. Não há retries automáticos nem desativação
de TLS. O comando é finito e não executa em segundo plano por conta própria.

O coletor não segue redirecionamentos; restringe hosts e rotas às cinco competições
selecionadas e aos PDFs
`/sumulas/ANO/NUMEROse.pdf`. Recusa conteúdo acima de 10 MiB ou sem marcadores
básicos de PDF. Salva pelo SHA-256 em `data/cbf/sumulas/ANO/` e registra URL de origem,
URL do PDF, ano, hash, horário da coleta, caminho, ETag e Last-Modified na tabela
`cbf_sumulas` do banco configurado. Não sobrescreve revisões: `--refresh` consulta
novamente uma URL e guarda outro hash se o documento mudou. Por padrão, um PDF já
presente é ignorado. PDFs, banco e arquivo de URLs em `data/` são locais e não entram
no Git. Faça backup de `data/cbf/` separadamente do backup SQLite.

Piloto real: duas súmulas foram baixadas e registradas. A de 2025,
`142209se.pdf`, tem SHA-256
`500e6b1c6daefac05e977f34da5f0b56c17f5b07e31aa11cceb17501a604fec1`;
o PDF de três páginas identifica Fortaleza x Mirassol em 24/08/2025.
A de 2026, `142269se.pdf`, tem SHA-256
`e264614a9f44fa2577b35aaeb9ba536f179263144ba048c58c2164b61e9ff8cd`,
idêntico ao exemplar local previamente analisado. O servidor `www.cbf.com.br`
entregou somente o certificado final, sem o intermediário necessário. Uma cadeia
pública fornecida pela Sectigo permitiu verificar o TLS, sem desligar a validação.

## Clubes e certificado TLS

O escopo combinado para 2026 é Série A, B, C, D e Copa do Brasil masculinas.
Cada índice de competição lista IDs, nomes e UFs. Para cada clube o comando coleta
três abas: atletas listados (nome, apelido e clube atual), histórico de jogos
(equipes, placar, local/data textual e link) e estatísticas agregadas (gols,
resultados e cartões). O HTML completo também é salvo por hash em `data/cbf/html/`;
observações estruturadas ficam em `cbf_team_pages` e clubes em `cbf_teams`.
Nenhum atleta listado é automaticamente considerado disponível, titular ou ativo.

Para verificar as páginas da CBF neste ambiente, baixe a cadeia pública indicada
pela [Sectigo](https://www.sectigo.com/knowledge-base/detail/Sectigo-new-Public-Roots-and-Issuing-CAs-Hierarchy)
para `data/cbf/certs/sectigo-ov-bundle.crt` e configure `SPORTS_CBF_CA_BUNDLE`
com esse caminho. O pacote usado no piloto veio do anexo oficial “UserTRUST to
R46 to OV R36_Bundle”, com SHA-256
`c584761a149e111c050505e424dc79ac1764cf15bfe818b38b203460c02dcaaf`.
O arquivo é dado operacional local, não commitado. A aplicação mantém as CAs do
sistema e acrescenta essa cadeia; nunca usa `verify=False`.

```bash
mkdir -p data/cbf/certs
curl -fL https://support.sectigo.com/sfc/servlet.shepherd/version/download/068Uj00000Xugfw \
  -o data/cbf/certs/sectigo-ov-bundle.crt
sha256sum data/cbf/certs/sectigo-ov-bundle.crt
```

Confira o hash e a cadeia antes de usar. O anexo pode mudar no futuro; nesse caso,
valide-o novamente com a documentação oficial da Sectigo.

```bash
SPORTS_CBF_CA_BUNDLE=data/cbf/certs/sectigo-ov-bundle.crt \
  uv run sports-stats-analyzer cbf-teams --season 2026 --max-requests 20
uv run sports-stats-analyzer cbf-team-coverage --season 2026
uv run sports-stats-analyzer cbf-team-audit --season 2026
```

O primeiro comando começa pelos cinco índices, depois coleta as três abas de cada
ID. Ao repetir, pula páginas já armazenadas; `--refresh` força nova observação.
`--max-requests` limita o tamanho do lote, não a cota temporal. Para um processo
contínuo, aumente esse valor e acrescente `--progress` para emitir cada página
concluída, mantendo o mesmo diretório de lock. Outros anos
exigem `--season`. IDs repetidos ou nomes divergentes são preservados para auditoria,
sem fusão automática. Em 19/09/2026 o índice da Série C listou tanto “ITUANO FC”
quanto “Ituano” com IDs distintos; por isso 21 IDs não significam 21 clubes reais.
Os cinco índices de 2026 retornaram 20, 20, 21, 96 e 126 IDs, respectivamente
para Séries A–D e Copa do Brasil; são 171 IDs únicos entre competições. Esses números
representam o site observado, não uma validação independente dos participantes.
São 283 participações e 849 páginas de abas, além dos cinco índices. A coleta
integral de 2026 terminou com cobertura registrada para as três abas de todas
as participações. `cbf-team-audit` confere também os arquivos HTML, a estrutura
do conteúdo e candidatos de identidade, sem novas requisições ou fusão de IDs.
A [auditoria inicial](experiments/cbf-2026-audit.md) encontrou páginas íntegras
e um caso da Série C que ainda exige revisão humana. Consulte
`cbf-team-coverage` para conferir apenas a presença das abas. Uma interrupção em
uma nova coleta não exige reiniciar do zero.
Por decisão do responsável, a coleta de 2023–2025 nessas mesmas competições é a
segunda etapa, após concluir e auditar 2026; não começou neste lote.

A execução integral de 2026 foi feita como unidade temporária do `systemd --user`;
em 19/09/2026, a unidade estava inativa com `Result=success` e código de saída 0:

```bash
systemctl --user status sports-stats-cbf-teams-2026.service
journalctl --user -u sports-stats-cbf-teams-2026.service -n 30 --no-pager
uv run sports-stats-analyzer cbf-team-coverage --season 2026
```

Ela não reinicia automaticamente se falhar. Para interromper deliberadamente,
use `systemctl --user stop sports-stats-cbf-teams-2026.service`; para retomar,
execute `cbf-teams` novamente com o mesmo ano, certificado e diretório de cota.
O progresso pode ser consultado sem interromper a coleta. Não execute uma segunda
varredura ao mesmo tempo; o lock evitaria exceder a cota, mas duplicaria trabalho.
Nesta máquina, `Linger=no`: a unidade do usuário depende de uma sessão de login
ativa e pode parar ao sair do computador ou suspender a máquina. A retomada é segura.

O PDF fornece evidência pós-jogo de escalação e substituições, não de disponibilidade
pré-jogo. Ainda faltam descoberta completa dos jogos, extração tabular, revisão de
qualidade, conciliação de atletas/equipes/partidas e avaliação temporal do impacto
no modelo. Não usar estes documentos para ajustar previsões até concluir essas etapas.
