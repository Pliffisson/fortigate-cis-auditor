# Plano de integração do CIS Controls ao auditor

## Fonte e escopo

Documento analisado: [CIS Controls Guide v8.1.2](reference/CIS_Controls_Guide_v8.1.2_0325_v2.pdf), 146 páginas de PDF. A capa apresenta a família v8.1 e março de 2025; o sumário e as páginas internas identificam v8.1.2.

SHA-256: `e21b6d20098f3b0ed6391f95ac8f60fb7958a4b74389f96b456b37cd6ac878e4`.

**Implementado em 07/10/2026:** catálogo das 153 salvaguardas; 16 relacionamentos candidatos com evidências adicionais; referências nos testes; seção compartilhada na interface e nos relatórios HTML/PDF; JSON/API com metadados e alinhamento; filtros IG e busca. Relacionamentos continuam explicitamente propostos pelo projeto, com revisão organizacional pendente. As etapas de histórico/revisão autenticada e operação com IdP/MFA exigem uma implantação própria e permanecem planejadas.

O guia tem 18 controles e 153 salvaguardas. IG1 reúne 56 salvaguardas; IG2 inclui IG1 e totaliza 130; IG3 inclui todas as 153. Os grupos priorizam um programa organizacional conforme risco e recursos (páginas impressas 5–7; PDF 11–13). Level 1/Level 2 continuam sendo os perfis técnicos do benchmark FortiGate. Não existe equivalência automática entre Level 1 e IG1 ou entre Level 2 e IG2.

O projeto atual avalia 64 recomendações do CIS FortiGate 7.4.x v1.0.1. Um arquivo de configuração fornece evidências de um equipamento; não comprova inventário corporativo, processos, operação de SIEM, retenção real de logs, treinamento ou resposta a incidentes. A aprovação de uma recomendação técnica pode contribuir para uma salvaguarda sem demonstrar seu atendimento integral.

Este plano é uma proposta técnica do projeto, com referências ao guia. As relações abaixo são candidatas para revisão, não um mapeamento oficial CIS homologado.

## 1. Criar uma camada de referência independente

Adicionar `cis_benchmark/controls/catalog.json` para metadados de salvaguardas e `cis_benchmark/controls/mapping.json` para relacionamentos com as recomendações FortiGate. Registrar versão, hash e páginas da fonte. Manter `rules/catalog.json` e os critérios técnicos existentes.

Cada salvaguarda deve ter identificador, controle pai, grupos aplicáveis, tipo de ativo, função de segurança e referência da fonte. Cada relação deve informar benchmark e versão, ID da recomendação, ID da salvaguarda, justificativa, alcance da evidência, evidências adicionais exigidas, origem do relacionamento e situação de revisão.

Usar campos distintos: `benchmark_rule_id` e `safeguard_id`. Por exemplo, a recomendação FortiGate `4.2.1` não é a salvaguarda Controls `4.2`.

Validar as relações contra os dois catálogos e revisar os relacionamentos publicados no benchmark e em fontes CIS antes de apresentá-los como oficiais. Importar IDs não basta: a versão e o texto da salvaguarda precisam corresponder ao documento analisado.

## 2. Priorizar os relacionamentos pertinentes ao FortiGate

| Salvaguardas do guia | Evidência candidata no projeto | Complemento necessário | Referência impressa / PDF |
|---|---|---|---|
| 4.2: processo de configuração segura de rede | Conjunto dos testes e relatório de desvios | Procedimento aprovado, responsável, revisão anual ou após mudanças significativas | 29 / 35 |
| 4.6 e 12.3: administração segura | FortiGate 2.4.5, protocolos administrativos criptografados | Processo de administração e abrangência dos ativos | 30, 59 / 36, 65 |
| 4.7: contas padrão | FortiGate 2.4.1, remoção da conta padrão | Tratamento das contas padrão nos demais ativos | 30 / 36 |
| 4.9: DNS confiável | FortiGate 1.1, servidores DNS configurados | Lista de DNS autorizados; configuração isolada não comprova confiança | 31 / 37 |
| 8.2 e 8.5: logs habilitados e detalhados | FortiGate 3.4 e recomendações de logging | Recebimento real e conteúdo dos eventos | 44–45 / 50–51 |
| 8.4: sincronização de tempo | FortiGate 2.1.4, NTP | Duas fontes sincronizadas quando suportado; diagnóstico operacional | 44 / 50 |
| 8.6: logs DNS | FortiGate 4.3.2 | Eventos efetivamente coletados nos ativos pertinentes | 45 / 51 |
| 8.9: centralização de logs | Configuração de destinos syslog/FortiAnalyzer | Recebimento, cobertura e retenção centralizada | 45 / 51 |
| 12.2 e 13.4: arquitetura e filtragem entre segmentos | Políticas, interfaces, zonas e serviços | Diagrama, fluxos autorizados e revisão de privilégio mínimo | 59, 63 / 65, 69 |
| 13.8 e 13.10: prevenção de intrusão e filtragem de aplicação | FortiGate 4.1.2 e 4.5.4, perfis aplicados | Cobertura, licenciamento e operação dos mecanismos | 64 / 70 |

Evitar inferências por palavras semelhantes: um firewall de rede não comprova firewall instalado nos servidores (4.4) ou nos dispositivos dos usuários (4.5); antivírus no FortiGate não comprova cobertura antimalware dos endpoints.

## 3. Apresentar a contribuição aos Controls na interface e nos relatórios

Adicionar uma seção “Alinhamento ao CIS Controls v8.1.2”, com filtro IG1/IG2/IG3 independente do filtro Level 1/Level 2. O grupo deve ser uma escolha informada pela organização, não deduzido do modelo do firewall.

Em cada recomendação, mostrar as salvaguardas relacionadas, o alcance da verificação e o complemento necessário. Usar estados específicos para esta camada: evidência técnica disponível, revisão organizacional pendente, não avaliado pelo projeto e atendimento validado por revisor. Exceção aceita deve continuar visível como exceção; não converter em aprovação.

Preservar o score técnico atual. Não calcular conformidade organizacional copiando PASS/FAIL das regras FortiGate. Uma salvaguarda relacionada a várias regras deve aparecer uma vez na agregação. Relacionamentos sem avaliação não entram como salvaguardas atendidas. Mostrar quantidade total do grupo, salvaguardas com evidência e pendências separadamente; eventual score organizacional exige critérios próprios documentados.

Adicionar os metadados ao JSON de forma compatível com os consumidores existentes e reutilizar a informação nos templates do dashboard, HTML e PDF.

## 4. Acrescentar revisão manual e plano de ação

Para cada salvaguarda pertinente, registrar responsável, escopo, descrição ou referência da evidência, data da verificação, conclusão do revisor, pendências, prazo e justificativa de exceções. Uma resposta declarada sem evidência não deve receber atendimento validado.

Primeiras evidências manuais recomendadas:

- 4.2: procedimento de configuração segura de rede, revisado anualmente ou após mudanças relevantes.
- 6.5: MFA para contas administrativas quando suportado, com validação do fluxo real.
- 8.10: retenção de logs dos ativos por pelo menos 90 dias.
- 8.11: revisão de logs semanal ou mais frequente.
- 11.1–11.5: processo de recuperação, backups automatizados, proteção, isolamento e testes de recuperação.
- 12.1: revisão mensal ou mais frequente do suporte das versões da infraestrutura de rede.
- 13.1: alertas de segurança centralizados com correlação; armazenar logs no Loki, por si só, não demonstra atendimento.

Fora do escopo FortiGate, marcar explicitamente “não avaliado pelo projeto”. Reservar “não aplicável” para decisão de escopo justificada. Manter as recomendações CLI como previews que exigem parâmetros do ambiente; procedimentos organizacionais não têm correção automática por comandos CLI.

## 5. Aplicar o guia também à operação do auditor

Para uso compartilhado, planejar autenticação centralizada via Traefik/IdP com MFA e perfis de acesso; verificar a necessidade conforme o grupo e o escopo definidos. O HTTPS atual e o isolamento do container ajudam, mas não comprovam todas as salvaguardas de administração e acesso.

Criar eventos estruturados de acesso, análise, download e exclusão, sem conteúdo de configuração, comandos sensíveis ou segredos. Encaminhar os eventos ao coletor de logs existente, definir retenção, revisão e alertas. O prazo de 90 dias da salvaguarda 8.10 trata de logs, não exige armazenar backups FortiGate por 90 dias.

Atualmente as auditorias expiram e se perdem após reinício, e a aplicação afirma que não armazena configurações permanentemente. Se a revisão manual precisar de histórico, implementar armazenamento autenticado de resultados/evidências com política de retenção e exclusão antes de prometer persistência. Atualizar os textos de privacidade conforme o comportamento efetivo. Não persistir os arquivos `.conf` como consequência automática desta integração.

Dependências, aplicação e testes continuam executados em containers. A análise do PDF não precisa adicionar um leitor de PDF às dependências de produção: os metadados revisados podem ser mantidos em arquivos JSON versionados por versão da fonte.

## 6. Ordem recomendada e critérios de entrega

1. **Referência e mapeamento:** catálogo, relações revisadas, páginas, versão e hash; todos os IDs válidos e sem duplicatas.
2. **Visualização:** seção de alinhamento, grupos e exportação; nenhum filtro IG altera o score técnico ou é confundido com Level.
3. **Revisão e plano de ação:** evidências, responsáveis e prazos; confirmação humana rastreável e persistência somente com controles de acesso implementados.
4. **Operação:** autenticação/MFA, logs e alertas conforme escopo; testar tanto funcionamento quanto ausência de segredos nos eventos.

Executar os testes existentes no perfil Docker `test` e os testes de interface no perfil `browser`. Adicionar casos para relações de muitos para muitos, versão da fonte, agregação sem duplicidade, evidência incompleta, filtros IG e escape das anotações manuais. Nenhuma aprovação técnica pode promover automaticamente uma salvaguarda organizacional a atendida.

## Atribuição e publicação

A página 2 do PDF informa atribuição ao CIS, referência ao site dos Controls e licença CC BY-NC-ND 4.0, com condições próprias para uso comercial e redistribuição de conteúdo modificado. Preservar a fonte original e distinguir os metadados e análises do projeto do texto oficial ao disponibilizar a integração. Referências: https://www.cisecurity.org/controls/ e https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.
