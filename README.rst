hypothesis-jsonschema-invalid
=============================

An experimental project for the generation of JSON data that does NOT match the given JSON schema.

.. code:: python

    from hypothesis import given
    from hypothesis_jsonschema_unfit import not_from_schema

    SCHEMA = {
        "items": {
            "type": "object",
            "required": ["key1", "key2"],
            "properties": {"key1": {"type": "string"}, "key2": {"type": "integer"}},
        },
        "type": "array",
        "minItems": 4,
    }

    @given(not_from_schema(SCHEMA))
    def test(instance):
        ...
