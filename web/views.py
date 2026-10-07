"""Flask dashboard and API; auditing and report serialization live in the core."""
import io
import secrets
import threading
import time
from cis_benchmark.timezone import local_now

from flask import make_response, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from cis_benchmark.audit import audit_content
from cis_benchmark.config_parser import decode_config
from cis_benchmark.reporting.export import export_report

from werkzeug.security import check_password_hash



def register_views(app, session_store):
    audit_sessions = session_store.sessions
    audit_sessions_lock = session_store.lock
    processing_slot = threading.BoundedSemaphore(1)
    rate_windows = {}
    rate_lock = threading.Lock()
    app.extensions['processing_slot'] = processing_slot
    app.extensions['rate_windows'] = rate_windows

    def respond_error(message, status, headers=None):
        if request.path.startswith('/api/'):
            response = make_response(jsonify(error=message), status)
        else:
            audit = audit_sessions.get(session.get('sid')) or {'report': None}
            deleting = request.path == '/delete-audit'
            response = make_response(render_template(
                'dashboard.html', audit=audit, error=message,
                error_title='Não foi possível excluir a auditoria.' if deleting else None,
                error_hint='Atualize a página e tente excluir novamente.' if deleting else None,
            ), status)
        response.headers.update(headers or {})
        return response

    @app.errorhandler(HTTPException)
    def request_error(error):
        message, status = audit_error(error)
        headers = {key: value for key, value in error.get_headers() if key.lower() != 'content-type'}
        return respond_error(message, status, headers)

    @app.before_request
    def request_limits():
        if request.path == '/health':
            return None
        rate_limit = app.config['REQUESTS_PER_MINUTE']
        if rate_limit > 0:
            now = time.monotonic()
            with rate_lock:
                for key in list(rate_windows):
                    if now - rate_windows[key][0] >= 60:
                        del rate_windows[key]
                key = request.remote_addr or 'unknown'
                if key not in rate_windows and len(rate_windows) >= 1024:
                    return respond_error('Limite de clientes atingido; tente novamente.', 429)
                start, count = rate_windows.get(key, (now, 0))
                if count >= rate_limit:
                    return respond_error('Limite de requisições atingido; tente novamente.', 429, {'Retry-After': str(max(1, int(60 - (now - start))))})
                rate_windows[key] = (start, count + 1)
        if request.method == 'POST' or request.path == '/download/pdf':
            if not processing_slot.acquire(blocking=False):
                return respond_error('Análise ou exportação em andamento; tente novamente.', 429, {'Retry-After': '3'})
            g.processing_slot = True
        user = app.config['AUTH_USER']
        password_hash = app.config['AUTH_PASSWORD_HASH']
        if bool(user) != bool(password_hash):
            return jsonify(error='Configure AUTH_USER e AUTH_PASSWORD_HASH juntos.'), 503
        if user and password_hash:
            auth = request.authorization
            if not auth or not secrets.compare_digest((auth.username or '').encode('utf-8'), user.encode('utf-8')) or not check_password_hash(password_hash, auth.password or ''):
                return 'Autenticação necessária.', 401, {'WWW-Authenticate': 'Basic realm="FortiGate Auditor"'}
            if request.method == 'POST' and request.path == '/upload':
                token = request.form.get('csrf_token', '')
                if not token or not secrets.compare_digest(token.encode('utf-8'), session.get('csrf_token', '').encode('utf-8')):
                    return respond_error('Formulário expirado; atualize a página.', 400)


    @app.teardown_request
    def release_processing_slot(error=None):
        if g.pop('processing_slot', False):
            processing_slot.release()


    def get_browser_sid():
        sid = session.get("sid")
        if not isinstance(sid, str) or len(sid) < 32:
            sid = secrets.token_urlsafe(32)
            session.clear()
            session["sid"] = sid
        session.setdefault('csrf_token', secrets.token_urlsafe(32))
        session.permanent = True
        session_store.touch(sid)
        return sid


    def browser_audit(sid):
        with audit_sessions_lock:
            return audit_sessions.get(sid)


    def audit_upload():
        """One validation/decoding path for both upload endpoints."""
        file = request.files.get("config_file")
        if file is None:
            raise ValueError("Nenhum arquivo enviado")
        if not file.filename:
            raise ValueError("Nenhum arquivo selecionado")
        filename = secure_filename(file.filename)
        if not filename.lower().endswith(".conf"):
            raise ValueError("Somente arquivos .conf são permitidos")
        data = file.stream.read()
        if not data:
            raise ValueError("O arquivo está vazio")
        content = decode_config(data)
        report = audit_content(content, request.form.get("level", "all"), request.form.get("expected_timezone") or None)
        return filename, report


    def audit_error(error):
        if isinstance(error, RequestEntityTooLarge):
            return "Arquivo excede o limite de upload configurado (incluindo os dados do formulário).", 413
        if isinstance(error, HTTPException):
            return error.description, error.code
        if isinstance(error, ValueError):
            app.logger.warning("Upload rejeitado: %s", error)
            return str(error), 400
        app.logger.exception("Falha na auditoria")
        return "Falha interna na auditoria.", 500


    @app.after_request
    def security_headers(response):
        response.headers.update({"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                                 "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
                                 "Pragma": "no-cache", "Expires": "0",
                                 "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"})
        return response


    @app.get("/health")
    def health():
        return jsonify(status="ok")


    @app.get("/")
    def index():
        return render_template("dashboard.html", audit=browser_audit(get_browser_sid()))


    @app.post("/upload")
    def upload_config():
        sid = get_browser_sid()
        try:
            filename, report = audit_upload()
        except Exception as error:
            message, status = audit_error(error)
            return render_template("dashboard.html", audit=browser_audit(sid), error=message), status
        try:
            session_store.save(sid, report, filename, local_now(app.config['TZ']).strftime("%Y-%m-%d %H:%M:%S"))
        except ValueError as error:
            return render_template("dashboard.html", audit=browser_audit(sid), error=str(error)), 400
        return redirect(url_for("index"))


    @app.post("/api/audit")
    def api_audit():
        try:
            _, report = audit_upload()
            return jsonify(report.to_dict())
        except Exception as error:
            message, status = audit_error(error)
            return jsonify(error=message), status


    @app.get("/download/<format_type>")
    def download_report(format_type):
        sid = get_browser_sid()
        audit = browser_audit(sid)
        if not audit or audit["report"] is None:
            return respond_error("Nenhuma auditoria disponível; a sessão pode ter expirado. Envie o arquivo novamente.", 400)
        try:
            artifact = audit.get('pdf') if format_type == 'pdf' else None
            if artifact is None:
                artifact = export_report(audit["report"], format_type, audit["config_file"])
                if format_type == 'pdf':
                    session_store.cache_pdf(sid, audit, artifact)
        except ValueError as error:
            return respond_error(str(error), 400)
        except Exception:
            app.logger.exception("Falha na geração de relatório")
            return respond_error("Falha interna na geração de relatório.", 500)
        timestamp = local_now(app.config['TZ']).strftime("%Y%m%d_%H%M%S")
        extension = "txt" if format_type == "remediation" else format_type
        name = "Remediation" if format_type == "remediation" else "CIS_Report"
        return send_file(io.BytesIO(artifact.content), as_attachment=True,
                         download_name=f"{name}_{timestamp}.{extension}", mimetype=artifact.mimetype)


    @app.post('/delete-audit')
    def delete_audit():
        # Expired/restarted sessions have nothing to delete. Returning home is safe;
        # active reports still require the session's CSRF token.
        sid = session.get('sid')
        with audit_sessions_lock:
            audit = audit_sessions.get(sid)
            if not audit or audit['report'] is None:
                audit_sessions.pop(sid, None)
                session.clear()
                return redirect(url_for('index'))
        token = request.form.get('csrf_token', '')
        if not token or not secrets.compare_digest(token.encode('utf-8'), session.get('csrf_token', '').encode('utf-8')):
            return respond_error('Formulário expirado; atualize a página.', 400)
        with audit_sessions_lock:
            audit_sessions.pop(sid, None)
        session.clear()
        return redirect(url_for('index'))
