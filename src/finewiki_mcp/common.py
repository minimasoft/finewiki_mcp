"""Common utilities shared between indexer and server."""

import tantivy


def get_schema() -> tantivy.Schema:
    """Return the schema used for the index."""
    schema_builder = tantivy.SchemaBuilder()
    schema_builder.add_integer_field("id", stored=True, indexed=True)
    schema_builder.add_text_field("title", stored=True, index_option="position")
    schema_builder.add_text_field("content", stored=True, index_option="position")
    schema_builder.add_text_field("url", stored=True, index_option="position")
    return schema_builder.build()
