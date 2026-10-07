"""System configuration and high availability checks."""
from ...config_parser import cli_values
from .common import global_settings_check, settings_check, ha_check, outcome, integer


def evaluate(config, rid, options):
    result = global_settings_check(config, rid)
    if result is not None:
        return result
    if rid == "2.1.3":
        timezone = options.get("expected_timezone")
        if timezone is None:
            return outcome("MANUAL_REVIEW", "Validar timezone com a localização; informe expected_timezone para comparar.")
        return settings_check(config, "system global", {"timezone": str(timezone)})
    if rid == "2.1.4":
        check = settings_check(config, "system ntp", {"ntpsync": "enable"})
        return outcome("MANUAL_REVIEW", "NTP habilitado; coletar diag sys ntp status e confirmar synchronized: yes.") if check[0] == "PASS" else check
    if rid == "2.1.5":
        return settings_check(config, "system global", {"hostname": lambda x: bool(x.strip())})
    if rid == "2.1.6":
        return outcome("MANUAL_REVIEW", "Verificar versão suportada, PSIRT e caminho de atualização para o modelo.")
    if rid == "2.1.7":
        return settings_check(config, "system auto-install", {"auto-install-config": "disable", "auto-install-image": "disable"}, {"auto-install-config": "enable", "auto-install-image": "enable"})
    if rid == "2.2.1":
        return settings_check(config, "system password-policy", {"status": "enable", "minimum-length": lambda x: integer(x) >= 14, "apply-to": lambda x: {"admin-password", "ipsec-preshared-key"} <= set(cli_values(x))}, {"status": "disable"})
    if rid == "2.2.2":
        check = settings_check(config, "system global", {"admin-lockout-threshold": lambda x: 1 <= integer(x) <= 3, "admin-lockout-duration": lambda x: 1 <= integer(x) <= 900}, {"admin-lockout-threshold": "3", "admin-lockout-duration": "60"})
        return check[0], check[1] + " PDF p.54 especifica duration <=900; a remediação usa 900."
    if rid.startswith("2.5."):
        return ha_check(config, rid)
