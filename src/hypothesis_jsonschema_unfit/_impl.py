import itertools
from copy import deepcopy
from functools import partial
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, TypeVar, Union

from hypothesis import strategies as st
from hypothesis.errors import Unsatisfiable
from hypothesis_jsonschema import from_schema

T = TypeVar("T")


def negate(schema: T) -> Dict[str, T]:
    """Logical negation of the whole schema."""
    return {"not": schema}


def replace_property(schema: Dict[str, Any], name: str, value: Any) -> Dict[str, Any]:
    """Replace a property in an "object" schema."""
    copied = deepcopy(schema)
    copied["properties"][name] = value
    return copied


def replace_item(schema: Dict[str, Any], idx: int, value: Any) -> Dict[str, Any]:
    """Replace an item in an "array" schema if "items" is a list."""
    copied = deepcopy(schema)
    copied["items"][idx] = value
    return copied


def replace_items(schema: Dict[str, Any], value: Any) -> Dict[str, Any]:
    """Replace "items" in an "array" schema."""
    copied = deepcopy(schema)
    copied["items"] = value
    return copied


Mutation = Callable[[Dict[str, Any]], Union[Dict[str, Any], bool]]


def _handle_object_schema(schema: Dict[str, Any]) -> Generator[Mutation, None, None]:
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not required or any(prop not in required for prop in properties):
        # no required -> any other property will fit
        yield negate
    else:
        generated = False
        for name, prop in properties.items():
            for mutation in get_mutations(prop):
                value = mutation(prop)
                if value is False:
                    continue
                generated = True
                yield partial(replace_property, name=name, value=value)
        if not generated:
            # no possible to negate any defined property - need to negate the whole schema
            yield negate


def _handle_array_schema(schema: Dict[str, Any]) -> Generator[Mutation, None, None]:
    items = schema.get("items")
    if not items or items is True:
        yield negate
        return
    if isinstance(items, list):
        generated = False
        if False in items:
            yield negate
            return
        for idx, item in enumerate(items):
            for mutation in get_mutations(item):
                value = mutation(item)
                if value is False:
                    continue
                generated = True
                yield partial(replace_item, idx=idx, value=value)
        if not generated:
            yield negate
    if isinstance(items, dict):
        min_items = schema.get("minItems", 0)
        if min_items == 0 or schema.get("contains") == {}:
            yield negate
        else:
            for mutation in get_mutations(items):
                yield partial(replace_items, value=mutation(items))


def _is_simple_type(type_: List[Optional[str]]) -> bool:
    # `None` is for simplicity - represents any type
    return any(name in type_ for name in ("null", "boolean", "number", "integer", "string", None))


def get_mutations(schema: Any) -> Generator[Mutation, None, None]:
    if schema == {}:
        # Special case - negation will reject any input
        return
    if isinstance(schema, bool):
        yield lambda x: not x
        return
    type_ = schema.get("type")
    if not isinstance(type_, list):
        type_ = [type_]
    if _is_simple_type(type_):
        yield negate
    if "object" in type_:
        yield from _handle_object_schema(schema)
    if "array" in type_:
        yield from _handle_array_schema(schema)


def _apply_mutations(schema: Any, mutations: Tuple[Mutation, ...]) -> Any:
    new_schema = schema
    for mutation in mutations:
        new_schema = mutation(new_schema)
    return new_schema


def _mutate(schema: Any, limit: int = 100) -> Generator:
    """Generate different mutations for the given schema."""
    all_mutations = list(get_mutations(schema))
    generated = 0
    for length in range(1, len(all_mutations) + 1):
        for mutations in itertools.combinations(all_mutations, length):
            if generated >= limit:
                return
            yield _apply_mutations(schema, mutations)
            generated += 1


@st.composite  # type: ignore
def not_from_schema(draw: Callable, schema: Dict[str, Any]) -> Any:
    """Generate data that does NOT match the given schema."""
    mutations = list(_mutate(schema))
    if not mutations:
        raise Unsatisfiable
    mutation_strategies = st.sampled_from(mutations)
    mutated_strategy = draw(mutation_strategies)
    schema_strategy = from_schema(mutated_strategy)
    return draw(schema_strategy)
