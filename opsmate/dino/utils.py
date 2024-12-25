from typing import Callable
from inspect import signature


def args_dump(fn: Callable, cbk: Callable, args, kwargs):
    """dump the matching args and kwargs from the function to the callback

    Args:
        fn: Source function whose arguments are being passed
        cbk: Callback function to match arguments against
        args: Positional arguments passed to fn
        kwargs: Keyword arguments passed to fn

    Returns:
        Tuple of (matched_args, matched_kwargs) for the callback function

    Example:
    def fn(a, b, c=1, d=2):
        pass

    def cbk(a, d=2):
        pass

    args_dump(fn, cbk, (1, 2), {"c": 3, "d": 4})
    >> ( (1,), {"d": 4})
    """
    fn_params = list(signature(fn).parameters.keys())
    cbk_params = set(signature(cbk).parameters.keys())

    # Match positional arguments
    matched_args = tuple(
        arg for i, arg in enumerate(args) if fn_params[i] in cbk_params
    )

    # Match keyword arguments
    matched_kwargs = {k: v for k, v in kwargs.items() if k in cbk_params}

    return matched_args, matched_kwargs
