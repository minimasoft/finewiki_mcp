"""MCP Server for FineWiki and FineWeb-Edu with Tantivy search capabilities."""

import anyio
from pathlib import Path

try:
    from finewiki_mcp.searcher import FineWikiSearcher, FineWebEduSearcher
except ImportError:
    from searcher import FineWikiSearcher, FineWebEduSearcher


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
                name="fetch_edu_content",
                description="""Fetch the full content of a FineWeb-Edu document by ID.

Use this after getting a document ID from fineweb_search_by_text.
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
            if fineweb_edu_searcher is None:
                return [TextContent(type="text", text="FineWeb-Edu index not available. Please build the index first with: ./run_finewiki.sh index --dataset fineweb-edu")]
            req = SearchByTextRequest(**arguments)
            results = fineweb_edu_searcher.search_by_text(req.query, req.limit)
            return [TextContent(type="text", text=str(results))]

        elif name == "fetch_edu_content":
            if fineweb_edu_searcher is None:
                return [TextContent(type="text", text="FineWeb-Edu index not available. Please build the index first with: ./run_finewiki.sh index --dataset fineweb-edu")]
            req = FetchEduContentRequest(**arguments)
            content = fineweb_edu_searcher.fetch_content(req.doc_id)
            if content:
                return [TextContent(type="text", text=str(content))]
            return [TextContent(type="text", text="Document not found")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    def initialize_searchers(index_dir: str):
        nonlocal finewiki_searcher, fineweb_edu_searcher
        finewiki_searcher = FineWikiSearcher(index_dir=index_dir)
        print(f"Loaded FineWiki index from {index_dir}")
        edu_path = Path(index_dir).parent / "index_data_fineweb_edu"
        fineweb_edu_searcher = FineWebEduSearcher(index_dir=edu_path)
        print(f"Loaded FineWeb-Edu index from {edu_path}")

    return server, initialize_searchers


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run FineWiki MCP Server")
    parser.add_argument(
        "--index-dir",
        default="index_data",
        help="Directory containing the tantivy index (default: index_data)",
    )
    parser.add_argument(
        "--mode",
        choices=["server", "test"],
        default="server",
        help="Mode to run in: 'server' for MCP server, 'test' for quick test (default: server)",
    )

    args = parser.parse_args()

    if args.mode == "test":
        from finewiki_mcp.tester import run_test
        run_test(args.index_dir)
    else:
        server, init_searchers = create_app()
        init_searchers(args.index_dir)

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
