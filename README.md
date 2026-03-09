# 📚 Offline Knowledge MCP

A **Model Context Protocol (MCP)** server that provides unified search across ~21 million articles — FineWiki English (~6.6M) and FineWeb-Edu educational content (~14.4M). 🌐

**No API keys. No rate limits. No trackers. Just pure offline AI context! 💪**

> **Key Features:**
> - 🔍 Unified full-text search across both datasets with a single query
> - 🐳 Runs in Docker (no local dependencies needed)
> - ⚡ Uses Tantivy for lightning-fast indexing and search (~60ms fetch time)
> - 💾 Complete offline knowledge: 29GB + 71GB = 100GB for ~21M articles
> - 📖 Aggregated tools: `text_search_knowledge` and `fetch_knowledge`
> 
---

## 🎯 What is This?

This MCP server gives you **unlimited offline context** by combining Wikipedia and curated educational web content into a single searchable knowledge base. Perfect for research, fact-checking, or any AI application that needs reliable offline information.

Think of it as your own personal offline Google + Wikipedia API running entirely on your machine. 🏠

---

## 📥 Download Parquet Files

### FineWiki English Dataset (Wikipedia)

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

### FineWeb-Edu Dataset (Educational Web)

FineWeb-Edu contains curated educational content from the web (~14.4M articles).

```bash
# Place your fineweb-edu parquet files in ./fineweb-edu/
mkdir -p fineweb-edu
# Copy or download parquet files here
```

---

## 🐳 Docker Setup (Recommended)

### Step 1: Build Both Indexes

**Build FineWiki index (~30 minutes):**
```bash
./run_finewiki.sh index --dataset finewiki
```

**Build FineWeb-Edu index (~60-90 minutes):**
```bash
./run_finewiki.sh index --dataset fineweb-edu
```

This will:
- Build the Docker image (once)
- Scan all `.parquet` files in the specified directory
- Create Tantivy search indexes:
  - `index_data/` → FineWiki (~29GB for 6.6M articles)
  - `index_data_fineweb_edu/` → FineWeb-Edu (~71GB for ~14.4M articles)
- **Note:** After indexing, you can delete parquet files — all content is in the index

### Step 2: Start the MCP Server

```bash
./run_finewiki.sh server --dataset finewiki
```

The server automatically loads both indexes and exposes unified search tools.

---

## 🧪 Testing

Run the built-in test to verify everything works:

```bash
./run_finewiki.sh test --index-dir index_data
```

**Expected output:**
```
Test Mode - Testing aggregated knowledge tools
FineWiki index: /host_project/index_data
  FineWiki index loaded in 0.003s
  Memory after loading: 0.04 GB
  FineWeb-Edu index loaded from /host_project/index_data_fineweb_edu
  Memory after both indices loaded: 0.06 GB

======================================================================
Testing text_search_knowledge + fetch_knowledge tools
======================================================================

--- Query: 'machine learning' ---
  Search completed in X.XXXs
  Found XX total results (X Wikipedia, X Educational)
...

======================================================================
SUMMARY
======================================================================
Queries tested: 3
Total fetches performed: 6
Average fetch time: ~60ms
Final memory usage: ~0.32 GB

✓ All tests completed successfully!
```

---

## 🤖 Integrating with MCP Clients

### Sample Configuration

**For Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "offline-knowledge": {
      "command": "bash",
      "args": [
        "/path/to/finewiki_mcp/run_finewiki.sh",
        "server",
        "--dataset",
        "finewiki"
      ]
    }
  }
}
```

**For other MCP clients:**

```json
{
  "offline-knowledge": {
    "command": "docker",
    "args": [
      "run",
      "--rm",
      "-v", "/path/to/index_data:/host_project/index_data:ro",
      "-v", "/path/to/index_data_fineweb_edu:/host_project/index_data_fineweb_edu:ro",
      "offline-knowledge-mcp:latest"
    ]
  }
}
```

> **Note:** Replace `/path/to/` with your actual paths to the repository and index directories.

---

## 🧰 Available Tools

The MCP server exposes two unified search tools that work across both datasets:

| Tool | Description |
|------|-------------|
| `text_search_knowledge` | Search ~21M articles simultaneously — returns up to 20 results split between Wikipedia and educational web content. IDs are prefixed with `wiki:` or `edu:` for unified fetching. |
| `fetch_knowledge` | Fetch full content by prefixed ID (`wiki:12345` or `edu:abc-def`). Returns complete article/document with all available fields. |

### Tool Usage Examples

**Example 1: Research query across both sources**
```json
{
  "name": "text_search_knowledge",
  "arguments": {
    "query": "machine learning"
  }
}
```
*Returns:* ~20 results (e.g., 10 Wikipedia + 10 Educational) with IDs like:
- `wiki:34567` → Wikipedia article about machine learning
- `edu:ml-tutorial-2024` → Educational tutorial on ML

**Example 2: Fetch full content from search results**
```json
{
  "name": "fetch_knowledge",
  "arguments": {
    "doc_id": "wiki:34567"
  }
}
```
*Returns:* Complete Wikipedia article with `id`, `title`, `content`, `url`.

```json
{
  "name": "fetch_knowledge",
  "arguments": {
    "doc_id": "edu:ml-tutorial-2024"
  }
}
```
*Returns:* Educational document with `id`, `text`, `url`, `dump`, `date`, `language`.

---

## 🏗️ Project Structure

```
finewiki_mcp/
├── src/finewiki_mcp/
│   ├── __init__.py       # Package initialization (exports searcher classes)
│   ├── common.py         # Shared utilities (Tantivy schema definitions)
│   ├── indexer.py        # Index generation from Parquet files
│   ├── searcher.py       # FineWikiSearcher, FineWebEduSearcher, aggregate_search()
│   ├── server.py         # MCP server with text_search_knowledge + fetch_knowledge
│   └── tester.py         # Test utilities (tests aggregated knowledge tools)
├── index_data/           # FineWiki Tantivy index (~29GB for 6.6M articles) 🗂️
├── index_data_fineweb_edu/  # FineWeb-Edu index (~71GB for ~14.4M articles) 🗂️
├── finewiki_en/          # FineWiki parquet files (optional after indexing) 📦
├── fineweb-edu/          # FineWeb-Edu parquet files (optional after indexing) 📦
├── run_finewiki.sh       # Docker runner script (index/server/test modes) ⚙️
├── links.sh              # Downloads for FineWiki parquet files 🔗
├── pyproject.toml        # Project dependencies (tantivy, mcp)
└── README.md             # This documentation 📖
```

---

## 🔧 How It Works

1. **Indexing** 📝
   Uses [Tantivy](https://github.com/quickwit-oss/tantivy) to create fast full-text search indexes from Parquet files.

   **FineWiki schema:**
   - `id`: Document identifier (integer, stored, indexed)
   - `title`: Article title (stored, indexed)
   - `content`: Full article text (stored, indexed)
   - `url`: Source URL (stored, indexed)

   **FineWeb-Edu schema:**
   - `id`: String document identifier (stored, indexed)
   - `text`: Main educational content (stored, indexed)
   - `dump`: Dump date/source identifier (stored, indexed)
   - `url`: Source URL (stored, indexed)
   - `date`: Content date (stored, indexed)
   - `file_path`: Original file path (stored, indexed)
   - `language`: Language code (stored, indexed)

2. **Aggregated Search** 🔍
   The `aggregate_search()` function queries both indexes simultaneously:
   ```python
   def aggregate_search(wiki_searcher, edu_searcher, query, total_limit=20):
       # Split limit between sources (default 10-10)
       wiki_results = wiki_searcher.search_by_content(query, limit=half)
       edu_results = edu_searcher.search_by_text(query, limit=remaining)
       
       # Prefix IDs for unified fetching
       combined = [
           {"id": f"wiki:{hit['id']}", ...} for hit in wiki_results
       ] + [
           {"id": f"edu:{hit['id']}", ...} for hit in edu_results
       ]
       return combined
   ```

3. **Unified Fetching** 📚
   The `fetch_knowledge` tool parses the prefix and fetches from the appropriate source:
   - `wiki:12345` → Calls `FineWikiSearcher.fetch_content(12345)`
   - `edu:abc-def` → Calls `FineWebEduSearcher.fetch_content("abc-def")`

---

## 📊 Storage Requirements

| Dataset | Articles | Index Size | Parquet Files (optional) |
|---------|----------|------------|--------------------------|
| FineWiki English | ~6.6M | **29GB** | ~20-25GB |
| FineWeb-Edu | ~14.4M | **71GB** | Varies |
| **Total** | **~21M** | **100GB** | — |

> **Note:** After running `./run_finewiki.sh index`, you can safely delete the parquet files.

### Performance Benchmarks (from test run)

```
Index loaded: ~3ms per searcher
Memory usage:
  - FineWiki only: 0.04 GB
  - Both indexes: 0.06 GB
  - After operations: 0.32 GB max

Average fetch time: ~60ms (with both indexes loaded)
```

---

## 🛠️ Development (Optional)

Work on the code locally without Docker:

```bash
# Install dependencies
uv sync

# Run indexer directly (FineWiki)
uv run python -m finewiki_mcp.indexer \
    --parquet-dir finewiki_en \
    --index-dir index_data

# Run server in test mode
uv run python -m finewiki_mcp.server \
    --index-dir index_data \
    --mode test
```

---

## 📚 License

This project is provided as-is for educational and research purposes. Feel free to adapt and extend! 🚀

---

**Offline knowledge, unlimited context! 🧠✨**
