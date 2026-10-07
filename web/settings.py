"""Load and validate deployment settings once, before serving requests."""
import os
from pathlib import Path
from cis_benchmark.timezone import configured_timezone, DEFAULT_TIMEZONE


def load_settings(overrides=None):
    values = dict(os.environ)
    values.update(overrides or {})
    timezone = configured_timezone(values.get('TZ', DEFAULT_TIMEZONE)).key
    def integer(name, default, minimum, maximum):
        try:
            value = int(values.get(name, default))
        except (ValueError, TypeError):
            raise ValueError(f'{name} deve ser um número inteiro.') from None
        if not minimum <= value <= maximum:
            raise ValueError(f'{name} deve estar entre {minimum} e {maximum}.')
        return value
    secure = str(values.get('SESSION_COOKIE_SECURE', 'true')).lower()
    if secure not in ('true', 'false', '1', '0', 'yes', 'no'):
        raise ValueError('SESSION_COOKIE_SECURE deve ser true ou false.')
    user = values.get('AUTH_USER', '')
    password_hash = values.get('AUTH_PASSWORD_HASH', '')
    if bool(user) != bool(password_hash):
        raise ValueError('Configure AUTH_USER e AUTH_PASSWORD_HASH juntos.')
    if password_hash and not password_hash.startswith(('scrypt:', 'pbkdf2:')):
        raise ValueError('AUTH_PASSWORD_HASH deve ser um hash gerado pelo Werkzeug.')
    if password_hash and (len(password_hash.split('$')) != 3 or not all(password_hash.split('$'))):
        raise ValueError('AUTH_PASSWORD_HASH deve conter método, salt e digest do Werkzeug.')
    secret_file = values.get('SECRET_KEY_FILE')
    secret = Path(secret_file).read_text().strip() if secret_file else values.get('SECRET_KEY', '').strip()
    if secret_file and not secret:
        raise ValueError('SECRET_KEY_FILE não pode estar vazio.')
    return dict(MAX_CONTENT_LENGTH=integer('MAX_UPLOAD_MB', 10, 1, 50) * 1024 * 1024,
                REQUESTS_PER_MINUTE=integer('REQUESTS_PER_MINUTE', 0, 0, 100000),
                AUTH_USER=user, AUTH_PASSWORD_HASH=password_hash, TZ=timezone,
                SESSION_COOKIE_SECURE=secure in ('true', '1', 'yes'), SECRET_KEY=secret)
