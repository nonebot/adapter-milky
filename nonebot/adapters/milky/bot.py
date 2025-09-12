import re
from io import BytesIO
from pathlib import Path
from collections.abc import Sequence
from typing_extensions import override
from typing import TYPE_CHECKING, Any, Union, Literal, Optional

from nonebot.message import handle_event
from nonebot.compat import type_validate_python

from nonebot.adapters import Bot as BaseBot

from .config import ClientInfo
from .utils import api, log, to_uri
from .message import Reply, Message, MessageSegment
from .model.common import Group, Friend, Member, Profile
from .event import Event, MessageEvent, MessageRecallEvent
from .model.message import IncomingMessage, IncomingForwardedMessage
from .model.api import (
    ImplInfo,
    FilesInfo,
    LoginInfo,
    Announcement,
    FriendRequest,
    MessageResponse,
    GroupNotification,
    GroupEssenceMessage,
)

if TYPE_CHECKING:
    from .adapter import Adapter


async def _check_reply(bot: "Bot", event: MessageEvent) -> None:
    """检查消息中存在的回复，去除并赋值 `event.reply`, `event.to_me`。

    参数:
        bot: Bot 对象
        event: MessageEvent 对象
    """
    try:
        index = [x.type == "reply" for x in event.message].index(True)
    except ValueError:
        return
    msg_seg: Reply = event.message[index]  # type: ignore
    try:
        event.reply = await bot.get_message(
            message_scene=event.data.message_scene,
            peer_id=event.data.peer_id,
            message_seq=msg_seg.data["message_seq"],
        )
    except Exception as e:
        log("WARNING", f"Error when getting message reply info: {e!r}")
        return

    # ensure string comparation
    if str(event.reply.sender_id) == str(event.self_id):
        event.to_me = True
    del event.message[index]

    if (
        len(event.message) > index
        and event.message[index].type == "mention"
        and str(event.message[index].data["user_id"]) == str(event.reply.sender_id)
    ):
        del event.message[index]

    if len(event.message) > index and event.message[index].type == "text":
        event.message[index].data["text"] = event.message[index].data["text"].lstrip()
        if not event.message[index].data["text"]:
            del event.message[index]

    if not event.message:
        event.message.append(MessageSegment.text(""))


def _check_at_me(bot: "Bot", event: MessageEvent) -> None:
    """检查消息开头或结尾是否存在 @机器人，去除并赋值 `event.to_me`。

    参数:
        bot: Bot 对象
        event: MessageEvent 对象
    """
    if not isinstance(event, MessageEvent):
        return

    # ensure message not empty
    if not event.message:
        event.message.append(MessageSegment.text(""))

    if event.data.message_scene != "group":
        event.to_me = True
    else:

        def _is_at_me_seg(segment: MessageSegment):
            return segment.type == "mention" and str(segment.data["user_id"]) == str(event.self_id)

        # check the first segment
        if _is_at_me_seg(event.message[0]):
            event.to_me = True
            event.message.pop(0)
            if event.message and event.message[0].type == "text":
                event.message[0].data["text"] = event.message[0].data["text"].lstrip()
                if not event.message[0].data["text"]:
                    del event.message[0]
            if event.message and _is_at_me_seg(event.message[0]):
                event.message.pop(0)
                if event.message and event.message[0].type == "text":
                    event.message[0].data["text"] = event.message[0].data["text"].lstrip()
                    if not event.message[0].data["text"]:
                        del event.message[0]

        if not event.to_me:
            # check the last segment
            i = -1
            last_msg_seg = event.message[i]
            if last_msg_seg.type == "text" and not last_msg_seg.data["text"].strip() and len(event.message) >= 2:
                i -= 1
                last_msg_seg = event.message[i]

            if _is_at_me_seg(last_msg_seg):
                event.to_me = True
                del event.message[i:]

        if not event.message:
            event.message.append(MessageSegment.text(""))


def _check_nickname(bot: "Bot", event: MessageEvent) -> None:
    """检查消息开头是否存在昵称，去除并赋值 `event.to_me`。

    参数:
        bot: Bot 对象
        event: MessageEvent 对象
    """
    first_msg_seg = event.message[0]
    if first_msg_seg.type != "text":
        return

    nicknames = {re.escape(n) for n in bot.config.nickname}
    if not nicknames:
        return

    # check if the user is calling me with my nickname
    nickname_regex = "|".join(nicknames)
    first_text = first_msg_seg.data["text"]
    if m := re.search(rf"^({nickname_regex})([\s,，]*|$)", first_text, re.IGNORECASE):
        log("DEBUG", f"User is calling me {m[1]}")
        event.to_me = True
        first_msg_seg.data["text"] = first_text[m.end() :]


class Bot(BaseBot):
    adapter: "Adapter"

    @override
    def __init__(self, adapter: "Adapter", self_id: str, info: ClientInfo):
        super().__init__(adapter, self_id)

        # Bot 配置信息
        self.info: ClientInfo = info

    async def _call(self, action: str, data: Optional[dict] = None) -> dict:
        return await self.adapter.call_http(self.info, action, data)

    def __getattr__(self, item):
        raise AttributeError(f"'Bot' object has no attribute '{item}'")

    async def handle_event(self, event: Event) -> None:
        """处理收到的事件。"""
        if isinstance(event, MessageEvent):
            await _check_reply(self, event)
            _check_at_me(self, event)
            _check_nickname(self, event)

        await handle_event(self, event)

    @override
    async def send(
        self,
        event: "Event",
        message: Union[str, "Message", "MessageSegment"],
        **kwargs: Any,
    ) -> Any:
        if isinstance(event, (MessageEvent, MessageRecallEvent)):
            if event.is_private:
                return await self.send_private_message(
                    user_id=int(event.get_user_id()),
                    message=message,
                )
            return await self.send_group_message(
                group_id=event.data.peer_id,
                message=message,
            )
        elif event.is_private:
            return await self.send_private_message(
                user_id=int(event.get_user_id()),
                message=message,
            )
        elif group_id := getattr(event.data, "group_id", None):
            return await self.send_group_message(
                group_id=group_id,
                message=message,
            )
        else:
            raise TypeError(event)

    # =-=-= 消息 API =-=-=

    @api
    async def send_private_message(
        self,
        *,
        user_id: int,
        message: Union[str, MessageSegment, Sequence[MessageSegment]],
    ):
        """发送私聊消息

        Args:
            user_id: 好友 QQ 号
            message: 消息内容

        Returns:
            消息结果 (message_seq, time)
        """
        _message = Message(message)
        _message = await _message.sendable(self)
        result = await self._call(
            "send_private_message",
            {
                "user_id": user_id,
                "message": _message.to_elements(),
            },
        )
        return type_validate_python(MessageResponse, result)

    @api
    async def send_group_message(
        self,
        *,
        group_id: int,
        message: Union[str, MessageSegment, Sequence[MessageSegment]],
    ):
        """发送群消息

        Args:
            group_id: 群号
            message: 消息内容
        Returns:
            消息结果 (message_seq, time)
        """

        _message = Message(message)
        _message = await _message.sendable(self)
        result = await self._call(
            "send_group_message",
            {
                "group_id": group_id,
                "message": _message.to_elements(),
            },
        )
        return type_validate_python(MessageResponse, result)

    @api
    async def get_message(self, *, message_scene: str, peer_id: int, message_seq: int) -> IncomingMessage:
        """获取消息

        Args:
            message_scene: 消息场景
            peer_id: 好友 QQ 号或群号
            message_seq: 消息序列号
        Returns:
            消息对象 (IncomingMessage)
        """

        result = await self._call("get_message", locals())
        return type_validate_python(IncomingMessage, result["message"])

    @api
    async def get_history_messages(
        self,
        *,
        message_scene: str,
        peer_id: int,
        start_message_seq: Optional[int] = None,
        limit: int = 20,
    ) -> tuple[list[IncomingMessage], int]:
        """获取历史消息

        Args:
            message_scene: 消息场景
            peer_id: 好友 QQ 号或群号
            start_message_seq: 起始消息序列号，不提供则从最新消息开始
            limit: 获取的最大消息数量
        Returns:
            消息列表 (list[IncomingMessage]) 和下一页起始消息序列号
        """

        result = await self._call("get_history_messages", locals())
        return type_validate_python(list[IncomingMessage], result["messages"]), result["next_message_seq"]

    @api
    async def get_resource_temp_url(self, resource_id: str) -> str:
        """获取资源临时链接

        Args:
            resource_id: 资源 ID
        Returns:
            可下载的临时链接
        """

        result = await self._call("get_resource_temp_url", {"resource_id": resource_id})
        return result["url"]

    @api
    async def get_forwarded_messages(self, forward_id: str) -> list[IncomingForwardedMessage]:
        """获取合并转发消息内容

        Args:
            forward_id: 转发消息 ID
        Returns:
            消息列表 (list[IncomingMessage])
        """
        result = await self._call("get_forwarded_messages", {"forward_id": forward_id})
        return type_validate_python(list[IncomingForwardedMessage], result["messages"])

    @api
    async def recall_private_message(self, *, user_id: int, message_seq: int) -> None:
        """撤回私聊消息

        Args:
            user_id: 好友 QQ 号
            message_seq: 消息序列号
        """
        await self._call("recall_private_message", locals())

    @api
    async def recall_group_message(self, *, group_id: int, message_seq: int) -> None:
        """撤回群消息

        Args:
            group_id: 群号
            message_seq: 消息序列号
        """
        await self._call("recall_group_message", locals())

    @api
    async def mark_message_as_read(self, *, message_scene: str, peer_id: int, message_seq: int) -> None:
        """标记消息为已读

        Args:
            message_scene: 消息场景
            peer_id: 好友 QQ 号或群号
            message_seq: 标为已读的消息序列号，该消息及更早的消息将被标记为已读
        """
        await self._call("mark_message_as_read", locals())

    # =-=-= 系统 API =-=-=

    @api
    async def get_login_info(self) -> LoginInfo:
        """获取登录信息"""
        result = await self._call("get_login_info")
        return type_validate_python(LoginInfo, result)

    @api
    async def get_impl_info(self) -> ImplInfo:
        """获取协议端信息"""
        result = await self._call("get_impl_info")
        return type_validate_python(ImplInfo, result)

    @api
    async def get_user_profile(self, *, user_id: int) -> Profile:
        """获取用户资料

        Args:
            user_id: 用户 QQ 号
        Returns:
            用户资料字典
        """
        result = await self._call("get_user_profile", {"user_id": user_id})
        return type_validate_python(Profile, result)

    @api
    async def get_friend_list(self, *, no_cache: bool = False) -> list[Friend]:
        """获取好友列表"""
        result = await self._call("get_friend_list", {"no_cache": no_cache})
        return type_validate_python(list[Friend], result["friends"])

    @api
    async def get_friend_info(self, *, user_id: int, no_cache: bool = False) -> Friend:
        """获取好友信息"""
        result = await self._call("get_friend_info", locals())
        return type_validate_python(Friend, result["friend"])

    @api
    async def get_group_list(self, *, no_cache: bool = False) -> list[Group]:
        """获取群列表"""
        result = await self._call("get_group_list", {"no_cache": no_cache})
        return type_validate_python(list[Group], result["groups"])

    @api
    async def get_group_info(self, *, group_id: int, no_cache: bool = False) -> Group:
        """获取群信息"""
        result = await self._call("get_group_info", locals())
        return type_validate_python(Group, result["group"])

    @api
    async def get_group_member_list(self, *, group_id: int, no_cache: bool = False) -> list[Member]:
        """获取群成员列表"""
        result = await self._call("get_group_member_list", locals())
        return type_validate_python(list[Member], result["members"])

    @api
    async def get_group_member_info(self, *, group_id: int, user_id: int, no_cache: bool = False) -> Member:
        """获取群成员信息"""
        result = await self._call("get_group_member_info", locals())
        return type_validate_python(Member, result["member"])

    @api
    async def get_cookies(self, *, domain: str):
        """获取指定域名的 Cookie"""
        result = await self._call("get_cookies", {"domain": domain})
        return result["cookies"]

    @api
    async def get_csrf_token(self):
        """获取 CSRF Token"""
        result = await self._call("get_csrf_token")
        return result["csrf_token"]

    # =-=-= 好友 API =-=-=

    @api
    async def send_friend_nudge(self, *, user_id: int, is_self: bool = False) -> None:
        """发送好友头像双击动作"""
        await self._call("send_friend_nudge", locals())

    @api
    async def send_profile_like(self, *, user_id: int, count: int = 1) -> None:
        """发送个人名片点赞动作"""
        await self._call("send_profile_like", locals())

    @api
    async def get_friend_requests(self, *, limit: int = 20, is_filtered: bool = False) -> list[FriendRequest]:
        """获取好友请求列表

        Args:
            limit: 获取的最大请求数量
            is_filtered: 是否只获取被过滤（由风险账号发起）的通知
        """
        result = await self._call("get_friend_requests", locals())
        return type_validate_python(list[FriendRequest], result["requests"])

    @api
    async def accept_friend_request(self, *, initiator_uid: str, is_filtered: bool = False) -> None:
        """同意好友请求

        Args:
            initiator_uid: 请求发起者 UID
            is_filtered: 是否是被过滤的请求
        """
        await self._call("accept_friend_request", locals())

    @api
    async def reject_friend_request(
        self, *, initiator_uid: str, is_filtered: bool = False, reason: Optional[str] = None
    ) -> None:
        """拒绝好友请求

        Args:
            initiator_uid: 请求发起者 UID
            is_filtered: 是否是被过滤的请求
            reason: 拒绝理由
        """
        await self._call("reject_friend_request", locals())

    # =-=-= 群聊 API =-=-=

    @api
    async def set_group_name(self, *, group_id: int, new_group_name: str) -> None:
        """设置群名称"""
        await self._call("set_group_name", locals())

    @api
    async def set_group_avatar(
        self,
        *,
        group_id: int,
        url: Optional[str] = None,
        path: Optional[Union[Path, str]] = None,
        base64: Optional[str] = None,
        raw: Union[None, bytes, BytesIO] = None,
    ) -> None:
        """设置群头像

        image_uri: 图像文件 URI，支持 file:// http(s):// base64:// 三种格式

        Args:
            group_id: 群号
            url: 图像 URL
            path: 图像文件路径
            base64: 图像文件 base64 编码
            raw: 图像文件二进制数据
        """
        uri = to_uri(url=url, path=path, base64=base64, raw=raw)
        await self._call("set_group_avatar", {"group_id": group_id, "image_uri": uri})

    @api
    async def set_group_member_card(self, *, group_id: int, user_id: int, card: str) -> None:
        """设置群成员名片

        Args:
            group_id: 群号
            user_id: 被设置的成员 QQ 号
            card: 新群名片
        """
        await self._call("set_group_member_card", locals())

    @api
    async def set_group_member_special_title(self, *, group_id: int, user_id: int, special_title: str) -> None:
        """设置群成员专属头衔

        Args:
            group_id: 群号
            user_id: 被设置的成员 QQ 号
            special_title: 专属头衔
        """
        await self._call("set_group_member_special_title", locals())

    @api
    async def set_group_member_admin(self, *, group_id: int, user_id: int, is_set: bool = True) -> None:
        """设置群管理员

        Args:
            group_id: 群号
            user_id: 被设置的成员 QQ 号
            is_set: 是否设置为管理员，false 为取消管理员
        """
        await self._call("set_group_member_admin", locals())

    @api
    async def set_group_member_mute(self, *, group_id: int, user_id: int, duration: int) -> None:
        """设置群成员禁言

        Args:
            group_id: 群号
            user_id: 被设置的成员 QQ 号
            duration: 禁言时长，单位为秒，0 为取消禁言
        """
        await self._call("set_group_member_mute", locals())

    @api
    async def set_group_whole_mute(self, *, group_id: int, is_mute: bool = True) -> None:
        """设置全员禁言

        Args:
            group_id: 群号
            is_mute: 是否设置为全员禁言，false 为取消全员禁言
        """
        await self._call("set_group_whole_mute", locals())

    @api
    async def kick_group_member(self, *, group_id: int, user_id: int, reject_add_request: bool = False) -> None:
        """踢出群成员

        Args:
            group_id: 群号
            user_id: 被踢出的成员 QQ 号
            reject_add_request: 是否拒绝后续的加群请求，默认不拒绝
        """
        await self._call("kick_group_member", locals())

    @api
    async def get_group_announcement_list(self, *, group_id: int) -> list[Announcement]:
        """获取群公告列表

        Args:
            group_id: 群号
        """
        result = await self._call("get_group_announcement_list", {"group_id": group_id})
        return type_validate_python(list[Announcement], result["announcements"])

    @api
    async def send_group_announcement(
        self,
        *,
        group_id: int,
        content: str,
        url: Optional[str] = None,
        path: Optional[Union[Path, str]] = None,
        base64: Optional[str] = None,
        raw: Union[None, bytes, BytesIO] = None,
    ):
        """发送群公告

        image_uri: 公告图片 URI，支持 file:// http(s):// base64:// 三种格式

        Args:
            group_id: 群号
            content: 公告内容
            url: 公告图片 URL
            path: 公告图片文件路径
            base64: 公告图片文件 base64 编码
            raw: 公告图片文件二进制数据
        """
        uri = to_uri(url=url, path=path, base64=base64, raw=raw)
        await self._call("send_group_announcement", {"group_id": group_id, "content": content, "image_uri": uri})

    @api
    async def delete_group_announcement(self, *, group_id: int, announcement_id: str) -> None:
        """删除群公告

        Args:
            group_id: 群号
            announcement_id: 公告 ID
        """
        await self._call("delete_group_announcement", locals())

    @api
    async def get_group_essence_messages(self, *, group_id: int, page_index: int, page_size: int) -> dict:
        """获取群精华消息

        Args:
            group_id: 群号
            page_index: 页码索引，从 0 开始
            page_size: 每页包含的精华消息数量
        Returns:
            精华消息列表和是否已到最后一页
        """
        result = await self._call("get_group_essence_messages", locals())
        return {
            "messages": type_validate_python(list[GroupEssenceMessage], result["messages"]),
            "is_end": result["is_end"],
        }

    @api
    async def set_group_essence_message(self, *, group_id: int, message_seq: int, is_set: bool = True) -> None:
        """设置群精华消息

        Args:
            group_id: 群号
            message_seq: 消息序列号
            is_set: 是否设置为精华消息，false 表示取消精华
        """
        await self._call("set_group_essence_message", locals())

    @api
    async def quit_group(self, *, group_id: int) -> None:
        """退出群聊

        Args:
            group_id: 群号
        """
        await self._call("quit_group", locals())

    @api
    async def send_group_message_reaction(
        self, *, group_id: int, message_seq: int, reaction: str, is_add: bool = True
    ) -> None:
        """发送群消息表情

        Args:
            group_id: 群号
            message_seq: 消息序列号
            reaction: 表情名称
            is_add: 是否添加表情，false 为删除表情
        """
        await self._call("send_group_message_reaction", locals())

    @api
    async def send_group_nudge(self, *, group_id: int, user_id: int) -> None:
        """发送群头像双击动作

        Args:
            group_id: 群号
            user_id: 被戳的群成员 QQ 号
        """
        await self._call("send_group_nudge", locals())

    @api
    async def get_group_notifications(
        self, *, start_notification_seq: Optional[int] = None, is_filtered: bool = False, limit: int = 20
    ) -> tuple[list[GroupNotification], int]:
        """获取群通知

        Args:
            start_notification_seq: 起始通知序列号
            is_filtered: 是否只获取被过滤（由风险账号发起）的通知
            limit: 获取的最大通知数量
        Returns:
            通知列表和下一页起始通知序列号
        """
        result = await self._call("get_group_notifications", locals())
        return type_validate_python(list[GroupNotification], result["notifications"]), result["next_notification_seq"]

    @api
    async def accept_group_request(
        self,
        *,
        notification_seq: int,
        notification_type: Literal["join_request", "invited_join_request"],
        group_id: int,
        is_filtered: bool = False,
    ) -> None:
        """同意群请求

        Args:
            notification_seq: 请求对应的通知序列号
            notification_type: 请求对应的通知类型, 可选值为 "join_request" 或 "invited_join_request"
            group_id: 请求所在的群号
            is_filtered: 是否是被过滤的请求
        """
        await self._call("accept_group_request", locals())

    @api
    async def reject_group_request(
        self,
        *,
        notification_seq: int,
        notification_type: Literal["join_request", "invited_join_request"],
        group_id: int,
        is_filtered: bool = False,
        reason: Optional[str] = None,
    ) -> None:
        """拒绝群请求

        Args:
            notification_seq: 请求对应的通知序列号
            notification_type: 请求对应的通知类型, 可选值为 "join_request" 或 "invited_join_request"
            group_id: 请求所在的群号
            is_filtered: 是否是被过滤的请求
            reason: 拒绝理由
        """
        await self._call("reject_group_request", locals())

    @api
    async def accept_group_invitation(self, *, group_id: int, invitation_seq: int) -> None:
        """同意群邀请

        Args:
            group_id: 群号
            invitation_seq: 邀请序列号
        """
        await self._call("accept_group_invitation", locals())

    @api
    async def reject_group_invitation(self, *, group_id: int, invitation_seq: int) -> None:
        """拒绝群邀请

        Args:
            group_id: 群号
            invitation_seq: 邀请序列号
        """
        await self._call("reject_group_invitation", locals())

    # =-=-= 文件 API =-=-=

    @api
    async def upload_private_file(
        self,
        *,
        user_id: int,
        url: Optional[str] = None,
        path: Optional[Union[Path, str]] = None,
        base64: Optional[str] = None,
        raw: Union[None, bytes, BytesIO] = None,
        file_name: Optional[str] = None,
    ) -> str:
        """上传私聊文件

        file_uri: 文件 URI，支持 file:// http(s):// base64:// 三种格式

        Args:
            user_id: 好友 QQ 号
            url: 文件 URL
            path: 文件路径
            base64: 文件 base64 编码
            raw: 文件二进制数据
            file_name: 文件名，若未提供则使用文件路径的文件名
        Returns:
            文件 ID
        """
        uri = to_uri(url=url, path=path, base64=base64, raw=raw)
        if file_name is None:
            if not path:
                raise ValueError("file_name must be provided if path or url is not given")
            file_name = Path(path).name
        result = await self._call("upload_private_file", {"file_uri": uri, "file_name": file_name, "user_id": user_id})
        return result["file_id"]

    @api
    async def upload_group_file(
        self,
        *,
        group_id: int,
        url: Optional[str] = None,
        path: Optional[Union[Path, str]] = None,
        base64: Optional[str] = None,
        raw: Union[None, bytes, BytesIO] = None,
        file_name: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
    ) -> str:
        """上传群文件

        file_uri: 文件 URI，支持 file:// http(s):// base64:// 三种格式

        Args:
            group_id: 群号
            url: 文件 URL
            path: 文件路径
            base64: 文件 base64 编码
            raw: 文件二进制数据
            file_name: 文件名，若未提供则使用文件路径中的文件名
            parent_folder_id: 父文件夹 ID，默认为根目录
        Returns:
            文件 ID
        """
        uri = to_uri(url=url, path=path, base64=base64, raw=raw)
        if file_name is None:
            if not path:
                raise ValueError("file_name must be provided if path or url is not given")
            file_name = Path(path).name
        result = await self._call(
            "upload_group_file",
            {"file_uri": uri, "group_id": group_id, "file_name": file_name, "parent_folder_id": parent_folder_id},
        )
        return result["file_id"]

    @api
    async def get_private_file_download_url(self, *, user_id: int, file_id: str, file_hash: str) -> str:
        """获取私聊文件下载链接

        Args:
            user_id: 好友 QQ 号
            file_id: 文件 ID
            file_hash: 文件的 TriSHA1 哈希值
        Returns:
            文件下载链接
        """
        result = await self._call("get_private_file_download_url", locals())
        return result["download_url"]

    @api
    async def get_group_file_download_url(self, *, group_id: int, file_id: str) -> str:
        """获取群文件下载链接

        Args:
            group_id: 群号
            file_id: 文件 ID
        Returns:
            可下载的链接
        """
        result = await self._call("get_group_file_download_url", locals())
        return result["download_url"]

    @api
    async def get_group_files(self, *, group_id: int, parent_folder_id: Optional[str] = None) -> FilesInfo:
        """获取群文件列表

        Args:
            group_id: 群号
            parent_folder_id: 父文件夹 ID，默认为根目录
        """
        result = await self._call("get_group_files", locals())
        return type_validate_python(FilesInfo, result)

    @api
    async def move_group_file(
        self, *, group_id: int, file_id: str, parent_folder_id: str = "/", target_folder_id: str = "/"
    ) -> None:
        """移动群文件

        Args:
            group_id: 群号
            file_id: 文件 ID
            parent_folder_id: 文件所在的文件夹 ID
            target_folder_id: 目标文件夹 ID
        """
        await self._call("move_group_file", locals())

    @api
    async def rename_group_file(
        self, *, group_id: int, file_id: str, parent_folder_id: str = "/", new_file_name: str
    ) -> None:
        """重命名群文件

        Args:
            group_id: 群号
            file_id: 文件 ID
            parent_folder_id: 文件所在的文件夹 ID
            new_file_name: 新文件名称
        """
        await self._call("rename_group_file", locals())

    @api
    async def delete_group_file(self, *, group_id: int, file_id: str) -> None:
        """删除群文件

        Args:
            group_id: 群号
            file_id: 文件 ID
        """
        await self._call("delete_group_file", locals())

    @api
    async def create_group_folder(self, *, group_id: int, folder_name: str) -> str:
        """创建群文件夹

        Args:
            group_id: 群号
            folder_name: 文件夹名
        Returns:
            新建文件夹的 ID
        """
        result = await self._call("create_group_folder", locals())
        return result["folder_id"]

    @api
    async def rename_group_folder(self, *, group_id: int, folder_id: str, new_folder_name: str) -> None:
        """重命名群文件夹

        Args:
            group_id: 群号
            folder_id: 文件夹 ID
            new_folder_name: 新文件夹名
        """
        await self._call("rename_group_folder", locals())

    @api
    async def delete_group_folder(self, *, group_id: int, folder_id: str) -> None:
        """删除群文件夹

        Args:
            group_id: 群号
            folder_id: 文件夹 ID
        """
        await self._call("delete_group_folder", locals())
