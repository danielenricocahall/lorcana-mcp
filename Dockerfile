FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
RUN uv python install 3.14t

LABEL io.modelcontextprotocol.server.name="io.github.danielenricocahall/lorcana-mcp"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "main.py"]