import io
import pytest
from cis_benchmark.audit import audit_content
from cis_benchmark.reporting.html_report import HTMLReportGenerator
from web.app import create_app
from tests import FIXTURE_PATH
from web import session_store

FIXTURE = FIXTURE_PATH


def test_export_includes_escaped_cli():
    report = audit_content(FIXTURE.read_text().replace('set pre-login-banner enable', 'set pre-login-banner disable'))
    html = HTMLReportGenerator().generate(report)
    assert 'set admin-port &lt;PORTA_HTTP_NAO_PADRAO&gt;' in html
    assert 'set pre-login-banner enable' in html


def test_bounded_store_expiry_and_eviction():
    store = session_store.SessionStore(max_sessions=2)
    store.touch('first')
    store.touch('second')
    store.touch('third')
    assert 'first' not in store.sessions
    assert len(store.sessions) == 2
    store.expire(now=10**12)
    assert not store.sessions


def test_delete_audit_clears_report(app, audit_sessions):
    app.config['SESSION_COOKIE_SECURE'] = False
    client = app.test_client()
    client.post('/upload', data={'config_file': (io.BytesIO(FIXTURE.read_bytes()), 'sample.conf')})
    with client.session_transaction() as session:
        sid = session['sid']
        token = session['csrf_token']
    assert audit_sessions[sid]['report']
    assert client.post('/delete-audit', data={'csrf_token': 'wrong'}).status_code == 400
    assert client.post('/delete-audit', data={'csrf_token': token}).status_code == 302
    assert sid not in audit_sessions
    assert client.get('/download/json').status_code == 400


@pytest.mark.parametrize('authenticated', [False, True])
def test_delete_expired_audit_returns_home_and_preserves_other_sessions(app, authenticated):
    import base64
    from werkzeug.security import generate_password_hash
    headers = {}
    if authenticated:
        app.config.update(AUTH_USER='auditor', AUTH_PASSWORD_HASH=generate_password_hash('secret'))
        headers = {'Authorization': 'Basic ' + base64.b64encode(b'auditor:secret').decode()}
    client = app.test_client()
    client.get('/', headers=headers)
    with client.session_transaction() as session:
        sid, token = session['sid'], session['csrf_token']
    store = app.extensions['audit_store']
    report = audit_content(FIXTURE.read_text())
    store.save(sid, report, 'sample.conf', '')
    store.save('other-session', report, 'other.conf', '')
    store.sessions.pop(sid)
    response = client.post('/delete-audit', data={'csrf_token': token}, headers=headers, follow_redirects=True)
    assert response.status_code == 200
    assert 'Formulário expirado' not in response.get_data(as_text=True)
    assert store.sessions['other-session']['report'] is report
    assert client.post('/delete-audit', data={'csrf_token': token}, headers=headers).status_code == 302


def test_delete_with_cookie_from_previous_container_returns_home(app):
    old = create_app({'TESTING': True, 'SESSION_COOKIE_SECURE': False, 'SECRET_KEY': 'old-key'})
    client = old.test_client()
    client.post('/upload', data={'config_file': (io.BytesIO(FIXTURE.read_bytes()), 'sample.conf')})
    with client.session_transaction() as session:
        token = session['csrf_token']
    restarted = app.test_client()
    restarted.set_cookie('cis_sid', client.get_cookie('cis_sid').value)
    response = restarted.post('/delete-audit', data={'csrf_token': token}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Formulário expirado' not in response.get_data(as_text=True)


@pytest.mark.parametrize('authenticated', [False, True])
def test_invalid_delete_token_preserves_active_audit_and_shows_correct_action(app, authenticated):
    import base64
    from werkzeug.security import generate_password_hash
    headers = {}
    if authenticated:
        app.config.update(AUTH_USER='auditor', AUTH_PASSWORD_HASH=generate_password_hash('secret'))
        headers = {'Authorization': 'Basic ' + base64.b64encode(b'auditor:secret').decode()}
    client = app.test_client()
    client.get('/', headers=headers)
    with client.session_transaction() as session:
        sid = session['sid']
    store = app.extensions['audit_store']
    store.save(sid, audit_content(FIXTURE.read_text()), 'sample.conf', '')
    response = client.post('/delete-audit', data={'csrf_token': 'wrong'}, headers=headers)
    assert response.status_code == 400
    page = response.get_data(as_text=True)
    assert 'Não foi possível excluir a auditoria.' in page
    assert 'Não foi possível analisar o arquivo.' not in page
    assert store.sessions[sid]['report']


def test_processing_slot_returns_retry_response(app, processing_slot):
    processing_slot.acquire()
    try:
        response = app.test_client().post('/api/audit')
        assert response.status_code == 429
        assert response.headers['Retry-After']
    finally:
        processing_slot.release()


def test_binding_respects_vdom_and_quoted_names():
    from cis_benchmark.rules.cli_preview import bind_objects
    from cis_benchmark.config_parser import FortiGateConfigParser
    config = FortiGateConfigParser().parse_content('config vdom\nedit "branch"\nconfig firewall policy\nedit 2\nset action accept\nnext\nend\nnext\nend')
    script = bind_objects(config, '3.4', [{'kind': 'firewall policy', 'scope': 'vdom:branch', 'name': '2'}], 'config firewall policy\nedit <ID_POLITICA>\nset logtraffic all\nnext\nend')
    assert 'edit "branch"' in script and 'edit "2"' in script
    assert '<ID_POLITICA>' not in script


def test_optional_authentication(monkeypatch):
    from werkzeug.security import generate_password_hash
    import base64
    monkeypatch.setenv('AUTH_USER', 'auditor')
    monkeypatch.setenv('AUTH_PASSWORD_HASH', generate_password_hash('test-password'))
    client = create_app({'TESTING': True}).test_client()
    assert client.get('/').status_code == 401
    assert client.get('/health').status_code == 200
    auth = base64.b64encode(b'auditor:test-password').decode()
    assert client.get('/', headers={'Authorization': 'Basic ' + auth}).status_code == 200


def test_pdf_download_is_cached(app, monkeypatch):
    from web import views as module
    from cis_benchmark.reporting.export import ReportExport
    app.config['SESSION_COOKIE_SECURE'] = False
    client = app.test_client()
    client.post('/upload', data={'config_file': (io.BytesIO(FIXTURE.read_bytes()), 'sample.conf')})
    calls = []
    def export(*args):
        calls.append(args)
        return ReportExport(b'%PDF-test', 'application/pdf')
    monkeypatch.setattr(module, 'export_report', export)
    assert client.get('/download/pdf').data == b'%PDF-test'
    assert client.get('/download/pdf').data == b'%PDF-test'
    assert len(calls) == 1


def test_large_file_upload_is_not_rejected_as_text_field(app):
    app.config['SESSION_COOKIE_SECURE'] = False
    content = FIXTURE.read_bytes() + b'\n#' + b'x' * 200000
    response = app.test_client().post('/api/audit', data={
        'config_file': (io.BytesIO(content), 'large.conf'),
    })
    assert response.status_code == 200


def test_session_budget_rejects_oversized_report(monkeypatch):
    report = audit_content(FIXTURE.read_text())
    store = session_store.SessionStore(max_bytes=1)
    with pytest.raises(ValueError, match='limite de armazenamento'):
        store.save('oversized', report, 'test.conf', '')


def test_request_rate_is_bounded(monkeypatch):
    client = create_app({'TESTING': True, 'REQUESTS_PER_MINUTE': 1}).test_client()
    assert client.get('/').status_code == 200
    assert client.get('/').status_code == 429
    assert client.get('/health').status_code == 200


def test_partial_auth_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv('AUTH_USER', 'auditor')
    monkeypatch.delenv('AUTH_PASSWORD_HASH', raising=False)
    with pytest.raises(ValueError, match='juntos'):
        create_app({'TESTING': True})
