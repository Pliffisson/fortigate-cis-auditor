# FortiGate CIS Auditor

Auditoria offline de exportações FortiOS **7.4.x**, baseada no PDF CIS FortiGate 7.4.x v1.0.1 fornecido neste projeto. Interface web, API e CLI usam o mesmo motor e geram relatórios HTML, JSON e PDF.

O catálogo contém 64 controles (39 Level 1 e 25 Level 2). O resultado distingue aprovação, falha, revisão manual, não aplicabilidade e erro. A porcentagem representa conformidade parcial dos controles avaliados; a cobertura informa quanto foi verificado. Uma exportação offline não comprova conformidade integral nem certificação CIS. Veja os critérios e limitações na [análise do benchmark](docs/cis_74_analysis.md).

O motor legado 7.0.x foi removido porque não foi validado pelo PDF atual. Outras famílias e exportações sem cabeçalho de versão são rejeitadas.

## Alinhamento ao CIS Controls

A auditoria inclui uma seção de alinhamento ao **CIS Controls v8.1.2**, com catálogo de 153 salvaguardas e relações propostas pelo projeto para 16 delas. As relações mostram quais testes FortiGate contribuem como evidência parcial e o que ainda precisa ser comprovado pela organização; não são apresentadas como mapeamento oficial CIS.

IG1 contém 56 salvaguardas, IG2 contém 130 e IG3 contém 153. O filtro de grupo é independente de Level 1/Level 2 e não altera o score técnico. “Com evidência técnica” inclui testes concluídos como PASS ou FAIL e não significa salvaguarda atendida. “Revisão organizacional pendente” não é aprovação; “não avaliada pelo projeto” não significa não aplicável à organização.

Abra **CIS Controls → Explorar salvaguardas e evidências necessárias** para selecionar o grupo, buscar um ID ou incluir as salvaguardas sem relacionamento aos testes atuais. Cada recomendação técnica também mostra seus relacionamentos nos detalhes. HTML/PDF incluem o alinhamento; JSON e API acrescentam `controls_alignment` e `results[].controls_safeguards`, preservando os campos anteriores. A impressão apresenta todas as 16 relações independentemente dos filtros ativos.

O catálogo e os relacionamentos ficam em `cis_benchmark/controls`; a fonte é identificada por versão, páginas e SHA-256. Esta etapa não armazena revisões organizacionais nem declara conformidade corporativa. Histórico de evidências, responsáveis e prazos, autenticação centralizada/MFA e logs operacionais estão detalhados no [plano de implementação](docs/cis_controls_implementation.md).

## Executar em container

Requisitos: Docker e Docker Compose.

Ao obter o projeto pelo GitHub, crie seu `.env` a partir de `.env.example`. Arquivos `.env`, configurações reais de equipamentos, relatórios e PDFs de referência não fazem parte do repositório. Os documentos CIS utilizados na análise devem ser obtidos separadamente; o catálogo da aplicação inclui a identificação e o hash das fontes.

```bash
# Somente na primeira configuração, se .env ainda não existir:
cp .env.example .env

docker compose up -d --build --wait
docker compose logs -f auditor
```

O acesso é feito pelo Traefik existente em **https://auditoria-fortinet.enw.internal**. Configure `AUDITOR_DOMAIN` e `TRAEFIK_NETWORK` no `.env`; a rede externa padrão é `proxy`. O auditor usa apenas a porta interna `8000`, sem publicar uma porta na VM. Mantenha `SESSION_COOKIE_SECURE=true` para HTTPS.

O Traefik precisa do provider Docker, entrypoint `websecure`, certificado para o domínio e dos middlewares existentes `secure-headers@file` e `compress@file`. O certificado interno atual cobre `*.enw.internal`; os computadores clientes precisam confiar na autoridade que o emitiu. Cadastre no DNS interno o registro A `auditoria-fortinet.enw.internal` apontando para `192.168.101.160`. O redirecionamento HTTP para HTTPS já é configurado pelo Traefik da VM.

Envie um backup `.conf`, preferencialmente obtido com `show full-configuration` e mantendo seu cabeçalho. Escolha Level 1, Level 2 ou ambos. O timezone esperado é opcional e deve ser o ID utilizado pelo FortiOS.

No cabeçalho, **Logo da empresa** permite selecionar, trocar ou remover uma imagem PNG, JPG ou WebP de até 2 MB. A logo fica salva apenas no navegador utilizado, aparece no cabeçalho da interface e não é enviada ao servidor nem incluída nos relatórios exportados.

A interface usa uma paleta grafite/verde e JetBrains Mono, servida localmente pelo container. Os arquivos Regular e Bold são da [versão oficial 2.304](https://github.com/JetBrains/JetBrainsMono/tree/v2.304), com licença preservada em `web/static/fonts/OFL.txt`. O tema fica em `web/static/theme.css`.

Para capturas do terminal, salve a saída de `get system status` antes da saída de `show full-configuration`, incluindo a linha `Version:`. Arquivos UTF-8 e Unicode UTF-16/UTF-32 com marcador de codificação são aceitos. Backups criptografados precisam ser exportados novamente como texto antes da análise.

Os relatórios da interface ficam em memória por sessão, por até duas horas. Reiniciar o serviço descarta esses relatórios. A implantação usa um worker Gunicorn com duas threads; múltiplos workers exigem armazenamento compartilhado. O container executa como usuário sem privilégios, com sistema de arquivos somente leitura, limites de recursos e healthcheck.

```bash
docker compose down
```

## CLI

A CLI recebe entrada e saída por volumes explícitos. Exemplo com a configuração fictícia de testes:

```bash
mkdir -p reports
docker compose run --rm --no-deps \
  --user "$(id -u):$(id -g)" \
  -v "$PWD/tests/fixtures:/input:ro" \
  -v "$PWD/reports:/output" \
  auditor python /app/run_audit.py /input/sample.conf \
  --output-dir /output --format html,json,pdf --level all
```

Opções: `--level 1|2|all`, `--format html,json,pdf`, `--expected-timezone ID`, `--output-dir DIRETORIO` e `--no-remediation`. A remediação é sempre um preview comentado, gerado somente para falhas confirmadas com comandos disponíveis. O auditor não executa comandos no FortiGate.

## API

```bash
curl -F 'config_file=@backup.conf' -F 'level=all' \
  http://127.0.0.1:8000/api/audit
```

O campo opcional `expected_timezone` usa o mesmo critério da CLI. `/health` verifica a disponibilidade do serviço. A API retorna a avaliação em JSON sem criar uma sessão de relatórios no navegador.

## Validação

A imagem de testes adiciona pytest à mesma base da aplicação. As dependências de testes ficam fora da imagem de produção.

```bash
docker compose --profile test build tests
docker compose --profile test run --rm tests
docker compose --profile test run --rm tests python tests/container_smoke.py
```

O smoke test verifica upload, isolamento de sessões, API, arquivos estáticos e download HTML/JSON/PDF/remediação. `tests/fixtures/sample.conf` é fictício e não serve como modelo de configuração em conformidade.

## Estrutura

```text
cis_benchmark/
  audit.py              # Pipeline único de auditoria
  benchmark.py          # Metadados e seleção de versão
  cli.py                # CLI
  config_parser.py      # Parser com escopos e VDOMs
  scoring.py            # Pontuação e cobertura
  remediation.py        # Preview comentado
  rules/
    base.py
    catalog.json        # Inventário dos 64 controles
    guidance.py         # Critérios e orientações
    registry.py         # Registro e despacho dos controles
    checks/             # Avaliadores por área CIS e helpers comuns
    cli_preview.py      # Comandos vinculados aos objetos afetados
  reporting/            # Exportação compartilhada HTML/JSON/PDF
    templates/          # Estrutura e tabelas do relatório exportado
    assets/             # CSS e JavaScript incorporados ao HTML
web/
  app.py                # Fábrica da aplicação
  settings.py           # Configuração validada na inicialização
  views.py              # Interface, API e downloads
  session_store.py      # Armazenamento temporário por instância
  templates/dashboard.html
  static/               # CSS e JavaScript da interface
tests/
  fixtures/sample.conf
  conftest.py           # Fixtures e aplicações isoladas
  unit/                # Parser, catálogo, regras e pontuação
  integration/         # Pipeline, API, sessões e exportação
  browser/             # Interface e relatório independente em Chromium
  container_smoke.py
docs/
  architecture.md
  cis_74_analysis.md
  reference/            # PDF original preservado
Dockerfile
compose.yaml
requirements.txt        # Dependências de produção com versões fixadas
requirements-dev.txt    # Dependência de testes
requirements-browser.txt # Dependência do teste em Chromium
run_audit.py            # Entrada compatível da CLI
```

Backups, segredos, relatórios locais e o PDF de referência ficam fora da imagem de produção. Detalhes do pipeline estão na [arquitetura](docs/architecture.md).

## Limites e acesso

A tela inicial destaca o upload e informa nome, tamanho e erros de seleção. As opções de nível e timezone esperado ficam em “Opções avançadas”, com CIS completo como padrão. “Como exportar a configuração” reúne as instruções e o botão para copiar os comandos CLI. A validação do navegador orienta sobre extensão, arquivo vazio e tamanho; o servidor mantém a validação do conteúdo e do limite total do envio.

O resumo identifica o arquivo analisado e a data da avaliação. A navegação “Resumo / Falhas / Todos os controles” acompanha a rolagem e destaca a seção atual; “Falhas” aparece quando houver resultados reprovados. Os status na interface são exibidos em português, com ícones e cores, enquanto API/JSON mantêm os códigos PASS, FAIL, MANUAL_REVIEW, NOT_APPLICABLE e ERROR. Transições respeitam a preferência de movimento reduzido do navegador.

Os indicadores de falhas, revisão manual, erros e não aplicáveis são atalhos para a lista completa já filtrada. Cada controle tem detalhes com critério esperado, evidência, orientação e referência CIS. A ordenação pode usar ID CIS, nível ou severidade; filtros e ordem são mantidos no `sessionStorage` da aba, por auditoria, sem salvar o relatório ou os comandos. “Limpar filtros” restaura a visualização inicial. “Imprimir resumo” inclui indicadores, falhas e pendências independentemente dos filtros ativos, e restaura a tela após fechar a impressão.

A cobertura aparece em azul e indica “Avaliação parcial” quando restam controles aplicáveis sem conclusão. Ela mede a extensão da avaliação, não a segurança da configuração. A conformidade geral e por nível usa a escala visual do projeto: verde ≥80%, amarelo ≥60% e <80%, laranja ≥40% e <60%, vermelho <40%; sem controles avaliados, usa cinza. Esses limites são convenções deste projeto, não critérios de aprovação ou certificação CIS.

Depois do upload, o resultado aparece no topo. A metodologia e a legenda podem ser expandidas em “Como interpretar os resultados e as cores”; “Analisar outro arquivo” abre o formulário de um novo upload. As tabelas têm busca por ID/nome/configuração e filtros independentes por nível e categoria; a tabela completa também filtra status. “Limpar filtros” restaura os resultados. No celular, as linhas aparecem como cartões; no desktop, o cabeçalho acompanha a rolagem da tabela. Os comandos CLI ficam em “Ver comandos CLI”, com cópia por botão e orientação para parâmetros. Downloads ficam em “Exportar relatório”, junto da ação secundária de exclusão.

Configure `TZ=America/Manaus` no `.env` para datas, horários e logs (UTC−04:00). Outros exemplos: `America/Sao_Paulo` e `UTC`. Após alterar, execute `docker compose up -d --wait auditor`; envie novamente o arquivo para atualizar a data da auditoria. JSON e previews de remediação incluem o deslocamento UTC. Esse timezone pertence à aplicação e é independente do timezone esperado do FortiGate no formulário.

O upload HTTP tem limite padrão de 10 MB, configurável por `MAX_UPLOAD_MB` (até 50 MB). A CLI mantém o limite de 50 MB. Uma análise ou geração de PDF é processada por vez; solicitações concorrentes recebem HTTP 429 com indicação para tentar novamente. O formulário limita campos de texto a 128 KB e até dez partes multipart.

O armazenamento em memória mantém até 100 sessões e um orçamento de 64 MB para o tamanho serializado dos relatórios e PDFs. Esse orçamento não representa o consumo total do processo Python. Sessões expiram após duas horas de inatividade, com limpeza a cada 30 segundos; ao atingir limites, a sessão menos recente é removida. “Excluir minha auditoria” remove o relatório e o PDF da sessão. O PDF é reutilizado até um novo upload ou expiração.

Para habilitar autenticação HTTP Basic, configure `AUTH_USER` e `AUTH_PASSWORD_HASH` no `.env`. Gere o hash com `werkzeug.security.generate_password_hash`, usando entrada interativa para não gravar a senha no histórico do shell. Coloque o hash entre aspas simples no `.env` para preservar os caracteres `$`. Publique esse modo somente por proxy HTTPS e configure `SESSION_COOKIE_SECURE=true`; certificados e domínio devem ser configurados no proxy da sua infraestrutura. Sem essas variáveis, permanece o modo local sem autenticação. O formulário autenticado usa token CSRF; a API recebe credenciais HTTP Basic e não usa sessão de navegador.

Teste real em Chromium, em imagem separada da produção:

```bash
docker compose --profile browser build browser
docker compose --profile browser run --rm browser
```

Os testes verificam seleção de arquivo, erro visível, upload válido, comandos CLI, exclusão e largura do formulário em tela pequena. Templates CLI usam nomes e IDs identificados na evidência, com aspas e escopo VDOM; parâmetros operacionais continuam como `<...>`. Revise os comandos antes de aplicar.

Os testes em Chromium também verificam o HTML exportado sem recursos externos: estilos, filtros e escape de conteúdo. Os arquivos em `reporting/assets` são incorporados ao download; não precisam acompanhar o relatório. Para executar apenas uma área da suíte no container de testes, use `docker compose --profile test run --rm tests python -m pytest -q -p no:cacheprovider tests/unit` ou substitua por `tests/integration`.

`REQUESTS_PER_MINUTE` limita requisições por endereço de conexão. Na implantação com Traefik, fica em `0` (desativado no aplicativo), pois o proxy compartilha seu endereço entre clientes. O middleware dedicado do Traefik limita cada cliente a uma taxa média de 120 requisições por minuto, com rajadas de até 20. O aplicativo não confia automaticamente em cabeçalhos encaminhados. O healthcheck interno não passa pelo proxy.

Medição sintética nesta validação: 10.000 políticas (679 KB) foram avaliadas em aproximadamente 1,04 s, com pico de RSS de 31,1 MB e nenhum erro interno. Esse cenário mede o motor em processo separado, sem geração de PDF, e não estabelece o consumo máximo para arquivos reais de 10 MB.

## VS Code sem Python no computador

A aplicação, CLI, testes e Chromium executam em containers. O aviso “No Python found” vem da extensão do VS Code aberta no ambiente local; ele não significa que o container está sem Python.

Para desenvolver usando somente o Python do container:

1. Cancele a instalação local de Python.
2. Tenha Docker disponível e instale a extensão **Dev Containers** (`ms-vscode-remote.remote-containers`) no VS Code.
3. Abra esta pasta e execute **Dev Containers: Reopen in Container** pela paleta de comandos (`Ctrl+Shift+P`).
4. Aguarde a construção do ambiente. O interpretador será `/usr/local/bin/python` dentro do container, com as dependências da aplicação e pytest.

A configuração está em `.devcontainer/devcontainer.json`. O terminal e a execução de testes do editor passam a usar o container de desenvolvimento; o código continua na pasta do projeto por volume. A imagem de produção mantém seus limites e configurações próprios.

Dentro do terminal do Dev Container:

```bash
python -m pytest -q -p no:cacheprovider
python run_audit.py tests/fixtures/sample.conf --output-dir /tmp/reports
# Para iniciar a interface no ambiente de desenvolvimento:
gunicorn --no-control-socket --workers 1 --threads 2 --bind 0.0.0.0:8000 web.app:app
```

O Dev Container já configura `SESSION_COOKIE_SECURE=false` para acesso HTTP no ambiente de desenvolvimento. Para a implantação normal, continue usando `docker compose up -d --build --wait` no terminal do computador. Nenhum Python ou pip local é necessário.

## Integridade da exportação e remediação

O parser normaliza espaços e tabulações nos nomes das seções. Comandos não interpretados dentro dos blocos geram avisos com número de linha e seção, sem reproduzir seus valores; a lista mostra até 100 ocorrências. Nessas exportações, conclusões estáticas PASS/FAIL/N/A ficam como revisão manual e não geram comandos de correção. Exporte novamente com `show full-configuration` para concluir a auditoria.

API e JSON incluem `parse_warnings` e, por controle, `affected_objects` com `kind`, `name` e `scope`. Os modelos CLI usam esses objetos estruturados, sem extrair nomes do texto da evidência. Objetos com o mesmo nome em VDOMs distintos permanecem separados.

Erros de concorrência, limite de requisições, formulário e ausência/expiração de relatório aparecem na página; `/api/audit` preserva respostas JSON. As variáveis de implantação são validadas na inicialização: upload entre 1 e 50 MB, limite de requisições inteiro não negativo e credenciais de autenticação completas.

`web/app.py` cria instâncias independentes por `create_app`, `web/settings.py` carrega a configuração e `web/views.py` registra as rotas. Cada instância possui seu armazenamento e seus limites. O estágio Docker `dependencies` instala produção, `test_dependencies` acrescenta pytest e `browser_dependencies` instala Playwright/Chromium. Somente depois o código é copiado, permitindo reutilizar essas instalações em alterações de código.
