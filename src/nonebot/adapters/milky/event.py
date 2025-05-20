from copy import deepcopy
from typing_extensions import override
from typing import TYPE_CHECKING, Union, Literal, TypeVar, Optional

from nonebot.internal.adapter import Event as BaseEvent
from nonebot.compat import model_validator, type_validate_python

from .message import Reply, Message, MessageSegment
from .model import Group, Friend, Member, ModelBase


class Event(BaseEvent, ModelBase):
    """Milky 的事件基类"""

    __event_type__: str
    """事件类型"""

    time: int
    """事件发生的时间戳"""

    self_id: int
    """机器人 QQ 号"""

    data: dict
    """事件数据"""

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
    def is_private(self) -> bool:
        return True

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

    segments: list[dict]
    """消息段列表"""

    client_seq: Optional[int] = None
    """私聊消息的客户端序列号"""

    friend: Optional[Friend] = None

    group: Optional[Group] = None

    group_member: Optional[Member] = None

    @property
    def message(self) -> Message:
        """消息对象"""
        return Message.from_elements(self.segments)

    def get_reply(self) -> Reply:
        """根据消息 ID 构造回复对象"""
        return MessageSegment.reply(self.message_seq, self.client_seq)

    @property
    def sender(self) -> Union[Friend, Member]:
        return self.friend or self.group_member  # type: ignore


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

    @property
    def is_private(self) -> bool:
        """是否为私聊消息"""
        return self.data.message_scene == "friend"


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

    sender_id: int
    """发送者 QQ号"""

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

    @property
    def is_private(self) -> bool:
        """是否为私聊消息"""
        return self.data.message_scene == "friend"

    @override
    def get_user_id(self) -> str:
        return str(self.data.sender_id)

    @override
    def get_session_id(self) -> str:
        if self.data.message_scene == "group":
            return f"{self.data.peer_id}_{self.data.sender_id}"
        return str(self.data.peer_id)


class FriendNudgeData(ModelBase):
    """好友头像双击数据"""

    user_id: int
    """好友 QQ 号"""

    is_self_send: bool
    """是否是自己发送的头像双击"""

    is_self_receive: bool
    """是否是自己接收的头像双击"""


@register_event_class
class FriendNudgeEvent(NoticeEvent):
    """好友头像双击事件"""

    __event_type__ = "friend_nudge"

    data: FriendNudgeData

    @override
    def get_user_id(self) -> str:
        return str(self.data.user_id)

    @override
    def get_session_id(self) -> str:
        return str(self.data.user_id)

    @override
    def is_tome(self) -> bool:
        return self.data.is_self_receive

    @property
    def is_private(self) -> bool:
        return True


class FriendFileUploadData(ModelBase):
    """好友文件上传数据"""

    user_id: int
    """好友 QQ 号"""

    file_id: str
    """文件 ID"""

    file_name: str
    """文件名"""

    file_size: int
    """文件大小"""

    is_self: bool
    """是否是自己上传的文件"""


@register_event_class
class FriendFileUploadEvent(NoticeEvent):
    """好友文件上传事件"""

    __event_type__ = "friend_file_upload"

    data: FriendFileUploadData

    @override
    def get_user_id(self) -> str:
        return str(self.data.user_id)

    @override
    def get_session_id(self) -> str:
        return str(self.data.user_id)

    @override
    def is_tome(self) -> bool:
        return True

    @property
    def is_private(self) -> bool:
        return True


class GroupAdminChangeData(ModelBase):
    """群管理员变更数据"""

    group_id: int
    """群号"""

    user_id: int
    """发生变更的 QQ 号"""

    is_set: bool
    """是否被设置为管理员, True 为设置, False 为取消"""


@register_event_class
class GroupAdminChangeEvent(NoticeEvent):
    """群管理员变更事件"""

    __event_type__ = "group_admin_change"

    data: GroupAdminChangeData

    @override
    def get_user_id(self) -> str:
        return str(self.data.user_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.user_id}"


class GroupEssenceMessageChangeData(ModelBase):
    """群精华消息变更数据"""

    group_id: int
    """群号"""

    message_seq: int
    """发生变更的消息序列号"""

    is_set: bool
    """是否被设置为精华, True 为设置, False 为取消"""


@register_event_class
class GroupEssenceMessageChangeEvent(NoticeEvent):
    """群精华消息变更事件"""

    __event_type__ = "group_essence_message_change"

    data: GroupEssenceMessageChangeData


class GroupMemberIncreaseData(ModelBase):
    """群成员增加数据"""

    group_id: int
    """群号"""

    user_id: int
    """增加成员的 QQ 号"""

    operator_id: Optional[int] = None
    """操作人 QQ号 （管理员 QQ 号，如果是管理员同意入群）"""

    invitor_id: Optional[int] = None
    """邀请人 QQ号 （邀请人 QQ 号，如果是被邀请入群）"""


@register_event_class
class GroupMemberIncreaseEvent(NoticeEvent):
    """群成员增加事件"""

    __event_type__ = "group_member_increase"

    data: GroupMemberIncreaseData

    @override
    def get_user_id(self) -> str:
        return str(self.data.user_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.user_id}"


class GroupMemberDecreaseData(ModelBase):
    """群成员减少数据"""

    group_id: int
    """群号"""

    user_id: int
    """减少成员的 QQ 号"""

    operator_id: Optional[int] = None
    """操作人 QQ号 （管理员 QQ 号，如果是管理员踢人）"""


@register_event_class
class GroupMemberDecreaseEvent(NoticeEvent):
    """群成员减少事件"""

    __event_type__ = "group_member_decrease"

    data: GroupMemberDecreaseData

    @override
    def get_user_id(self) -> str:
        return str(self.data.user_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.user_id}"


class GroupNameChangeData(ModelBase):
    """群名称变更数据"""

    group_id: int
    """群号"""

    name: str
    """新的群名称"""

    operator_id: int
    """操作人 QQ号"""


@register_event_class
class GroupNameChangeEvent(NoticeEvent):
    """群名称变更事件"""

    __event_type__ = "group_name_change"

    data: GroupNameChangeData

    @override
    def get_user_id(self) -> str:
        return str(self.data.operator_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.operator_id}"


class GroupMessageReactionData(ModelBase):
    """群消息表情数据"""

    group_id: int
    """群号"""

    user_id: int
    """发送者 QQ号"""

    message_seq: int
    """被回应的消息序列号"""

    face_id: str
    """表情 ID"""

    is_add: bool
    """是否添加表情，True 为添加，False 为取消"""


@register_event_class
class GroupMessageReactionEvent(NoticeEvent):
    """群消息表情回应事件"""

    __event_type__ = "group_message_reaction"

    data: GroupMessageReactionData

    @override
    def get_user_id(self) -> str:
        return str(self.data.user_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.user_id}"


class GroupMuteData(ModelBase):
    """群成员禁言数据"""

    group_id: int
    """群号"""

    user_id: int
    """被禁言的 QQ 号"""

    duration: int
    """禁言时长，单位秒; 0 表示取消禁言"""


@register_event_class
class GroupMuteEvent(NoticeEvent):
    """群成员禁言事件"""

    __event_type__ = "group_mute"

    data: GroupMuteData

    @property
    def is_cancel(self) -> bool:
        """是否为取消禁言"""
        return self.data.duration == 0

    @override
    def get_user_id(self) -> str:
        return str(self.data.user_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.user_id}"


class GroupWholeMuteData(ModelBase):
    """群全员禁言数据"""

    group_id: int
    """群号"""

    operator_id: int
    """操作人 QQ号"""

    is_mute: bool
    """是否禁言，True 为禁言，False 为取消禁言"""


@register_event_class
class GroupWholeMuteEvent(NoticeEvent):
    """群全员禁言事件"""

    __event_type__ = "group_whole_mute"

    data: GroupWholeMuteData

    @property
    def is_cancel(self) -> bool:
        """是否为取消禁言"""
        return not self.data.is_mute

    @override
    def get_user_id(self) -> str:
        return str(self.data.operator_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.operator_id}"


class GroupNudgeData(ModelBase):
    """群头像双击数据"""

    group_id: int
    """群号"""

    sender_id: int
    """发送者 QQ号"""

    receiver_id: int
    """接收者 QQ号"""


@register_event_class
class GroupNudgeEvent(NoticeEvent):
    """群头像双击事件"""

    __event_type__ = "group_nudge"

    data: GroupNudgeData

    @override
    def get_user_id(self) -> str:
        return str(self.data.sender_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.sender_id}"


class GroupFileUploadData(ModelBase):
    """群文件上传数据"""

    group_id: int
    """群号"""

    user_id: int
    """上传者 QQ号"""

    file_id: str
    """文件 ID"""

    file_name: str
    """文件名"""

    file_size: int
    """文件大小"""


@register_event_class
class GroupFileUploadEvent(NoticeEvent):
    """群文件上传事件"""

    __event_type__ = "group_file_upload"

    data: GroupFileUploadData

    @override
    def get_user_id(self) -> str:
        return str(self.data.user_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.user_id}"


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

    @override
    def get_user_id(self) -> str:
        return str(self.data.operator_id)

    @override
    def get_session_id(self) -> str:
        return str(self.data.operator_id)

    @override
    def is_tome(self) -> bool:
        return True

    @property
    def is_private(self) -> bool:
        return True


class GroupJoinRequestData(ModelBase):
    """入群请求数据"""

    request_id: str
    """请求 ID"""

    operator_id: int
    """发起请求的 QQ 号"""

    group_id: int
    """申请进入的群号"""

    comment: Optional[str] = None
    """申请附加信息"""


@register_event_class
class GroupJoinRequestEvent(RequestEvent):
    """入群请求事件"""

    __event_type__ = "group_join_request"

    data: GroupJoinRequestData

    @override
    def get_user_id(self) -> str:
        return str(self.data.operator_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.operator_id}"


class GroupInviteRequestData(ModelBase):
    """邀请他人入群请求数据"""

    request_id: str
    """请求 ID"""

    operator_id: int
    """发起请求的 QQ 号"""

    group_id: int
    """邀请加入的群号"""

    invitee_id: int
    """被邀请人 QQ 号"""


@register_event_class
class GroupInviteRequestEvent(RequestEvent):
    """邀请他人入群请求事件"""

    __event_type__ = "group_invite_request"

    data: GroupInviteRequestData

    @override
    def get_user_id(self) -> str:
        return str(self.data.operator_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.operator_id}"


class GroupInvitationData(ModelBase):
    """邀请机器人(自己)入群请求数据"""

    request_id: str
    """请求 ID"""

    operator_id: int
    """发起请求的 QQ 号"""

    group_id: int
    """邀请加入的群号"""


@register_event_class
class GroupInvitationEvent(RequestEvent):
    """邀请机器人(自己)入群请求事件"""

    __event_type__ = "group_invitation_request"

    data: GroupInvitationData

    @override
    def get_user_id(self) -> str:
        return str(self.data.operator_id)

    @override
    def get_session_id(self) -> str:
        return f"{self.data.group_id}_{self.data.operator_id}"
