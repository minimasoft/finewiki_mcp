"""Common utilities shared between indexer and server."""

import tantivy


def get_schema(dataset: str = "finewiki") -> tantivy.Schema:
    """Return the schema used for the index.

    Args:
        dataset: Dataset name - either 'finewiki' or 'fineweb-edu'.
                 Defaults to 'finewiki'.

    Returns:
        Tantivy schema configured for the specified dataset.

    Schema differences:
        - finewiki: id (int), title, content, url
        - fineweb-edu: id (str), text, dump, url, date, file_path, language
    """
    schema_builder = tantivy.SchemaBuilder()

    if dataset == "fineweb-edu":
        # FineWeb-Edu schema
        schema_builder.add_text_field("id", stored=True, index_option="position")
        schema_builder.add_text_field("text", stored=True, index_option="position")
        schema_builder.add_text_field("dump", stored=True)
        schema_builder.add_text_field("url", stored=True, index_option="position")
        schema_builder.add_text_field("date", stored=True)
        schema_builder.add_text_field("language", stored=True)
    else:
        # FineWiki schema (default)
        schema_builder.add_integer_field("id", stored=True, indexed=True)
        schema_builder.add_text_field("title", stored=True, index_option="position")
        schema_builder.add_text_field("content", stored=True, index_option="position")
        schema_builder.add_text_field("url", stored=True, index_option="position")

    return schema_builder.build()


def get_dataset_info(dataset: str = "finewiki") -> dict:
    """Get metadata about a dataset.

    Args:
        dataset: Dataset name - either 'finewiki' or 'fineweb-edu'.

    Returns:
        Dictionary containing dataset configuration.
    """
    if dataset == "fineweb-edu":
        return {
            "name": "fineweb-edu",
            "default_index_dir": "index_data_fineweb_edu",
            "default_parquet_dir": "fineweb-edu",
            "primary_text_field": "text",
            "id_type": "string",
        }
    else:
        return {
            "name": "finewiki",
            "default_index_dir": "index_data",
            "default_parquet_dir": "finewiki_en",
            "primary_text_field": "content",
            "id_type": "integer",
        }
