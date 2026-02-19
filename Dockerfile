# Build stage - using uv for dependency management
FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Configure the Python directory so it is consistent
ENV UV_PYTHON_INSTALL_DIR=/python

# Only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

# Install Python 3.14 (matches .python-version)
RUN uv python install 3.14

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./

# Sync dependencies without installing the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Copy application source
COPY src/ ./src/
COPY main.py ./

# Create the virtual environment and install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Runtime stage - Debian 12 slim with Python and standard libraries
FROM debian:bookworm-slim

WORKDIR /app

# Install required runtime dependencies (zlib, etc. for numpy/pyarrow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzstd1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the managed Python from builder
COPY --from=builder /python/cpython-3.14.3-linux-x86_64-gnu /usr/local/python

# Create symlink for system python to use our managed version
RUN ln -sf /usr/local/python/bin/python3.14 /usr/local/bin/python && \
    ln -sf /usr/local/python/bin/pip3.14 /usr/local/bin/pip

# Copy the virtual environment from builder (includes all dependencies)
COPY --from=builder /app/.venv /app/.venv

# Create a symlink for venv python pointing to managed Python
RUN ln -sf /usr/local/python/bin/python3.14 /app/.venv/bin/python

# Copy application source
COPY src/ ./src/
COPY main.py ./

# Set PATH to use our managed Python first
ENV PATH="/usr/local/python/bin:/app/.venv/bin:$PATH"

# Override the default entrypoint with python from venv
ENTRYPOINT ["/app/.venv/bin/python"]
CMD ["src/finewiki_mcp/server.py", "--index-dir", "index_data", "--parquet-dir", "finewiki_en"]
