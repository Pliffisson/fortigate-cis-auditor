"""Shared audit pipeline for CLI, browser uploads and API."""
from .config_parser import FortiGateConfigParser
from .benchmark import select_benchmark, SOURCE_DOCUMENT, SOURCE_SHA256
from .rules import get_all_rules
from .scoring import ComplianceScorer
from .controls import build_alignment


def audit_content(content, level="all", expected_timezone=None):
    return audit_config(FortiGateConfigParser().parse_content(content), level, expected_timezone)


def audit_file(filepath, level="all", expected_timezone=None):
    return audit_config(FortiGateConfigParser().parse_file(filepath), level, expected_timezone)


def audit_config(config, level="all", expected_timezone=None):
    if level not in ("1", "2", "all"):
        raise ValueError("Nível inválido; use 1, 2 ou all.")
    parser = FortiGateConfigParser()
    content = config.raw_content
    if not content.strip() or not parser.validate_config(content):
        raise ValueError("Conteúdo não reconhecido como exportação FortiGate; use show full-configuration com cabeçalho de versão.")
    selection = select_benchmark(content)
    if not selection.supported:
        raise ValueError(selection.message)
    family = '.'.join(selection.fortios_version.split('.')[:2])
    rules = get_all_rules(family, options={"expected_timezone": expected_timezone})
    if level != "all":
        rules = [r for r in rules if r.level.value == int(level)]
    report = ComplianceScorer().calculate([rule.evaluate(config) for rule in rules])
    report.parse_warnings = config.parse_warnings
    report.benchmark = selection.benchmark
    report.fortios_version = selection.fortios_version
    report.source_document = SOURCE_DOCUMENT
    report.source_sha256 = SOURCE_SHA256
    report.controls_alignment = build_alignment(report.results)
    for result in report.results:
        result.controls_safeguards = [
            {'safeguard_id': safeguard['id'], 'title': safeguard['title'],
             'implementation_groups': safeguard['implementation_groups'],
             'source_page': safeguard['source_page'], 'pdf_page': safeguard['pdf_page'],
             'additional_evidence': safeguard['additional_evidence']}
            for safeguard in report.controls_alignment['safeguards']
            if any(ref['benchmark_rule_id'] == result.rule_id for ref in safeguard['benchmark_references'])
        ]
    return report
