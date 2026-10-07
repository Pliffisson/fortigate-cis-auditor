"""Shared report serialization for browser downloads and CLI files."""
import io
from dataclasses import dataclass
from .html_report import HTMLReportGenerator
from .json_report import JSONReportGenerator
from .pdf_report import PDFReportGenerator
from ..remediation import RemediationEngine

REPORT_FORMATS = ("html", "json", "pdf")


@dataclass(frozen=True)
class ReportExport:
    content: bytes
    mimetype: str


def export_report(report, format_type, config_file="", html_content=None):
    if format_type in ("html", "pdf"):
        html = html_content if html_content is not None else HTMLReportGenerator().generate(report, config_file)
        if format_type == "html":
            return ReportExport(html.encode("utf-8"), "text/html; charset=utf-8")
        buffer = io.BytesIO()
        PDFReportGenerator().generate(html, buffer)
        return ReportExport(buffer.getvalue(), "application/pdf")
    if format_type == "json":
        content = JSONReportGenerator().generate(report, config_file)
        return ReportExport(content.encode("utf-8"), "application/json")
    if format_type == "remediation":
        content = RemediationEngine().generate_script(report.failed_results)
        return ReportExport(content.encode("utf-8"), "text/plain; charset=utf-8")
    raise ValueError("Formato inválido; use html, json, pdf ou remediation.")
