"""Index generator for FineWiki and FineWeb-Edu datasets using Tantivy."""

import json
import shutil
import time
from pathlib import Path

import pyarrow.parquet as pq
import tantivy

try:
    from finewiki_mcp.common import get_schema, get_dataset_info
except ImportError:
    from common import get_schema, get_dataset_info


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


def create_index(index_dir: Path, dataset: str = "finewiki") -> tantivy.Index:
    """Create a new tantivy index.

    Args:
        index_dir: Directory to create the index in.
        dataset: Dataset name - either 'finewiki' or 'fineweb-edu'.

    Returns:
        Initialized tantivy Index instance.
    """
    index_dir.mkdir(parents=True, exist_ok=True)
    schema = get_schema(dataset)
    return tantivy.Index(schema, path=str(index_dir))


def load_parquet_files(parquet_dir: Path) -> list[Path]:
    """Load all parquet files from a directory."""
    if not parquet_dir.exists():
        raise FileNotFoundError(f"Parquet directory not found: {parquet_dir}")
    return sorted(parquet_dir.glob("*.parquet"))


def index_parquet_file(
    index: tantivy.Index, parquet_file: Path, dataset: str = "finewiki"
) -> int:
    """Index a single parquet file and return the number of documents indexed.

    Args:
        index: Tantivy Index instance to add documents to.
        parquet_file: Path to the parquet file to index.
        dataset: Dataset name - either 'finewiki' or 'fineweb-edu'.

    Returns:
        Number of documents indexed from this file.
    """
    reader = pq.ParquetFile(parquet_file)
    num_rows = reader.metadata.num_rows

    writer = index.writer()

    table = reader.read().to_pandas()

    if dataset == "fineweb-edu":
        # FineWeb-Edu schema: text, id, dump, url, date, file_path, language
        for _, row in table.iterrows():
            doc = tantivy.Document()
            doc.add_text("id", str(row.get("id", "")))
            doc.add_text("text", str(row.get("text", "")))
            doc.add_text("dump", str(row.get("dump", "")))
            doc.add_text("url", str(row.get("url", "")))
            doc.add_text("date", str(row.get("date", "")))
            doc.add_text("language", str(row.get("language", "")))
            writer.add_document(doc)
    else:
        # FineWiki schema: page_id, title, text (content), url
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
    parquet_dir: Path,
    index_dir: Path = Path("index_data"),
    dataset: str = "finewiki",
) -> tuple[int, int]:
    """Build the full index from parquet files. Returns (total_docs, total_files).

    Args:
        parquet_dir: Directory containing parquet files.
        index_dir: Output directory for index.
        dataset: Dataset name - either 'finewiki' or 'fineweb-edu'.

    Returns:
        Tuple of (total_documents_indexed, total_files_processed).

    Raises:
        FileNotFoundError: If parquet directory does not exist.
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
    print(f"Dataset: {dataset}")
    print("This will delete the old index and rebuild from scratch.")

    # 10-second countdown
    for i in range(10, 0, -1):
        print(f"Deleting old index and starting in {i} seconds...", end="\r")
        time.sleep(1)
    print("\n")

    # Remove backed up index if it exists (we're doing a full rebuild)
    if old_index_path.exists():
        print("Removing backup of old index...")
        shutil.rmtree(old_index_path)

    # Create fresh index
    print(f"Creating new {dataset} index at {index_dir}...")
    index = create_index(index_path, dataset)

    total_docs = 0
    for parquet_file in parquet_files:
        print(f"Indexing {parquet_file.name}...")
        docs_in_file = index_parquet_file(index, parquet_file, dataset)
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

    metadata = {
        "indexed_files": index_file_hash_map,
        "version": 1,
        "dataset": dataset,
    }
    save_metadata(index_dir, metadata)

    print(f"\nIndexing complete! Indexed {total_docs} documents across {len(parquet_files)} files.")
    return total_docs, len(parquet_files)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build Tantivy index from FineWiki or FineWeb-Edu parquet files"
    )
    parser.add_argument(
        "--parquet-dir",
        default=None,
        help="Directory containing parquet files. Defaults to 'finewiki_en' for finewiki "
             "or 'fineweb-edu' for fineweb-edu dataset.",
    )
    parser.add_argument(
        "--index-dir",
        default=None,
        help="Output directory for index. Defaults to 'index_data' for finewiki "
             "or 'index_data_fineweb_edu' for fineweb-edu dataset.",
    )
    parser.add_argument(
        "--dataset",
        choices=["finewiki", "fineweb-edu"],
        default="finewiki",
        help="Dataset to index (default: finewiki)",
    )

    args = parser.parse_args()

    # Set defaults based on dataset if not provided
    dataset_info = get_dataset_info(args.dataset)
    parquet_dir = args.parquet_dir or dataset_info["default_parquet_dir"]
    index_dir = args.index_dir or dataset_info["default_index_dir"]

    print(f"Building {args.dataset} index from {parquet_dir}...")
    total_docs, total_files = build_index(
        Path(parquet_dir),
        Path(index_dir),
        args.dataset,
    )
    print(f"Indexing complete! Indexed {total_docs} documents across {total_files} files.")
