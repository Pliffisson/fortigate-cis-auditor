"""Shared fixtures; each test receives independent application state."""
import pytest
from tests import FIXTURE_PATH
from cis_benchmark.config_parser import FortiGateConfigParser
from web.app import create_app


@pytest.fixture
def sample_config_path():
    return str(FIXTURE_PATH)


@pytest.fixture
def parser():
    return FortiGateConfigParser()


@pytest.fixture
def sample_config(parser, sample_config_path):
    return parser.parse_file(sample_config_path)


@pytest.fixture
def app():
    instance = create_app({'TESTING': True, 'SESSION_COOKIE_SECURE': False,
                           'AUTH_USER': '', 'AUTH_PASSWORD_HASH': '',
                           'REQUESTS_PER_MINUTE': 0})
    yield instance
    instance.extensions['audit_store'].close()


@pytest.fixture
def audit_sessions(app):
    return app.extensions['audit_store'].sessions


@pytest.fixture
def processing_slot(app):
    return app.extensions['processing_slot']
