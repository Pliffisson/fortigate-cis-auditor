"""Application factory; runtime state belongs to each Flask instance."""
import io
import secrets
from flask import Flask, Request, send_from_directory, abort
from pathlib import Path
from jinja2 import ChoiceLoader, FileSystemLoader
from .settings import load_settings
from .session_store import SessionStore
from .views import register_views


class MemoryRequest(Request):
    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        return io.BytesIO()


def create_app(settings=None):
    app = Flask(__name__)
    report_resources = Path(__file__).resolve().parent.parent / 'cis_benchmark' / 'reporting'
    app.jinja_loader = ChoiceLoader([app.jinja_loader, FileSystemLoader(report_resources / 'templates')])

    @app.get('/assets/controls-alignment/<filename>')
    def controls_alignment_asset(filename):
        if filename not in ('controls-alignment.css', 'controls-alignment.js'):
            abort(404)
        return send_from_directory(report_resources / 'assets', filename)

    app.request_class = MemoryRequest
    app.config.update(load_settings(settings))
    app.config['TESTING'] = bool((settings or {}).get('TESTING', False))
    app.config.update(MAX_FORM_MEMORY_SIZE=128 * 1024, MAX_FORM_PARTS=10,
                      SESSION_COOKIE_NAME='cis_sid', SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Lax', SESSION_REFRESH_EACH_REQUEST=True,
                      PERMANENT_SESSION_LIFETIME=7200)
    app.config['SECRET_KEY'] = app.config['SECRET_KEY'] or secrets.token_hex(32)
    store = SessionStore()
    app.extensions['audit_store'] = store
    register_views(app, store)
    if not (settings or {}).get('TESTING', False):
        store.start()
    return app


app = create_app()
# Compatibility for callers using the default WSGI instance.
audit_sessions = app.extensions['audit_store'].sessions
processing_slot = app.extensions['processing_slot']
