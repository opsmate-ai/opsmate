import pytest

from opsmate.dino.utils import args_dump


def test_args_dump():
    def fn(a, b, c=1, d=2):
        pass

    def cbk(a, d=2):
        pass

    assert args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4}) == ((1,), {"d": 4})


def test_args_dump_with_unmatching():
    def fn(a, b, c=1, d=2):
        pass

    def cbk(a, d=2, e=3):
        pass

    assert args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4}) == ((1,), {"d": 4})


@pytest.mark.asyncio
async def test_args_dump_async():
    async def fn(a, b, c=1, d=2):
        pass

    async def cbk(a, d=2):
        pass

    assert args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4}) == ((1,), {"d": 4})


@pytest.mark.asyncio
async def test_args_dump_async_to_sync_with_kwargs():
    async def fn(a, b, c=1, d=2):
        pass

    def cbk(a, d=2):
        pass

    assert args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4}) == ((1,), {"d": 4})


def test_args_dump_sync_to_async_with_kwargs():
    def fn(a, b, c=1, d=2):
        pass

    async def cbk(a, d=2):
        pass

    assert args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4}) == ((1,), {"d": 4})
