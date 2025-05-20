from ..message import Reply
from .base import ModelBase
from .common import FileInfo, FolderInfo


class MessagePrivateResponse(ModelBase):
    """私聊消息响应"""

    message_seq: int
    """消息序列号"""

    time: int
    """消息发送时间"""

    client_seq: int
    """	消息的客户端序列号"""

    def get_reply(self) -> Reply:
        """获取回复消息"""
        return Reply("reply", {"message_seq": self.message_seq, "client_seq": self.client_seq})


class MessageGroupResponse(ModelBase):
    """群聊消息响应"""

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


class FilesInfo(ModelBase):
    """文件列表信息"""

    files: list[FileInfo]
    """文件列表"""

    folder: list[FolderInfo]
    """文件夹列表"""
