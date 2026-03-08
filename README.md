# 🌊 FineWiki MCP Server

A **Model Context Protocol (MCP)** server that provides search and content retrieval for the FineWiki English dataset and FineWeb-Edu. 📚

**No API keys. No rate limits. No trackers. Just pure offline AI context! 💪**

> **Key Features:**
> - 🔍 Fast full-text search across multi-gigabyte datasets
> - 🐳 Runs in Docker (no local dependencies needed)
> - ⚡ Uses Tantivy for lightning-fast indexing and search (~20ms content retrieval)
> - 💾 All-inclusive index: 30GB for 6.6M articles (parquet files optional after indexing)
> - 📖 Supports both FineWiki (Wikipedia-like) and FineWeb-Edu (curated web education)

---

## 🎯 What is This?

This is a **sample project** demonstrating how to integrate large datasets as MCP tools — giving you unlimited offline context for your AI applications without any tracking, keys, or restrictions!

Think of it as your own personal Wikipedia API that runs entirely on your machine. 🏠

---

## 📥 Download Parquet Files

### FineWiki English Dataset

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

### FineWeb-Edu Dataset

FineWeb-Edu contains curated educational content from the web. Download parquet files to `fineweb-edu/` directory:

```bash
# Place your fineweb-edu parquet files in ./fineweb-edu/
mkdir -p fineweb-edu
# Copy or download parquet files here
```

---

## 🐳 Docker Setup (Recommended)

This project runs entirely inside Docker — no Python installation required!

### Step 1: Build the Index

**For FineWiki:**
```bash
./run_finewiki.sh index
# Or explicitly: ./run_finewiki.sh index --dataset finewiki
```

**For FineWeb-Edu:**
```bash
./run_finewiki.sh index --dataset fineweb-edu
```

This will:
- Build the Docker image (once)
- Scan all `.parquet` files in the specified directory
- Create the search index in `index_data/` (or `index_data_fineweb_edu/`)
- **Note:** After indexing, you can optionally delete parquet files as all content is now stored in the index

### Step 2: Start the MCP Server

**For FineWiki:**
```bash
./run_finewiki.sh server
# Or explicitly: ./run_finewiki.sh server --dataset finewiki
```

**For FineWeb-Edu:**
```bash
./run_finewiki.sh server --dataset fineweb-edu
```

The server is now running and ready to accept MCP connections!

> **Note:** The server automatically loads both indexes if they exist, making all tools available.

---

## 🧪 Testing

Run the built-in test to verify everything works:

**For FineWiki:**
```bash
./run_finewiki.sh test
```

**For FineWeb-Edu:**
```bash
./run_finewiki.sh test --index-dir index_data_fineweb_edu --parquet-dir fineweb-edu
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

The MCP server exposes powerful search tools for both FineWiki and FineWeb-Edu datasets.

### FineWiki Tools (Wikipedia-like articles)

| Tool | Description |
|------|-------------|
| `search_by_title` | Search for articles by title (fast!) |
| `search_by_content` | Full-text search across all article content |
| `fetch_content` | Get the complete article by ID |

### FineWeb-Edu Tools (Curated web education)

| Tool | Description |
|------|-------------|
| `fineweb_search_by_text` | Search educational content by text |
| `fineweb_search_by_dump` | Filter content by dump date (YYYY-MM) |
| `fineweb_search_by_language` | Filter content by language code |
| `fineweb_search_by_date` | Filter content by specific date (YYYY-MM-DD) |
| `fetch_edu_content` | Get the complete document by ID |

### Tool Usage Examples

**FineWiki:**
- Use `search_by_title` when you know the article name
- Use `search_by_content` to find articles containing specific information
- Use `fetch_content` with a document ID from search results to get full content

**FineWeb-Edu:**
- Use `fineweb_search_by_text` for general educational content search
- Use `fineweb_search_by_dump` to find content from specific time periods
- Use `fineweb_search_by_language` to filter by language (e.g., 'en', 'es')
- Use `fetch_edu_content` with a document ID to get full educational articles

---

## 🏗️ Project Structure

```
finewiki_mcp/
├── src/finewiki_mcp/
│   ├── __init__.py       # Package initialization
│   ├── common.py         # Shared utilities (schema definitions)
│   ├── indexer.py        # Index generation script
│   └── server.py         # MCP server implementation
├── index_data/           # FineWiki Tantivy index storage 🗂️
├── index_data_fineweb_edu/  # FineWeb-Edu index storage 🗂️
├── finewiki_en/          # FineWiki parquet files (can delete after indexing) 📦
├── fineweb-edu/          # FineWeb-Edu parquet files (can delete after indexing) 📦
├── run_finewiki.sh       # Docker runner script ⚙️
├── pyproject.toml        # Project dependencies
└── README.md
```

---

## 🔧 How It Works

1. **Indexing** 📝
   Uses [Tantivy](https://github.com/quickwit-oss/tantivy) to create a fast full-text search index from Parquet files.

   **FineWiki schema:**
   - `id`: Document identifier (integer, stored, indexed)
   - `title`: Document title (stored, indexed)
   - `content`: Full text content (stored, indexed)
   - `url`: Source URL (stored, indexed)

   **FineWeb-Edu schema:**
   - `id`: String document identifier (stored, indexed)
   - `text`: Main educational content (stored, indexed)
   - `dump`: Dump date/source identifier (stored, indexed)
   - `url`: Source URL (stored, indexed)
   - `date`: Content date (stored, indexed)
   - `file_path`: Original file path (stored, indexed)
   - `language`: Language code (stored, indexed)

2. **Storage** 💾
   After indexing (~30GB for 6.6M FineWiki articles), parquet files are no longer needed. All content is stored directly in the index.

3. **Search** 🔍
   Query parsing using Tantivy's powerful query parser with fuzzy matching

4. **Fetching** 📚
   Direct access to indexed content - no file lookups required!

---

## 📊 Storage Requirements

| Dataset | Articles | Index Size | Parquet Files (optional) |
|---------|----------|------------|--------------------------|
| FineWiki English | 6.6M | ~30GB | ~20-25GB |
| FineWeb-Edu | Varies | Depends on content | Varies |

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
