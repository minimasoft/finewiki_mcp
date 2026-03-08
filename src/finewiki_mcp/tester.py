"""Test utilities for FineWiki MCP Server."""

import sys
import time
import resource
from pathlib import Path

try:
    from finewiki_mcp.searcher import FineWikiSearcher, FineWebEduSearcher
except ImportError:
    from searcher import FineWikiSearcher, FineWebEduSearcher


# Test queries for FineWeb-Edu dataset
FINEWEB_EDU_QUERIES = [
    "python tutorial",
    "machine learning",
    "react documentation",
]


def run_test(index_dir: str) -> None:
    """Run a quick test mode: load index and search for 'Banana' in titles, 
    'Mozart' in content (FineWiki), and educational queries (FineWeb-Edu)."""

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

    # Load FineWeb-Edu searcher
    edu_index_path = Path(index_dir).parent / "index_data_fineweb_edu"
    if (edu_index_path / ".index").exists():
        fineweb_edu_searcher = FineWebEduSearcher(index_dir=edu_index_path)
        print(f"  Loaded FineWeb-Edu index from {edu_index_path}")
    else:
        fineweb_edu_searcher = None
        print(f"  FineWeb-Edu index not found at {edu_index_path}, skipping FineWeb-Edu tests")

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

    # FineWeb-Edu tests
    if fineweb_edu_searcher:
        print("\n" + "=" * 60)
        print("FineWeb-Edu Tests")
        print("=" * 60)

        for query in FINEWEB_EDU_QUERIES:
            print(f"\nSearching for '{query}' in text...")
            start_time = time.time()
            text_results = fineweb_edu_searcher.search_by_text(query, limit=5)
            query_time = time.time() - start_time
            print(f"  Query completed in {query_time:.3f}s")
            print(f"  Found {len(text_results)} results:")
            for r in text_results:
                text_preview = (r['text_preview'][:40] + "...") if len(r['text_preview']) > 40 else r['text_preview']
                print(f"    - ID: {r['id']}, Preview: {text_preview}, Score: {r['score']:.4f}")

            # Fetch full content of all results
            if text_results:
                print(f"\nFetching full content of all '{query}' results...")
                fetch_times = []
                for i, result in enumerate(text_results):
                    start_time = time.time()
                    content = fineweb_edu_searcher.fetch_content(result["id"])
                    elapsed = time.time() - start_time
                    fetch_times.append(elapsed)

                    if content:
                        print(f"  Result {i+1}: Fetch completed in {elapsed:.3f}s")
                        print(f"    ID: {content['id']}")
                        print(f"    URL: {content.get('url', 'N/A')}")
                        print(f"    Text length: {len(content.get('text', ''))} characters")
                        preview = content.get("text", "")[:200].replace("\n", " ")
                        print(f"    Preview: {preview}...")
                    else:
                        print(f"  Result {i+1}: Document not found")

                avg_fetch_time = sum(fetch_times) / len(fetch_times)
                total_fetch_time = sum(fetch_times)
                print(f"\n  Total fetch time for {len(text_results)} results: {total_fetch_time:.3f}s")
                print(f"  Average fetch time per result: {avg_fetch_time*1000:.1f}ms")

        mem_after_edu = get_memory_usage()
        print(f"\n  Memory after FineWeb-Edu tests: {mem_after_edu:.2f} GB")

    print("\nTest completed successfully!")
