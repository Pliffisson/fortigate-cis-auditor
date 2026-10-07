from datetime import timedelta
import json
import pytest
from cis_benchmark.audit import audit_content
from cis_benchmark.reporting.json_report import JSONReportGenerator
from cis_benchmark.timezone import local_now
from tests import FIXTURE_PATH
from web.settings import load_settings


def test_local_time_and_json_use_configured_timezone(monkeypatch):
    monkeypatch.setenv('TZ', 'America/Manaus')
    assert local_now().utcoffset() == timedelta(hours=-4)
    data = json.loads(JSONReportGenerator().generate(audit_content(FIXTURE_PATH.read_text())))
    assert data['metadata']['generated_at'].endswith('-04:00')
    monkeypatch.setenv('TZ', 'UTC')
    assert local_now().utcoffset() == timedelta(0)


def test_invalid_timezone_is_rejected_at_startup():
    with pytest.raises(ValueError, match='TZ'):
        load_settings({'TZ': 'Invalid/Timezone'})
