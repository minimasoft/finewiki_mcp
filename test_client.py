#!/usr/bin/env python3
"""Test client for FineWiki MCP server using stdio protocol."""

import asyncio
import json
import time
from pathlib import Path

# List of search queries to test
SEARCH_QUERIES = [
    "Banana",
    "Mozart",
    "Python programming language",
    "Mount Everest",
    "Artificial intelligence",
]


async def send_request(writer, method: str, params: dict) -> dict:
    """Send a request and wait for response."""
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": int(time.time() * 1000),
    }
    
    writer.write(json.dumps(request).encode())
    writer.write(b"\n")
    await writer.drain()
    
    response_line = await reader.readline()
    return json.loads(response_line.decode())


async def test_server():
    """Test the FineWiki MCP server with multiple searches and content fetches."""
    from subprocess import Popen, PIPE
    
    project_dir = Path(__file__).parent.resolve()
    index_dir = project_dir / "index_data"
    
    if not index_dir.exists():
        print(f"Error: Index directory not found: {index_dir}")
        print("Run 'bash run_finewiki.sh index' first to build the index.")
        return
    
    # Start Docker container with server
    cmd = [
        "docker", "run",
        "--rm",
        "-v", f"{project_dir}:/host_project",
        "-w", "/app",
        "--entrypoint=",
        "finewiki-mcp",
        "/app/.venv/bin/python", "-u",
        "src/finewiki_mcp/server.py",
        "--index-dir", "/host_project/index_data",
        "--parquet-dir", "/host_project/finewiki_en"
    ]
    
    print("Starting FineWiki MCP server...")
    proc = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=None)
    
    # Give Docker a moment to start
    await asyncio.sleep(1)
    
    reader, writer = await asyncio.open_connection(
        sock=proc.stdout.fileno(), 
        limit=10_000_000
    )
    
    try:
        # Read initialization messages (notifications before response)
        while True:
            line = await reader.readline()
            if not line:
                break
            msg = json.loads(line.decode())
            print(f"Server: {msg}")
            
            # Look for the initial response that starts the session
            if "result" in msg or "error" in msg:
                break
            
    except Exception as e:
        print(f"Error reading init: {e}")
    
    total_start = time.time()
    results = []
    
    try:
        # Test 1: Search by title for each query and fetch first result
        for query in SEARCH_QUERIES:
            print(f"\n{'='*60}")
            print(f"Query: '{query}'")
            print("-" * 40)
            
            # Search by title
            search_start = time.time()
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "search_by_title",
                    "arguments": {"query": query, "limit": 3}
                },
                "id": int(time.time() * 1000)
            }
            writer.write(json.dumps(request).encode() + b"\n")
            await writer.drain()
            
            response = json.loads((await reader.readline()).decode())
            search_time = time.time() - search_start
            
            if "error" in response:
                print(f"Search error: {response['error']}")
                continue
            
            result_data = response.get("result", [])
            # Parse the text content
            try:
                results_text = result_data[0]["text"] if isinstance(result_data, list) else str(result_data)
                hits = eval(results_text) if isinstance(results_text, str) else result_data
                print(f"Search completed in {search_time:.3f}s")
                print(f"Found {len(hits)} results:")
                
                for i, hit in enumerate(hits[:3]):
                    print(f"  [{i+1}] ID: {hit['id']}, Title: {hit['title'][:50]}..., Score: {hit['score']:.4f}")
                
                # Fetch content of first result
                if hits:
                    fetch_start = time.time()
                    request = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "fetch_content",
                            "arguments": {"doc_id": hits[0]["id"]}
                        },
                        "id": int(time.time() * 1000)
                    }
                    writer.write(json.dumps(request).encode() + b"\n")
                    await writer.drain()
                    
                    response = json.loads((await reader.readline()).decode())
                    fetch_time = time.time() - fetch_start
                    
                    content_text = response.get("result", [{}])[0].get("text", "") if isinstance(response.get("result"), list) else str(response.get("result", ""))
                    print(f"Fetch completed in {fetch_time:.3f}s")
                    print(f"Content length: {len(content_text)} characters")
                    
                    results.append({
                        "query": query,
                        "search_time": search_time,
                        "fetch_time": fetch_time,
                        "total_time": search_time + fetch_time,
                        "num_results": len(hits),
                        "first_title": hits[0]["title"] if hits else None
                    })
                else:
                    results.append({
                        "query": query,
                        "search_time": search_time,
                        "fetch_time": 0,
                        "total_time": search_time,
                        "num_results": 0,
                        "first_title": None
                    })
            except Exception as e:
                print(f"Parsing error: {e}")
                results.append({
                    "query": query,
                    "search_time": search_time,
                    "fetch_time": 0,
                    "total_time": search_time,
                    "num_results": 0,
                    "first_title": None
                })
        
        # Summary
        total_time = time.time() - total_start
        print(f"\n{'='*60}")
        print("SUMMARY")
        print("="*60)
        print(f"{'Query':<30} {'Search(s)':<10} {'Fetch(s)':<10} {'Total(s)':<10} {'Results':<8}")
        print("-"*60)
        
        for r in results:
            title = (r["first_title"][:25] + "...") if r["first_title"] and len(r["first_title"]) > 28 else (r["first_title"] or "")
            print(f"{r['query']:<30} {r['search_time']:<10.3f} {r['fetch_time']:<10.3f} {r['total_time']:<10.3f} {r['num_results']:<8}")
        
        print("-"*60)
        print(f"{'TOTAL':<30} {'':<10} {'':<10} {total_time:<10.3f}")
        print(f"\nTested {len(results)} queries, completed in {total_time:.3f}s")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(test_server())
