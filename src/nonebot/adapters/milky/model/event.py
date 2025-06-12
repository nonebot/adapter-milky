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
    def sender(self) -> Union[Friend, Member]:
        return self.friend or self.group_member  # type: ignore


class FriendRequest(ModelBase):
    """好友请求"""

    request_id: str
    """请求 ID"""

    time: int
    """请求发起时间"""

    is_filtered: bool
    """是否已被过滤（发起自风险账户）"""

    initiator_id: int
    """请求发起者 QQ号"""

    state: Literal["pending", "accepted", "rejected", "ignored"]
    """请求状态"""

    comment: Optional[str] = None
    """好友请求附加信息"""

    via: Optional[str] = None
    """好友请求来源"""


class GroupJoinRequest(ModelBase):
    """入群请求"""

    request_id: str
    """请求 ID"""

    time: int
    """请求发起时间"""

    is_filtered: bool
    """是否已被过滤（发起自风险账户）"""

    initiator_id: int
    """请求发起者 QQ号"""

    state: Literal["pending", "accepted", "rejected", "ignored"]
    """请求状态"""

    group_id: int
    """群号"""

    operator_id: Optional[int] = None
    """处理请求的用户 QQ 号"""

    request_type: Literal["join", "invite"]
    """类型标识符"""

    comment: Optional[str] = None
    """入群请求附加信息"""

    invitee_id: Optional[int] = None
    """被邀请者 QQ号"""


class InvitationRequest(ModelBase):
    """邀请请求"""

    request_id: str
    """请求 ID"""

    time: int
    """请求发起时间"""

    is_filtered: bool
    """是否已被过滤（发起自风险账户）"""

    initiator_id: int
    """请求发起者 QQ号"""

    state: Literal["pending", "accepted", "rejected", "ignored"]
    """请求状态"""

    group_id: int
    """群号"""
