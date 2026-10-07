"""Security Fabric and automation checks."""
from .common import entries, value, outcome, settings_check


def evaluate(config, rid, options):
    if rid == "5.1.1":
        stitches = entries(config, "system automation-stitch")
        actions = {b.name: b for b in entries(config, "system automation-action")}
        triggers = {b.name: b for b in entries(config, "system automation-trigger")}
        for b in stitches:
            if value(b, "status", "disable") != "enable":
                continue
            trigger = triggers.get(b.get("trigger"))
            if trigger is None or not ("compromised" in trigger.name.lower() or value(trigger, "event-type") == "compromised-host"):
                continue
            refs = b.get_sub_block("actions")
            if refs and any(value(actions.get(e.get("action")), "action-type") in ("quarantine", "quarantine-forticlient") for e in refs.entries() if e.get("action") in actions):
                return outcome("PASS", "Automation stitch habilitado liga trigger de comprometimento a ação de quarentena.")
        return outcome("FAIL", "Quarentena de host comprometido não comprovada por trigger, stitch ativo e ação vinculada.") if config.get_blocks("system automation-stitch") else outcome("MANUAL_REVIEW", "Exportar configurações de automation trigger/action/stitch.")
    if rid == "5.2.1.1":
        check = settings_check(config, "system csf", {"status": "enable"}, {"status": "disable"})
        return outcome("MANUAL_REVIEW", "Fabric habilitado; validar papel Root, nome, FortiAnalyzer e interfaces autorizadas na GUI.") if check[0] == "PASS" else check
