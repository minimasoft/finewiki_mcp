# FineWiki MCP Server - Project Context

## Overview

**FineWiki MCP Server** is a Model Context Protocol (MCP) server that provides offline search and content retrieval for the FineWiki English dataset. It enables AI applications to access multi-gigabyte Wikipedia-like datasets without API keys, rate limits, or tracking.

### Key Technologies
- **Tantivy**: Rust-based full-text search library (via Python bindings) for lightning-fast indexing (~20ms retrieval)
- **MCP (Model Context Protocol)**: Standard protocol for AI tool integration
- **Docker**: Containerized deployment (no local Python dependencies required)
- **Python 3.14** with `uv` for dependency management

### Architecture
```
Parquet Files → Indexer (Tantivy) → Searchable Index → MCP Server → AI Clients
     ↓                                    ↓                    ↓
finewiki_en/                        index_data/          stdio protocol
(6.6M articles, ~20-25GB)         (~17-30GB)           Port 9000
```

---

## Project Structure

```
finewiki_mcp/
├── src/finewiki_mcp/
│   ├── __init__.py       # Package initialization (__version__ = "0.1.0")
│   ├── common.py         # Shared utilities (get_schema() for Tantivy)
│   ├── indexer.py        # Index generation from Parquet files
│   └── server.py         # MCP server implementation + test mode
├── index_data/           # Tantivy index storage (created by indexer)
├── finewiki_en/          # Parquet files directory (downloaded separately)
├── run_finewiki.sh       # Docker runner script (index/server/test modes)
├── links.sh              # Downloads Parquet files using aria2c
├── Dockerfile            # Multi-stage build using uv
├── pyproject.toml        # Project dependencies
└── README.md             # User documentation
```

---

## Building and Running

### Prerequisites
- Docker installed
- `aria2` for downloading Parquet files (optional, see below)

### 1. Download Parquet Files
```bash
./links.sh
# Downloads to finewiki_en/ directory
# Requires: aria2c (install via apt/brew)
```

### 2. Build the Index
```bash
./run_finewiki.sh index [--parquet-dir <dir>] [--index-dir <dir>]
```
This scans all `.parquet` files and creates a Tantivy index in `index_data/`.

**Note:** After indexing, parquet files can be deleted (all content stored in index).

### 3. Run the MCP Server
```bash
./run_finewiki.sh server [--index-dir <dir>] [--parquet-dir <dir>]
```
Server listens on port 9000 via stdio protocol.

### 4. Test the Setup
```bash
./run_finewiki.sh test
```
Runs built-in tests: searches for "Banana" (titles) and "Mozart" (content), fetches results, reports timing.

---

## Development

### Local Development (without Docker)
```bash
# Install dependencies using uv
uv sync

# Run indexer directly
uv run python -m finewiki_mcp.indexer --parquet-dir finewiki_en --index-dir index_data

# Run server directly
uv run python -m finewiki_mcp.server --index-dir index_data --parquet-dir finewiki_en

# Run tests
pytest
```

### Code Style
- **Formatter/Linter**: Ruff (configured in `pyproject.toml`)
- **Python Version**: 3.14 (see `.python-version`)
- **Package Manager**: uv

---

## MCP Tools Exposed

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_by_title` | Search documents by title | `query`, `limit` (default: 10) |
| `search_by_content` | Full-text search across content | `query`, `limit` (default: 10) |
| `fetch_content` | Get full document by ID | `doc_id` |

### Example MCP Client Configuration
```json
{
  "finewiki": {
    "command": "bash",
    "args": ["/path/to/run_finewiki.sh", "server"]
  }
}
```

---

## Data Schema

Tantivy index schema (`src/finewiki_mcp/common.py`):
- `id`: Integer (stored, indexed) - Wikipedia page ID
- `title`: Text (stored, indexed with positions)
- `content`: Text (stored, indexed with positions) - Full article text
- `url`: Text (stored, indexed with positions)

---

## Storage Requirements

| Dataset | Articles | Index Size | Parquet Files |
|---------|----------|------------|---------------|
| FineWiki English | 6.6M | ~17-30GB | ~20-25GB |

---

## Key Implementation Details

### Indexer (`indexer.py`)
- Supports incremental indexing via `indexed_files.json` metadata
- Handles interrupted runs by backing up old index to `.index_old`
- Commits after each Parquet file for durability

### Server (`server.py`)
- Uses MCP stdio protocol for communication
- Lazy initialization of searcher on startup
- Test mode (`--mode test`) for performance benchmarking

### Docker Setup
- Multi-stage build using `uv` for efficient dependency caching
- Python 3.14 managed via uv, symlinked to system python
- Runtime dependencies: `libzstd1` (for pyarrow/numpy)

---

## Current TODOs

- Add support for fineweb-edu dumps

---

## Testing

Built-in test client (`test_client.py`):
```bash
python test_client.py
# Tests 5 sample queries, measures search + fetch times
```

---

**License**: Educational/research purposes. Adapt and extend as needed.
