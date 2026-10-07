"""Independent bounded stores, cleaned lazily and by their own timer."""
import json
import secrets
import threading
import time


class SessionStore:
    def __init__(self, max_sessions=100, max_bytes=64 * 1024 * 1024, ttl=7200):
        self.sessions = {}
        self.lock = threading.RLock()
        self.max_sessions, self.max_bytes, self.ttl = max_sessions, max_bytes, ttl
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._cleaner, daemon=True, name='audit-session-cleanup').start()

    def close(self):
        self._stop.set()

    def expire(self, now=None):
        now = time.time() if now is None else now
        with self.lock:
            for key in list(self.sessions):
                if now - self.sessions[key]['last_seen'] > self.ttl:
                    del self.sessions[key]

    def enforce_limits(self):
        while len(self.sessions) > self.max_sessions or sum(e.get('size', 0) for e in self.sessions.values()) > self.max_bytes:
            del self.sessions[min(self.sessions, key=lambda key: self.sessions[key]['last_seen'])]

    def touch(self, sid):
        with self.lock:
            self.expire()
            entry = self.sessions.setdefault(sid, {'report': None, 'config_file': '', 'timestamp': None, 'size': 0})
            entry['last_seen'] = time.time()
            self.enforce_limits()

    def save(self, sid, report, filename, timestamp):
        size = len(json.dumps(report.to_dict(), ensure_ascii=False).encode('utf-8'))
        if size > self.max_bytes:
            raise ValueError('Relatório excede o limite de armazenamento em memória.')
        with self.lock:
            self.sessions[sid] = {'report': report, 'config_file': filename, 'timestamp': timestamp,
                                 'view_id': secrets.token_hex(12),
                                 'last_seen': time.time(), 'size': size, 'pdf': None}
            self.enforce_limits()

    def cache_pdf(self, sid, entry, artifact):
        with self.lock:
            if self.sessions.get(sid) is entry and entry.get('pdf') is None:
                entry['pdf'] = artifact
                entry['size'] += len(artifact.content)
                self.enforce_limits()

    def _cleaner(self):
        while not self._stop.wait(30):
            self.expire()
