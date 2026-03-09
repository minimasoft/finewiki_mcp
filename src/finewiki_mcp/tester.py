"""Test utilities for FineWiki MCP Server."""

import sys
import time
import resource
from pathlib import Path

try:
    from finewiki_mcp.searcher import (
        FineWikiSearcher,
        FineWebEduSearcher,
        aggregate_search,
    )
except ImportError:
    from searcher import FineWikiSearcher, FineWebEduSearcher, aggregate_search


# Test queries for aggregated knowledge search
KNOWLEDGE_QUERIES = [
    "machine learning",
    "photosynthesis",
    "python programming",
]


def run_test(index_dir: str) -> None:
    """Test the text_search_knowledge and fetch_knowledge MCP tools."""

    def get_memory_usage() -> float:
        """Get current memory usage in GB."""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            return usage.ru_maxrss / (1024 * 1024 * 1024)
        else:
            return usage.ru_maxrss / (1024 * 1024)

    print(f"Test Mode - Testing aggregated knowledge tools")
    print(f"FineWiki index: {index_dir}")

    start_time = time.time()
    finewiki_searcher = FineWikiSearcher(index_dir=index_dir)
    load_time = time.time() - start_time
    mem_after_wiki_load = get_memory_usage()
    print(f"  FineWiki index loaded in {load_time:.3f}s")
    print(f"  Memory after loading: {mem_after_wiki_load:.2f} GB")

    # Load FineWeb-Edu searcher (required for aggregated search)
    edu_index_path = Path(index_dir).parent / "index_data_fineweb_edu"
    if (edu_index_path / ".index").exists():
        fineweb_edu_searcher = FineWebEduSearcher(index_dir=edu_index_path)
        print(f"  FineWeb-Edu index loaded from {edu_index_path}")
    else:
        print(f"\nERROR: FineWeb-Edu index not found at {edu_index_path}")
        print(
            "Build the index first with: ./run_finewiki.sh index --dataset fineweb-edu"
        )
        return

    mem_after_load = get_memory_usage()
    print(f"  Memory after both indices loaded: {mem_after_load:.2f} GB")

    # Test aggregated search and fetch for each query
    print("\n" + "=" * 70)
    print("Testing text_search_knowledge + fetch_knowledge tools")
    print("=" * 70)

    all_fetch_times = []

    for query in KNOWLEDGE_QUERIES:
        print(f"\n--- Query: '{query}' ---")

        # Test aggregate_search (used by text_search_knowledge tool)
        start_time = time.time()
        results = aggregate_search(
            finewiki_searcher, fineweb_edu_searcher, query, total_limit=20
        )
        search_time = time.time() - start_time

        print(f"  Search completed in {search_time:.3f}s")

        # Count wiki vs edu results
        wiki_count = sum(1 for r in results if r["id"].startswith("wiki:"))
        edu_count = sum(1 for r in results if r["id"].startswith("edu:"))
        print(
            f"  Found {len(results)} total results ({wiki_count} Wikipedia, {edu_count} Educational)"
        )

        # Show top 3 results
        print(f"  Top results:")
        for i, r in enumerate(results[:3]):
            title_preview = (
                (r["title"][:50] + "...") if len(r["title"]) > 50 else r["title"]
            )
            print(
                f"    {i + 1}. [{r['id'].split(':')[0]}] {title_preview} (score: {r['score']:.4f})"
            )

        # Fetch first result from each source type (if available)
        fetch_targets = []
        for r in results:
            if r["id"].startswith("wiki:") and not any(
                t[0] == "wiki" for t in fetch_targets
            ):
                fetch_targets.append(("wiki", r))
            elif r["id"].startswith("edu:") and not any(
                t[0] == "edu" for t in fetch_targets
            ):
                fetch_targets.append(("edu", r))
            if len(fetch_targets) == 2:
                break

        print(f"\n  Fetching content for first result from each source:")
        fetch_times = []

        for source_type, result in fetch_targets:
            doc_id = result["id"]
            start_time = time.time()

            # Simulate the fetch_knowledge tool logic
            if doc_id.startswith("wiki:"):
                wiki_id = int(doc_id[5:])
                content = finewiki_searcher.fetch_content(wiki_id)
                source_name = "Wikipedia"
            else:  # edu:
                edu_id = doc_id[4:]
                content = fineweb_edu_searcher.fetch_content(edu_id)
                source_name = "Educational"

            elapsed = time.time() - start_time
            fetch_times.append(elapsed)
            all_fetch_times.append(elapsed)

            if content:
                print(f"\n  [{source_name}] Fetch completed in {elapsed:.3f}s")
                print(f"    ID: {doc_id}")

                if source_type == "wiki":
                    print(f"    Title: {content.get('title', 'N/A')}")
                    content_text = content.get("content", "")
                else:
                    url = content.get("url", "N/A")
                    print(f"    URL: {url}")
                    content_text = content.get("text", "")

                print(f"    Content length: {len(content_text)} characters")
                preview = content_text[:150].replace("\n", " ")
                print(f"    Preview: {preview}...")
            else:
                print(f"\n  [{source_name}] Document not found: {doc_id}")

        total_fetch_time = sum(fetch_times)
        print(f"\n  Total fetch time for this query: {total_fetch_time:.3f}s")
        print(
            f"  Average per document: {(total_fetch_time / len(fetch_times)) * 1000:.1f}ms"
        )

    # Summary statistics
    mem_final = get_memory_usage()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Queries tested: {len(KNOWLEDGE_QUERIES)}")
    print(f"Total fetches performed: {len(all_fetch_times)}")
    if all_fetch_times:
        avg_fetch = (sum(all_fetch_times) / len(all_fetch_times)) * 1000
        print(f"Average fetch time: {avg_fetch:.1f}ms")
    print(f"Final memory usage: {mem_final:.2f} GB")
    print("\n✓ All tests completed successfully!")
