# 🌊 FineWiki MCP Server

A **Model Context Protocol (MCP)** server that provides search and content retrieval for the FineWiki English dataset. 📚

**No API keys. No rate limits. No trackers. Just pure offline AI context! 💪**

> **Key Features:**
> - 🔍 Fast full-text search across multi-gigabyte datasets
> - 🐳 Runs in Docker (no local dependencies needed)
> - ⚡ Uses Tantivy for lightning-fast indexing and search
> - 📦 Works with Parquet files for efficient columnar storage

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

### Step 2: Start the MCP Server

```bash
./run_finewiki.sh server
```

The server is now running and ready to accept MCP connections!

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
├── finewiki_en/          # Parquet files directory 📦
├── run_finewiki.sh       # Docker runner script ⚙️
├── pyproject.toml        # Project dependencies
└── README.md
```

---

## 🔧 How It Works

1. **Indexing** 📝  
   Uses [Tantivy](https://github.com/quickwit-oss/tantivy) to create a fast full-text search index from Parquet files

2. **Storage** 💾  
   Index stores id, title, and url; content stays in Parquet files (no duplication!)

3. **Search** 🔍  
   Query parsing using Tantivy's powerful query parser with fuzzy matching

4. **Fetching** 📚  
   Direct access to Parquet files using PyArrow for efficient columnar reading

---

## 🧪 Testing

Run the built-in test to verify everything works:

```bash
./run_finewiki.sh test
```

This searches for "Banana" in titles and "Mozart" in content.

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
