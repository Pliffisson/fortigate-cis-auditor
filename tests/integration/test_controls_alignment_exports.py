import io
from cis_benchmark.audit import audit_content
from cis_benchmark.reporting.export import export_report
from tests import FIXTURE_PATH


def test_controls_alignment_in_dashboard_api_html_and_json(app):
    client = app.test_client()
    response = client.post('/upload', data={'config_file': (io.BytesIO(FIXTURE_PATH.read_bytes()), 'sample.conf')}, follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Alinhamento ao CIS Controls v8.1.2' in html
    assert 'Revisão organizacional pendente' in html
    assert 'data-ig-filter' in html
    assert '137 não avaliadas pelo projeto' in html
    for kind in ('html', 'json'):
        response = client.get(f'/download/{kind}')
        assert response.status_code == 200
        if kind == 'html':
            assert 'CIS Controls v8.1.2' in response.get_data(as_text=True)
            assert 'data-safeguard-search' in response.get_data(as_text=True)
        else:
            data = response.json
            assert len(data['compliance']['controls_alignment']['safeguards']) == 153
            assert 'controls_safeguards' in data['compliance']['results'][0]
    response = client.post('/api/audit', data={'config_file': (io.BytesIO(FIXTURE_PATH.read_bytes()), 'sample.conf')})
    assert response.json['controls_alignment']['groups']['IG1']['total_safeguards'] == 56


def test_relationships_are_escaped_in_both_renderers(app):
    report = audit_content(FIXTURE_PATH.read_text())
    report.controls_alignment['safeguards'][0]['title'] = '<script>alert(1)</script>'
    exported = export_report(report, 'html').content.decode()
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in exported
    assert '<script>alert(1)</script>' not in exported
    with app.test_request_context('/'):
        from flask import render_template
        html = render_template('controls_alignment.html', alignment=report.controls_alignment)
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html


def test_alignment_assets_are_available_and_restricted(app):
    client = app.test_client()
    assert client.get('/assets/controls-alignment/controls-alignment.js').status_code == 200
    assert client.get('/assets/controls-alignment/controls-alignment.css').status_code == 200
    assert client.get('/assets/controls-alignment/report.js').status_code == 404
