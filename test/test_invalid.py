import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis.errors import Unsatisfiable

from hypothesis_jsonschema_unfit import not_from_schema
from hypothesis_jsonschema_unfit._impl import _mutate

from .utils import assert_not_valid


def check_schema(schema):
    mutated_strategy = not_from_schema(schema)

    @given(mutated_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test(instance):
        assert_not_valid(schema, instance)

    test()


@pytest.mark.parametrize(
    "schema",
    (
        {"type": "integer"},
        {"type": "integer", "minimum": 0},
        {"type": "integer", "maximum": 5},
        {"type": "integer", "minimum": 0, "maximum": 5},
        {"type": "integer", "multipleOf": 2},
        {"type": "integer", "multipleOf": 1},
        {"type": "integer", "exclusiveMinimum": 0},
        {"type": "integer", "exclusiveMaximum": 5},
        {"type": "integer", "exclusiveMinimum": 0, "exclusiveMaximum": 5},
        {"type": "number"},
        {"type": "number", "minimum": 0},
        {"type": "number", "maximum": 5},
        {"type": "number", "minimum": 0, "maximum": 5},
        {"type": "number", "multipleOf": 2},
        {"type": "number", "exclusiveMinimum": 0},
        {"type": "number", "exclusiveMaximum": 5},
        {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 5},
        {"type": "string"},
        {"type": "string", "maxLength": 5},
        {"type": "string", "minLength": 2},
        {"type": "string", "minLength": 2, "maxLength": 5},
        {"type": "string", "minLength": 2, "maxLength": 5, "pattern": "a{5}"},
        {"type": "string", "pattern": ".*"},
        {"type": "integer", "enum": [1, 2, 3]},
        {"type": "integer", "const": 5},
        {"type": "null"},
        {"type": "boolean"},
        {"enum": [1, 2, 3]},
        {"type": ["integer", "string"], "minimum": 10},
    ),
)
def test_primitive(schema):
    check_schema(schema)


@pytest.mark.parametrize(
    "schema",
    (
        {"type": "array", "items": [{"type": "integer", "minimum": 1}]},
        {"type": "array", "items": [{"type": "integer", "minimum": 1}, {"type": "string", "minLength": 5},],},
        {"type": "array", "items": [{"type": "integer", "minimum": 1}], "maxItems": 5},
        {"type": "array", "items": [{"type": "integer", "minimum": 1}], "minItems": 5},
        {"type": "array", "items": [{"type": "integer", "minimum": 1}], "uniqueItems": False,},
        {"type": "array", "items": {"type": "integer", "minimum": 1}, "minItems": 1},
        {"items": {"type": "null"}, "type": "array"},
        {"items": {"type": "null"}, "type": "array", "minItems": 0},
        {"items": [{}], "type": "array"},
        {"contains": {}, "items": {}, "type": "array"},
        {"items": True, "type": "array", "uniqueItems": True},
        {"items": [True], "type": "array"},
        {"items": [False, {"type": "null"}], "type": "array"},
        {"items": [{"type": "null"}, True], "type": "array"},
        {
            "items": {
                "type": "object",
                "required": ["key1", "key2"],
                "properties": {"key1": {"type": "string"}, "key2": {"type": "integer"}},
            },
            "type": "array",
            "minItems": 4,
        },
    ),
)
def test_negate_array(schema):
    check_schema(schema)


@pytest.mark.parametrize(
    "schema",
    (
        {"type": "object"},
        {"additionalProperties": {}, "type": "object"},
        {"properties": {"": {}}, "type": "object"},
        {"type": "object", "properties": {"key": {"type": "integer"}}},
        {
            "type": "object",
            "properties": {
                "key": {"type": "integer"},
                "values": {"type": "object", "properties": {"inner": {"type": "string"}}, "required": ["inner"],},
            },
            "required": ["key", "values"],
        },
        # Test generation limit
        {
            "type": "object",
            "properties": {
                "key1": {"type": "integer"},
                "key2": {"type": "integer"},
                "key3": {"type": "integer"},
                "key4": {"type": "integer"},
                "key5": {"type": "integer"},
                "key6": {"type": "string"},
                "key7": {"type": "string"},
                "key8": {"type": "string"},
            },
            "required": ["key1", "key2", "key3", "key4", "key5", "key6", "key7", "key8",],
            "additionalProperties": False,
        },
        {"properties": {"": {"type": "null"}}, "type": "object"},
        {"properties": {"": {"type": "null"}}, "type": "object", "additionalProperties": True,},
        {"properties": {"0": {"type": "null"}}, "required": [""], "type": "object"},
        {"properties": {"": {}, "0": {"type": "null"}}, "required": [""], "type": "object",},
        {"properties": {"": True}, "required": [""], "type": "object"},
    ),
)
def test_negate_object(schema):
    check_schema(schema)


def test_combination():
    schema = {
        "type": "object",
        "properties": {
            "key": {"type": "integer"},
            "values": {"type": "object", "properties": {"inner": {"type": "string"}}, "required": ["inner"],},
        },
        "required": ["key", "values"],  # Doesn't work without "required"
    }
    assert list(_mutate(schema)) == [
        {
            "properties": {
                "key": {"not": {"type": "integer"}},
                "values": {"properties": {"inner": {"type": "string"}}, "required": ["inner"], "type": "object",},
            },
            "required": ["key", "values"],
            "type": "object",
        },
        {
            "properties": {
                "key": {"type": "integer"},
                "values": {
                    "properties": {"inner": {"not": {"type": "string"}}},
                    "required": ["inner"],
                    "type": "object",
                },
            },
            "required": ["key", "values"],
            "type": "object",
        },
        {
            "properties": {
                "key": {"not": {"type": "integer"}},
                "values": {
                    "properties": {"inner": {"not": {"type": "string"}}},
                    "required": ["inner"],
                    "type": "object",
                },
            },
            "required": ["key", "values"],
            "type": "object",
        },
    ]


def test_unsatisfiable():
    with pytest.raises(Unsatisfiable):
        mutated = not_from_schema({})

        @given(mutated)
        def test(schema):
            pass

        test()
