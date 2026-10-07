"""Run in the built image: python /tests/container_smoke.py."""

import io
import os
import sys
from pathlib import Path

os.environ["SESSION_COOKIE_SECURE"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.app import create_app


from tests import FIXTURE_PATH

app = create_app({'TESTING': True, 'SESSION_COOKIE_SECURE': False})
content = FIXTURE_PATH.read_bytes()
client = app.test_client()
assert client.get("/health").json == {"status": "ok"}
assert client.get("/").status_code == 200
assert client.get("/static/dashboard.css").status_code == 200
assert client.get("/static/dashboard.js").status_code == 200
assert client.post("/upload", data={}).status_code == 400
assert client.post(
    "/upload",
    data={"config_file": (io.BytesIO(b""), "empty.conf")},
).status_code == 400

response = client.post(
    "/upload",
    data={"config_file": (io.BytesIO(content), "sample.conf")},
    follow_redirects=True,
)
assert response.status_code == 200
assert b"Erro na auditoria" not in response.data
assert "HttpOnly" in response.headers.get("Set-Cookie", "")
assert "Secure;" not in response.headers.get("Set-Cookie", "")
assert response.headers["Cache-Control"].startswith("no-store")

for kind in ("html", "json", "pdf", "remediation"):
    response = client.get(f"/download/{kind}")
    assert response.status_code == 200, (kind, response.data[:500])
    assert response.data, kind
    if kind == "pdf":
        assert response.data.startswith(b"%PDF-")
    if kind == "json":
        assert response.json["compliance"]["summary"]["total_rules"] > 0

other_browser = app.test_client()
assert other_browser.get("/download/json").status_code == 400

response = client.post(
    "/api/audit",
    data={"config_file": (io.BytesIO(content), "sample.conf")},
)
assert response.status_code == 200
assert response.json["summary"]["total_rules"] > 0
print("Container smoke checks passed: upload, session isolation, API, HTML/JSON/PDF/remediation.")
