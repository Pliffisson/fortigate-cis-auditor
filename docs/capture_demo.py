"""Capture the real UI using only the fictional fixture, inside the browser container."""
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from web.app import create_app


def main():
    output = Path('/demo-images')
    output.mkdir(parents=True, exist_ok=True)
    fixture = Path('/app/tests/fixtures/sample.conf').read_bytes()
    assert b'FICTIONAL TEST CONFIGURATION' in fixture
    app = create_app({'TESTING': True, 'SESSION_COOKIE_SECURE': False,
                      'AUTH_USER': '', 'AUTH_PASSWORD_HASH': '', 'REQUESTS_PER_MINUTE': 0})
    server = make_server('127.0.0.1', 8765, app, threaded=True)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=['--disable-dev-shm-usage'])
            page = browser.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=1)
            page.goto('http://127.0.0.1:8765')
            page.evaluate('document.fonts.ready')

            def mark_demo():
                page.evaluate("""() => {
                    const notice = document.createElement('div');
                    notice.textContent = 'DEMONSTRAÇÃO • Configuração e dados fictícios • Ambiente de testes';
                    notice.style.cssText = 'padding:10px 16px;margin-bottom:20px;border:1px solid #475742;border-radius:8px;background:#202922;color:#b8e986;font-size:12px;line-height:1.6';
                    document.querySelector('main').prepend(notice);
                }""")

            mark_demo()
            page.screenshot(path=str(output / 'tela-inicial.png'))
            page.set_input_files('#config-file', {'name': 'fortigate-demonstracao.conf',
                                                'mimeType': 'text/plain', 'buffer': fixture})
            page.locator('.upload .analyze').click()
            page.wait_for_selector('#assessment-summary')
            # Use a fixed fictional date so examples never reveal production metadata.
            store = app.extensions['audit_store']
            with store.lock:
                for audit in store.sessions.values():
                    if audit['report'] is not None:
                        audit['timestamp'] = '2026-01-15 10:00:00'
            page.reload()
            page.evaluate('document.fonts.ready')
            mark_demo()
            assert page.locator('.audit-file').inner_text() == 'Arquivo: fortigate-demonstracao.conf'
            assert page.locator('.audit-source time').inner_text() == '2026-01-15 10:00:00'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            height = page.locator('.stats-secondary').evaluate('node => Math.ceil(node.getBoundingClientRect().bottom + 24)')
            page.set_viewport_size({'width': 1600, 'height': height})
            page.screenshot(path=str(output / 'resumo-auditoria.png'))
            browser.close()
            print('Demo screenshots captured using fictional fixture and fixed example timestamp.')
    finally:
        server.shutdown()
        worker.join(timeout=5)
        app.extensions['audit_store'].close()


if __name__ == '__main__':
    main()
