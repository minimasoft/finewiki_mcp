# FineWiki MCP Server

A Model Context Protocol (MCP) server that provides search and content retrieval capabilities for the FineWiki English dataset using Tantivy indexing.

## Overview

This project implements an MCP server that:
- Indexes the FineWiki English dataset from parquet files using [Tantivy](https://github.com/quickwit-oss/tantivy)
- Provides search by title
- Provides search by full content
- Fetches complete document content directly from parquet files

## Installation

```bash
# Clone and navigate to the project
cd finewiki_mcp

# Install dependencies
uv sync
```

## Prerequisites

You need the FineWiki English dataset in parquet format. Download it from HuggingFace:

```bash
# Option 1: Download specific partition(s)
wget https://huggingface.co/datasets/HuggingFaceFW/finewiki/resolve/main/partitions/english/0000.parquet -O finewiki_en/0000.parquet

# Option 2: Use huggingface-cli
pip install huggingface_hub
huggingface-cli download HuggingFaceFW/finewiki --repo-type dataset --include "*/ partitions/english/*.parquet" --local-dir finewiki_en
```

The parquet files should be placed in the `finewiki_en` directory (or specify a different path with `--parquet-dir`).

## Usage

### 1. Build the Index

First, build the Tantivy index from your parquet files:

```bash
uv run python -m finewiki_mcp.indexer --parquet-dir finewiki_en --index-dir index_data
```

Options:
- `--parquet-dir`: Directory containing parquet files (default: `finewiki_en`)
- `--index-dir`: Output directory for the index (default: `index_data`)

### 2. Run the MCP Server

Start the server:

```bash
uv run python -m finewiki_mcp.server --index-dir index_data --parquet-dir finewiki_en
```

The server runs over stdio and can be integrated with any MCP-compatible client.

### 3. Available Tools

The MCP server exposes three tools:

#### `search_by_title`
Search for documents by title.

**Parameters:**
- `query` (string, required): Search query for titles
- `limit` (integer, optional): Maximum number of results (default: 10)

**Returns:** List of matching documents with id, title, url, and score.

#### `search_by_content`
Search for documents by full content.

**Parameters:**
- `query` (string, required): Search query for content
- `limit` (integer, optional): Maximum number of results (default: 10)

**Returns:** List of matching documents with id, title, url, and score.

#### `fetch_content`
Fetch the full content of a document by its ID.

**Parameters:**
- `doc_id` (integer, required): Document ID to fetch

**Returns:** Object containing id, title, content, and url.

## Project Structure

```
finewiki_mcp/
├── src/finewiki_mcp/
│   ├── __init__.py       # Package initialization
│   ├── indexer.py        # Index generation script
│   └── server.py         # MCP server implementation
├── index_data/           # Tantivy index storage (created by indexer)
├── finewiki_en/          # Parquet files directory
├── pyproject.toml        # Project dependencies
└── README.md
```

## Architecture

- **Indexing**: Uses [Tantivy](https://github.com/quickwit-oss/tantivy) for fast full-text search
- **Storage**: Index stores id, title, and url; content is stored in parquet files to avoid duplication
- **Search**: Query parsing using Tantivy's query parser
- **Fetching**: Direct access to parquet files using PyArrow for efficient columnar reading

## Configuration

### Linting with Ruff

```bash
uv run ruff check .
```

### Testing

```bash
uv run pytest
```

## License

This project is provided as-is for educational and research purposes.
