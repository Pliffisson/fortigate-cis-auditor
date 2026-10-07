"""Administrative access and SNMP checks."""
from ...config_parser import cli_values
from .common import global_settings_check, settings_check, entries, all_entries, value, outcome, network_specific, check_admin_hosts, label, integer


def evaluate(config, rid, options):
    result = global_settings_check(config, rid)
    if result is not None:
        return result
    if rid == "2.3.1":
        check = settings_check(config, "system snmp sysinfo", {"status": "enable"}, {"status": "disable"})
        if check[0] != "PASS":
            return check
        if entries(config, "system snmp community"):
            return outcome("FAIL", "Existem comunidades SNMPv1/v2c.")
        if not config.get_blocks("system snmp community") or not config.get_blocks("system snmp user"):
            return outcome("MANUAL_REVIEW", "Exportar inventário completo de comunidades e usuários SNMP.")
        if not entries(config, "system snmp user"):
            return outcome("FAIL", "Nenhum usuário SNMPv3 configurado.")
        return all_entries(config, "system snmp user", lambda b: value(b, "security-level") == "auth-priv")
    if rid == "2.3.2":
        check = all_entries(config, "system snmp user", lambda b: bool(cli_values(b.get("notify-hosts", ""))) and all(network_specific(x) for x in cli_values(b.get("notify-hosts", ""))))
        return outcome("MANUAL_REVIEW", "notify-hosts específico; confirmar hosts autorizados.") if check[0] == "PASS" else check
    if rid == "2.3.3":
        return all_entries(config, "system snmp user", lambda b: value(b, "queries", "enable") == "disable")
    if rid == "2.3.4":
        return outcome("MANUAL_REVIEW", "PDF p.65 diverge: texto usa freeable 35%, exemplo/remediação 50%; validar thresholds e status SNMP com o responsável.")
    if rid == "2.4.1":
        admins = entries(config, "system admin")
        if not admins:
            return outcome("MANUAL_REVIEW", "Exportar todas as contas administrativas.")
        if any(b.name.lower() == "admin" for b in admins):
            return outcome("FAIL", "Conta padrão admin presente. Título/remediação do PDF exigem removê-la; teste de login descrito é insuficiente para provar remoção.")
        return outcome("PASS", "Conta admin ausente e contas com outros nomes presentes na exportação.")
    if rid == "2.4.2":
        return check_admin_hosts(config)
    if rid == "2.4.3":
        check = all_entries(config, "system admin", lambda b: bool(b.get("accprofile")))
        return outcome("MANUAL_REVIEW", "Comparar privilégios dos perfis com função de cada administrador; presença de accprofile não prova privilégio mínimo.") if check[0] in ("PASS", "NOT_APPLICABLE") else check
    if rid == "2.4.5":
        return all_entries(config, "system interface", lambda b: not ({"http", "telnet"} & set(cli_values(b.get("allowaccess", "")))))
    if rid in ("2.4.6", "2.4.8"):
        if not config.get_blocks("firewall local-in-policy"):
            return outcome("MANUAL_REVIEW", "Exportar local-in policies de todos os VDOMs.")
        policies = [b for b in entries(config, "firewall local-in-policy") if value(b, "status", "enable") != "disable"]
        if not policies:
            return outcome("FAIL", "Nenhuma local-in policy habilitada.")
        if rid == "2.4.6":
            return outcome("MANUAL_REVIEW", "Local-in policies encontradas; validar cobertura e ordem para tráfego destinado ao firewall.")
        accept = [b for b in policies if value(b, "action", "deny") == "accept"]
        if not accept:
            return outcome("NOT_APPLICABLE", "Nenhuma local-in policy ativa permitindo tráfego.")
        bad = [b for b in accept if value(b, "virtual-patch", "disable") != "enable"]
        return outcome("FAIL", "Virtual patch ausente: " + ", ".join(label(b) for b in bad), bad) if bad else outcome("PASS", "Virtual patch habilitado em todas as local-in policies permissivas identificadas.")
    if rid == "2.4.7":
        return settings_check(config, "system global", {"admin-port": lambda x: 1 <= integer(x) <= 65535 and integer(x) not in (80, 443, 8080, 8081, 4433, 10443), "admin-sport": lambda x: 1 <= integer(x) <= 65535 and integer(x) not in (80, 443, 8080, 8081, 4433, 10443), "admin-https-redirect": "disable"}, {"admin-port": "80", "admin-sport": "443", "admin-https-redirect": "enable"})
