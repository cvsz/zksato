FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system zksato && useradd --system --gid zksato --create-home zksato

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install . \
    && chown -R zksato:zksato /app

USER zksato
EXPOSE 9999

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9999/health', timeout=3)" || exit 1

CMD ["uvicorn", "zksato.api:app", "--host", "0.0.0.0", "--port", "9999"]
