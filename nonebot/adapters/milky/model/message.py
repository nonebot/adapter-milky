from typing import Union, Literal, Optional

from .base import ModelBase
from .common import Group, Friend, Member
from ..message import Reply, Message, MessageSegment


class IncomingMessage(ModelBase):
    """接收的消息"""

    message_scene: Literal["friend", "group", "temp"]

    peer_id: int
    """好友 QQ号或群号"""

    message_seq: int
    """消息序列号"""

    sender_id: int
    """发送者 QQ号"""

    time: int
    """消息发送时间"""

    segments: list[dict]
    """消息段列表"""

    friend: Optional[Friend] = None

    group: Optional[Group] = None

    group_member: Optional[Member] = None

    @property
    def message(self) -> Message:
        """消息对象"""
        return Message.from_elements(self.segments)

    def get_reply(self) -> Reply:
        """根据消息 ID 构造回复对象"""
        return MessageSegment.reply(self.message_seq)

    @property
    def scene(self) -> Union[Group, Friend]:
        return self.group or self.friend  # type: ignore

    @property
    def sender(self) -> Union[Friend, Member]:
        return self.friend or self.group_member  # type: ignore


class IncomingForwardedMessage(ModelBase):
    """接收的转发消息"""

    sender_name: str
    """发送者名称"""

    avatar_url: str
    """发送者头像 URL"""

    time: int
    """消息 Unix 时间戳（秒）"""

    segments: list[dict]
    """消息段列表"""

    @property
    def message(self) -> Message:
        """消息对象"""
        return Message.from_elements(self.segments)
