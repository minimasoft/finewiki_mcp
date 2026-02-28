# 🌊 FineWiki MCP Server

A **Model Context Protocol (MCP)** server that provides search and content retrieval for the FineWiki English dataset. 📚

**No API keys. No rate limits. No trackers. Just pure offline AI context! 💪**

> **Key Features:**
> - 🔍 Fast full-text search across multi-gigabyte datasets
> - 🐳 Runs in Docker (no local dependencies needed)
> - ⚡ Uses Tantivy for lightning-fast indexing and search (~20ms content retrieval)
> - 💾 All-inclusive index: 30GB for 6.6M articles (parquet files optional after indexing)

---

## 🎯 What is This?

This is a **sample project** demonstrating how to integrate large datasets as MCP tools — giving you unlimited offline context for your AI applications without any tracking, keys, or restrictions!

Think of it as your own personal Wikipedia API that runs entirely on your machine. 🏠

---

## 📥 Quick Start: Download Parquet Files

The FineWiki English dataset is stored in Parquet format. Here's how to get it:

### ✅ Best Method: Using `aria2c` (parallel + resumable)

```bash
./links.sh
```

This downloads all parquet files using aria2 for maximum speed ⚡

> **Install aria2:**
> ```bash
> # Ubuntu/Debian
> sudo apt install aria2
>
> # macOS
> brew install aria2
> ```

> **Note:** The `links.sh` script is in the project root and downloads files to `finewiki_en/`.

---

## 🐳 Docker Setup (Recommended)

This project runs entirely inside Docker — no Python installation required!

### Step 1: Build the Index

First, build the Tantivy index from your parquet files:

```bash
./run_finewiki.sh index
```

This will:
- Build the Docker image (once)
- Scan all `.parquet` files in `finewiki_en/`
- Create the search index in `index_data/`
- **Note:** After indexing, you can optionally delete parquet files as all content is now stored in the index

### Step 2: Start the MCP Server

```bash
./run_finewiki.sh server
```

The server is now running and ready to accept MCP connections!

---

## 🧪 Testing

Run the built-in test to verify everything works:

```bash
./run_finewiki.sh test
```

This will:
- Search for "Banana" in titles (returns 5 results)
- Search for "Mozart" in content (returns 5 results)
- Fetch full content of each result to measure real-world performance
- Report timing statistics and memory usage

---

## 🤖 Integrating with MCP Clients

Here's a sample configuration for your MCP client (`claude_desktop_config.json` or similar):

```json
{
  "finewiki": {
    "command": "bash",
    "args": [
      "/path/to/finewiki_mcp/run_finewiki.sh",
      "server"
    ]
  }
}
```

> **Note:** Replace `/path/to/` with the actual path where you cloned this repository.

---

## 🧰 Available Tools

The MCP server exposes three powerful tools:

| Tool | Description |
|------|-------------|
| `search_by_title` | Search for documents by title (fast!) |
| `search_by_content` | Full-text search across all content |
| `fetch_content` | Get the complete document by ID |

---

## 🏗️ Project Structure

```
finewiki_mcp/
├── src/finewiki_mcp/
│   ├── __init__.py       # Package initialization
│   ├── indexer.py        # Index generation script
│   └── server.py         # MCP server implementation
├── index_data/           # Tantivy index storage (created by indexer) 🗂️
├── finewiki_en/          # Parquet files directory - can be deleted after indexing! 📦
├── run_finewiki.sh       # Docker runner script ⚙️
├── pyproject.toml        # Project dependencies
└── README.md
```

---

## 🔧 How It Works

1. **Indexing** 📝
   Uses [Tantivy](https://github.com/quickwit-oss/tantivy) to create a fast full-text search index from Parquet files. The index includes:
   - `id`: Document identifier (stored, indexed)
   - `title`: Document title (stored, indexed)
   - `content`: Full text content (stored, indexed)
   - `url`: Source URL (stored, indexed)

2. **Storage** 💾
   After indexing (~30GB for 6.6M articles), parquet files are no longer needed. All content is stored directly in the index.

3. **Search** 🔍
   Query parsing using Tantivy's powerful query parser with fuzzy matching

4. **Fetching** 📚
   Direct access to indexed content - no file lookups required!

---

## 📊 Storage Requirements

| Dataset | Articles | Index Size | Parquet Files (optional) |
|---------|----------|------------|--------------------------|
| FineWiki English | 6.6M | ~30GB | ~20-25GB |

> **Note:** After running `./run_finewiki.sh index`, you can safely delete the parquet files if disk space is a concern.

---

## 🛠️ Development (Optional)

If you want to work on the code locally:

```bash
# Install dependencies
uv sync

# Run indexer directly (without Docker)
uv run python -m finewiki_mcp.indexer --parquet-dir finewiki_en --index-dir index_data

# Run server directly
uv run python -m finewiki_mcp.server --index-dir index_data --parquet-dir finewiki_en
```

---

## 📚 License

This project is provided as-is for educational and research purposes. Feel free to adapt and extend! 🚀

---

**Happy RAGging! 🧠✨**
