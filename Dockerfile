# Build stage - using uv with managed Python 3.12
FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_INSTALL_DIR=/python
ENV UV_PYTHON_PREFERENCE=only-managed

# Install Python before the project for caching
RUN uv python install 3.12

WORKDIR /app

# Copy lock file and pyproject.toml first for caching
COPY uv.lock pyproject.toml ./

# Sync dependencies (without installing project)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Copy application source
COPY src/ ./src/
COPY main.py ./

# Full sync to install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Runtime stage - distroless Python3 base (Debian 12)
FROM gcr.io/distroless/python3-debian12

WORKDIR /app

# Copy source code
COPY src/ ./src/
COPY main.py ./

# Copy the venv site-packages from builder to runtime's site-packages location
COPY --from=builder /app/.venv/lib/python*/site-packages/* /usr/local/lib/python3.11/site-packages/

# Default entrypoint - distroless uses python3 as entrypoint
ENTRYPOINT ["/usr/bin/python3"]
