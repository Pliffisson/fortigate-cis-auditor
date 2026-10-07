"""Render standalone HTML reports with embedded styles and scripts."""
import logging
from ..timezone import local_now
from functools import lru_cache
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

logger = logging.getLogger(__name__)
_RESOURCE_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def _report_resources():
    environment = Environment(
        loader=FileSystemLoader(_RESOURCE_DIR / 'templates'),
        autoescape=select_autoescape(('html',)), undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    return (environment.get_template('report.html'),
            (_RESOURCE_DIR / 'assets/report.css').read_text(encoding='utf-8') + '\n' +
            (_RESOURCE_DIR / 'assets/controls-alignment.css').read_text(encoding='utf-8'),
            (_RESOURCE_DIR / 'assets/report.js').read_text(encoding='utf-8') + '\n' +
            (_RESOURCE_DIR / 'assets/controls-alignment.js').read_text(encoding='utf-8'))


class HTMLReportGenerator:
    def generate(self, report, config_file: str = '', output_path: str = '') -> str:
        html = self._build_report(report, config_file)
        if output_path:
            Path(output_path).write_text(html, encoding='utf-8')
            logger.info('HTML report saved: %s', output_path)
        return html

    def _build_report(self, report, config_file: str) -> str:
        template, css, js = _report_resources()
        return template.render(
            report=report, config_file=config_file,
            timestamp=local_now().strftime('%Y-%m-%d %H:%M:%S'),
            pct_color=self._pct_color, gauge_color=self._pct_color(report.overall_percentage),
            l1_color=self._pct_color(report.level1_percentage),
            l2_color=self._pct_color(report.level2_percentage), report_css=css, report_js=js,
        )

    @staticmethod
    def _pct_color(pct: float) -> str:
        if pct >= 80:
            return '#10b981'
        if pct >= 60:
            return '#f59e0b'
        if pct >= 40:
            return '#f97316'
        return '#ef4444'
