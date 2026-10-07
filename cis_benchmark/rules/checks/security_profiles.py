"""Security profile assignment and inspection checks."""
from .common import profile_policies, settings_check, check_profiles, protocol_options, outcome, value


def evaluate(config, rid, options):
    if rid == "4.1.1":
        return profile_policies(config, "ips-sensor", "ips sensor", lambda b: value(b, "scan-botnet-connections", "disable") == "block", internet=True)
    if rid in ("4.1.2", "4.2.2", "4.5.4"):
        field, kind = {"4.1.2": ("ips-sensor", "ips sensor"), "4.2.2": ("av-profile", "antivirus profile"), "4.5.4": ("application-list", "application list")}[rid]
        return profile_policies(config, field, kind, manual=True)
    if rid == "4.2.1":
        return settings_check(config, "system autoupdate schedule", {"status": "enable", "frequency": "automatic"}, {"status": "enable", "frequency": "automatic"})
    if rid in ("4.2.4", "4.2.5"):
        key = "machine-learning-detection" if rid == "4.2.4" else "grayware"
        return settings_check(config, "antivirus settings", {key: "enable"}, {key: "enable"})
    if rid == "4.2.3":
        return check_profiles(config, "antivirus profile", lambda b: protocol_options(b, "outbreak-prevention", "block"))
    if rid == "4.2.6":
        check = settings_check(config, "system fortiguard", {"sandbox-inline-scan": "enable"}, {"sandbox-inline-scan": "disable"})
        if check[0] != "PASS":
            return check
        return profile_policies(config, "av-profile", "antivirus profile", lambda b: value(b, "feature-set") == "proxy" and value(b, "fortisandbox-mode") == "inline" and protocol_options(b, "fortisandbox", "block"))
    if rid == "4.2.7":
        return outcome("MANUAL_REVIEW", "Validar CDR em AV proxy e cobertura de XLSB, OpenOffice e RTF na GUI; não inferir suporte só pela existência do perfil.")
    if rid == "4.3.1":
        return outcome("MANUAL_REVIEW", "Identificar todas as políticas que transportam DNS e validar o bloqueio de domínios botnet no perfil aplicado.")
    if rid == "4.3.2":
        return check_profiles(config, "dnsfilter profile", lambda b: value(b, "log-all-domain", "disable") == "enable")
    if rid == "4.3.3":
        return profile_policies(config, "dnsfilter-profile", "dnsfilter profile", internet=True)
    if rid == "4.4.1":
        return outcome("MANUAL_REVIEW", "Validar categorias Malicious Websites, Phishing e Spam URLs em Block e perfil aplicado; requer identificação das categorias FortiGuard.")
    if rid == "4.5.1":
        return outcome("MANUAL_REVIEW", "Confirmar categorias P2P e Proxy bloqueadas em cada Application Control relevante; não confundir com Web Filtering 4.4.1.")
    if rid == "4.5.2":
        return check_profiles(config, "application list", lambda b: value(b, "enforce-default-app-port", "disable") == "enable")
    if rid == "4.5.3":
        return outcome("MANUAL_REVIEW", "Validar categorias e Unknown Applications sem ação Allow; usar Monitor para registrar tráfego permitido.")
