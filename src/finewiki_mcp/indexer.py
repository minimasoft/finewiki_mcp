"""Index generator for FineWiki dataset using Tantivy."""

import json
import os
import shutil
import time
from pathlib import Path

import pyarrow.parquet as pq
import tantivy

try:
    from finewiki_mcp.common import get_schema
except ImportError:
    from common import get_schema


METADATA_FILE = "indexed_files.json"


def load_metadata(index_dir: Path) -> dict:
    """Load indexed files metadata from index directory."""
    metadata_path = index_dir / METADATA_FILE
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            return json.load(f)
    return {"indexed_files": {}, "version": 1}


def save_metadata(index_dir: Path, metadata: dict) -> None:
    """Save indexed files metadata to index directory."""
    metadata_path = index_dir / METADATA_FILE
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def create_index(index_dir: Path) -> tantivy.Index:
    """Create a new tantivy index."""
    index_dir.mkdir(parents=True, exist_ok=True)
    schema = get_schema()
    return tantivy.Index(schema, path=str(index_dir))


def load_parquet_files(parquet_dir: Path) -> list[Path]:
    """Load all parquet files from a directory."""
    if not parquet_dir.exists():
        raise FileNotFoundError(f"Parquet directory not found: {parquet_dir}")
    return sorted(parquet_dir.glob("*.parquet"))


def index_parquet_file(
    index: tantivy.Index, parquet_file: Path
) -> int:
    """Index a single parquet file and return the number of documents indexed."""
    reader = pq.ParquetFile(parquet_file)
    num_rows = reader.metadata.num_rows

    writer = index.writer()

    table = reader.read().to_pandas()

    for _, row in table.iterrows():
        doc = tantivy.Document()
        doc.add_integer("id", int(row.get("page_id", 0)))
        doc.add_text("title", str(row.get("title", "")))
        doc.add_text("content", str(row.get("text", "")))
        doc.add_text("url", str(row.get("url", "")))
        writer.add_document(doc)

    writer.commit()
    return num_rows


def build_index(
    parquet_dir: Path, index_dir: Path = Path("index_data")
) -> tuple[int, int]:
    """Build the full index from parquet files. Returns (total_docs, total_files).

    Args:
        parquet_dir: Directory containing parquet files
        index_dir: Output directory for index
    """
    # Ensure parquet directory exists
    if not parquet_dir.exists():
        raise FileNotFoundError(f"Parquet directory not found: {parquet_dir}")

    parquet_files = load_parquet_files(parquet_dir)

    if not parquet_files:
        print(f"No parquet files found in {parquet_dir}")
        return 0, 0

    index_path = index_dir / ".index"
    old_index_path = index_dir / ".index_old"

    # If old index exists from a previous failed run, clean it up
    if old_index_path.exists():
        print("Cleaning up leftover old index...")
        shutil.rmtree(old_index_path)

    # If new index already exists, rename it to .index_old first
    if index_path.exists():
        print(f"Backing up existing index to {old_index_path.name}...")
        index_path.rename(old_index_path)
        print("Index backed up. Proceeding with full re-index...")

    print("\n=== Starting Full Re-Index ===\n")
    print("This will delete the old index and rebuild from scratch.")
    
    # 10-second countdown
    for i in range(10, 0, -1):
        print(f"Deleting old index and starting in {i} seconds...", end="\r")
        time.sleep(1)
    print("\n")

    # Remove backed up index if it exists (we're doing a full rebuild)
    if old_index_path.exists():
        print(f"Removing backup of old index...")
        shutil.rmtree(old_index_path)

    # Create fresh index
    print(f"Creating new index at {index_dir}...")
    index = create_index(index_path)

    total_docs = 0
    for parquet_file in parquet_files:
        print(f"Indexing {parquet_file.name}...")
        docs_in_file = index_parquet_file(index, parquet_file)
        total_docs += docs_in_file
        print(f"  Indexed {docs_in_file} documents")

    # Save minimal metadata
    index_file_hash_map = {}
    for parquet_file in parquet_files:
        reader = pq.ParquetFile(parquet_file)
        num_rows = reader.metadata.num_rows
        index_file_hash_map[parquet_file.name] = {
            "docs": num_rows,
        }
    save_metadata(index_dir, {"indexed_files": index_file_hash_map, "version": 1})

    print(f"\nIndexing complete! Indexed {total_docs} documents across {len(parquet_files)} files.")
    return total_docs, len(parquet_files)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build Tantivy index from FineWiki parquet files"
    )
    parser.add_argument(
        "--parquet-dir",
        default="finewiki_en",
        help="Directory containing parquet files (default: finewiki_en)",
    )
    parser.add_argument(
        "--index-dir", default="index_data", help="Output directory for index (default: index_data)"
    )

    args = parser.parse_args()

    print(f"Building index from {args.parquet_dir}...")
    total_docs, total_files = build_index(
        Path(args.parquet_dir),
        Path(args.index_dir),
    )
    print(f"Indexing complete! Indexed {total_docs} documents across {total_files} files.")
