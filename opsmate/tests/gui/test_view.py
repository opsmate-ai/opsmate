import pytest
from pydantic import BaseModel

from opsmate.gui.views import normalize_output_format


class DemoModel(BaseModel):
    a: str
    b: int


@pytest.mark.asyncio
async def test_normalize_output_format():
    assert normalize_output_format(DemoModel(a="b", b=1)) == {
        "a": "b",
        "b": 1,
    }
    assert normalize_output_format("abc") == "abc"
    assert normalize_output_format(1) == 1
    assert normalize_output_format(1.0) == 1.0

    assert normalize_output_format([DemoModel(a="b", b=1), {"c": "d", "e": 2.0}]) == [
        {"a": "b", "b": 1},
        {"c": "d", "e": 2.0},
    ]

    assert normalize_output_format(
        {
            "a": DemoModel(a="b", b=1),
            "b": {"c": "d", "e": 2.0},
            "c": [DemoModel(a="b", b=1), {"c": "d", "e": 2.0}],
        }
    ) == {
        "a": {"a": "b", "b": 1},
        "b": {"c": "d", "e": 2.0},
        "c": [{"a": "b", "b": 1}, {"c": "d", "e": 2.0}],
    }
