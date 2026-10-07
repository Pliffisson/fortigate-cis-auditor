# Adaptação ao CIS FortiGate 7.4.x v1.0.1

## Fonte e escopo

A referência é o PDF fornecido pelo usuário: `CIS_FortiGate_7.4.x_Benchmark_v1.0.1.pdf`.
A capa identifica v1.0.1 e imprime a data `01-07-2026`.
SHA-256: `639f91a8fb583246d4850d1d2a91c582057e7adb65db6ce9aff25c8dd523c723`.
A numeração de páginas desta análise é a impressa no documento; o catálogo
registra também a posição da página no arquivo PDF (impressa + 1).

A análise encontrou **64 recomendações**, sendo **39 Level 1 e 25 Level 2**.
A classificação original contém **48 Automated e 16 Manual**. Essa classificação
é preservada, mas Automated no CIS não significa que uma exportação offline
contenha todas as evidências necessárias ao procedimento.

O PDF permanece em `docs/reference` e é excluído da imagem. O auditor não depende
dele em runtime: usa o catálogo e os critérios implementados. Não há alegação
de certificação CIS, execução CIS-CAT, nem comprovação de conformidade integral
com base somente na porcentagem exibida.

## Diferenças em relação ao motor anterior

- O motor legado 7.0.x (56 IDs) foi removido; somente 7.4.x é suportado.
- 2.1.13, 2.3.3, 2.3.4, 2.5.4 e 4.2.7 são novos no catálogo implementado.
- Web Filtering ocupa 4.4.1; Application Control passa a 4.5.1–4.5.4.
- Logging é reorganizado em 7.2.1 e 7.3.1–7.3.3.
- A GUI administrativa exige somente TLS 1.3 (2.1.10).
- Password Policy exige pelo menos 14 caracteres e ambos os escopos (2.2.1).
- A conta admin deve ser removida conforme título/remediação de 2.4.1.
- O timeout administrativo admite até 15 minutos, não somente 10 (2.4.4).
- WAN não deve expor HTTPS, SSH ou PING, além dos serviços inseguros (1.3).
- Virtual patching precisa cobrir todas as local-in policies permissivas (2.4.8).

## Estados, pontuação e evidências

`PASS` comprova o critério estático implementado; `FAIL` identifica uma violação.
`MANUAL_REVIEW` requer contexto organizacional, diagnóstico ao vivo, validação
da GUI, inventário externo ou resolução de ambiguidades do documento.
`NOT_APPLICABLE` é usado quando há evidência de não aplicabilidade, como SSL VPN
explicitamente desabilitada. Ausência de uma seção não prova não aplicabilidade.
`ERROR` representa falha interna e não aprovação nem falha de configuração.

Conformidade parcial = PASS / (PASS + FAIL).
Cobertura = (PASS + FAIL) / (total - NOT_APPLICABLE).
Pendências e erros não contam como PASS. Quando há pendências, a classificação
de risco é `Incomplete`, inclusive se a porcentagem parcial chegar a 100%.
Severidades e pesos são convenções do projeto; o novo catálogo usa severidade
Medium uniforme até existir uma metodologia de risco revisada, sem atribuir
pesos oficiais ao CIS.

Defaults só são usados onde o PDF documenta o valor e a seção está presente.
Seções ausentes e valores sem default documentado exigem revisão. Recomenda-se
`show full-configuration` com o cabeçalho do backup. Nomes iguais de políticas e
perfis em VDOMs diferentes são mantidos separados. Inventário parcial de VDOMs
não pode resultar em aprovação dos controles de políticas.

Cada resultado inclui ID, título, nível, classificação Automated/Manual,
página, esperado, evidência e orientação. JSON, HTML, PDF, dashboard e CLI
identificam o benchmark efetivamente selecionado. `expected_timezone` na API/form
ou `--expected-timezone` na CLI permite comparar a configuração ao timezone
esperado, em vez de escolher uma localização arbitrária.

## Ambiguidades e limitações explícitas

| Controle | Observação | Decisão do auditor |
|---|---|---|
| 2.2.2, p.54 | Audit usa duration <=900; remediação usa 900. | Seguir literalmente o Audit: threshold 1–3 e duration 1–900; registrar a diferença. Não inventar um mínimo de 900. |
| 2.3.3, p.63 | Descrição condiciona a desativação a usuários que só recebem traps. | Verificar queries disable e manter a classificação CIS; exceções para usuários de consultas exigem avaliação operacional. |
| 2.3.4, p.65 | Texto usa freeable 35%, enquanto configuração e remediação usam 50%. | MANUAL_REVIEW; sem threshold arbitrário. |
| 2.4.1, p.68 | Título/remediação pedem remover admin; Audit ainda descreve tentativa de login com senha vazia. | Validar remoção conforme objetivo e remediação; não executar tentativas de login. |
| 6.1.2, p.158 | Audit contém ssl-max-prot-ver; remediação usa ssl-max-proto-ver. | Usar ssl-max-proto-ver, consistente com a remediação. |
| 7.3.2/7.3.3, p.170/172 | Títulos, critérios e remediações duplicados; seção indicada é log syslog setting. | Preservar ambos os IDs para rastreabilidade, marcar revisão; não criar dois PASS com o mesmo teste. |

NTP requer diagnóstico `diag sys ntp status`. HA precisa de evidência dos demais
membros. Certificado próprio referenciado não prova cadeia confiável. Syslog
configurado não prova recebimento. Privilégio mínimo depende da função do usuário.
WAN/Internet depende de topologia e rotas; a descoberta por role wan e zonas SD-WAN
é apenas uma aproximação e deve ser confirmada pelo analista.

O motor preserva recomendações GUI/manual sem traduzi-las para números de
categorias inventados: Web Filter, categorias Application Control, CDR e ISDB
ficam como revisão quando o PDF não oferece evidência suficiente para uma
verificação offline confiável. A classificação original permanece Automated ou
Manual conforme a fonte, independentemente do estado de avaliação offline.

Remediações CLI são previews comentados. Controles globais com valores explícitos
possuem comandos; modelos parametrizados para interfaces, contas, políticas e HA
exigem adaptação pelo analista. O modelo de troca de administrador exige testar o novo acesso antes da exclusão e não é
transformada em um comando automático de remoção.

## Catálogo e critérios

A tabela abaixo resume os critérios implementados, sem reproduzir o PDF completo.

| ID | Nível | CIS | Página | Critério resumido |
|---|---|---|---|---|
| 1.1 | L1 | Automated | 17 | DNS primário e secundário configurados; validar confiança dos servidores. |
| 1.2 | L1 | Manual | 19 | Todas as zonas com intrazone deny (default documentado: deny). |
| 1.3 | L1 | Manual | 21 | Nenhum serviço administrativo nas interfaces WAN, incluindo HTTPS, SSH e PING. |
| 2.1.1 | L1 | Automated | 25 | pre-login-banner enable. |
| 2.1.2 | L1 | Automated | 27 | post-login-banner enable. |
| 2.1.3 | L1 | Automated | 29 | Timezone compatível com a localização operacional. |
| 2.1.4 | L1 | Manual | 31 | NTP habilitado e synchronized: yes no diagnóstico ao vivo. |
| 2.1.5 | L1 | Automated | 34 | Hostname definido. |
| 2.1.6 | L2 | Manual | 36 | Firmware adequado ao modelo, atualizado e revisado contra PSIRT. |
| 2.1.7 | L2 | Automated | 39 | auto-install-config disable e auto-install-image disable. |
| 2.1.8 | L2 | Automated | 41 | ssl-static-key-ciphers disable. |
| 2.1.9 | L2 | Automated | 43 | strong-crypto enable. |
| 2.1.10 | L1 | Automated | 44 | admin-https-ssl-versions somente tlsv1-3. |
| 2.1.11 | L2 | Automated | 46 | gui-cdn-usage enable. |
| 2.1.12 | L1 | Automated | 47 | log-single-cpu-high enable. |
| 2.1.13 | L2 | Automated | 49 | gui-display-hostname disable. |
| 2.2.1 | L1 | Automated | 51 | Política habilitada, mínimo de 14 caracteres, escopo admin-password e ipsec-preshared-key. |
| 2.2.2 | L1 | Automated | 54 | Audit p.54: threshold <=3 e duration <=900; ambos positivos. Remediação usa 3/900. |
| 2.3.1 | L1 | Automated | 57 | Agente SNMP ativo, nenhuma comunidade v1/v2c, usuários v3 auth-priv. |
| 2.3.2 | L2 | Manual | 61 | notify-hosts específico para cada usuário SNMPv3, sem 0.0.0.0. |
| 2.3.3 | L2 | Automated | 63 | queries disable nos usuários destinados somente a traps. |
| 2.3.4 | L1 | Automated | 65 | Thresholds de memória SNMP revisados; texto 35% e exemplo 50% divergem. |
| 2.4.1 | L1 | Automated | 68 | Conta admin removida e outra conta administrativa existente; seguir título/remediação. |
| 2.4.2 | L1 | Manual | 71 | Todas as contas administrativas restritas a hosts/redes autorizados. |
| 2.4.3 | L1 | Manual | 74 | Perfis e permissões compatíveis com funções e privilégio mínimo. |
| 2.4.4 | L1 | Automated | 77 | Timeout administrativo positivo e <=15 minutos, inclusive overrides. |
| 2.4.5 | L1 | Automated | 79 | Nenhuma interface com HTTP ou Telnet em allowaccess. |
| 2.4.6 | L1 | Automated | 81 | Local-in policies ativas com cobertura e ordem adequadas. |
| 2.4.7 | L1 | Automated | 84 | Portas HTTP/HTTPS administrativas incomuns e admin-https-redirect disable. |
| 2.4.8 | L1 | Automated | 86 | virtual-patch enable em todas as local-in policies permissivas. |
| 2.5.1 | L2 | Automated | 89 | HA a-p/a-a, cluster name, senha e heartbeat; consistência entre membros. |
| 2.5.2 | L1 | Automated | 92 | Todas as interfaces críticas monitoradas no HA. |
| 2.5.3 | L1 | Automated | 94 | ha-mgmt-status enable; reserva com interface e gateway. |
| 2.5.4 | L2 | Automated | 96 | group-id não padrão, entre 1 e 1023. |
| 3.1 | L2 | Manual | 99 | Revisão periódica comprovada por histórico, necessidade de negócio e hit counters. |
| 3.2 | L1 | Automated | 101 | Nenhuma política permissiva ativa com serviço ALL. |
| 3.3 | L1 | Automated | 103 | Regras de bloqueio inbound/outbound dos ISDBs listados, habilitadas e com logging. |
| 3.4 | L1 | Automated | 105 | Logging de todas as sessões permitidas e violações negadas em políticas ativas. |
| 4.1.1 | L2 | Automated | 109 | IPS com scan-botnet-connections block aplicado às políticas de saída WAN. |
| 4.1.2 | L1 | Manual | 111 | IPS adequado aplicado às políticas permitidas com inspeção ativa. |
| 4.2.1 | L2 | Automated | 113 | Atualizações AV habilitadas com frequency automatic. |
| 4.2.2 | L2 | Manual | 115 | AV adequado aplicado às políticas permitidas com inspeção ativa. |
| 4.2.3 | L2 | Automated | 116 | outbreak-prevention block por protocolo nos perfis AV. |
| 4.2.4 | L2 | Automated | 118 | machine-learning-detection enable em antivirus settings. |
| 4.2.5 | L2 | Automated | 120 | grayware enable em antivirus settings. |
| 4.2.6 | L1 | Automated | 122 | Sandbox inline global habilitado, AV proxy/inline e fortisandbox block por protocolo. |
| 4.2.7 | L2 | Automated | 125 | CDR AV proxy com cobertura XLSB, OpenOffice e RTF. |
| 4.3.1 | L2 | Automated | 128 | Bloqueio botnet C&C DNS aplicado a todas as políticas que transportam DNS. |
| 4.3.2 | L1 | Automated | 130 | log-all-domain enable nos perfis DNS Filter. |
| 4.3.3 | L1 | Automated | 132 | DNS Filter aplicado às políticas de saída Internet com inspeção ativa. |
| 4.4.1 | L1 | Automated | 134 | Web Filter aplicado; Malicious Websites, Phishing e Spam URLs em Block. |
| 4.5.1 | L1 | Manual | 137 | Categorias P2P e Proxy em Block no Application Control. |
| 4.5.2 | L2 | Automated | 139 | enforce-default-app-port enable nos perfis Application Control. |
| 4.5.3 | L1 | Manual | 141 | Nenhuma categoria em Allow; tráfego permitido em Monitor, incluindo Unknown Applications. |
| 4.5.4 | L1 | Manual | 143 | Application Control adequado aplicado às políticas permitidas com inspeção ativa. |
| 5.1.1 | L1 | Automated | 147 | Stitch de host comprometido habilitado com trigger e ações de quarentena vinculadas. |
| 5.2.1.1 | L2 | Manual | 152 | Security Fabric Root, FortiAnalyzer, nome e interfaces de associação corretos. |
| 6.1.1 | L2 | Automated | 156 | SSL VPN usa certificado assinado por CA confiável, com cadeia e validade verificadas. |
| 6.1.2 | L2 | Automated | 158 | SSL VPN min tls1-2, max tls1-3 e algorithm high. |
| 7.1.1 | L2 | Automated | 162 | Todos os tipos de eventos habilitados. |
| 7.2.1 | L2 | Automated | 165 | Destino remoto de Syslog habilitado e recebimento confirmado. |
| 7.3.1 | L1 | Automated | 168 | FortiAnalyzer com transmissão ativa, reliable enable e enc-algorithm high. |
| 7.3.2 | L1 | Manual | 170 | Criptografia efetiva de Syslog; validar CLI indicada no PDF. |
| 7.3.3 | L1 | Manual | 172 | Duplicata textual de 7.3.2; requer revisão e esclarecimento. |
