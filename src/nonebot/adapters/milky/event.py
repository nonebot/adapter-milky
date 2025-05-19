from enum import Enum
from copy import deepcopy
from datetime import datetime
from typing_extensions import override, deprecated
from typing import TYPE_CHECKING, Any, Union, Literal, TypeVar, Optional

from pydantic import Field
from nonebot.compat import model_validator, type_validate_python
from nonebot.internal.matcher import current_bot
from nonebot.internal.adapter import Event as BaseEvent

from .message import Message, Reply, MessageSegment
from .model import Group, Friend, Member, ModelBase


class Event(BaseEvent, ModelBase):
    """Milky 的事件基类"""

    __event_type__: str
    """事件类型"""

    time: int
    """事件发生的时间戳"""

    self_id: int
    """机器人 QQ 号"""

    def get_type(self) -> str:
        return ""

    def get_event_name(self) -> str:
        return self.__event_type__

    def get_event_description(self) -> str:
        return self.__event_type__

    def get_user_id(self) -> str:
        raise ValueError("This event does not have a user_id")

    def get_session_id(self) -> str:
        raise ValueError("This event does not have a session_id")

    def get_message(self) -> "Message":
        raise ValueError("This event does not have a message")

    def is_tome(self) -> bool:
        return False

    @property
    def event_type(self) -> str:
        return self.__event_type__


EVENT_CLASSES: dict[str, type[Event]] = {}

E = TypeVar("E", bound="Event")


def register_event_class(event_class: type[E]) -> type[E]:
    EVENT_CLASSES[event_class.__event_type__] = event_class
    return event_class


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

    client_seq: Optional[int] = None
    """私聊消息的客户端序列号"""

    segments: list[dict]
    """消息段列表"""

    @property
    def message(self) -> Message:
        """消息对象"""
        return Message.from_elements(self.segments)

    def get_reply(self) -> Reply:
        """根据消息 ID 构造回复对象"""
        return MessageSegment.reply(self.message_seq, self.client_seq)


@register_event_class
class MessageEvent(Event):
    """接收消息事件"""

    __event_type__ = "message_receive"

    data: IncomingMessage

    reply: Optional[IncomingMessage] = None
    """可能的引用消息对象"""

    to_me: bool = False

    if TYPE_CHECKING:
        message: Message
        original_message: Message

    @model_validator(mode="before")
    def handle_message(cls, values):
        if isinstance(values, dict):
            if isinstance(values["data"], dict):
                segments = values["data"].get("segments", [])
            else:
                segments = values["data"].segments
            values["message"] = Message.from_elements(segments)
            values["original_message"] = deepcopy(values["message"])
        return values

    def convert(self) -> "MessageEvent":
        cls = {
            "friend": FriendMessageEvent,
            "group": GroupMessageEvent,
            "temp": TempMessageEvent,
        }[self.data.message_scene]
        return type_validate_python(cls, self)

    @property
    def message_id(self) -> int:
        """消息 ID"""
        return self.data.message_seq

    @override
    def get_type(self) -> str:
        return "message"

    @override
    def is_tome(self) -> bool:
        return self.to_me

    @override
    def get_message(self) -> "Message":
        return self.message

    @override
    def get_user_id(self) -> str:
        return str(self.data.sender_id)

    @override
    def get_session_id(self) -> str:
        if self.data.message_scene == "group":
            return f"{self.data.peer_id}_{self.data.sender_id}"
        return str(self.data.peer_id)

    @override
    def get_event_name(self) -> str:
        return f"message:{self.data.message_scene}"

    @override
    def get_event_description(self) -> str:
        return f"{self.message_id}: {''.join(str(self.message))}"

    @property
    def reply_to(self) -> Reply:
        """根据消息 ID 构造回复对象"""
        return MessageSegment.reply(self.data.message_seq, self.data.client_seq)


class TempMessageEvent(MessageEvent):
    """临时消息事件"""


class FriendMessageEvent(MessageEvent):
    """好友消息事件"""


class GroupMessageEvent(MessageEvent):
    """群消息事件"""


class NoticeEvent(Event):
    @override
    def get_type(self) -> str:
        return "notice"


class MessageRecallData(ModelBase):
    """撤回消息数据"""

    message_scene: Literal["friend", "group", "temp"]
    """消息 ID"""

    peer_id: int
    """好友 QQ号或群号"""

    message_seq: int
    """消息序列号"""

    operator_id: Optional[int] = None
    """操作人 QQ号"""


@register_event_class
class MessageRecallEvent(NoticeEvent):
    """撤回消息事件"""

    __event_type__ = "message_recall"

    data: MessageRecallData

    @override
    def get_event_name(self) -> str:
        return f"recall:{self.data.message_scene}"


class RequestEvent(Event):

    @override
    def get_type(self) -> str:
        return "request"


class FriendRequestData(ModelBase):
    """好友请求数据"""

    request_id: str
    """请求 ID"""

    operator_id: int
    """发起请求的 QQ 号"""

    comment: Optional[str] = None
    """好友请求附加信息"""

    via: Optional[str] = None
    """好友请求来源"""


@register_event_class
class FriendRequestEvent(RequestEvent):
    """好友请求事件"""

    __event_type__ = "friend_request"

    data: FriendRequestData
