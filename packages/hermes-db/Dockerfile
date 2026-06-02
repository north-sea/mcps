FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/
COPY alembic.ini ./
COPY migrations/ migrations/

RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache .

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/hermes-db-mcp /usr/local/bin/hermes-db-mcp
COPY --from=builder /usr/local/bin/alembic /usr/local/bin/alembic
COPY src/ src/
COPY alembic.ini ./
COPY migrations/ migrations/

ENV TRANSPORT=streamable-http
EXPOSE 8080

ENTRYPOINT ["hermes-db-mcp"]
