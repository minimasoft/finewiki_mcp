"""MCP Server for FineWiki and FineWeb-Edu with Tantivy search capabilities."""

import sys
import time
from pathlib import Path

import tantivy

try:
    from finewiki_mcp.common import get_schema
except ImportError:
    from common import get_schema


class FineWikiSearcher:
    """Searcher class for FineWiki dataset.

    Provides search and fetch functionality for Wikipedia-like articles.
    Supports searching by title and content, with document fetching by ID.
    """

    def __init__(self, index_dir: str | Path = "index_data", parquet_dir: str | Path = "finewiki_en"):
        self.index_path = Path(index_dir)
        # Try to open existing index, or create new one
        if (self.index_path / "segments").exists():
            self.index = tantivy.Index.open(self.index_path)
        else:
            self.index = tantivy.Index(get_schema("finewiki"), path=str(self.index_path / '.index'))
        self.reader = self.index.searcher()

    def _get_document_by_id_from_index(self, doc_id: int) -> dict | None:
        """Get document from the index by ID.

        Args:
            doc_id: Integer document ID (Wikipedia page ID).

        Returns:
            Dictionary with id, title, content, url or None if not found.
        """
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
        """Search documents by title.

        Args:
            query: Search query for titles.
            limit: Maximum number of results to return (default: 10).

        Returns:
            List of dictionaries with id, title, and score.
        """
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
        """Search documents by full content.

        Args:
            query: Search query for content.
            limit: Maximum number of results to return (default: 10).

        Returns:
            List of dictionaries with id, title, and score.
        """
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
        """Fetch full content of a document by ID.

        Args:
            doc_id: Integer document ID to fetch.

        Returns:
            Dictionary with id, title, content, url or None if not found.
        """
        return self._get_document_by_id_from_index(doc_id)


class FineWebEduSearcher:
    """Searcher class for FineWeb-Edu dataset.

    Provides search and fetch functionality for educative web content.
    Supports searching by text, dump, date, language, and URL fields.
    Documents are fetched by string ID.

    Dataset schema:
        - id: String identifier for the document
        - text: Main educational content text
        - dump: Dump date/source identifier
        - url: Source URL of the content
        - date: Content date
        - file_path: Original file path
        - language: Language code
    """

    def __init__(self, index_dir: str | Path = "index_data_fineweb_edu", parquet_dir: str | Path = "fineweb-edu"):
        self.index_path = Path(index_dir)
        # Try to open existing index, or create new one
        if (self.index_path / "segments").exists():
            self.index = tantivy.Index.open(self.index_path)
        else:
            self.index = tantivy.Index(get_schema("fineweb-edu"), path=str(self.index_path / '.index'))
        self.reader = self.index.searcher()

    def _get_document_by_id_from_index(self, doc_id: str) -> dict | None:
        """Get document from the index by ID.

        Args:
            doc_id: String document ID.

        Returns:
            Dictionary with all document fields or None if not found.
        """
        query = self.index.parse_query(f"id:\"{doc_id}\"", ["id"])

        searcher = self.index.searcher()
        results = searcher.search(query, limit=1)

        if results.hits:
            score, doc_address = results.hits[0]
            doc = searcher.doc(doc_address)
            return {
                "id": doc.get_first("id"),
                "text": doc.get_first("text"),
                "dump": doc.get_first("dump"),
                "url": doc.get_first("url"),
                "date": doc.get_first("date"),
                "language": doc.get_first("language"),
            }
        return None

    def search_by_text(
        self, query: str, limit: int = 10
    ) -> list[dict]:
        """Search documents by text content.

        Args:
            query: Search query for educational content.
            limit: Maximum number of results to return (default: 10).

        Returns:
            List of dictionaries with id, text preview, and score.
        """
        parsed_query = self.index.parse_query(query, ["text"])

        searcher = self.index.searcher()
        results = searcher.search(parsed_query, limit=limit)

        hits = []
        for score, doc_address in results.hits:
            doc = searcher.doc(doc_address)
            text = doc.get_first("text") or ""
            # Provide a preview of the text (first 200 chars)
            text_preview = text[:200] + "..." if len(text) > 200 else text
            hits.append({
                "id": doc.get_first("id"),
                "text_preview": text_preview,
                "score": float(score),
            })

        return hits

    def search_by_dump(
        self, dump: str, limit: int = 10
    ) -> list[dict]:
        """Search documents by dump identifier.

        Args:
            dump: Dump date/identifier to filter by (e.g., "2024-01").
            limit: Maximum number of results to return (default: 10).

        Returns:
            List of dictionaries with id, dump, and score.
        """
        parsed_query = self.index.parse_query(f"dump:\"{dump}\"", ["dump"])

        searcher = self.index.searcher()
        results = searcher.search(parsed_query, limit=limit)

        hits = []
        for score, doc_address in results.hits:
            doc = searcher.doc(doc_address)
            hits.append({
                "id": doc.get_first("id"),
                "dump": doc.get_first("dump"),
                "score": float(score),
            })

        return hits

    def search_by_language(
        self, language: str, limit: int = 10
    ) -> list[dict]:
        """Search documents by language.

        Args:
            language: Language code to filter by (e.g., "en", "es").
            limit: Maximum number of results to return (default: 10).

        Returns:
            List of dictionaries with id, language, and score.
        """
        parsed_query = self.index.parse_query(f"language:\"{language}\"", ["language"])

        searcher = self.index.searcher()
        results = searcher.search(parsed_query, limit=limit)

        hits = []
        for score, doc_address in results.hits:
            doc = searcher.doc(doc_address)
            hits.append({
                "id": doc.get_first("id"),
                "language": doc.get_first("language"),
                "score": float(score),
            })

        return hits

    def search_by_date(
        self, date: str, limit: int = 10
    ) -> list[dict]:
        """Search documents by date.

        Args:
            date: Date string to filter by (e.g., "2024-01-15").
            limit: Maximum number of results to return (default: 10).

        Returns:
            List of dictionaries with id, date, and score.
        """
        parsed_query = self.index.parse_query(f"date:\"{date}\"", ["date"])

        searcher = self.index.searcher()
        results = searcher.search(parsed_query, limit=limit)

        hits = []
        for score, doc_address in results.hits:
            doc = searcher.doc(doc_address)
            hits.append({
                "id": doc.get_first("id"),
                "date": doc.get_first("date"),
                "score": float(score),
            })

        return hits

    def fetch_content(self, doc_id: str) -> dict | None:
        """Fetch full content of a document by ID.

        Args:
            doc_id: String document ID to fetch.

        Returns:
            Dictionary with all document fields or None if not found.
        """
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

    class SearchByTextRequest(BaseModel):
        query: str
        limit: int = 10

    class SearchByDumpRequest(BaseModel):
        dump: str
        limit: int = 10

    class SearchByLanguageRequest(BaseModel):
        language: str
        limit: int = 10

    class SearchByDateRequest(BaseModel):
        date: str
        limit: int = 10

    class FetchEduContentRequest(BaseModel):
        doc_id: str

    server = Server("finewiki-search")

    finewiki_searcher: FineWikiSearcher | None = None
    fineweb_edu_searcher: FineWebEduSearcher | None = None

    # Define tools with comprehensive documentation for LLM usage
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="search_by_title",
                description="""Search for Wikipedia articles by title.

Use this when you know the exact or partial title of an article you're looking for.
Returns matching document IDs and titles that can be used with fetch_content.

Best for: Looking up specific topics, people, places, or concepts by name.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query - article title or keywords (e.g., 'Banana', 'Albert Einstein')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10, max: 100)"
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="search_by_content",
                description="""Search Wikipedia articles by full content.

Use this when you're looking for articles containing specific information,
but don't know the exact title. Searches the entire article text.

Best for: Finding articles about concepts, facts, or detailed information.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query - keywords or phrases to find in article content"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10, max: 100)"
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="fetch_content",
                description="""Fetch the full content of a Wikipedia article by ID.

Use this after getting a document ID from search_by_title or search_by_content.
Returns the complete article with id, title, content, and url.

Best for: Getting detailed information about a specific topic.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doc_id": {
                            "type": "integer",
                            "description": "The document ID (Wikipedia page ID) to fetch"
                        },
                    },
                    "required": ["doc_id"],
                },
            ),
            Tool(
                name="fineweb_search_by_text",
                description="""Search FineWeb-Edu educational content by text.

FineWeb-Edu contains curated educational content from the web. Use this to find
educational articles, tutorials, documentation, and learning materials.

Returns document IDs with text previews that can be used with fetch_edu_content.

Best for: Finding educational resources, tutorials, documentation, and learning materials.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query - keywords or phrases in educational content"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10, max: 100)"
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="fineweb_search_by_dump",
                description="""Search FineWeb-Edu content by dump identifier.

FineWeb-Edu content is organized by dumps (date-based collections). Use this to
find all educational content from a specific time period.

Dump format: YYYY-MM (e.g., "2024-01" for January 2024)

Best for: Finding content from specific time periods or analyzing temporal trends.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dump": {
                            "type": "string",
                            "description": "Dump identifier (format: YYYY-MM, e.g., '2024-01')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)"
                        },
                    },
                    "required": ["dump"],
                },
            ),
            Tool(
                name="fineweb_search_by_language",
                description="""Search FineWeb-Edu content by language.

FineWeb-Edu contains educational content in multiple languages. Use this to
filter results by language code.

Language codes: 'en' (English), 'es' (Spanish), 'fr' (French), etc.

Best for: Finding educational content in a specific language.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "language": {
                            "type": "string",
                            "description": "Language code (e.g., 'en', 'es', 'fr', 'de')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)"
                        },
                    },
                    "required": ["language"],
                },
            ),
            Tool(
                name="fineweb_search_by_date",
                description="""Search FineWeb-Edu content by specific date.

Use this to find educational content from a specific date. More precise than
search_by_dump when you need exact date filtering.

Date format: YYYY-MM-DD (e.g., "2024-01-15")

Best for: Finding content published on or around a specific date.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date string (format: YYYY-MM-DD, e.g., '2024-01-15')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)"
                        },
                    },
                    "required": ["date"],
                },
            ),
            Tool(
                name="fetch_edu_content",
                description="""Fetch the full content of a FineWeb-Edu document by ID.

Use this after getting a document ID from fineweb_search_by_text, 
fineweb_search_by_dump, fineweb_search_by_language, or fineweb_search_by_date.
Returns complete document with id, text, dump, url, date, file_path, and language.

Best for: Getting full educational articles, tutorials, or documentation.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doc_id": {
                            "type": "string",
                            "description": "The document ID (string identifier) to fetch"
                        },
                    },
                    "required": ["doc_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[TextContent]:
        nonlocal finewiki_searcher, fineweb_edu_searcher

        # FineWiki tools
        if name == "search_by_title":
            req = SearchByTitleRequest(**arguments)
            results = finewiki_searcher.search_by_title(req.query, req.limit)
            return [TextContent(type="text", text=str(results))]

        elif name == "search_by_content":
            req = SearchByContentRequest(**arguments)
            results = finewiki_searcher.search_by_content(req.query, req.limit)
            return [TextContent(type="text", text=str(results))]

        elif name == "fetch_content":
            req = FetchContentRequest(**arguments)
            content = finewiki_searcher.fetch_content(req.doc_id)
            if content:
                return [TextContent(type="text", text=str(content))]
            return [TextContent(type="text", text="Document not found")]

        # FineWeb-Edu tools
        elif name == "fineweb_search_by_text":
            req = SearchByTextRequest(**arguments)
            results = fineweb_edu_searcher.search_by_text(req.query, req.limit)
            return [TextContent(type="text", text=str(results))]

        elif name == "fineweb_search_by_dump":
            req = SearchByDumpRequest(**arguments)
            results = fineweb_edu_searcher.search_by_dump(req.dump, req.limit)
            return [TextContent(type="text", text=str(results))]

        elif name == "fineweb_search_by_language":
            req = SearchByLanguageRequest(**arguments)
            results = fineweb_edu_searcher.search_by_language(req.language, req.limit)
            return [TextContent(type="text", text=str(results))]

        elif name == "fineweb_search_by_date":
            req = SearchByDateRequest(**arguments)
            results = fineweb_edu_searcher.search_by_date(req.date, req.limit)
            return [TextContent(type="text", text=str(results))]

        elif name == "fetch_edu_content":
            req = FetchEduContentRequest(**arguments)
            content = fineweb_edu_searcher.fetch_content(req.doc_id)
            if content:
                return [TextContent(type="text", text=str(content))]
            return [TextContent(type="text", text="Document not found")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    def initialize_searchers(index_dir: str, parquet_dir: str):
        nonlocal finewiki_searcher, fineweb_edu_searcher
        finewiki_searcher = FineWikiSearcher(index_dir=index_dir)
        print(f"Loaded FineWiki index from {index_dir}")

        # Try to load fineweb-edu index if it exists
        fineweb_index_dir = Path("index_data_fineweb_edu")
        if (fineweb_index_dir / "segments").exists() or (fineweb_index_dir / ".index" / "segments").exists():
            fineweb_edu_searcher = FineWebEduSearcher(index_dir=fineweb_index_dir)
            print(f"Loaded FineWeb-Edu index from {fineweb_index_dir}")
        else:
            print("FineWeb-Edu index not found (run indexer with --dataset fineweb-edu to create)")

    return server, initialize_searchers



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
    finewiki_searcher = FineWikiSearcher(index_dir=index_dir)
    load_time = time.time() - start_time
    mem_after_load = get_memory_usage()
    print(f"  Index loaded in {load_time:.3f}s")
    print(f"  Memory after loading: {mem_after_load:.2f} GB")

    # Search for 'Banana' in titles
    print("\nSearching for 'Banana' in titles...")
    start_time = time.time()
    title_results = finewiki_searcher.search_by_title("Banana", limit=5)
    query_time = time.time() - start_time
    print(f"  Query completed in {query_time:.3f}s")
    print(f"  Found {len(title_results)} results:")
    for r in title_results:
        print(f"    - ID: {r['id']}, Title: {r['title']}, Score: {r['score']:.4f}")

    # Search for 'Mozart' in content
    print("\nSearching for 'Mozart' in content...")
    start_time = time.time()
    content_results = finewiki_searcher.search_by_content("Mozart", limit=5)
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
            content = finewiki_searcher.fetch_content(result["id"])
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
            content = finewiki_searcher.fetch_content(result["id"])
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

    # Test FineWeb-Edu if available
    fineweb_index_dir = Path("index_data_fineweb_edu")
    if (fineweb_index_dir / "segments").exists() or (fineweb_index_dir / ".index" / "segments").exists():
        print("\n=== Testing FineWeb-Edu Index ===")
        start_time = time.time()
        fineweb_searcher = FineWebEduSearcher(index_dir=fineweb_index_dir)
        load_time = time.time() - start_time
        print(f"  FineWeb-Edu index loaded in {load_time:.3f}s")

        # Search for educational content
        print("\nSearching for 'python programming' in FineWeb-Edu...")
        start_time = time.time()
        text_results = fineweb_searcher.search_by_text("python programming", limit=5)
        query_time = time.time() - start_time
        print(f"  Query completed in {query_time:.3f}s")
        print(f"  Found {len(text_results)} results:")
        for r in text_results:
            print(f"    - ID: {r['id']}")
            print(f"      Preview: {r['text_preview'][:100]}...")

        # Fetch a document if found
        if text_results:
            print("\nFetching full content of first result...")
            content = fineweb_searcher.fetch_content(text_results[0]["id"])
            if content:
                print(f"  Title/ID: {content['id']}")
                print(f"  Dump: {content['dump']}")
                print(f"  Language: {content['language']}")
                print(f"  URL: {content['url']}")
                print(f"  Text length: {len(content['text'])} characters")

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
        server, init_searchers = create_app()
        init_searchers(args.index_dir, args.parquet_dir)

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
