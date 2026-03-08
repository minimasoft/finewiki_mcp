"""FineWiki MCP Server with Tantivy indexing."""

__version__ = "0.1.0"

from finewiki_mcp.searcher import FineWikiSearcher, FineWebEduSearcher
from finewiki_mcp.tester import run_test
from finewiki_mcp.server import create_app

__all__ = ["FineWikiSearcher", "FineWebEduSearcher", "run_test", "create_app"]
