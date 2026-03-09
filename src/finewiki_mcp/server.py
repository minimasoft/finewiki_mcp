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

    class TextSearchKnowledgeRequest(BaseModel):
        query: str

    class FetchKnowledgeRequest(BaseModel):
        doc_id: str

    server = Server("finewiki-search")

    finewiki_searcher: FineWikiSearcher | None = None
    fineweb_edu_searcher: FineWebEduSearcher | None = None

    # Define tools with comprehensive documentation for LLM usage
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="text_search_knowledge",
                description="""Full-text search across both Wikipedia and educational web content.

Searches FineWiki (Wikipedia) and FineWeb-Edu (educational web) simultaneously.
Returns up to 20 results split between sources (default 10-10).
If one source has fewer results, the other gets more.

IDs are prefixed with 'wiki:' or 'edu:' for use with fetch_knowledge.

Best for: Broad research questions, exploring topics across multiple sources,
finding both encyclopedic and educational content on a subject.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query - keywords or phrases to find across all knowledge sources",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="fetch_knowledge",
                description="""Fetch full content by prefixed ID from either Wikipedia or educational web.

Use this after getting a document ID from text_search_knowledge.
The doc_id should include the source prefix ('wiki:' or 'edu:').

Returns complete article/document with all available fields.

Best for: Getting detailed information after finding relevant documents.

Examples:
- 'wiki:12345' → Fetches Wikipedia article with ID 12345
- 'edu:abc-def' → Fetches educational document with ID abc-def""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doc_id": {
                            "type": "string",
                            "description": "Prefixed document ID (e.g., 'wiki:12345' or 'edu:abc-def')",
                        },
                    },
                    "required": ["doc_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        nonlocal finewiki_searcher, fineweb_edu_searcher

        # Aggregated knowledge tools
        if name == "text_search_knowledge":
            if fineweb_edu_searcher is None:
                return [
                    TextContent(
                        type="text",
                        text="FineWeb-Edu index not available. Please build the index first with: ./run_finewiki.sh index --dataset fineweb-edu",
                    )
                ]
            req = TextSearchKnowledgeRequest(**arguments)
            from finewiki_mcp.searcher import aggregate_search

            results = aggregate_search(
                finewiki_searcher, fineweb_edu_searcher, req.query, total_limit=20
            )
            return [TextContent(type="text", text=str(results))]

        elif name == "fetch_knowledge":
            req = FetchKnowledgeRequest(**arguments)
            doc_id = req.doc_id

            # Parse prefix and fetch from appropriate source
            if doc_id.startswith("wiki:"):
                wiki_id = int(doc_id[5:])  # Remove 'wiki:' prefix
                content = finewiki_searcher.fetch_content(wiki_id)
                if content:
                    return [TextContent(type="text", text=str(content))]
                return [
                    TextContent(
                        type="text", text=f"Wikipedia document not found: {doc_id}"
                    )
                ]

            elif doc_id.startswith("edu:"):
                edu_id = doc_id[4:]  # Remove 'edu:' prefix
                if fineweb_edu_searcher is None:
                    return [
                        TextContent(
                            type="text",
                            text="FineWeb-Edu index not available. Please build the index first with: ./run_finewiki.sh index --dataset fineweb-edu",
                        )
                    ]
                content = fineweb_edu_searcher.fetch_content(edu_id)
                if content:
                    return [TextContent(type="text", text=str(content))]
                return [
                    TextContent(
                        type="text", text=f"Educational document not found: {doc_id}"
                    )
                ]

            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Invalid doc_id format: '{doc_id}'. Expected prefix 'wiki:' or 'edu:'",
                    )
                ]

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
