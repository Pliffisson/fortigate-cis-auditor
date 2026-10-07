"""Configured local time shared by the dashboard, CLI and exports."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = 'America/Manaus'


def configured_timezone(name=None):
    name = name if name is not None else os.environ.get('TZ', DEFAULT_TIMEZONE)
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ValueError('TZ deve ser um timezone IANA válido, como America/Manaus ou America/Sao_Paulo.') from None


def local_now(name=None):
    return datetime.now(configured_timezone(name))
