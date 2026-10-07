"""CLI entry point for the current benchmark and shared report pipeline."""
import argparse
import logging
from .timezone import local_now
from pathlib import Path
from .audit import audit_file
from .reporting.export import REPORT_FORMATS, export_report
from .reporting.html_report import HTMLReportGenerator


def run_audit(config_path, level="all", output_dir="reports", formats=None,
              generate_remediation=True, expected_timezone=None):
    formats = list(dict.fromkeys(formats if formats is not None else ("html", "json")))
    if not formats or any(kind not in REPORT_FORMATS for kind in formats):
        raise ValueError("Formatos inválidos; use html,json,pdf.")
    report = audit_file(config_path, level, expected_timezone)
    print(report.benchmark)
    for warning in report.parse_warnings:
        print(f'Aviso: {warning}')
    print(f"Conformidade parcial: {report.overall_percentage}% ({report.passed_rules}/{report.evaluated_rules} avaliados)")
    print(f"Cobertura: {report.coverage_percentage}% de {report.total_rules} controles")
    print(f"PASS: {report.passed_rules} | FAIL: {report.failed_rules} | Revisão manual: {report.manual_review_rules} | N/A: {report.not_applicable_rules} | Erros: {report.error_rules}")
    print(f"Classificação: {report.risk_rating}")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    timestamp = local_now().strftime("%Y%m%d_%H%M%S_%f")
    stem = Path(config_path).stem
    html = HTMLReportGenerator().generate(report, str(config_path)) if {"html", "pdf"}.intersection(formats) else None
    for kind in formats:
        artifact = export_report(report, kind, str(config_path), html_content=html)
        path = output / f"CIS_Audit_{stem}_{timestamp}.{kind}"
        path.write_bytes(artifact.content)
        print(f"{kind.upper()}: {path}")
    if generate_remediation and report.failed_results:
        path = output / f"Remediation_{stem}_{timestamp}.txt"
        path.write_bytes(export_report(report, "remediation", str(config_path)).content)
        print(f"Remediação (preview): {path}")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Auditoria offline CIS FortiGate 7.4.x")
    parser.add_argument("config_file", help="Exportação FortiGate com cabeçalho de versão")
    parser.add_argument("--format", default="html,json", help="html,json,pdf")
    parser.add_argument("--level", default="all", choices=("1", "2", "all"))
    parser.add_argument("--expected-timezone", help="ID FortiOS do timezone esperado")
    parser.add_argument("--output-dir", default="reports")
    parser.add_argument("--no-remediation", action="store_true", help="Não gerar preview de remediação")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        run_audit(args.config_file, args.level, args.output_dir,
                  [kind.strip() for kind in args.format.split(',')],
                  not args.no_remediation, args.expected_timezone)
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, f"Erro: {error}\n")


if __name__ == "__main__":
    main()
