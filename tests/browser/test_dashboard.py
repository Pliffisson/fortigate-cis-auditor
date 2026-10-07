"""Real Chromium checks, enabled in the dedicated browser image."""
import os
import threading
from tests import FIXTURE_PATH
import pytest

pytestmark = pytest.mark.skipif(os.environ.get('BROWSER_TESTS') != '1', reason='Use the browser Compose profile')


def test_browser_upload_layout_errors_and_cli(app):
    from playwright.sync_api import sync_playwright, expect
    from werkzeug.serving import make_server
    app.config['SESSION_COOKIE_SECURE'] = False
    server = make_server('127.0.0.1', 8765, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=['--disable-dev-shm-usage'])
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            page.goto('http://127.0.0.1:8765')
            page.evaluate('document.fonts.ready')
            assert page.evaluate('document.fonts.check(\'14px "JetBrains Mono"\')')
            assert 'JetBrains Mono' in page.locator('body').evaluate('node => getComputedStyle(node).fontFamily')
            assert page.locator('body').evaluate('node => getComputedStyle(node).backgroundColor') == 'rgb(16, 20, 18)'
            page.locator('.branding-menu > summary').click()
            page.set_input_files('#logo-file', {'name': 'bad.svg', 'mimeType': 'image/svg+xml', 'buffer': b'<svg></svg>'})
            expect(page.locator('#logo-status')).to_contain_text('PNG, JPG ou WebP')
            page.set_input_files('#logo-file', {'name': 'bad.png', 'mimeType': 'image/png', 'buffer': b'invalid'})
            expect(page.locator('#logo-status')).to_contain_text('Não foi possível abrir')
            import base64
            raster = page.evaluate("() => { const c = document.createElement('canvas'); c.width = 160; c.height = 60; c.getContext('2d').fillRect(0, 0, 160, 60); return c.toDataURL('image/png').split(',')[1]; }")
            page.set_input_files('#logo-file', {'name': 'company.png', 'mimeType': 'image/png', 'buffer': base64.b64decode(raster)})
            expect(page.locator('#company-logo')).to_be_visible()
            expect(page.locator('#logo-status')).to_contain_text('Logo atualizada')
            assert page.locator('#default-brand-icon').is_hidden()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.reload()
            expect(page.locator('#company-logo')).to_be_visible()
            page.locator('.branding-menu > summary').click()
            page.locator('#remove-logo').click()
            expect(page.locator('#company-logo')).to_be_hidden()
            expect(page.locator('#default-brand-icon')).to_be_visible()
            page.reload()
            expect(page.locator('#company-logo')).to_be_hidden()
            screenshot_dir = os.environ.get('SCREENSHOT_DIR')
            if screenshot_dir:
                page.screenshot(path=f'{screenshot_dir}/initial-mobile.png')
                page.set_viewport_size({'width': 1440, 'height': 1000})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path=f'{screenshot_dir}/initial-desktop.png')
                page.set_viewport_size({'width': 390, 'height': 844})
            field = page.locator('#expected-timezone')
            assert not field.is_visible()
            page.locator('.advanced-options > summary').click()
            assert field.is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not page.locator('.export-cli').is_visible()
            guide = page.locator('.export-guide')
            guide.locator('summary').click()
            assert guide.locator('pre code').is_visible()
            page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: {writeText: async text => {window.guideCopied = text;}}, configurable: true})")
            guide.locator('.copy-cli').click()
            expect(guide.locator('.copy-status')).to_have_text('Comandos copiados.')
            assert 'show full-configuration' in page.evaluate('window.guideCopied')
            guide.locator('summary').click()
            assert page.locator('select[name=level]').input_value() == 'all'
            page.set_input_files('#config-file', {'name': 'invalid.txt', 'mimeType': 'text/plain', 'buffer': b'invalid'})
            assert 'Formato inválido' in page.get_by_role('alert').inner_text()
            assert page.locator('#selected-file-name').inner_text() == 'invalid.txt'
            assert page.locator('#selected-file-size').inner_text()
            assert page.locator('#replace-file').is_visible()
            assert page.locator('#config-file').evaluate('input => !input.checkValidity()')
            page.set_input_files('#config-file', {'name': 'empty.conf', 'mimeType': 'text/plain', 'buffer': b''})
            assert 'arquivo está vazio' in page.get_by_role('alert').inner_text()
            limit = page.locator('#config-file').get_attribute('data-max-bytes')
            page.locator('#config-file').evaluate("input => input.dataset.maxBytes = '2'")
            page.set_input_files('#config-file', {'name': 'large.conf', 'mimeType': 'text/plain', 'buffer': b'invalid'})
            assert 'excede o limite' in page.get_by_role('alert').inner_text()
            page.locator('#config-file').evaluate('(input, limit) => input.dataset.maxBytes = limit', limit)
            page.set_input_files('#config-file', {'name': 'invalid.conf', 'mimeType': 'text/plain', 'buffer': b'invalid'})
            assert page.locator('#file-error').is_hidden()
            page.locator('.upload .analyze').click()
            assert page.get_by_role('alert').is_visible()
            page.set_input_files('#config-file', str(FIXTURE_PATH))
            page.locator('.upload .analyze').click()
            page.wait_for_selector('.remediation-cli', state='attached')
            assert 'config ' in ' '.join(page.locator('.remediation-cli').all_text_contents())
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            panel = page.locator('#failures')
            assert page.locator('.audit-file').inner_text() == 'Arquivo: sample.conf'
            alignment = page.locator('#controls-alignment')
            score = page.locator('.primary-score .value').inner_text()
            alignment.locator('.alignment-details > summary').click()
            assert alignment.locator('[data-safeguard]:visible').count() == 16
            alignment.locator('[data-show-unmapped]').check()
            assert alignment.locator('[data-safeguard]:visible').count() == 153
            alignment.locator('[data-ig-filter]').select_option('IG1')
            assert alignment.locator('[data-safeguard]:visible').count() == 56
            alignment.locator('[data-safeguard-search]').fill('13.8')
            assert alignment.locator('[data-safeguard]:visible').count() == 0
            assert alignment.locator('[data-alignment-empty]').is_visible()
            alignment.locator('[data-ig-filter]').select_option('IG3')
            assert alignment.locator('[data-safeguard]:visible').count() == 1
            assert 'Revisão organizacional pendente' in alignment.locator('[data-safeguard]:visible').inner_text()
            assert page.locator('.primary-score .value').inner_text() == score
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            alignment.locator('[data-safeguard-search]').fill('')
            alignment.locator('[data-ig-filter]').select_option('')
            alignment.locator('[data-show-unmapped]').uncheck()
            alignment.locator('.alignment-details > summary').click()
            navigation = page.get_by_role('navigation', name='Seções da auditoria')
            navigation.get_by_role('link', name='Falhas', exact=True).click()
            expect(navigation.get_by_role('link', name='Falhas', exact=True)).to_have_attribute('aria-current', 'location')
            navigation.get_by_role('link', name='Todos os controles', exact=True).click()
            expect(navigation.get_by_role('link', name='Todos os controles', exact=True)).to_have_attribute('aria-current', 'location')
            for status, label in [('PASS', '✓ Aprovado'), ('FAIL', '✕ Falha'), ('MANUAL_REVIEW', '◷ Revisão manual')]:
                text = page.locator(f'#all-controls [data-status="{status}"] td[data-label="Status"]').first.inner_text()
                assert ' '.join(text.split()) == label
            navigation.get_by_role('link', name='Resumo', exact=True).click()
            expect(navigation.get_by_role('link', name='Resumo', exact=True)).to_have_attribute('aria-current', 'location')
            total = panel.locator('[data-control-row]').count()
            assert total > 0
            first = panel.locator('[data-control-row]').first
            category = first.get_attribute('data-category')
            level = first.get_attribute('data-level')
            title = first.locator('.control-name').inner_text()
            panel.locator('[data-search]').fill(title)
            panel.locator('select[data-category]').select_option(category)
            panel.locator('select[data-level]').select_option(level)
            assert panel.locator('[data-control-row]:visible').count() == 1
            panel.locator('select[data-level]').select_option('2' if level == '1' else '1')
            assert panel.locator('[data-filter-empty]').is_visible()
            panel.get_by_role('button', name='Limpar filtros').click()
            assert panel.locator('[data-control-row]:visible').count() == total
            details = panel.locator('.cli-details').first
            assert not details.locator('pre').is_visible()
            details.locator('summary').click()
            expected_cli = details.locator('code').inner_text()
            for secure in (True, False):
                page.evaluate('''secure => {
                    window.copiedCommands = '';
                    Object.defineProperty(window, 'isSecureContext', {value: secure, configurable: true});
                    Object.defineProperty(navigator, 'clipboard', {value: {writeText: async text => {window.copiedCommands = text;}}, configurable: true});
                    document.execCommand = command => {window.copiedCommands = document.querySelector('textarea[readonly]').value; return command === 'copy';};
                }''', secure)
                details.locator('.copy-cli').click()
                assert details.get_by_role('status').inner_text() == 'Comandos copiados.'
                assert details.locator('.copy-cli').inner_text() == '✓ Copiado'
                assert page.evaluate('window.copiedCommands') == expected_cli
            all_panel = page.locator('#all-controls')
            all_panel.locator('select[data-status]').select_option('FAIL')
            assert all_panel.locator('[data-control-row]:visible').count() == total
            all_panel.locator('[data-search]').fill('no-such-control')
            assert all_panel.locator('[data-filter-empty]').is_visible()
            all_panel.get_by_role('button', name='Limpar filtros').click()
            assert all_panel.locator('[data-control-row]:visible').count() == 64
            # Sorting and filters survive reload, but are scoped to this audit.
            all_panel.locator('[data-sort]').select_option('level')
            levels = all_panel.locator('[data-control-row]').evaluate_all('rows => rows.map(row => Number(row.dataset.level))')
            assert levels == sorted(levels)
            all_panel.locator('select[data-status]').select_option('FAIL')
            page.reload()
            assert all_panel.locator('[data-sort]').input_value() == 'level'
            assert all_panel.locator('select[data-status]').input_value() == 'FAIL'
            assert all_panel.locator('[data-control-row]:visible').count() == total
            row_details = all_panel.locator('[data-control-row]:visible .control-details').first
            row_details.locator('summary').click()
            assert row_details.locator('dl').is_visible()
            assert 'Critério esperado' in row_details.inner_text()
            assert 'Referência CIS' in row_details.inner_text()
            assert all_panel.locator('select[data-status]').input_value() == 'FAIL'
            page.locator('[data-status-shortcut="MANUAL_REVIEW"]').click()
            assert all_panel.locator('select[data-status]').input_value() == 'MANUAL_REVIEW'
            assert all_panel.locator('[data-control-row]:visible').count() > 0
            page.locator('[data-status-shortcut="FAIL"]').click()
            assert all_panel.locator('[data-control-row]:visible').count() == total
            page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
            page.emulate_media(media='print')
            assert not page.locator('.assessment-actions').is_visible()
            assert not navigation.is_visible()
            assert all_panel.locator('[data-control-row]:visible').count() > 0
            assert all_panel.locator('[data-control-row]:visible').evaluate_all("rows => rows.every(row => ['MANUAL_REVIEW', 'ERROR'].includes(row.dataset.status))")
            assert panel.locator('[data-control-row]:visible').count() == total
            page.emulate_media(media='screen')
            page.evaluate("window.dispatchEvent(new Event('afterprint'))")
            assert all_panel.locator('select[data-status]').input_value() == 'FAIL'
            assert all_panel.locator('[data-control-row]:visible').count() == total
            all_panel.get_by_role('button', name='Limpar filtros').click()
            page.locator('.export-menu summary').click()
            assert page.locator('.export-options a').count() == 4
            assert page.locator('.export-options').is_visible()
            page.locator('.export-menu summary').click()
            page.locator('.methodology summary').click()
            assert page.locator('.compliance-legend').is_visible()
            page.locator('.methodology summary').click()
            screenshot_dir = os.environ.get('SCREENSHOT_DIR')
            if screenshot_dir:
                page.locator('.audit-summary').scroll_into_view_if_needed()
                page.screenshot(path=f'{screenshot_dir}/mobile.png')
            page.set_viewport_size({'width': 1440, 'height': 1000})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert panel.locator('th').first.evaluate("element => getComputedStyle(element).position") == 'sticky'
            if screenshot_dir:
                page.locator('.audit-summary').scroll_into_view_if_needed()
                page.screenshot(path=f'{screenshot_dir}/desktop.png')
            page.get_by_role('button', name='Excluir minha auditoria').click()
            page.wait_for_selector('.upload')
            assert page.locator('.remediation-cli').count() == 0
            response = page.goto('http://127.0.0.1:8765/download/json')
            assert response.status == 400
            assert page.get_by_role('alert').is_visible()
            assert 'sessão pode ter expirado' in page.get_by_role('alert').inner_text()
            app.config['REQUESTS_PER_MINUTE'] = 1
            page.goto('http://127.0.0.1:8765')
            response = page.goto('http://127.0.0.1:8765')
            assert response.status == 429
            assert 'Limite de requisições' in page.get_by_role('alert').inner_text()
            app.config['REQUESTS_PER_MINUTE'] = 0
            page.goto('http://127.0.0.1:8765')
            page.set_input_files('#config-file', str(FIXTURE_PATH))
            page.locator('.upload .analyze').click()
            page.wait_for_selector('.remediation-cli', state='attached')
            # The page remains open while its report expires on the server.
            app.extensions['audit_store'].sessions.clear()
            page.get_by_role('button', name='Excluir minha auditoria').click()
            page.wait_for_selector('.upload')
            assert page.get_by_role('alert').count() == 0
            assert page.locator('.remediation-cli').count() == 0
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_exported_report_works_without_external_resources():
    from playwright.sync_api import sync_playwright
    from cis_benchmark.audit import audit_content
    from cis_benchmark.reporting.html_report import HTMLReportGenerator

    report = audit_content(FIXTURE_PATH.read_text())
    report.results[0].title = '</td><script>window.reportInjected = true</script>'
    html = HTMLReportGenerator().generate(report)
    requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=['--disable-dev-shm-usage'])
        page = browser.new_page()
        page.route('**/*', lambda route: (requests.append(route.request.url), route.abort()))
        page.set_content(html)
        assert page.locator('#allControlsTable tbody tr').count() == 64
        assert page.evaluate('getComputedStyle(document.body).backgroundColor') == 'rgb(10, 14, 23)'
        assert page.evaluate('window.reportInjected === undefined')
        alignment = page.locator('#controls-alignment')
        assert alignment.locator('[data-safeguard]:visible').count() == 16
        alignment.locator('[data-show-unmapped]').check()
        alignment.locator('[data-ig-filter]').select_option('IG2')
        assert alignment.locator('[data-safeguard]:visible').count() == 130
        page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
        assert alignment.locator('[data-safeguard]:visible').count() == 16
        page.evaluate("window.dispatchEvent(new Event('afterprint'))")
        assert alignment.locator('[data-safeguard]:visible').count() == 130
        page.get_by_role('button', name='Fail', exact=True).click()
        assert page.locator('#allControlsTable tbody tr:visible').count() == report.failed_rules
        page.locator('#searchInput').fill('no-such-control')
        assert page.locator('#allControlsTable tbody tr:visible').count() == 0
        assert requests == []
        browser.close()
