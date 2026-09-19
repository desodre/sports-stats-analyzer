# Coleta inicial de súmulas CBF

Estado em 19/09/2026: coletor manual/retomável para a Série A. A autorização de
raspagem foi informada pelo responsável pelo projeto. O comando aceita URLs de
páginas de jogo em `www.cbf.com.br` ou PDFs de súmula em `conteudo.cbf.com.br`;
não usa token, API interna, navegador automatizado ou fontes de terceiros.

```bash
uv run sports-stats-analyzer cbf-collect \
  --url https://conteudo.cbf.com.br/sumulas/2026/142269se.pdf \
  --max-documents 1
uv run sports-stats-analyzer cbf-collect --urls-file data/cbf-urls.txt --max-documents 10
```

O arquivo de entrada usa uma URL por linha e permite comentários com `#` no início.
Uma página de jogo exige duas requisições: HTML e PDF. O limite conta **todas** as
requisições à CBF, inclusive falhas; há pelo menos 31 segundos entre inícios de
requisições. Isso garante até dez acessos em qualquer janela de cinco minutos e
evita rajadas. O timestamp é gravado antes do acesso em
`SPORTS_RATE_LIMIT_DIR/cbf-public.lock`. Processos nesta máquina devem usar o mesmo
diretório; outras máquinas ou ferramentas externas não compartilham a cota.
Não remova o lock para antecipar a coleta. Não há retries automáticos nem desativação
de TLS. O comando é finito e não executa em segundo plano por conta própria.

O coletor não segue redirecionamentos; restringe hosts e rotas à Série A e aos PDFs
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
idêntico ao exemplar local previamente analisado. A consulta de uma página
de jogo em `www.cbf.com.br` falhou neste ambiente por cadeia TLS não verificável,
inclusive usando a CA do sistema. Não foi desabilitada a verificação de certificado.
Até resolver a cadeia/certificado, use somente URLs diretas de PDF verificadas;
isso limita a descoberta automática de documentos.
O PDF fornece evidência pós-jogo de escalação e substituições, não de disponibilidade
pré-jogo. Ainda faltam descoberta completa dos jogos, extração tabular, revisão de
qualidade, conciliação de atletas/equipes/partidas e avaliação temporal do impacto
no modelo. Não usar estes documentos para ajustar previsões até concluir essas etapas.
