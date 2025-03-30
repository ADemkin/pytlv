from datetime import datetime
from math import isclose
from math import isnan

from hypothesis import given
from hypothesis import strategies as st

from tlv import dumps
from tlv import loads


@given(data=st.none())
def test_none(data: None) -> None:
    assert loads(dumps(data)) == data


@given(data=st.booleans())
def test_boolean(data: bool) -> None:
    assert loads(dumps(data)) == data


@given(data=st.text())
def test_string(data: str) -> None:
    assert loads(dumps(data)) == data


@given(data=st.integers())
def test_integer(data: int):
    assert loads(dumps(data)) == data


@given(data=st.floats())
def test_float(data: float):
    encoded = loads(dumps(data))
    if all([isnan(encoded), isnan(data)]):
        return
    assert isclose(data, encoded)


@given(data=st.datetimes())
def test_datetime(data: datetime):
    assert loads(dumps(data)) == data


def values():
    return st.one_of(
        st.text(),
        st.integers(),
        st.floats(allow_nan=False),
        st.booleans(),
        st.none(),
        st.tuples(),
        st.datetimes(),
    )


def keys():
    return st.one_of(
        st.text(),
        st.integers(),
        st.floats(allow_nan=False),
        st.booleans(),
        st.tuples(),
        st.none(),
        st.datetimes(),
    )


@given(data=st.lists(values()))
def test_list(data: list):
    assert loads(dumps(data)) == data


@given(data=st.sets(values()))
def test_set(data: set):
    assert loads(dumps(data)) == data


@given(data=st.tuples(values()))
def test_tuple(data: tuple):
    assert loads(dumps(data)) == data


@given(
    data=st.dictionaries(
        keys=keys(),
        values=values(),
    )
)
def test_dict(data: dict):
    assert loads(dumps(data)) == data


@given(
    data=st.recursive(
        base=values(),
        extend=st.lists,
        max_leaves=10,
    )
)
def test_recursive_list(data: list):
    assert loads(dumps(data)) == data


@given(
    data=st.recursive(
        base=st.dictionaries(
            keys=keys(),
            values=values(),
        ),
        extend=lambda inner: st.dictionaries(
            keys=keys(),
            values=inner,
        ),
        max_leaves=10,
    )
)
def test_recursive_dict(data: dict):
    assert loads(dumps(data)) == data


@given(
    data=st.recursive(
        base=values(),
        extend=lambda inner: st.one_of(
            st.lists(inner),
            st.dictionaries(
                keys=keys(),
                values=inner,
            ),
            st.tuples(),
        ),
        max_leaves=10,
    )
)
def test_recursive(data: dict | list | set | tuple):
    assert loads(dumps(data)) == data
