"""Index generator for FineWiki dataset using Tantivy."""

import hashlib
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path

import pyarrow.parquet as pq
import tantivy


METADATA_FILE = "indexed_files.json"


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def load_metadata(index_dir: Path) -> dict:
    """Load indexed files metadata from index directory."""
    metadata_path = index_dir / METADATA_FILE
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            result = json.load(f)
            print(f"Loaded metadata: {result}")
            return result
    return {"indexed_files": {}, "version": 1}


def save_metadata(index_dir: Path, metadata: dict) -> None:
    """Save indexed files metadata to index directory."""
    metadata_path = index_dir / METADATA_FILE
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to {metadata_path}")


@contextmanager
def acquire_lock(lock_path: Path):
    """Context manager for acquiring a lock file. Raises if already locked."""
    pid = os.getpid()

    if lock_path.exists():
        try:
            existing_pid = int(lock_path.read_text().strip())
            # Check if process is still running
            if existing_pid != pid and os.path.exists(f"/proc/{existing_pid}"):
                raise RuntimeError(
                    f"Another indexing process is running (PID: {existing_pid}). "
                    "If this is a stale lock, manually remove the lock file."
                )
        except ValueError:
            pass  # Lock file exists but contains invalid content

    try:
        lock_path.write_text(str(pid))
        yield
    finally:
        if lock_path.exists() and int(lock_path.read_text().strip()) == pid:
            lock_path.unlink()


def create_index(index_dir: Path) -> tantivy.Index:
    """Create or open a tantivy index."""
    index_dir.mkdir(parents=True, exist_ok=True)

    schema_builder = tantivy.SchemaBuilder()
    schema_builder.add_integer_field("id", stored=True)
    schema_builder.add_text_field("title", stored=True, index_option="position")
    schema_builder.add_text_field("content", stored=False, index_option="position")
    # url is not indexed/stored for offline use
    # schema_builder.add_text_field("url", stored=True, index_option="position")
    schema_builder.add_integer_field("row_index", stored=True)
    schema_builder.add_text_field("parquet_file_path", stored=True)

    schema = schema_builder.build()
    return tantivy.Index(schema, path=str(index_dir))


def load_parquet_files(parquet_dir: Path) -> list[Path]:
    """Load all parquet files from a directory."""
    if not parquet_dir.exists():
        raise FileNotFoundError(f"Parquet directory not found: {parquet_dir}")
    return sorted(parquet_dir.glob("*.parquet"))


def index_parquet_file(
    index: tantivy.Index, parquet_file: Path, batch_size: int = 1000
) -> int:
    """Index a single parquet file and return the number of documents indexed."""
    reader = pq.ParquetFile(parquet_file)
    num_rows = reader.metadata.num_rows

    writer = index.writer()

    table = reader.read().to_pandas()

    for row_idx, (_, row) in enumerate(table.iterrows()):
        doc = tantivy.Document()
        doc.add_integer("id", int(row.get("page_id", 0)))
        doc.add_text("title", str(row.get("title", "")))
        doc.add_text("content", str(row.get("text", "")))
        # url is not indexed/stored for offline use
        # doc.add_text("url", str(row.get("url", "")))
        doc.add_integer("row_index", row_idx)
        doc.add_text("parquet_file_path", str(parquet_file))
        writer.add_document(doc)

    writer.commit()
    return num_rows


def get_temp_index_dir(index_dir: Path) -> Path:
    """Get the temporary directory path for index building."""
    return index_dir / ".index_tmp"


@contextmanager
def temp_index_directory(index_dir: Path):
    """Context manager for managing a temporary index directory with cleanup on failure."""
    temp_dir = get_temp_index_dir(index_dir)

    # Remove any existing temp directory from previous incomplete runs
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    # Create fresh temp directory
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        yield temp_dir
    except Exception as e:
        # Cleanup on failure
        print(f"\nIndexing failed! Cleaning up temporary files... {e}")
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except:
                print("Error cleaning up")
                pass
        raise e


def build_index(
    parquet_dir: Path, index_dir: Path = Path("index_data"), force_rebuild: bool = False
) -> tuple[int, int]:
    """Build the full index from parquet files. Returns (total_docs, total_files).

    Args:
        parquet_dir: Directory containing parquet files
        index_dir: Output directory for index
        force_rebuild: If True, rebuild even if files are already indexed
    """
    # Ensure parquet directory exists
    if not parquet_dir.exists():
        raise FileNotFoundError(f"Parquet directory not found: {parquet_dir}")

    parquet_files = load_parquet_files(parquet_dir)

    if not parquet_files:
        print(f"No parquet files found in {parquet_dir}")
        return 0, 0

    # Load existing metadata
    metadata = load_metadata(index_dir)
    index_file_hash_map = metadata.get("indexed_files", {})

    # Determine which files need indexing
    files_to_index = []
    for parquet_file in parquet_files:
        file_hash = compute_file_hash(parquet_file)

        if force_rebuild or parquet_file.name not in index_file_hash_map:
            # File not indexed yet, or force rebuild
            print(f"New file {parquet_file.name} (hash: {file_hash[:16]}...), indexing...")
            files_to_index.append((parquet_file, file_hash))
        else:
            # Check if hash matches - compare only the "hash" field from stored metadata
            stored_entry = index_file_hash_map.get(parquet_file.name, {})
            stored_hash = stored_entry.get("hash") if isinstance(stored_entry, dict) else None
            print(f"Checking {parquet_file.name}: computed={file_hash[:16]}..., stored={stored_hash[:16] if stored_hash else 'N/A'}...")
            if index_file_hash_map[parquet_file.name].get("hash") != file_hash:
                # File hash changed, needs re-indexing
                print(f"Detected change in {parquet_file.name}, re-indexing...")
                files_to_index.append((parquet_file, file_hash))
            else:
                # File already indexed with same content
                print(f"Skipping {parquet_file.name} (already indexed)")

    if not files_to_index:
        total_docs = sum(
            index_file_hash_map.get(pf.name, {}).get("docs", 0)
            for pf in parquet_files
            if pf.name in index_file_hash_map
        )
        # Re-read to get actual doc count since we're using cached metadata
        total_docs = 0
        for parquet_file in parquet_files:
            reader = pq.ParquetFile(parquet_file)
            total_docs += reader.metadata.num_rows

        return total_docs, len(parquet_files)

    lock_path = index_dir / ".indexer.lock"

    with acquire_lock(lock_path):
        with temp_index_directory(index_dir) as temp_dir:
            # Create index in temporary directory
            print(f"Creating temporary index at {temp_dir}...")
            index = create_index(temp_dir)

            total_docs = 0
            for parquet_file, file_hash in files_to_index:
                print(f"Indexing {parquet_file.name}...")
                docs_in_file = index_parquet_file(index, parquet_file)
                total_docs += docs_in_file
                print(f"  Indexed {docs_in_file} documents")

            # Now that indexing is complete and index is finalized,
            # we can safely update the metadata with file hashes
            for parquet_file, file_hash in files_to_index:
                reader = pq.ParquetFile(parquet_file)
                num_rows = reader.metadata.num_rows
                stored_entry = index_file_hash_map.get(parquet_file.name, {})
                print(f"Updating metadata for {parquet_file.name}: hash={file_hash[:16]}..., docs={num_rows}, previously_indexed_at={stored_entry.get('indexed_at', 'N/A')}")
                index_file_hash_map[parquet_file.name] = {
                    "hash": file_hash,
                    "docs": num_rows,
                    "indexed_at": str(Path(temp_dir).name)  # Reference to temp dir name for debugging
                }

            # Save metadata before moving (so we can recover if move fails)
            save_metadata(index_dir, {"indexed_files": index_file_hash_map, "version": 1})

            # Atomically replace the old index with the new one using rename (atomic on same FS)
            actual_index_files = [p for p in temp_dir.iterdir() if p.name != ".index_tmp"]

            print("Moving final index to target directory...")
            # Use a stable name for the new index directory
            new_index_name = f".index_new_{os.getpid()}"
            new_index_dir = index_dir / new_index_name

            # Clean up any existing .index_new_* from previous incomplete operations
            for item in index_dir.iterdir():
                if item.name.startswith(".index_new_"):
                    shutil.rmtree(item)

            # Move temp directory contents to a stable-named new index location
            temp_dir.rename(new_index_dir)

            # Now that staging is complete, remove old index files but keep metadata and lock
            preserve_files = {METADATA_FILE, ".indexer.lock"}
            for item in index_dir.iterdir():
                if item.name not in preserve_files and not item.name.startswith(".index_new_") and item.is_dir():
                    shutil.rmtree(item)
                elif item.name not in preserve_files and not item.name.startswith(".index_new_"):
                    item.unlink()

            # Finally, rename new_index to the standard index name (atomic on same filesystem)
            final_index_name = ".index"
            if (index_dir / final_index_name).exists():
                shutil.rmtree(index_dir / final_index_name)
            new_index_dir.rename(index_dir / final_index_name)

    print(f"Indexing complete! Indexed {total_docs} documents across {len(files_to_index)} files.")
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
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild even if files are already indexed",
    )

    args = parser.parse_args()

    print(f"Building index from {args.parquet_dir}...")
    total_docs, total_files = build_index(
        Path(args.parquet_dir),
        Path(args.index_dir),
    )
    print(f"Indexing complete! Indexed {total_docs} documents across {total_files} files.")
