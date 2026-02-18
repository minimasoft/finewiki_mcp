"""Index generator for FineWiki dataset using Tantivy."""

from pathlib import Path

import pyarrow.parquet as pq
import tantivy


def create_index(index_dir: str | Path = "index_data") -> tantivy.Index:
    """Create or open a tantivy index."""
    index_path = Path(index_dir)
    index_path.mkdir(parents=True, exist_ok=True)

    schema_builder = tantivy.SchemaBuilder()
    schema_builder.add_integer_field("id", stored=True, indexed=True)
    schema_builder.add_text_field("title", stored=True, indexed=True)
    schema_builder.add_text_field("content", stored=False, indexed=True)
    schema_builder.add_text_field("url", stored=True, indexed=True)

    schema = schema_builder.build()
    index = tantivy.Index(schema, path=str(index_path))
    return index


def load_parquet_files(parquet_dir: str | Path) -> list[Path]:
    """Load all parquet files from a directory."""
    parquet_path = Path(parquet_dir)
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet directory not found: {parquet_path}")

    return list(parquet_path.glob("*.parquet"))


def index_parquet_file(
    index: tantivy.Index, parquet_file: str | Path, batch_size: int = 1000
) -> int:
    """Index a single parquet file and return the number of documents indexed."""
    reader = pq.ParquetFile(parquet_file)
    num_rows = reader.metadata.num_rows

    writer = index.writer()

    for batch_start in range(0, num_rows, batch_size):
        # Track progress - could be used for logging if needed
        _ = min(batch_start + batch_size, num_rows)
        table = reader.read_row_group(batch_start // 128).to_pandas()

        for _, row in table.iterrows():
            doc = tantivy.Document()
            doc.add_integer("id", int(row.get("id", 0)))
            doc.add_text("title", str(row.get("title", "")))
            doc.add_text("content", str(row.get("text", "")))
            doc.add_text("url", str(row.get("url", "")))
            writer.add_document(doc)

    writer.commit()
    return num_rows


def build_index(
    parquet_dir: str | Path, index_dir: str | Path = "index_data"
) -> tuple[int, int]:
    """Build the full index from parquet files. Returns (total_docs, total_files)."""
    index = create_index(index_dir)
    parquet_files = load_parquet_files(parquet_dir)

    total_docs = 0
    for parquet_file in parquet_files:
        print(f"Indexing {parquet_file.name}...")
        docs_in_file = index_parquet_file(index, parquet_file)
        total_docs += docs_in_file
        print(f"  Indexed {docs_in_file} documents")

    # Optimize the index
    print("Optimizing index...")
    index.optimize()

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
    total_docs, total_files = build_index(args.parquet_dir, args.index_dir)
    print(f"Indexing complete! Indexed {total_docs} documents across {total_files} files.")
