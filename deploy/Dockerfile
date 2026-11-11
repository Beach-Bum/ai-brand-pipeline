# The MCP server over HTTP, for a container platform such as Cloud Run.
# NEVER BUILT OR RUN: written from the project's own run command; verify on first use.
# Build from the repository root:  docker build -f deploy/Dockerfile -t brand-agent .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /usr/local/bin/uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY brand_agent ./brand_agent
COPY brands ./brands

# The platform sets PORT; the server must listen on every interface inside the container.
ENV HOST=0.0.0.0 PORT=8080 BRAND_ID=example
CMD ["uv", "run", "--no-dev", "python", "-m", "brand_agent.server", "--http"]
