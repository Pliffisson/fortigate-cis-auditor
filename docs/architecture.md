# Arquitetura

## Pipeline

`CLI / upload web / API → audit → parser → benchmark → regras → pontuação → exportação`

`audit_file` e `audit_content` compartilham `audit_config`: o conteúdo é interpretado uma vez. `benchmark.py` centraliza metadados e catálogo, detecta a versão pelo cabeçalho anterior aos blocos e aceita somente FortiOS 7.4.x. `rules/catalog.json`, `rules/registry.py` e `rules/guidance.py` mantêm inventário, avaliações e orientações dos 64 controles.

O parser usa uma pilha de config/edit e preserva blocos aninhados, listas entre aspas, certificados multilinha e escopos global/VDOM. Perfis de políticas são resolvidos no mesmo VDOM. Exportações malformadas ou excessivamente aninhadas são rejeitadas.

## Resultados e saídas

Os estados são PASS, FAIL, MANUAL_REVIEW, NOT_APPLICABLE e ERROR. Somente PASS/FAIL entram na conformidade parcial. A cobertura considera os controles aplicáveis avaliados. Pendências impedem uma classificação de risco completa; severidades e pesos são convenções do projeto.

`reporting/export.py` compartilha a serialização entre CLI e downloads. PDF usa o relatório HTML, que escapa valores da configuração. Resultados carregam benchmark, versão, hash da fonte, página e classificação CIS original. A CLI reutiliza o HTML quando exporta HTML e PDF na mesma execução. Remediações contêm apenas comentários e nunca são executadas.

`web/views.py` compartilha validação e processamento dos uploads entre interface e API. A API é independente das sessões de navegador. CSS e JavaScript da interface estão em `web/static`; os relatórios HTML mantêm estilos embutidos para serem arquivos portáveis.

Veja [a análise da fonte](cis_74_analysis.md) para critérios, ambiguidades e limitações offline.

## Organização do código e dos testes

`rules/registry.py` registra os controles e despacha avaliações para `rules/checks`: sistema/HA, administração/SNMP, rede/políticas, perfis de segurança, Fabric, VPN e logging. `checks/common.py` concentra helpers de evidência e inventário; os critérios e os estados dos controles foram preservados.

O gerador HTML usa Jinja com escape automático e templates em `reporting/templates`. CSS e JavaScript ficam em `reporting/assets` e são incorporados à saída, preservando o relatório independente e a renderização do PDF. Templates e recursos são carregados uma vez por processo. Somente esses recursos locais confiáveis usam `safe`.

`tests/unit`, `tests/integration` e `tests/browser` separam os tipos de validação. `tests/conftest.py` fornece fixtures compartilhadas e uma aplicação independente por teste; caminhos de dados sintéticos ficam centralizados em `tests/__init__.py`. O smoke test continua em `tests/container_smoke.py`. A imagem de produção não cria diretórios de relatórios; a CLI cria seu diretório de saída conforme o argumento informado.

## Alinhamento ao CIS Controls

`controls/catalog.json` registra as 153 salvaguardas v8.1.2, grupos, ativo, função e páginas da fonte. `controls/mapping.json` mantém 16 relacionamentos candidatos, originados da análise do projeto, com justificativa e evidência complementar. `controls.build_alignment` valida IDs e versões, preserva cada resultado técnico e agrega por salvaguarda sem duplicidade. Nenhum PASS técnico gera atendimento organizacional.

`audit_config` adiciona o alinhamento ao relatório e referências a cada resultado. Os scores permanecem calculados antes desta etapa. Grupos IG são independentes dos níveis do benchmark; testes não incluídos na avaliação têm estado `NOT_SELECTED` no relacionamento. Falhas também são evidência técnica, enquanto resultados manuais, erros e N/A não entram como testes concluídos PASS/FAIL.

O template `reporting/templates/controls_alignment.html` e os assets `reporting/assets/controls-alignment.*` são compartilhados pela interface e exportação. Flask serve somente os dois assets permitidos, sob a CSP existente; o HTML exportado incorpora ambos e funciona sem requisições externas. PDF apresenta os relacionamentos abertos. Não existe armazenamento de revisão organizacional nesta etapa.

## Containers e execução

O estágio `dependencies` instala as dependências fixadas; `test_dependencies` e `browser_dependencies` acrescentam ferramentas antes da cópia do código. `runtime` copia somente a aplicação. `production` é o estágio final padrão. O estágio `tests` acrescenta pytest e a suíte, disponível pelo perfil Compose `test`. O fixture fictício entra somente na imagem de testes; backups e o PDF são excluídos do contexto.

Um worker Gunicorn com duas threads atende Flask. Relatórios e chave de sessão ficam em memória; reinícios descartam sessões. Mais workers ou réplicas exigem armazenamento compartilhado. Compose usa usuário UID 10001, sistema de arquivos somente leitura, tmpfs, remoção de capabilities, limites de recursos e healthcheck. A CLI monta entrada e saída explicitamente. Consulte o [README](../README.md) para comandos.

## Limites e remediações

`web/session_store.py` mantém o armazenamento limitado por quantidade de sessões e tamanho serializado de relatórios/PDFs, com expiração periódica. `web/views.py` admite somente uma operação pesada de cada vez e reutiliza o PDF por sessão. O orçamento serializado não mede todo o heap Python. A autenticação Basic é opcional e requer proxy HTTPS em implantação compartilhada; formulários autenticados usam CSRF.

`rules/cli_preview.py` preenche objetos explicitamente identificados na evidência com aspas e escopo VDOM. Um preview contém no máximo 32 objetos; parâmetros operacionais continuam explícitos. HTML/PDF, dashboard e JSON preservam os comandos e a orientação. O score ponderado permanece no JSON por compatibilidade, enquanto o dashboard apresenta cobertura.

## Instâncias e evidências

`create_app` em `web/app.py` valida as variáveis com `web/settings.py` antes de registrar as rotas em `web/views.py`. Cada instância tem SessionStore, semáforo e contadores próprios; testes não iniciam a limpeza periódica. A instância WSGI continua disponível em `web.app:app`.

As avaliações retornam objetos afetados estruturados (`kind`, `name`, `scope`) e os modelos CLI usam esses campos diretamente. Comandos desconhecidos dentro da configuração geram avisos com linha/seção, sem valores; exportações assim exigem revisão manual para conclusões estáticas. HTML, PDF, JSON, CLI e dashboard mostram os avisos. As seções são normalizadas para espaços e tabulações equivalentes.
