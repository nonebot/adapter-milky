from enum import Enum

from ..message import Reply
from .base import ModelBase
from .common import FileInfo, FolderInfo


class MessageResponse(ModelBase):
    """消息响应"""

    message_seq: int
    """消息序列号"""

    time: int
    """消息发送时间"""

    def get_reply(self) -> Reply:
        """获取回复消息"""
        return Reply("reply", {"message_seq": self.message_seq})


class LoginInfo(ModelBase):
    """登录信息"""

    uin: int
    """登录 QQ号"""

    nickname: str
    """登录昵称"""


class QQProtocolType(str, Enum):
    """QQ 协议平台"""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    ANDROID_PAD = "android_pad"
    ANDROID_PHONE = "android_phone"
    IPAD = "ipad"
    IPHONE = "iphone"
    HARMONY = "harmony"
    WATCH = "watch"


class ImplInfo(ModelBase):
    """协议端信息"""

    impl_name: str
    """协议端名称"""

    impl_version: str
    """协议端版本"""

    qq_protocol_version: str
    """协议端使用的 QQ 协议版本"""

    qq_protocol_type: QQProtocolType
    """协议端使用的 QQ 协议类型"""

    milky_version: str
    """协议端实现的 Milky 协议版本，目前为 1.0"""


class FilesInfo(ModelBase):
    """文件列表信息"""

    files: list[FileInfo]
    """文件列表"""

    folder: list[FolderInfo]
    """文件夹列表"""
