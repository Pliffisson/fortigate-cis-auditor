FROM python:3.12-slim-bookworm AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
        libjpeg62-turbo libopenjp2-7 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 auditor \
    && useradd --uid 10001 --gid auditor --no-create-home auditor
COPY requirements.txt .
RUN pip install --requirement requirements.txt
ENV TZ=America/Manaus

# Expensive installations depend only on dependency files, never application code.
FROM dependencies AS test_dependencies
COPY requirements-dev.txt ./
RUN pip install --requirement requirements-dev.txt

FROM test_dependencies AS browser_dependencies
COPY requirements-browser.txt ./
RUN pip install --requirement requirements-browser.txt
ENV BROWSER_TESTS=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install --with-deps --only-shell chromium \
    && chmod -R a+rX /ms-playwright \
    && rm -rf /var/lib/apt/lists/*

FROM dependencies AS runtime
COPY --chown=auditor:auditor cis_benchmark ./cis_benchmark
COPY --chown=auditor:auditor web ./web
COPY --chown=auditor:auditor run_audit.py .
USER auditor
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1
CMD ["gunicorn", "--no-control-socket", "--workers", "1", "--threads", "2", "--timeout", "180", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "web.app:app"]

FROM test_dependencies AS tests
COPY --chown=auditor:auditor cis_benchmark ./cis_benchmark
COPY --chown=auditor:auditor web ./web
COPY --chown=auditor:auditor run_audit.py pytest.ini ./
COPY --chown=auditor:auditor tests ./tests
USER auditor
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

FROM browser_dependencies AS browser
COPY --chown=auditor:auditor cis_benchmark ./cis_benchmark
COPY --chown=auditor:auditor web ./web
COPY --chown=auditor:auditor run_audit.py pytest.ini ./
COPY --chown=auditor:auditor tests ./tests
USER auditor
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/browser"]

FROM tests AS development
USER root
RUN mkdir -p /home/auditor && chown auditor:auditor /home/auditor
USER auditor
CMD ["sleep", "infinity"]

FROM runtime AS production
