from typing import Optional

from nonebot.exception import AdapterException
from nonebot.exception import ActionFailed as BaseActionFailed
from nonebot.exception import NetworkError as BaseNetworkError
from nonebot.exception import NoLogException as BaseNoLogException
from nonebot.exception import ApiNotAvailable as BaseApiNotAvailable


class MilkyAdapterException(AdapterException):
    def __init__(self):
        super().__init__("OneBot V11")


class NoLogException(BaseNoLogException, MilkyAdapterException):
    pass


class NetworkError(BaseNetworkError, MilkyAdapterException):
    """网络错误。"""

    def __init__(self, msg: Optional[str] = None):
        super().__init__()
        self.msg: Optional[str] = msg
        """错误原因"""

    def __repr__(self):
        return f"NetWorkError(message={self.msg!r})"


class InvalidParameter(NetworkError):
    """参数格式错误。"""


class NoAccessToken(NetworkError):
    """鉴权凭据未提供。"""


class InvalidAccessToken(NetworkError):
    """鉴权凭据不匹配。"""


class UnsupportedApi(NetworkError):
    """API 未定义。"""


class UnsupportedContentType(NetworkError):
    """不支持的 Content-Type。"""


class ApiNotAvailable(BaseApiNotAvailable, MilkyAdapterException):
    def __init__(self, msg: Optional[str] = None):
        super().__init__()
        self.msg: Optional[str] = msg
        """错误原因"""


class ActionFailed(BaseActionFailed, MilkyAdapterException):
    """API 请求返回错误信息。"""

    def __init__(self, **kwargs):
        super().__init__()
        self.info = kwargs
        """所有错误信息"""

    def __repr__(self):
        return "ActionFailed(" + ", ".join(f"{k}={v!r}" for k, v in self.info.items()) + ")"
