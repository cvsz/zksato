FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

WORKDIR /build
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip \
    && python -m pip install .

FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="zksato" \
      org.opencontainers.image.description="Risk-first SET/TFEX trading control plane" \
      org.opencontainers.image.source="https://github.com/cvsz/zksato"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    HOME=/home/zksato

RUN groupadd --system zksato \
    && useradd --system --gid zksato --create-home --home-dir /home/zksato zksato

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
USER zksato
EXPOSE 9569

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9569/health', timeout=3)" || exit 1

CMD ["uvicorn", "zksato.api:app", "--host", "0.0.0.0", "--port", "9569"]
