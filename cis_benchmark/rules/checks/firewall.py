"""Network interfaces and firewall policy checks."""
from ...config_parser import cli_values
from .common import settings_check, network_specific, all_entries, value, entries, outcome, label, policy_inventory, allowed


def evaluate(config, rid, options):
    if rid == "1.1":
        return settings_check(config, "system dns", {"primary": network_specific, "secondary": network_specific}, {"primary": "96.45.45.45", "secondary": "96.45.46.46"})
    if rid == "1.2":
        return all_entries(config, "system zone", lambda b: value(b, "intrazone", "deny") == "deny")
    if rid == "1.3":
        interfaces = entries(config, "system interface")
        wan = [b for b in interfaces if value(b, "role") == "wan"]
        bad = [b for b in wan if set(cli_values(b.get("allowaccess", ""))) & {"https", "http", "ping", "ssh", "snmp", "radius-acct", "telnet", "fgfm"}]
        return outcome("FAIL", "Acesso administrativo em WAN: " + ", ".join(label(b) for b in bad), bad) if bad else outcome("MANUAL_REVIEW", "Confirmar todas as interfaces WAN pela topologia; sem violações nas interfaces role wan identificadas.")
    if rid == "3.1":
        return outcome("MANUAL_REVIEW", "Requer histórico de revisão, finalidade de negócio e hit counters; backup não comprova revisão periódica.")
    if rid == "3.2":
        problem = policy_inventory(config)
        if problem:
            return problem
        bad = [b for b in allowed(config) if "ALL" in {x.upper() for x in cli_values(b.get("service", "ALL"))}]
        if bad:
            return outcome("FAIL", "Políticas permissivas com serviço ALL: " + ", ".join(label(b) for b in bad), bad)
        return outcome("PASS", "Nenhuma política permissiva ativa utiliza serviço ALL.")
    if rid == "3.3":
        return outcome("MANUAL_REVIEW", "Verificar ISDBs de origem/destino, cobertura, ordem e logging das regras de bloqueio; IDs numéricos requerem catálogo ISDB do dispositivo.")
    if rid == "3.4":
        problem = policy_inventory(config)
        if problem:
            return problem
        return all_entries(config, "firewall policy", lambda b: value(b, "status", "enable") == "disable" or value(b, "logtraffic", "disable") == "all")
