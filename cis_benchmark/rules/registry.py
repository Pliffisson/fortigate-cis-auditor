"""Benchmark rule registration and dispatch to domain evaluators."""
import json
from .base import CISRule, CISLevel, RuleSeverity
from .guidance import EXPECTED, CLI, CLI_TEMPLATES
from .cli_preview import bind_objects
from .checks import system, administration, firewall, security_profiles, fabric, vpn, logging
from .checks.common import outcome
from ..benchmark import NAME as BENCHMARK, CATALOG


def evaluate(config, rid, options):
    domain = {'1': firewall, '2': system, '3': firewall, '4': security_profiles,
              '5': fabric, '6': vpn, '7': logging}.get(rid.split('.')[0])
    if rid.startswith(('2.3.', '2.4.')):
        domain = administration
    result = domain.evaluate(config, rid, options) if domain else None
    return result if result is not None else outcome(
        'MANUAL_REVIEW', 'Critério exige evidência adicional; consultar página indicada.')


class PDFRule(CISRule):
    def __init__(self, item, options=None):
        self.item = item
        self.options = options or {}
        super().__init__(rule_id=item['rule_id'], title=item['title'], level=CISLevel(item['level']),
                         severity=RuleSeverity.MEDIUM, description=f"Avaliação offline baseada no PDF, página {item['source_page']}.",
                         expected_value=EXPECTED[item['rule_id']],
                         remediation="Revisar o procedimento do PDF e adaptar a remediação ao ambiente; não aplicar exemplos literalmente.",
                         category={"1": "Network", "2": "System", "3": "Policies", "4": "Security Profiles", "5": "Security Fabric", "6": "VPN", "7": "Logging"}[item['rule_id'][0]],
                         cis_section=item['rule_id'], references=[f"{BENCHMARK}, p. {item['source_page']} (PDF {item['pdf_page']})"])

    def evaluate(self, config):
        try:
            evaluation = evaluate(config, self.rule_id, self.options)
            status, message = evaluation
            if config.parse_warnings and status in ('PASS', 'FAIL', 'NOT_APPLICABLE'):
                status, message = 'MANUAL_REVIEW', 'Exportação contém comandos não interpretados; exporte show full-configuration antes de concluir este controle. '
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Evaluation error for %s", self.rule_id)
            evaluation = None
            status, message = "ERROR", "Erro interno ao avaliar controle; verificar log técnico."
        result = self._make_result(status == "PASS", message)
        result.affected_objects = list(getattr(evaluation, 'affected_objects', ()))
        result.evaluation_status = status
        result.assessment = self.item['assessment']
        result.source_page = self.item['source_page']
        if status == "FAIL" and self.rule_id in CLI:
            kind, commands = CLI[self.rule_id]
            scripts = []
            for block in config.get_blocks(kind):
                script = f"config {kind}\n{commands}\nend"
                if block.scope.startswith("vdom:"):
                    name = json.dumps(block.scope.split(':', 1)[1], ensure_ascii=False)
                    script = f"config vdom\nedit {name}\n{script}\nnext\nend"
                elif config.vdom_names:
                    script = f"config global\n{script}\nend"
                if script not in scripts:
                    scripts.append(script)
            result.remediation_cli = '\n'.join(scripts)
            if self.rule_id == "2.4.4" and "Perfil administrativo" in message:
                result.remediation_cli = ""
        if status in ("MANUAL_REVIEW", "ERROR"):
            result.remediation = "Coletar evidência adicional e revisar o critério: " + self.expected_value
        if status == "FAIL" and self.rule_id in CLI_TEMPLATES:
            guidance, template = CLI_TEMPLATES[self.rule_id]
            template = bind_objects(config, self.rule_id, result.affected_objects, template)
            result.remediation = guidance + " Substitua todos os parâmetros entre <...>; use o escopo global/VDOM indicado na evidência."
            result.remediation_cli = "# MODELO: substitua os parâmetros <...> e confirme o escopo antes de aplicar.\n" + template
        return result


def get_all_rules(options=None):
    return [PDFRule(item, options) for item in CATALOG]
