"""Event and remote logging checks."""
from .common import label, outcome, value, settings_check


def evaluate(config, rid, options):
    if rid == "7.1.1":
        blocks = config.get_blocks("log eventfilter")
        if not blocks:
            return outcome("MANUAL_REVIEW", "Exportar log eventfilter.")
        bad = [label(b) + ": " + k for b in blocks for k, v in b.settings.items() if v == "disable"]
        return outcome("FAIL", "Eventos desabilitados: " + ", ".join(bad)) if bad else outcome("PASS", "Nenhum tipo de evento desabilitado; defaults habilitados conforme PDF.")
    if rid == "7.2.1":
        blocks = [b for kind in ("log syslogd setting", "log syslogd2 setting", "log syslogd3 setting", "log syslogd4 setting") for b in config.get_blocks(kind)]
        if not blocks:
            return outcome("MANUAL_REVIEW", "Exportar settings dos destinos Syslog.")
        if not any(value(b, "status", "disable") == "enable" and b.get("server") for b in blocks):
            return outcome("FAIL", "Nenhum servidor Syslog ativo configurado.")
        return outcome("MANUAL_REVIEW", "Servidor Syslog configurado; confirmar recebimento efetivo no destino.")
    if rid == "7.3.1":
        return settings_check(config, "log fortianalyzer setting", {"status": "enable", "reliable": "enable", "enc-algorithm": "high"}, {"status": "disable", "reliable": "disable"})
    if rid in ("7.3.2", "7.3.3"):
        return outcome("MANUAL_REVIEW", "PDF duplica 7.3.2/7.3.3 e usa config log syslog setting; validar CLI 7.4.x e criptografia efetiva de cada destino, sem contar duas aprovações automáticas.")
