import io
import os
import re
import base64
from datetime import datetime
from typing_extensions import override
from typing import IO, TYPE_CHECKING, Any, Union, Optional, cast, overload, Sequence

from nonebot.message import handle_event
from nonebot.compat import type_validate_python
from nonebot.internal.matcher import current_event

from nonebot.adapters import Bot as BaseBot

from .config import ClientInfo
from .utils import API, log
from .message import Reply, Message, MessageSegment
from .model import (
    Group,
    Friend,
    Member,
    FileInfo,
    Announcement,
    MessagePrivateResponse,
    MessageGroupResponse
)
from .event import (
    EVENT_CLASSES,
    Event,
    MessageEvent,
    IncomingMessage
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
            message_seq=msg_seg.data["message_seq"]
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
        and event.message[index].type == "at"
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
            return segment.type == "at" and str(segment.data["user_id"]) == str(event.self_id)

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
                    event.message[0].data["text"] = (
                        event.message[0].data["text"].lstrip()
                    )
                    if not event.message[0].data["text"]:
                        del event.message[0]

        if not event.to_me:
            # check the last segment
            i = -1
            last_msg_seg = event.message[i]
            if (
                last_msg_seg.type == "text"
                and not last_msg_seg.data["text"].strip()
                and len(event.message) >= 2
            ):
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
        first_msg_seg.data["text"] = first_text[m.end():]


class Bot(BaseBot):
    adapter: "Adapter"

    @override
    def __init__(self, adapter: "Adapter", self_id: str, info: ClientInfo):
        super().__init__(adapter, self_id)

        # Bot 配置信息
        self.info: ClientInfo = info

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
        if isinstance(event, MessageEvent):
            if event.data.message_scene == "group":
                return await self.send_group_message(
                    group_id=event.data.peer_id,
                    message=message,
                )
            return await self.send_private_message(
                user_id=event.data.peer_id,
                message=message,
            )
        raise TypeError(event)

    @API
    async def send_private_message(
        self,
        *,
        user_id: int,
        message: Union[str, MessageSegment, Sequence[MessageSegment]],
    ):
        """发送私聊消息"""

        _message = Message(message)
        result = await self.adapter.call_http(
            self,
            "send_private_message",
            {
                "user_id": user_id,
                "message": _message.to_elements(),
            }
        )
        return type_validate_python(MessagePrivateResponse, result)

    @API
    async def send_group_message(
        self,
        *,
        group_id: int,
        message: Union[str, MessageSegment, Sequence[MessageSegment]],
    ):
        """发送群消息"""

        _message = Message(message)
        result = await self.adapter.call_http(
            self,
            "send_group_message",
            {
                "group_id": group_id,
                "message": _message.to_elements(),
            }
        )
        return type_validate_python(MessageGroupResponse, result)

    @API
    async def get_message(
        self,
        *,
        message_scene: str,
        peer_id: int,
        message_seq: int
    ) -> IncomingMessage:
        """获取消息"""

        result = await self.adapter.call_http(
            self,
            "get_message",
            {
                "message_scene": message_scene,
                "peer_id": peer_id,
                "message_seq": message_seq
            }
        )
        return type_validate_python(IncomingMessage, result["message"])
