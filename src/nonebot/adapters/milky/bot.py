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
from .utils import API, log, to_uri
from .message import Reply, Message, MessageSegment
from .model.common import Group, Friend, Member, Announcement
from .event import Event, MessageEvent, IncomingMessage, MessageRecallEvent
from .model.api import FilesInfo, LoginInfo, MessageGroupResponse, MessagePrivateResponse

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
        self.call = self.adapter.call_http

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

    @API
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
            私聊消息结果 (message_seq, time, client_seq)
        """
        _message = Message(message)
        _message = await _message.sendable(self)
        result = await self.call(
            self,
            "send_private_message",
            {
                "user_id": user_id,
                "message": _message.to_elements(),
            },
        )
        return type_validate_python(MessagePrivateResponse, result)

    @API
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
            群消息结果 (message_seq, time)
        """

        _message = Message(message)
        _message = await _message.sendable(self)
        result = await self.call(
            self,
            "send_group_message",
            {
                "group_id": group_id,
                "message": _message.to_elements(),
            },
        )
        return type_validate_python(MessageGroupResponse, result)

    @API
    async def get_message(self, *, message_scene: str, peer_id: int, message_seq: int) -> IncomingMessage:
        """获取消息

        Args:
            message_scene: 消息场景
            peer_id: 好友 QQ 号或群号
            message_seq: 消息序列号
        Returns:
            消息对象 (IncomingMessage)
        """

        result = await self.call(self, "get_message", locals())
        return type_validate_python(IncomingMessage, result["message"])

    @API
    async def get_history_messages(
        self,
        *,
        message_scene: str,
        peer_id: int,
        direction: Literal["newer", "older"],
        start_message_seq: Optional[int] = None,
        limit: int = 20,
    ) -> list[IncomingMessage]:
        """获取历史消息

        Args:
            message_scene: 消息场景
            peer_id: 好友 QQ 号或群号
            direction: 消息获取方向
            start_message_seq: 起始消息序列号，不提供则从最新消息开始
            limit: 获取的最大消息数量
        Returns:
            消息列表 (list[IncomingMessage])
        """

        result = await self.call(self, "get_history_messages", locals())
        return type_validate_python(list[IncomingMessage], result["messages"])

    @API
    async def get_resource_temp_url(self, resource_id: str) -> str:
        """获取资源临时链接

        Args:
            resource_id: 资源 ID
        Returns:
            可下载的临时链接
        """

        result = await self.call(self, "get_resource_temp_url", {"resource_id": resource_id})
        return result["url"]

    @API
    async def get_forwarded_messages(self, forward_id: str) -> list[IncomingMessage]:
        """获取合并转发消息内容

        Args:
            forward_id: 转发消息 ID
        Returns:
            消息列表 (list[IncomingMessage])
        """
        result = await self.call(self, "get_forwarded_messages", {"forward_id": forward_id})
        return type_validate_python(list[IncomingMessage], result["messages"])

    @API
    async def recall_private_message(self, *, user_id: int, message_seq: int, client_seq: int) -> None:
        """撤回私聊消息

        Args:
            user_id: 好友 QQ 号
            message_seq: 消息序列号
            client_seq: 客户端序列号
        """
        await self.call(self, "recall_private_message", locals())

    @API
    async def recall_group_message(self, *, group_id: int, message_seq: int) -> None:
        """撤回群消息

        Args:
            group_id: 群号
            message_seq: 消息序列号
        """
        await self.call(self, "recall_group_message", locals())

    @API
    async def get_login_info(self) -> LoginInfo:
        """获取登录信息"""
        result = await self.call(self, "get_login_info")
        return type_validate_python(LoginInfo, result)

    @API
    async def get_friend_list(self, *, no_cache: bool = False) -> list[Friend]:
        """获取好友列表"""
        result = await self.call(self, "get_friend_list", {"no_cache": no_cache})
        return type_validate_python(list[Friend], result["friends"])

    @API
    async def get_friend_info(self, *, user_id: int, no_cache: bool = False) -> Friend:
        """获取好友信息"""
        result = await self.call(self, "get_friend_info", locals())
        return type_validate_python(Friend, result)

    @API
    async def get_group_list(self, *, no_cache: bool = False) -> list[Group]:
        """获取群列表"""
        result = await self.call(self, "get_group_list", {"no_cache": no_cache})
        return type_validate_python(list[Group], result["groups"])

    @API
    async def get_group_info(self, *, group_id: int, no_cache: bool = False) -> Group:
        """获取群信息"""
        result = await self.call(self, "get_group_info", locals())
        return type_validate_python(Group, result)

    @API
    async def get_group_member_list(self, *, group_id: int, no_cache: bool = False) -> list[Member]:
        """获取群成员列表"""
        result = await self.call(self, "get_group_member_list", locals())
        return type_validate_python(list[Member], result["members"])

    @API
    async def get_group_member_info(self, *, group_id: int, user_id: int, no_cache: bool = False) -> Member:
        """获取群成员信息"""
        result = await self.call(self, "get_group_member_info", locals())
        return type_validate_python(Member, result)

    @API
    async def send_friend_nudge(self, *, user_id: int, is_self: bool = False) -> None:
        """发送好友头像双击动作"""
        await self.call(self, "send_friend_nudge", locals())

    @API
    async def send_profile_like(self, *, user_id: int, count: int = 1) -> None:
        """发送个人名片点赞动作"""
        await self.call(self, "send_profile_like", locals())

    @API
    async def set_group_name(self, *, group_id: int, name: str) -> None:
        """设置群名称"""
        await self.call(self, "set_group_name", locals())

    @API
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
        await self.call(self, "set_group_avatar", {"group_id": group_id, "image_uri": uri})

    @API
    async def set_group_member_card(self, *, group_id: int, user_id: int, card: str) -> None:
        """设置群成员名片

        Args:
            group_id: 群号
            user_id: 被设置的成员 QQ 号
            card: 新群名片
        """
        await self.call(self, "set_group_member_card", locals())

    @API
    async def set_group_special_title(self, *, group_id: int, user_id: int, special_title: str) -> None:
        """设置群成员专属头衔

        Args:
            group_id: 群号
            user_id: 被设置的成员 QQ 号
            special_title: 专属头衔
        """
        await self.call(self, "set_group_special_title", locals())

    @API
    async def set_group_member_admin(self, *, group_id: int, user_id: int, is_set: bool = True) -> None:
        """设置群管理员

        Args:
            group_id: 群号
            user_id: 被设置的成员 QQ 号
            is_set: 是否设置为管理员，false 为取消管理员
        """
        await self.call(self, "set_group_member_admin", locals())

    @API
    async def set_group_member_mute(self, *, group_id: int, user_id: int, duration: int) -> None:
        """设置群成员禁言

        Args:
            group_id: 群号
            user_id: 被设置的成员 QQ 号
            duration: 禁言时长，单位为秒，0 为取消禁言
        """
        await self.call(self, "set_group_member_mute", locals())

    @API
    async def set_group_whole_mute(self, *, group_id: int, is_mute: bool = True) -> None:
        """设置全员禁言

        Args:
            group_id: 群号
            is_mute: 是否设置为全员禁言，false 为取消全员禁言
        """
        await self.call(self, "set_group_whole_mute", locals())

    @API
    async def kick_group_member(self, *, group_id: int, user_id: int, reject_add_request: bool = True) -> None:
        """踢出群成员

        Args:
            group_id: 群号
            user_id: 被踢出的成员 QQ 号
            reject_add_request: 是否拒绝后续的加群请求，默认拒绝
        """
        await self.call(self, "kick_group_member", locals())

    @API
    async def get_group_announcement_list(self, *, group_id: int) -> list[Announcement]:
        """获取群公告列表

        Args:
            group_id: 群号
        """
        result = await self.call(self, "get_group_announcement_list", {"group_id": group_id})
        return type_validate_python(list[Announcement], result["announcements"])

    @API
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
        await self.call(self, "send_group_announcement", {"group_id": group_id, "content": content, "image_uri": uri})

    @API
    async def delete_group_announcement(self, *, group_id: int, announcement_id: int) -> None:
        """删除群公告

        Args:
            group_id: 群号
            announcement_id: 公告 ID
        """
        await self.call(self, "delete_group_announcement", locals())

    @API
    async def quit_group(self, *, group_id: int) -> None:
        """退出群聊

        Args:
            group_id: 群号
        """
        await self.call(self, "quit_group", locals())

    @API
    async def send_group_message_reaction(self, *, message_seq: int, reaction: str, is_add: bool = True) -> None:
        """发送群消息表情

        Args:
            message_seq: 消息序列号
            reaction: 表情名称
            is_add: 是否添加表情，false 为删除表情
        """
        await self.call(self, "send_group_message_reaction", locals())

    @API
    async def send_group_nudge(self, *, group_id: int, user_id: int) -> None:
        """发送群头像双击动作

        Args:
            group_id: 群号
            user_id: 被戳的群成员 QQ 号
        """
        await self.call(self, "send_group_nudge", locals())

    @API
    async def accept_request(self, *, request_id: str) -> None:
        """同意请求

        Args:
            request_id: 请求 ID
        """
        await self.call(self, "accept_request", {"request_id": request_id})

    @API
    async def reject_request(self, *, request_id: str, reason: Optional[str] = None) -> None:
        """拒绝请求

        Args:
            request_id: 请求 ID
            reason: 拒绝理由
        """
        await self.call(self, "reject_request", locals())

    @API
    async def upload_private_file(
        self,
        *,
        user_id: int,
        url: Optional[str] = None,
        path: Optional[Union[Path, str]] = None,
        base64: Optional[str] = None,
        raw: Union[None, bytes, BytesIO] = None,
    ) -> str:
        """上传私聊文件

        file_uri: 文件 URI，支持 file:// http(s):// base64:// 三种格式

        Args:
            user_id: 好友 QQ 号
            url: 文件 URL
            path: 文件路径
            base64: 文件 base64 编码
            raw: 文件二进制数据
        Returns:
            文件 ID
        """
        uri = to_uri(url=url, path=path, base64=base64, raw=raw)
        result = await self.call(self, "upload_private_file", {"file_uri": uri, "user_id": user_id})
        return result["file_id"]

    @API
    async def upload_group_file(
        self,
        *,
        group_id: int,
        url: Optional[str] = None,
        path: Optional[Union[Path, str]] = None,
        base64: Optional[str] = None,
        raw: Union[None, bytes, BytesIO] = None,
    ) -> str:
        """上传群文件

        file_uri: 文件 URI，支持 file:// http(s):// base64:// 三种格式

        Args:
            group_id: 群号
            url: 文件 URL
            path: 文件路径
            base64: 文件 base64 编码
            raw: 文件二进制数据
        Returns:
            文件 ID
        """
        uri = to_uri(url=url, path=path, base64=base64, raw=raw)
        result = await self.call(self, "upload_group_file", {"file_uri": uri, "group_id": group_id})
        return result["file_id"]

    @API
    async def get_private_file_download_url(self, *, user_id: int, file_id: str) -> str:
        """获取私聊文件下载链接

        Args:
            user_id: 好友 QQ 号
            file_id: 文件 ID
        Returns:
            可下载的链接
        """
        result = await self.call(self, "get_private_file_download_url", locals())
        return result["download_url"]

    @API
    async def get_group_file_download_url(self, *, group_id: int, file_id: str) -> str:
        """获取群文件下载链接

        Args:
            group_id: 群号
            file_id: 文件 ID
        Returns:
            可下载的链接
        """
        result = await self.call(self, "get_group_file_download_url", locals())
        return result["download_url"]

    @API
    async def get_group_files(self, *, group_id: int, parent_folder_id: Optional[str] = None) -> FilesInfo:
        """获取群文件列表

        Args:
            group_id: 群号
            parent_folder_id: 父文件夹 ID，默认为根目录
        """
        result = await self.call(self, "get_group_files", locals())
        return type_validate_python(FilesInfo, result)

    @API
    async def move_group_file(self, *, group_id: int, file_id: str, target_folder_id: Optional[str] = None) -> None:
        """移动群文件

        Args:
            group_id: 群号
            file_id: 文件 ID
            target_folder_id: 目标文件夹 ID，默认为根目录
        """
        await self.call(self, "move_group_file", locals())

    @API
    async def rename_group_file(self, *, group_id: int, file_id: str, new_name: str) -> None:
        """重命名群文件

        Args:
            group_id: 群号
            file_id: 文件 ID
            new_name: 新文件名
        """
        await self.call(self, "rename_group_file", locals())

    @API
    async def delete_group_file(self, *, group_id: int, file_id: str) -> None:
        """删除群文件

        Args:
            group_id: 群号
            file_id: 文件 ID
        """
        await self.call(self, "delete_group_file", locals())

    @API
    async def create_group_folder(self, *, group_id: int, folder_name: str) -> str:
        """创建群文件夹

        Args:
            group_id: 群号
            folder_name: 文件夹名
        Returns:
            新建文件夹的 ID
        """
        result = await self.call(self, "create_group_folder", locals())
        return result["folder_id"]

    @API
    async def rename_group_folder(self, *, group_id: int, folder_id: str, new_name: str) -> None:
        """重命名群文件夹

        Args:
            group_id: 群号
            folder_id: 文件夹 ID
            new_name: 新文件夹名
        """
        await self.call(self, "rename_group_folder", locals())

    @API
    async def delete_group_folder(self, *, group_id: int, folder_id: str) -> None:
        """删除群文件夹

        Args:
            group_id: 群号
            folder_id: 文件夹 ID
        """
        await self.call(self, "delete_group_folder", locals())
