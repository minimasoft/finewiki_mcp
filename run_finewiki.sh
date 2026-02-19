#!/bin/bash
set -euo pipefail

# FineWiki MCP Runner Script
# Usage: ./run_finewiki.sh [mode] [options]
# Modes: index, server, test

IMAGE_NAME="finewiki-mcp"
CONTAINER_NAME="finewiki-mcp"

# Directories (defaults)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INDEX_DIR="${PROJECT_DIR}/index_data"
PARQUET_DIR=$(realpath "${PROJECT_DIR}/finewiki_en")

# Parse arguments
MODE="${1:-}"
shift || true

# Validate mode
if [[ "$MODE" != "index" && "$MODE" != "server" && "$MODE" != "test" ]]; then
    echo "Usage: $0 [index|server|test] [options]"
    echo ""
    echo "Modes:"
    echo "  index   Build the Tantivy index from parquet files"
    echo "          Options: --parquet-dir <dir> --index-dir <dir>"
    echo ""
    echo "  server  Run the MCP server"
    echo "          Options: --index-dir <dir> --parquet-dir <dir>"
    echo ""
    echo "  test    Run a quick test (search for 'Banana' in titles and 'Mozart' in content)"
    echo "          Options: --index-dir <dir> --parquet-dir <dir>"
    echo ""
    exit 1
fi

# Function to build the Docker image
build_image() {
    echo "Building Docker image..."
    docker build -t "$IMAGE_NAME" "$PROJECT_DIR"
}

# Function to run in index mode
run_index() {
    local parquet_dir="$PARQUET_DIR"
    local index_dir="$INDEX_DIR"

    # Parse remaining arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --parquet-dir)
                parquet_dir="$2"
                shift 2
                ;;
            --index-dir)
                index_dir="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Ensure parquet directory exists
    if [[ ! -d "$parquet_dir" ]]; then
        echo "Error: Parquet directory not found: $parquet_dir"
        echo "Please ensure your parquet files are in: $parquet_dir"
        exit 1
    fi

    # Create index directory if it doesn't exist
    mkdir -p "$index_dir"

    echo "Running indexer..."
    echo "  Parquet dir: $parquet_dir"
    echo "  Index dir:   $index_dir"

    # Get the resolved path for parquet directory (handles symlinks)
    local resolved_parquet=$(realpath "$parquet_dir")

    docker run --rm -t \
        -v "$PROJECT_DIR:/host_project" \
        -v "$(dirname "$resolved_parquet"):/parquet_data" \
        -w /app \
        --entrypoint="" \
        -e PYTHONUNBUFFERED=1 \
        "$IMAGE_NAME" \
        /app/.venv/bin/python -u src/finewiki_mcp/indexer.py \
        --parquet-dir "/parquet_data/$(basename "$resolved_parquet")" \
        --index-dir "/host_project/$(basename "$index_dir")"
}

# Function to run in server mode
run_server() {
    local index_dir="$INDEX_DIR"
    local parquet_dir="$PARQUET_DIR"

    # Parse remaining arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --index-dir)
                index_dir="$2"
                shift 2
                ;;
            --parquet-dir)
                parquet_dir="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Check if index exists
    if [[ ! -d "$index_dir" ]]; then
        echo "Error: Index directory not found: $index_dir"
        echo "Run 'index' mode first to build the index."
        exit 1
    fi

    # Check if parquet files exist
    if [[ ! -d "$parquet_dir" ]]; then
        echo "Warning: Parquet directory not found: $parquet_dir"
        echo "Server may fail if it cannot find parquet files for content fetching."
    fi

    echo "Starting MCP server..."
    echo "  Index dir:   $index_dir"
    echo "  Parquet dir: $parquet_dir"

    docker run --rm -it \
        -v "$PROJECT_DIR:/host_project" \
        -w /app \
        --publish 9000:9000 \
        --name "$CONTAINER_NAME" \
        --entrypoint="" \
        -e PYTHONUNBUFFERED=1 \
        "$IMAGE_NAME" \
        /app/.venv/bin/python -u src/finewiki_mcp/server.py \
        --index-dir "/host_project/$(basename "$index_dir")" \
        --parquet-dir "/host_project/$(basename "$parquet_dir")"
}

# Function to run in test mode
run_test() {
    local index_dir="$INDEX_DIR"
    local parquet_dir="$PARQUET_DIR"

    # Parse remaining arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --index-dir)
                index_dir="$2"
                shift 2
                ;;
            --parquet-dir)
                parquet_dir="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Check if index exists
    if [[ ! -d "$index_dir" ]]; then
        echo "Error: Index directory not found: $index_dir"
        echo "Run 'index' mode first to build the index."
        exit 1
    fi

    # Check if parquet files exist
    if [[ ! -d "$parquet_dir" ]]; then
        echo "Warning: Parquet directory not found: $parquet_dir"
        echo "Test may fail if it cannot find parquet files for content fetching."
    fi

    echo "Running test mode..."
    echo "  Index dir:   $index_dir"
    echo "  Parquet dir: $parquet_dir"

    docker run --rm -t \
        -v "$PROJECT_DIR:/host_project" \
        -w /app \
        --entrypoint="" \
        -e PYTHONUNBUFFERED=1 \
        "$IMAGE_NAME" \
        /app/.venv/bin/python -u src/finewiki_mcp/server.py \
        --index-dir "/host_project/$(basename "$index_dir")" \
        --parquet-dir "/host_project/$(basename "$parquet_dir")" \
        --mode test
}

build_image

# Main logic
case "$MODE" in
    index)
        run_index "$@"
        ;;
    server)
        run_server "$@"
        ;;
    test)
        run_test "$@"
        ;;
esac
