# FineWiki MCP - Development Guidelines for Agentic Coding Agents

## Build, Lint & Test Commands

### Project Setup
```bash
# Install dependencies with uv (recommended)
uv sync

# Alternative: pip install
cd src && pip install -e .
```

### Run Commands
- **MCP Server:** `uv run python src/finewiki_mcp/server.py --index-dir index_data`
- **Indexer (FineWiki):** `uv run python -m finewiki_mcp.indexer --dataset finewiki`
- **Indexer (Fineweb-Edu):** `uv run python -m finewiki_mcp.indexer --dataset fineweb-edu`

### Testing
**Note:** This project uses custom integration tests in `tester.py` rather than pytest unit tests.

```bash
# Run the built-in test mode (search + fetch verification)
uv run python src/finewiki_mcp/server.py --index-dir index_data --mode test

# Or via Docker runner:
./run.sh test --index-dir index_data
```

**Expected output:** Test queries against both indexes, reporting search times (~60ms per fetch), memory usage, and result counts.

### Linting (Ruff)
```bash
uv run ruff check src/
uv run ruff format src/ --check
```

---

## Code Style Guidelines

### Import Organization
1. Standard library imports first
2. Third-party packages second  
3. Local package imports last (with ImportError fallback pattern for flexibility)

```python
import json           # stdlib - 1st
from pathlib import Path
import tantivy        # third-party - 2nd

try:
    from finewiki_mcp.searcher import FineWikiSearcher  # local - 3rd
except ImportError:
    from searcher import FineWikiSearcher               # fallback for standalone execution
```

### Type Hints & Python Version
- Minimum Python version: **3.14**
- Use modern union syntax: `str | None`, not `Optional[str]`
- Use built-in collection types over typing module:
  - ✅ `list[dict]`, `dict[str, int]`  
  - ❌ `List[Dict]`, `Dict[str, int]`

```python
def search_by_title(self, query: str, limit: int = 10) -> list[dict]:
    """Search documents by title."""
```

### Docstrings (Google Style)
- Always include docstrings for functions and classes
- Format:
```python
def example_function(arg: str) -> bool:
    """Brief description on one line.

    Longer description if needed. Explains behavior, edge cases.

    Args:
        arg: Description of the argument.

    Returns:
        Description of return value.

    Raises:
        ValueError: When this happens.
    """
```

### Naming Conventions
- **Classes:** `PascalCase` (e.g., `FineWikiSearcher`, `TextSearchKnowledgeRequest`)
- **Functions/variables:** `snake_case` (e.g., `aggregate_search`, `index_dir`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `METADATA_FILE`)
- **Private members:** Single underscore prefix (e.g., `_get_document_by_id_from_index`)

### Error Handling
- Use explicit exception handling where failures are expected
- Return `None` for optional lookups that may not exist
- Raise specific exceptions with clear messages:
```python
if not parquet_dir.exists():
    raise FileNotFoundError(f"Parquet directory not found: {parquet_dir}")
```

### Code Organization Principles
1. **Single Responsibility:** Each module has a focused purpose:
   - `common.py`: Shared utilities, schema definitions
   - `indexer.py`: Index creation from parquet files
   - `searcher.py`: Search functionality (classes + aggregation)
   - `server.py`: MCP server tool definitions and routing
   - `tester.py`: Integration test utilities

2. **Immutability:** Prefer immutable data structures where possible; avoid mutation of inputs.

3. **Async/Await:** Use async for I/O-bound operations (network, file reads). The MCP server uses `async/await` with `anyio.run()`.

4. **Path Handling:** Always use `pathlib.Path` over string paths. Handle both string and Path arguments in public APIs.

5. **Documentation:** Tool descriptions for the MCP server must be comprehensive, explaining:
   - What the tool does
   - When to use it (use cases)
   - Input/output format
   - Examples of usage

---

## Architecture Notes

### Searcher Pattern
Both `FineWikiSearcher` and `FineWebEduSearcher` follow identical interfaces:
- `search_*()` methods return lists of dicts with `id`, preview text, score
- `fetch_content(id)` returns full document dict or `None`
- IDs are prefixed (`wiki:`, `edu:`) at the aggregation layer for unified fetching

### Tantivy Integration
- Use `Index.open()` for existing indexes, `Index(schema, path=...)` for new ones
- Always create a fresh index directory before building to avoid conflicts
- Store metadata in `indexed_files.json` for incremental tracking

---

## Adding New Features
1. Check if the feature fits existing module responsibilities
2. Add type hints and docstrings consistently
3. Update tool descriptions in `server.py` if adding MCP tools
4. Consider updating `tester.py` or add pytest tests if appropriate
5. Run `ruff check` before committing