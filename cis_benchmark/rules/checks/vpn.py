"""SSL VPN certificate and protocol checks."""
from .common import value, outcome, settings_check


def evaluate(config, rid, options):
    if rid in ("6.1.1", "6.1.2"):
        blocks = config.get_blocks("vpn ssl settings")
        if not blocks:
            return outcome("MANUAL_REVIEW", "Seção SSL VPN ausente; confirmar aplicabilidade.")
        if all(value(b, "status", "enable") == "disable" for b in blocks):
            return outcome("NOT_APPLICABLE", "SSL VPN explicitamente desabilitada.")
        if rid == "6.1.1":
            if any(not b.get("servercert") or b.get("servercert").lower().startswith(("fortinet", "self")) for b in blocks if value(b, "status", "enable") != "disable"):
                return outcome("FAIL", "SSL VPN sem certificado próprio ou com certificado de fábrica/autossinado identificado.")
            return outcome("MANUAL_REVIEW", "Certificado próprio referenciado; validar cadeia, CA confiável, validade e vínculo ao portal.")
        return settings_check(config, "vpn ssl settings", {"ssl-min-proto-ver": "tls1-2", "ssl-max-proto-ver": "tls1-3", "algorithm": "high"}, {"ssl-min-proto-ver": "tls1-2", "ssl-max-proto-ver": "tls1-3", "algorithm": "high"})
