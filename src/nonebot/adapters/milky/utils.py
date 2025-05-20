from io import BytesIO
from pathlib import Path
from base64 import b64encode
from functools import partial
from collections.abc import Awaitable
from typing_extensions import ParamSpec, Concatenate
from typing import TYPE_CHECKING, Any, Union, Generic, TypeVar, Callable, Optional, overload

from nonebot.utils import logger_wrapper

from .exception import (
    ActionFailed,
    NetworkError,
    NoAccessToken,
    UnsupportedApi,
    InvalidParameter,
    InvalidAccessToken,
    UnsupportedContentType,
)

if TYPE_CHECKING:
    from .bot import Bot

T = TypeVar("T")
B = TypeVar("B", bound="Bot")
R = TypeVar("R")
P = ParamSpec("P")


class API(Generic[B, P, R]):
    def __init__(self, func: Callable[Concatenate[B, P], Awaitable[R]]) -> None:
        self.func = func

    def __set_name__(self, owner: type[B], name: str) -> None:
        self.name = name

    @overload
    def __get__(self, obj: None, objtype: type[B]) -> "API[B, P, R]": ...

    @overload
    def __get__(self, obj: B, objtype: Optional[type[B]]) -> Callable[P, Awaitable[R]]: ...

    def __get__(
        self, obj: Optional[B], objtype: Optional[type[B]] = None
    ) -> "API[B, P, R] | Callable[P, Awaitable[R]]":
        if obj is None:
            return self

        return partial(obj.call_api, self.name)  # type: ignore

    async def __call__(self, inst: B, *args: P.args, **kwds: P.kwargs) -> R:
        return await self.func(inst, *args, **kwds)


log = logger_wrapper("Milky")


def handle_api_result(result: Optional[dict[str, Any]]) -> Any:
    """处理 API 请求返回值。

    参数:
        result: API 返回数据

    返回:
        API 调用返回数据

    异常:
        ActionFailed: API 调用失败
    """
    if isinstance(result, dict):
        if result.get("status") == "failed":
            raise ActionFailed(**result)
        return result.get("data")


def raise_api_response(status: int, message: Optional[str] = None) -> None:
    if status == 200:
        return
    if status == 400:
        raise InvalidParameter(message)
    if status == 401:
        raise NoAccessToken(message)
    if status == 403:
        raise InvalidAccessToken(message)
    if status == 404:
        raise UnsupportedApi(message)
    if status == 415:
        raise UnsupportedContentType(message)
    raise NetworkError(message)


def clean_params(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if not k.startswith("_") and k != "self" and v is not None}


def to_uri(
    url: Optional[str] = None,
    path: Optional[Union[Path, str]] = None,
    base64: Optional[str] = None,
    raw: Union[None, bytes, BytesIO] = None,
):
    if sum([bool(url), bool(path), bool(base64), bool(raw)]) > 1:
        raise ValueError("Too many binary initializers!")
    if path:
        return Path(path).as_uri()
    if url:
        return url
    if base64:
        return f"base64://{base64}"
    if raw:
        if isinstance(raw, BytesIO):
            _base64 = b64encode(raw.read()).decode()
        else:
            _base64 = b64encode(raw).decode()
        return f"base64://{_base64}"
    raise ValueError("No binary initializers!")
