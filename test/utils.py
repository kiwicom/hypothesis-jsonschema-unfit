import jsonschema
import pytest


def assert_not_valid(original_schema, instance):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance, original_schema)
