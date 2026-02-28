"""MCP Server for FineWiki with Tantivy search capabilities."""

import sys
import time
from pathlib import Path

import tantivy

try:
    from finewiki_mcp.common import get_schema
except ImportError:
    from common import get_schema


class FineWikiSearcher:
    """Searcher class that provides search and fetch functionality."""

    def __init__(self, index_dir: str | Path = "index_data", parquet_dir: str | Path = "finewiki_en"):
        self.index_path = Path(index_dir)
        # Try to open existing index, or create new one
        if (self.index_path / "segments").exists():
            self.index = tantivy.Index.open(self.index_path)
        else:
            self.index = tantivy.Index(get_schema(), path=str(self.index_path / '.index'))
        self.reader = self.index.searcher()

    def _get_document_by_id_from_index(self, doc_id: int) -> dict | None:
        """Get document from the index."""
        # Use parse_query with a numeric range to find document by ID
        query = self.index.parse_query(f"id:{doc_id}", ["id"])

        searcher = self.index.searcher()
        results = searcher.search(query, limit=1)

        if results.hits:
            score, doc_address = results.hits[0]
            doc = searcher.doc(doc_address)
            return {
                "id": doc.get_first("id"),
                "title": doc.get_first("title"),
                "content": doc.get_first("content"),
                "url": doc.get_first("url"),
            }
        return None

    def search_by_title(
        self, query: str, limit: int = 10
    ) -> list[dict]:
        """Search documents by title."""
        parsed_query = self.index.parse_query(query, ["title"])

        searcher = self.index.searcher()
        results = searcher.search(parsed_query, limit=limit)

        hits = []
        for score, doc_address in results.hits:
            doc = searcher.doc(doc_address)
            hits.append({
                "id": doc.get_first("id"),
                "title": doc.get_first("title"),
                "score": float(score),
            })

        return hits

    def search_by_content(
        self, query: str, limit: int = 10
    ) -> list[dict]:
        """Search documents by full content."""
        parsed_query = self.index.parse_query(query, ["content"])

        searcher = self.index.searcher()
        results = searcher.search(parsed_query, limit=limit)

        hits = []
        for score, doc_address in results.hits:
            doc = searcher.doc(doc_address)
            hits.append({
                "id": doc.get_first("id"),
                "title": doc.get_first("title"),
                "score": float(score),
            })

        return hits

    def fetch_content(self, doc_id: int) -> dict | None:
        """Fetch full content of a document by ID directly from the index."""
        return self._get_document_by_id_from_index(doc_id)


def create_app():
    """Create the MCP server application."""
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from pydantic import BaseModel

    class SearchByTitleRequest(BaseModel):
        query: str
        limit: int = 10

    class SearchByContentRequest(BaseModel):
        query: str
        limit: int = 10

    class FetchContentRequest(BaseModel):
        doc_id: int

    server = Server("finewiki-search")

    searcher: FineWikiSearcher | None = None

    # Define tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="search_by_title",
                description="Search for documents by title. Returns matching document IDs and titles.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query for titles"},
                        "limit": {"type": "integer", "description": "Maximum number of results (default: 10)"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="search_by_content",
                description="Search for documents by full content. Returns matching document IDs and titles.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query for content"},
                        "limit": {"type": "integer", "description": "Maximum number of results (default: 10)"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="fetch_content",
                description="Fetch the full content of a document by its ID. Returns id, title, content, and url.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "integer", "description": "Document ID to fetch"},
                    },
                    "required": ["doc_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[TextContent]:
        nonlocal searcher

        if name == "search_by_title":
            req = SearchByTitleRequest(**arguments)
            results = searcher.search_by_title(req.query, req.limit)
            return [TextContent(type="text", text=str(results))]

        elif name == "search_by_content":
            req = SearchByContentRequest(**arguments)
            results = searcher.search_by_content(req.query, req.limit)
            return [TextContent(type="text", text=str(results))]

        elif name == "fetch_content":
            req = FetchContentRequest(**arguments)
            content = searcher.fetch_content(req.doc_id)
            if content:
                return [TextContent(type="text", text=str(content))]
            return [TextContent(type="text", text="Document not found")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    def initialize_searcher(index_dir: str, parquet_dir: str):
        nonlocal searcher
        searcher = FineWikiSearcher(index_dir=index_dir)
        print(f"Loaded index from {index_dir}")

    return server, initialize_searcher



def run_test(index_dir: str, parquet_dir: str) -> None:
    """Run a quick test mode: load index and search for 'Banana' in titles and 'Mozart' in content."""
    import resource

    def get_memory_usage() -> float:
        """Get current memory usage in GB."""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is in KB on Linux, bytes on macOS
        if sys.platform == "darwin":
            return usage.ru_maxrss / (1024 * 1024 * 1024)
        else:
            return usage.ru_maxrss / (1024 * 1024)

    print(f"Test Mode - Loading index from {index_dir}...")

    start_time = time.time()
    searcher = FineWikiSearcher(index_dir=index_dir)
    load_time = time.time() - start_time
    mem_after_load = get_memory_usage()
    print(f"  Index loaded in {load_time:.3f}s")
    print(f"  Memory after loading: {mem_after_load:.2f} GB")

    # Search for 'Banana' in titles
    print("\nSearching for 'Banana' in titles...")
    start_time = time.time()
    title_results = searcher.search_by_title("Banana", limit=5)
    query_time = time.time() - start_time
    print(f"  Query completed in {query_time:.3f}s")
    print(f"  Found {len(title_results)} results:")
    for r in title_results:
        print(f"    - ID: {r['id']}, Title: {r['title']}, Score: {r['score']:.4f}")

    # Search for 'Mozart' in content
    print("\nSearching for 'Mozart' in content...")
    start_time = time.time()
    content_results = searcher.search_by_content("Mozart", limit=5)
    query_time = time.time() - start_time
    print(f"  Query completed in {query_time:.3f}s")
    print(f"  Found {len(content_results)} results:")
    for r in content_results:
        print(f"    - ID: {r['id']}, Title: {r['title']}, Score: {r['score']:.4f}")

    # Fetch full content of ALL Banana results
    if title_results:
        print("\nFetching full content of all 'Banana' results...")
        fetch_times = []
        for i, result in enumerate(title_results):
            start_time = time.time()
            content = searcher.fetch_content(result["id"])
            elapsed = time.time() - start_time
            fetch_times.append(elapsed)

            if content:
                print(f"  Result {i+1}: Fetch completed in {elapsed:.3f}s")
                print(f"    Title: {content['title']}")
                print(f"    Content length: {len(content['content'])} characters")
                preview = content["content"][:200].replace("\n", " ")
                print(f"    Preview: {preview}...")
            else:
                print(f"  Result {i+1}: Document not found")

        avg_fetch_time = sum(fetch_times) / len(fetch_times)
        total_fetch_time = sum(fetch_times)
        mem_after_fetch = get_memory_usage()
        print(f"\n  Total fetch time for {len(title_results)} results: {total_fetch_time:.3f}s")
        print(f"  Average fetch time per result: {avg_fetch_time*1000:.1f}ms")
        print(f"  Memory after fetching: {mem_after_fetch:.2f} GB")

    # Fetch full content of ALL Mozart results
    if content_results:
        print("\nFetching full content of all 'Mozart' results...")
        fetch_times = []
        for i, result in enumerate(content_results):
            start_time = time.time()
            content = searcher.fetch_content(result["id"])
            elapsed = time.time() - start_time
            fetch_times.append(elapsed)

            if content:
                print(f"  Result {i+1}: Fetch completed in {elapsed:.3f}s")
                print(f"    Title: {content['title']}")
                print(f"    Content length: {len(content['content'])} characters")
                preview = content["content"][:200].replace("\n", " ")
                print(f"    Preview: {preview}...")
            else:
                print(f"  Result {i+1}: Document not found")

        avg_fetch_time = sum(fetch_times) / len(fetch_times)
        total_fetch_time = sum(fetch_times)
        mem_after_all = get_memory_usage()
        print(f"\n  Total fetch time for {len(content_results)} results: {total_fetch_time:.3f}s")
        print(f"  Average fetch time per result: {avg_fetch_time*1000:.1f}ms")
        print(f"  Memory after fetching: {mem_after_all:.2f} GB")

    print("\nTest completed successfully!")


if __name__ == "__main__":
    import argparse
    import anyio

    parser = argparse.ArgumentParser(description="Run FineWiki MCP Server")
    parser.add_argument(
        "--index-dir",
        default="index_data",
        help="Directory containing the tantivy index (default: index_data)",
    )
    parser.add_argument(
        "--parquet-dir",
        default="finewiki_en",
        help="Directory containing parquet files (default: finewiki_en)",
    )
    parser.add_argument(
        "--mode",
        choices=["server", "test"],
        default="server",
        help="Mode to run in: 'server' for MCP server, 'test' for quick test (default: server)",
    )

    args = parser.parse_args()

    if args.mode == "test":
        run_test(args.index_dir, args.parquet_dir)
    else:
        server, init_searcher = create_app()
        init_searcher(args.index_dir, args.parquet_dir)

        async def main():
            from mcp.server.stdio import stdio_server
            from mcp.server import InitializationOptions, NotificationOptions

            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="finewiki-search",
                        server_version="0.1.0",
                        capabilities=server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )

        anyio.run(main)
