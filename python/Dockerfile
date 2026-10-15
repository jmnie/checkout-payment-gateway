FROM ghcr.io/astral-sh/uv:0.11.28 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app/python
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY python/pyproject.toml python/uv.lock ./
RUN uv sync --locked --no-dev
COPY python/payment_gateway_api ./payment_gateway_api
COPY docs/openapi.json /app/docs/openapi.json
RUN useradd --uid 10001 --no-create-home gateway
USER 10001
EXPOSE 8090
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s CMD ["/app/python/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=2)"]
CMD ["/app/python/.venv/bin/uvicorn", "payment_gateway_api.app:app", "--host", "0.0.0.0", "--port", "8090", "--no-access-log"]
