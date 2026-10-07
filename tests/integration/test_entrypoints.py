"""Regression tests for shared entry points and commented remediation previews."""
import io
from dataclasses import replace

import pytest

from cis_benchmark.audit import audit_content
from cis_benchmark.cli import run_audit
from cis_benchmark.remediation import RemediationEngine
from tests import FIXTURE_PATH

FIXTURE = FIXTURE_PATH


def test_web_rejects_unsupported_version_and_renders_pending(app):
    client = app.test_client()
    raw = '#config-version=FG200F-7.4.8-FW-build1234-test\nconfig system global\nset hostname test\nend\n'
    response = client.post('/api/audit', data={'config_file': (io.BytesIO(raw.replace('7.4.8', '7.6.1').encode()), 'test.conf')})
    assert response.status_code == 400
    response = client.post('/upload', data={'config_file': (io.BytesIO(raw.encode()), 'test.conf')}, follow_redirects=True)
    assert response.status_code == 200
    assert b'MANUAL_REVIEW' in response.data
    assert b'7.4.x v1.0.1' in response.data


@pytest.mark.parametrize("endpoint", ["/upload", "/api/audit"])
@pytest.mark.parametrize("filename,content,level", [
    ("backup.txt", b"data", "all"),
    ("empty.conf", b"", "all"),
    ("backup.conf", FIXTURE.read_bytes(), "invalid"),
])
def test_upload_endpoints_share_validation(app, endpoint, filename, content, level):
    response = app.test_client().post(endpoint, data={
        "config_file": (io.BytesIO(content), filename), "level": level,
    })
    assert response.status_code == 400


def test_api_does_not_create_browser_report_sessions(app, audit_sessions):
    before = set(audit_sessions)
    response = app.test_client().post("/api/audit", data={
        "config_file": (io.BytesIO(FIXTURE.read_bytes()), "backup.conf"),
    })
    assert response.status_code == 200
    assert "Set-Cookie" not in response.headers
    assert set(audit_sessions) == before


def test_cli_invalid_format_creates_no_output(tmp_path):
    output = tmp_path / "reports"
    with pytest.raises(ValueError, match="Formatos"):
        run_audit(FIXTURE, output_dir=output, formats=["invalid"])
    assert not output.exists()


def test_remediation_metadata_and_commands_are_all_commented():
    report = audit_content(FIXTURE.read_text())
    failure = next(r for r in report.failed_results if r.remediation_cli)
    failure = replace(failure, actual_value="unsafe\nexecute reboot", category="system\nexecute reboot")
    pending = replace(failure, rule_id="pending-control", evaluation_status="MANUAL_REVIEW")
    script = RemediationEngine().generate_script([failure, pending])
    assert "execute reboot" in script
    assert all(not line or line.startswith("#") for line in script.splitlines())
    assert "pending-control" not in script


@pytest.mark.parametrize("content,message", [
    (b"", "O arquivo está vazio"),
    (b"not a FortiGate export", "Conteúdo não reconhecido"),
    (FIXTURE.read_bytes().replace(b"7.4.8", b"7.2.8"), "suportado: 7.4.x"),
])
def test_browser_displays_reason_for_rejected_upload(app, content, message):
    response = app.test_client().post("/upload", data={
        "config_file": (io.BytesIO(content), "backup.conf"),
    })
    assert response.status_code == 400
    assert b'role="alert"' in response.data
    assert message in response.get_data(as_text=True)


@pytest.mark.parametrize("endpoint", ["/upload", "/api/audit"])
def test_oversized_upload_has_clear_error(app, endpoint):
    previous = app.config["MAX_CONTENT_LENGTH"]
    try:
        app.config["MAX_CONTENT_LENGTH"] = 100
        response = app.test_client().post(endpoint, data={
            "config_file": (io.BytesIO(FIXTURE.read_bytes()), "backup.conf"),
        })
        assert response.status_code == 413
        assert "limite de upload" in response.get_data(as_text=True)
    finally:
        app.config["MAX_CONTENT_LENGTH"] = previous


@pytest.mark.parametrize('encoding', ['utf-8-sig', 'utf-16', 'utf-16-be', 'utf-32'])
def test_unicode_export_supported_by_browser_and_cli(app, encoding, tmp_path):
    from cis_benchmark.audit import audit_file
    text = FIXTURE.read_text().replace('sample', 'amostra')
    if encoding == 'utf-16-be':
        text = '\ufeff' + text
    content = text.encode(encoding)
    path = tmp_path / 'unicode.conf'
    path.write_bytes(content)
    report = audit_file(path)
    assert report.total_rules == 64 and report.error_rules == 0
    response = app.test_client().post('/upload', data={
        'config_file': (io.BytesIO(content), 'unicode.conf'),
    }, follow_redirects=True)
    assert response.status_code == 200
    assert '<dt class="label">Cobertura</dt>' in response.get_data(as_text=True)


def test_cli_capture_with_status_and_irregular_whitespace():
    raw = ('Version: FortiGate-200F v7.4.8,build1234\n'
           'config\tsystem   global\nset\thostname test\nend\n')
    report = audit_content(raw)
    assert report.fortios_version == '7.4.8'
    assert report.error_rules == 0


def test_parameterized_cli_is_visible_and_escaped_in_dashboard(app):
    app.config['SESSION_COOKIE_SECURE'] = False
    response = app.test_client().post('/upload', data={
        'config_file': (io.BytesIO(FIXTURE.read_bytes()), 'sample.conf'),
    }, follow_redirects=True)
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'set admin-port &lt;PORTA_HTTP_NAO_PADRAO&gt;' in page
    assert 'Substitua todos os parâmetros' in page
    assert '<PORTA_HTTP_NAO_PADRAO>' not in page
    report = audit_content(FIXTURE.read_text())
    preview = RemediationEngine().generate_script(report.failed_results)
    assert 'set admin-port <PORTA_HTTP_NAO_PADRAO>' in preview
    assert all(not line or line.startswith('#') for line in preview.splitlines())
