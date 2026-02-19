#!/usr/bin/env python3
"""
Test script for FineWiki MCP server in stdio mode.
Performs multiple searches and fetches content for the first result of each,
timing all operations.

Usage:
    # Build image and start server (in another terminal):
    bash run_finewiki.sh server &
    
    # Run this test:
    python test_search.py

Or run both from scratch:
    bash run_finewiki.sh index
    python test_search.py --wait 5
"""

import asyncio
import json
import subprocess
import sys
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


def build_request(method: str, params: dict, request_id: int) -> dict:
    """Build a JSON-RPC 2.0 request."""
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id,
    }


async def send_message(writer, msg: dict):
    """Send a JSON message over the stream."""
    writer.write(json.dumps(msg).encode() + b"\n")
    await writer.drain()


async def read_message(reader) -> dict:
    """Read a JSON message from the stream."""
    line = await reader.readline()
    if not line:
        raise EOFError("No more data from server")
    return json.loads(line.decode())


async def test_server():
    """Test the FineWiki MCP server with searches and content fetches."""
    project_dir = Path(__file__).parent.resolve()
    index_dir = project_dir / "index_data"
    
    if not index_dir.exists():
        print(f"Error: Index directory not found: {index_dir}")
        print("Run 'bash run_finewiki.sh index' first to build the index.")
        return
    
    print("Starting FineWiki MCP server via Docker...")
    
    # Start Docker container with stdio
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
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    try:
        reader, writer = await asyncio.open_connection(
            sock=proc.stdout.fileno()
        )
    except Exception as e:
        print(f"Failed to connect: {e}")
        proc.terminate()
        return
    
    request_id = 1
    
    # Send initialize request (MCP protocol)
    init_request = build_request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    }, request_id)
    
    await send_message(writer, init_request)
    response = await read_message(reader)
    print(f"Initialized: {response.get('result', {})}")
    
    # Notify server ready
    notify_request = build_request("notification", {
        "method": "$/ready",
        "params": None
    }, request_id + 1)
    await send_message(writer, notify_request)
    
    total_start = time.time()
    results = []
    
    try:
        for query in SEARCH_QUERIES:
            print(f"\n{'='*60}")
            print(f"Query: '{query}'")
            print("-" * 40)
            
            # Search by title
            search_start = time.time()
            request_id += 1
            await send_message(writer, build_request("tools/call", {
                "name": "search_by_title",
                "arguments": {"query": query, "limit": 3}
            }, request_id))
            
            response = await read_message(reader)
            search_time = time.time() - search_start
            
            if "error" in response:
                print(f"Search error: {response['error']}")
                continue
            
            result_data = response.get("result", [])
            results_text = result_data[0].get("text", "") if isinstance(result_data, list) else str(result_data)
            
            # Parse the results (they're returned as string representation of dict/list)
            try:
                hits = eval(results_text)
            except:
                hits = []
            
            print(f"Search completed in {search_time:.3f}s")
            print(f"Found {len(hits)} results:")
            
            for i, hit in enumerate(hits[:3]):
                title = hit.get('title', '')[:45]
                print(f"  [{i+1}] ID: {hit['id']}, Title: {title}..., Score: {hit['score']:.4f}")
            
            # Fetch content of first result
            if hits:
                fetch_start = time.time()
                request_id += 1
                await send_message(writer, build_request("tools/call", {
                    "name": "fetch_content",
                    "arguments": {"doc_id": hits[0]["id"]}
                }, request_id))
                
                response = await read_message(reader)
                fetch_time = time.time() - fetch_start
                
                content_data = response.get("result", [])
                content_text = content_data[0].get("text", "") if isinstance(content_data, list) else str(content_data)
                
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
                print("No results to fetch")
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
        print(f"{'Query':<35} {'Search(s)':<10} {'Fetch(s)':<10} {'Total(s)':<10} {'Results':<8}")
        print("-"*75)
        
        for r in results:
            title = (r["first_title"][:32] + "...") if r["first_title"] and len(r["first_title"]) > 35 else (r["first_title"] or "")
            print(f"{title:<35} {r['search_time']:<10.3f} {r['fetch_time']:<10.3f} {r['total_time']:<10.3f} {r['num_results']:<8}")
        
        print("-"*75)
        print(f"{'TOTAL':<35} {'':<10} {'':<10} {total_time:<10.3f}")
        print(f"\nTested {len(results)} queries, completed in {total_time:.3f}s")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


async def test_direct_search():
    """Direct search testing without MCP protocol overhead - for benchmarking."""
    project_dir = Path(__file__).parent.resolve()
    
    print("Running direct search (no MCP)...")
    cmd = [
        "python", str(project_dir / "src" / "finewiki_mcp" / "server.py"),
        "--index-dir", str(project_dir / "index_data"),
        "--parquet-dir", str(project_dir / "finewiki_en"),
        "--mode", "test"
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:", proc.stderr)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test FineWiki MCP server")
    parser.add_argument("--mode", choices=["mcp", "direct"], default="mcp",
                       help="Test mode: 'mcp' for MCP protocol, 'direct' for inline test")
    
    args = parser.parse_args()
    
    if args.mode == "mcp":
        asyncio.run(test_server())
    else:
        asyncio.run(test_direct_search())
