"""Shared evidence helpers for offline checks."""
from dataclasses import dataclass
import ipaddress
from ...config_parser import cli_values

@dataclass(frozen=True)
class Evaluation:
    status: str
    message: str
    affected_objects: tuple = ()

    def __iter__(self):
        return iter((self.status, self.message))

    def __getitem__(self, index):
        return (self.status, self.message)[index]


def outcome(status, message, objects=()):
    targets = tuple({'kind': b.block_type, 'name': b.name, 'scope': b.scope} for b in objects)
    return Evaluation(status, message, targets)


def entries(config, kind):
    return [e for b in config.get_blocks(kind) for e in b.entries()]


def label(block):
    return f"{block.scope}/{block.name or block.block_type}"


def value(block, key, default=""):
    return block.get(key, default).lower()


def integer(text):
    try:
        return int(text)
    except (ValueError, TypeError):
        return -1


def settings_check(config, kind, requirements, defaults=None):
    blocks = config.get_blocks(kind)
    if not blocks:
        return outcome("MANUAL_REVIEW", f"Seção {kind} ausente; exporte show full-configuration.")
    defaults = defaults or {}
    bad, unknown, observed, bad_blocks = [], [], [], []
    for b in blocks:
        for key, expected in requirements.items():
            if not b.has(key) and key not in defaults:
                unknown.append(f"{label(b)}: {key}")
                continue
            actual = b.get(key, defaults.get(key, ""))
            observed.append(f"{label(b)}: {key}={actual or 'vazio'}")
            ok = expected(actual) if callable(expected) else actual.lower() == expected
            if not ok:
                bad.append(f"{label(b)}: {key}={actual or 'ausente'}")
                if b not in bad_blocks:
                    bad_blocks.append(b)
    if bad:
        return outcome("FAIL", "; ".join(bad), bad_blocks)
    if unknown:
        return outcome("MANUAL_REVIEW", "Valores ausentes sem default documentado: " + ", ".join(unknown))
    return outcome("PASS", "; ".join(observed))


def all_entries(config, kind, predicate):
    if not config.get_blocks(kind):
        return outcome("MANUAL_REVIEW", f"Seção {kind} não fornecida.")
    objects = entries(config, kind)
    if not objects:
        return outcome("NOT_APPLICABLE", f"Nenhuma entrada em {kind}.")
    bad = [b for b in objects if not predicate(b)]
    return outcome("FAIL", "Entradas fora do critério: " + ", ".join(label(b) for b in bad), bad) if bad else outcome("PASS", f"{len(objects)} entradas atendem ao critério estático.")


def allowed(config):
    return [b for b in entries(config, "firewall policy")
            if value(b, "status", "enable") != "disable" and value(b, "action", "deny") == "accept"]


def policy_inventory(config):
    if not config.get_blocks("firewall policy"):
        return outcome("MANUAL_REVIEW", "Inventário de políticas não fornecido.")
    missing = [v for v in config.vdom_names if not any(b.scope == f"vdom:{v}" for b in config.get_blocks("firewall policy"))]
    if missing:
        return outcome("MANUAL_REVIEW", "Exportação não inclui políticas de todos os VDOMs: " + ", ".join(missing))
    return None


def profile_for(config, policy, kind, name):
    return next((b for b in entries(config, kind)
                 if b.name == name and b.scope == policy.scope), None)


def profile_policies(config, field, kind, predicate=None, internet=False, manual=False):
    problem = policy_inventory(config)
    if problem:
        return problem
    policies = allowed(config)
    if internet:
        wan = {b.name for b in entries(config, "system interface") if value(b, "role") == "wan"}
        # Actual SD-WAN zone names, rather than assuming every zone is virtual-wan-link.
        for parent in config.get_blocks("system sdwan"):
            zones = parent.get_sub_block("zone")
            if zones:
                wan.update(b.name for b in zones.entries())
        wan.add("virtual-wan-link")
        policies = [b for b in policies if wan.intersection(cli_values(b.get("dstintf", "")))]
        if not policies:
            return outcome("MANUAL_REVIEW", "Nenhuma política de Internet identificada; confirmar WAN, zonas e rotas.")
    if not policies:
        return outcome("NOT_APPLICABLE", "Nenhuma política ativa com action accept no inventário fornecido.")
    bad, missing_profiles = [], []
    for b in policies:
        name = b.get(field)
        if not name or value(b, "utm-status", "disable") != "enable":
            bad.append(b)
            continue
        profile = profile_for(config, b, kind, name)
        if profile is None:
            missing_profiles.append(label(b))
        elif predicate and not predicate(profile):
            bad.append(b)
    if bad:
        return outcome("FAIL", "Políticas sem inspeção efetiva ou perfil fora do critério: " + ", ".join(label(b) for b in bad), bad)
    if missing_profiles:
        return outcome("MANUAL_REVIEW", "Perfis referenciados não estão na exportação: " + ", ".join(missing_profiles))
    if manual:
        return outcome("MANUAL_REVIEW", "Perfis atribuídos e UTM habilitado; validar adequação da inspeção ao tráfego.")
    if internet:
        return outcome("MANUAL_REVIEW", "Políticas WAN identificadas atendem ao critério estático; confirmar cobertura de todas as saídas Internet, zonas e rotas.")
    return outcome("PASS", f"{len(policies)} políticas identificadas atendem ao critério estático.")


def network_specific(text):
    tokens = cli_values(text)
    try:
        net = ipaddress.ip_network('/'.join(tokens) if len(tokens) == 2 else tokens[0], strict=False)
        return net.prefixlen > 0 and not net.network_address.is_unspecified
    except (ValueError, IndexError):
        return False


def check_admin_hosts(config):
    admins = entries(config, "system admin")
    if not admins:
        return outcome("MANUAL_REVIEW", "Inventário administrativo ausente ou vazio.")
    bad = []
    for b in admins:
        hosts = [v for k, v in b.settings.items() if k.startswith("trusthost") or k.startswith("ip6-trusthost")]
        # Default wildcard slots may accompany specific hosts in full exports.
        specific = [v for v in hosts if network_specific(v)]
        if not specific:
            bad.append(b)
    if bad:
        return outcome("FAIL", "Contas sem redes específicas: " + ", ".join(label(b) for b in bad), bad)
    return outcome("MANUAL_REVIEW", "Restrições específicas encontradas; confirmar que as redes são autorizadas para administração.")


def ha_check(config, rid):
    blocks = config.get_blocks("system ha")
    if not blocks:
        return outcome("MANUAL_REVIEW", "Seção system ha ausente.")
    active = [b for b in blocks if value(b, "mode", "standalone") in ("a-p", "a-a")]
    if not active:
        return outcome("FAIL" if rid == "2.5.1" else "NOT_APPLICABLE", "HA não está em modo a-p/a-a.")
    if rid == "2.5.1":
        if any(not all(b.get(k) for k in ("group-name", "password", "hbdev")) for b in active):
            return outcome("FAIL", "HA sem cluster name, credencial ou interfaces de heartbeat.")
        return outcome("MANUAL_REVIEW", "HA configurado; validar correspondência de parâmetros e sincronização entre membros.")
    if rid == "2.5.2":
        if any(not b.get("monitor") for b in active):
            return outcome("FAIL", "HA sem interfaces monitoradas.")
        return outcome("MANUAL_REVIEW", "Interfaces monitoradas configuradas; confirmar cobertura de todas as interfaces críticas.")
    if rid == "2.5.3":
        for b in active:
            mgmt = b.get_sub_block("ha-mgmt-interfaces")
            if value(b, "ha-mgmt-status", "disable") != "enable" or not mgmt or not any(e.get("interface") and network_specific(e.get("gateway")) for e in mgmt.entries()):
                return outcome("FAIL", "Reserva de gerenciamento requer status enable, interface e gateway.")
        return outcome("PASS", "Reserva de gerenciamento com interface e gateway configurados.")
    return settings_check(config, "system ha", {"group-id": lambda x: 1 <= integer(x) <= 1023})


def check_profiles(config, kind, predicate):
    return all_entries(config, kind, predicate)


def protocol_options(profile, key, expected):
    protocols = [b for b in profile.sub_blocks if not b.is_edit and b.block_type in
                 ("http", "ftp", "imap", "pop3", "smtp", "mapi", "nntp", "cifs", "ssh")]
    return bool(protocols) and all(value(b, key) == expected for b in protocols)


def global_settings_check(config, rid):
    global_checks = {
        "2.1.1": ("pre-login-banner", "enable", "disable"),
        "2.1.2": ("post-login-banner", "enable", "disable"),
        "2.1.8": ("ssl-static-key-ciphers", "disable", "enable"),
        "2.1.9": ("strong-crypto", "enable", "enable"),
        "2.1.10": ("admin-https-ssl-versions", lambda x: set(cli_values(x)) == {"tlsv1-3"}, "tlsv1-2 tlsv1-3"),
        "2.1.11": ("gui-cdn-usage", "enable", "enable"),
        "2.1.12": ("log-single-cpu-high", "enable", "disable"),
        "2.1.13": ("gui-display-hostname", "disable", "disable"),
        "2.4.4": ("admintimeout", lambda x: 1 <= integer(x) <= 15, "5"),
    }
    if rid in global_checks:
        k, wanted, default = global_checks[rid]
        result = settings_check(config, "system global", {k: wanted}, {k: default})
        if rid == "2.4.4" and result[0] == "PASS":
            overrides = [b for b in entries(config, "system accprofile") if value(b, "admintimeout-override", "disable") == "enable" and not 1 <= integer(b.get("admintimeout")) <= 15]
            if overrides:
                return outcome("FAIL", "Perfil administrativo sobrepõe timeout com valor superior a 15 ou inválido.")
        return result
    return None
