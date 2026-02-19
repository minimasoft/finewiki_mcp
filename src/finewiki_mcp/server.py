"""MCP Server for FineWiki with Tantivy search capabilities."""

import time
from pathlib import Path

import tantivy
import pyarrow.parquet as pq


def get_schema() -> tantivy.Schema:
    """Return the schema used for the index."""
    schema_builder = tantivy.SchemaBuilder()
    schema_builder.add_integer_field("id", stored=True)
    schema_builder.add_text_field("title", stored=True, index_option="position")
    schema_builder.add_text_field("content", stored=False, index_option="position")
    schema_builder.add_text_field("url", stored=True, index_option="position")
    return schema_builder.build()


class FineWikiSearcher:
    """Searcher class that provides search and fetch functionality."""

    def __init__(self, index_dir: str | Path = "index_data", parquet_dir: str | Path = "finewiki_en"):
        self.index_path = Path(index_dir)
        self.parquet_dir = Path(parquet_dir)
        # Try to open existing index, or create new one
        if (self.index_path / "segments").exists():
            self.index = tantivy.Index.open(self.index_path)
        else:
            self.index = tantivy.Index(get_schema(), path=str(self.index_path))
        self.reader = self.index.searcher()
        self._parquet_files: list[pq.ParquetFile] | None = None

    def _load_parquet_files(self) -> list[pq.ParquetFile]:
        """Lazy load parquet files for content fetching."""
        if self._parquet_files is None:
            self._parquet_files = []
            for pf in sorted(self.parquet_dir.glob("*.parquet")):
                self._parquet_files.append(pq.ParquetFile(pf))
        return self._parquet_files

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
                "url": doc.get_first("url"),
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
                "url": doc.get_first("url"),
                "score": float(score),
            })

        return hits

    def fetch_content(self, doc_id: int) -> dict | None:
        """Fetch full content of a document by ID from parquet files."""
        parquet_files = self._load_parquet_files()

        for pf in parquet_files:
            table = pf.read().to_pandas()
            if doc_id in table["page_id"].values:
                row = table[table["page_id"] == doc_id].iloc[0]
                return {
                    "id": int(row["page_id"]),
                    "title": str(row.get("title", "")),
                    "content": str(row.get("text", "")),
                    "url": str(row.get("url", "")),
                }

        return None

    def get_document_by_id(self, doc_id: int) -> dict | None:
        """Get document metadata from the index (without full content)."""
        query = tantivy.QueryTerm(tantivy.Term.from_u64("id", doc_id), indexed=True)
        searcher = self.index.searcher()
        results = searcher.search(query, limit=1)

        if results.hits:
            score, doc_address = results.hits[0]
            doc = searcher.doc(doc_address)
            return {
                "id": doc.get_first("id"),
                "title": doc.get_first("title"),
                "url": doc.get_first("url"),
                "score": float(score),
            }
        return None


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
                description="Search for documents by title. Returns matching document IDs, titles, URLs and scores.",
                parameters={
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
                description="Search for documents by full content. Returns matching document IDs, titles, URLs and scores.",
                parameters={
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
                parameters={
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
        searcher = FineWikiSearcher(index_dir=index_dir, parquet_dir=parquet_dir)
        print(f"Loaded index from {index_dir}")

    return server, initialize_searcher



def run_test(index_dir: str, parquet_dir: str) -> None:
    """Run a quick test mode: load index and search for 'Banana' in titles and 'Mozart' in content."""
    print(f"Test Mode - Loading index from {index_dir}...")
    
    start_time = time.time()
    searcher = FineWikiSearcher(index_dir=index_dir, parquet_dir=parquet_dir)
    load_time = time.time() - start_time
    print(f"  Index loaded in {load_time:.3f}s")
    
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
