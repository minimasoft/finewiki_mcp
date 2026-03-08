"""Searcher classes for FineWiki and FineWeb-Edu datasets."""

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

    def __init__(self, index_dir: str | Path = "index_data"):
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

    def __init__(self, index_dir: str | Path = "index_data_fineweb_edu"):
        self.index_path = Path(index_dir)
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

    def fetch_content(self, doc_id: str) -> dict | None:
        """Fetch full content of a document by ID.

        Args:
            doc_id: String document ID to fetch.

        Returns:
            Dictionary with all document fields or None if not found.
        """
        return self._get_document_by_id_from_index(doc_id)
