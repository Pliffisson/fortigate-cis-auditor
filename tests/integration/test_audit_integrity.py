"""Behavioral regressions for formatting, scoped evidence and isolated apps."""
import io
import pytest
from cis_benchmark.audit import audit_content
from cis_benchmark.config_parser import FortiGateConfigParser
from web.app import create_app
from tests import FIXTURE_PATH

HEADER = '#config-version=FG200F-7.4.8-FW-build1-test\n'
FIXTURE = FIXTURE_PATH


@pytest.mark.parametrize('spacing', [' ', '   ', '\t', ' \t '])
def test_spacing_does_not_change_audit_outcome(spacing):
    raw = HEADER + 'config system global\nset hostname test\nset pre-login-banner disable\nend\n'
    variant = raw.replace('config system global', f'config{spacing}system{spacing}global')
    baseline = audit_content(raw)
    report = audit_content(variant)
    assert [(r.rule_id, r.status) for r in report.results] == [(r.rule_id, r.status) for r in baseline.results]
    assert report.to_dict()['summary'] == baseline.to_dict()['summary']


def test_unknown_commands_are_visible_and_prevent_false_approval():
    raw = HEADER + 'config system global\nset hostname test\nset pre-login-banner enable\nappend unexpected data\nend\n'
    report = audit_content(raw)
    assert report.parse_warnings
    assert report.to_dict()['parse_warnings']
    assert next(r for r in report.results if r.rule_id == '2.1.1').status == 'MANUAL_REVIEW'
    assert report.error_rules == 0


def test_same_policy_id_only_remediates_failed_vdom():
    def vdom(name, service):
        return f'edit "{name}"\nconfig firewall policy\nedit 2\nset action accept\nset service {service}\nnext\nend\nnext\n'
    raw = HEADER + 'config vdom\n' + vdom('branch-a', 'ALL') + vdom('branch-b', 'HTTPS') + 'end\n'
    result = next(r for r in audit_content(raw).results if r.rule_id == '3.2')
    assert result.status == 'FAIL'
    assert result.affected_objects == [{'kind': 'firewall policy', 'name': '2', 'scope': 'vdom:branch-a'}]
    assert 'edit "branch-a"' in result.remediation_cli
    assert 'branch-b' not in result.remediation_cli
    assert '<ID_POLITICA>' not in result.remediation_cli


def test_evidence_text_cannot_select_unaffected_object():
    from cis_benchmark.rules.cli_preview import bind_objects
    config = FortiGateConfigParser().parse_content('config firewall policy\nedit 2\nnext\nedit 20\nnext\nend')
    template = 'config firewall policy\nedit <ID_POLITICA>\nset logtraffic all\nnext\nend'
    script = bind_objects(config, '3.4', [{'kind': 'firewall policy', 'name': '2', 'scope': 'global'}], template)
    assert 'edit "2"' in script and 'edit "20"' not in script


@pytest.mark.parametrize('key,value', [('MAX_UPLOAD_MB', 'abc'), ('MAX_UPLOAD_MB', 0), ('MAX_UPLOAD_MB', 51), ('REQUESTS_PER_MINUTE', -1), ('SESSION_COOKIE_SECURE', 'maybe'), ('AUTH_PASSWORD_HASH', 'plaintext')])
def test_invalid_settings_fail_before_serving(key, value):
    config = {'TESTING': True, key: value}
    if key == 'AUTH_PASSWORD_HASH':
        config['AUTH_USER'] = 'auditor'
    with pytest.raises(ValueError, match=key):
        create_app(config)


def test_factories_do_not_share_reports_or_limits():
    first = create_app({'TESTING': True, 'SESSION_COOKIE_SECURE': False})
    second = create_app({'TESTING': True, 'SESSION_COOKIE_SECURE': False})
    a, b = first.test_client(), second.test_client()
    response = a.post('/upload', data={'config_file': (io.BytesIO(FIXTURE.read_bytes()), 'sample.conf')})
    assert response.status_code == 302
    assert first.extensions['audit_store'].sessions
    assert not second.extensions['audit_store'].sessions
    assert b.get('/download/json').status_code == 400
    assert first.extensions['processing_slot'] is not second.extensions['processing_slot']


def test_busy_browser_sees_alert_and_api_stays_json():
    app = create_app({'TESTING': True})
    slot = app.extensions['processing_slot']
    slot.acquire()
    try:
        browser = app.test_client().post('/upload')
        assert browser.status_code == 429
        assert 'role="alert"' in browser.get_data(as_text=True)
        assert browser.headers['Retry-After'] == '3'
        api = app.test_client().post('/api/audit')
        assert api.status_code == 429 and api.json['error']
    finally:
        slot.release()


def test_rate_limit_and_expired_report_have_html_feedback():
    app = create_app({'TESTING': True, 'REQUESTS_PER_MINUTE': 1})
    client = app.test_client()
    assert client.get('/').status_code == 200
    response = client.get('/')
    assert response.status_code == 429 and b'role="alert"' in response.data
    app = create_app({'TESTING': True, 'REQUESTS_PER_MINUTE': 0})
    response = app.test_client().get('/download/pdf')
    assert response.status_code == 400
    assert 'sessão pode ter expirado' in response.get_data(as_text=True)


def test_disabled_event_is_failure_not_engine_error():
    report = audit_content(HEADER + 'config system global\nset hostname test\nend\nconfig log eventfilter\nset system disable\nend\n')
    result = next(r for r in report.results if r.rule_id == '7.1.1')
    assert result.status == 'FAIL'


def test_parser_diagnostics_do_not_expose_unknown_command_values():
    report = audit_content(HEADER + 'config system global\nset hostname test\nunknown-command SECRET_VALUE\nend\n')
    assert report.parse_warnings
    assert 'SECRET_VALUE' not in str(report.parse_warnings)


def test_policy_names_with_spaces_are_bound_as_one_cli_identifier():
    from cis_benchmark.rules.cli_preview import bind_objects
    config = FortiGateConfigParser().parse_content('config system interface\nedit "wan east"\nset role wan\nset allowaccess https\nnext\nend')
    targets = [{'kind': 'system interface', 'name': 'wan east', 'scope': 'global'}]
    script = bind_objects(config, '1.3', targets, 'config system interface\nedit "<INTERFACE_WAN>"\nunset allowaccess\nnext\nend')
    assert 'edit "wan east"' in script
    assert '<INTERFACE_WAN>' not in script


def test_oversized_authenticated_form_has_visible_error():
    import base64
    from werkzeug.security import generate_password_hash
    app = create_app({'TESTING': True, 'SESSION_COOKIE_SECURE': False, 'AUTH_USER': 'user',
                      'AUTH_PASSWORD_HASH': generate_password_hash('secret')})
    app.config['MAX_CONTENT_LENGTH'] = 100
    client = app.test_client()
    auth = {'Authorization': 'Basic ' + base64.b64encode(b'user:secret').decode()}
    client.get('/', headers=auth)
    response = client.post('/upload', headers=auth, data={'config_file': (io.BytesIO(FIXTURE.read_bytes()), 'sample.conf')})
    assert response.status_code == 413
    assert b'role="alert"' in response.data
    assert 'limite de upload' in response.get_data(as_text=True)
