from io import BytesIO
from pathlib import Path
from collections.abc import Iterable
from dataclasses import field, asdict, dataclass
from typing_extensions import NotRequired, override
from typing import TYPE_CHECKING, Any, Union, Literal, ClassVar, Optional, TypedDict

from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment

from .utils import to_uri

if TYPE_CHECKING:
    from .bot import Bot


class MessageSegment(BaseMessageSegment["Message"]):
    __element_type__: ClassVar[str] = ""

    @classmethod
    @override
    def get_message_class(cls) -> type["Message"]:
        # 返回适配器的 Message 类型本身
        return Message

    @classmethod
    def parse(cls, data: dict[str, Any]) -> "MessageSegment":
        return cls(cls.__element_type__, data)

    def dump(self):
        return asdict(self)

    def __init_subclass__(cls, **kwargs):
        cls.__element_type__ = kwargs.get("element_type", cls.__name__.lower())

    @override
    def __str__(self) -> str:
        shown_data = {k: v for k, v in self.data.items() if not k.startswith("_")}
        # 返回该消息段的纯文本表现形式，通常在日志中展示
        return self.data["text"] if self.is_text() else f"[{self.type}: {shown_data}]"

    @override
    def is_text(self) -> bool:
        # 判断该消息段是否为纯文本
        return self.type == "text"

    @staticmethod
    def text(content: str) -> "Text":
        """纯文本消息段"""
        return Text("text", {"text": content})

    @staticmethod
    def mention(user_id: int) -> "Mention":
        """提及 (@) 消息段"""
        return Mention("mention", {"user_id": user_id})

    @staticmethod
    def mention_all() -> "MentionAll":
        """提及全体 (@全体成员) 消息段"""
        return MentionAll("mention_all", {})

    @staticmethod
    def face(face_id: str) -> "Face":
        """表情消息段"""
        return Face("face", {"face_id": face_id})

    @staticmethod
    def reply(message_seq: int) -> "Reply":
        """引用消息段"""
        return Reply("reply", {"message_seq": message_seq})

    @staticmethod
    def image(
        url: Optional[str] = None,
        *,
        path: Optional[Union[Path, str]] = None,
        base64: Optional[str] = None,
        raw: Union[None, bytes, BytesIO] = None,
        summary: Optional[str] = None,
        sub_type: Literal["normal", "sticker"] = "normal",
    ):
        """图片消息段"""
        uri = to_uri(url=url, path=path, base64=base64, raw=raw)
        return Image("image", {"uri": uri, "summary": summary, "sub_type": sub_type})

    @staticmethod
    def record(
        url: Optional[str] = None,
        *,
        path: Optional[Union[Path, str]] = None,
        base64: Optional[str] = None,
        raw: Union[None, bytes, BytesIO] = None,
    ):
        """语音消息段"""
        uri = to_uri(url=url, path=path, base64=base64, raw=raw)
        return Record("record", {"uri": uri})

    @staticmethod
    def video(
        url: Optional[str] = None,
        *,
        path: Optional[Union[Path, str]] = None,
        base64: Optional[str] = None,
        raw: Union[None, bytes, BytesIO] = None,
        thumb_url: Optional[str] = None,
    ):
        """视频消息段"""
        uri = to_uri(url=url, path=path, base64=base64, raw=raw)
        return Video("video", {"uri": uri, "thumb_url": thumb_url})

    @staticmethod
    def forward(messages: list["OutgoingForwardedMessage"]) -> "Forward":
        """合并转发消息段"""
        return Forward("forward", {"messages": messages})

    @staticmethod
    def node(
        user_id: int,
        name: str,
        segments: "Message",
    ) -> "OutgoingForwardedMessage":
        """合并转发消息节点"""
        return OutgoingForwardedMessage(user_id=user_id, name=name, segments=segments)


class TextData(TypedDict):
    text: str


@dataclass
class Text(MessageSegment):
    data: TextData = field(default_factory=dict)  # type: ignore


class MentionData(TypedDict):
    user_id: int


@dataclass
class Mention(MessageSegment):
    data: MentionData = field(default_factory=dict)  # type: ignore


@dataclass
class MentionAll(MessageSegment, element_type="mention_all"):
    pass


class FaceData(TypedDict):
    face_id: str


@dataclass
class Face(MessageSegment):
    data: FaceData = field(default_factory=dict)  # type: ignore


class ReplyData(TypedDict):
    message_seq: int


@dataclass
class Reply(MessageSegment):
    data: ReplyData = field(default_factory=dict)  # type: ignore


class IncomingImageData(TypedDict):
    resource_id: str
    temp_url: str
    summary: NotRequired[str]
    sub_type: Literal["normal", "sticker"]


class OutgoingImageData(TypedDict):
    uri: str
    summary: Optional[str]
    sub_type: Literal["normal", "sticker"]


@dataclass
class Image(MessageSegment):
    data: Union[IncomingImageData, OutgoingImageData] = field(default_factory=dict)  # type: ignore


class IncomingRecordData(TypedDict):
    resource_id: str
    temp_url: str
    duration: int


class OutgoingRecordData(TypedDict):
    uri: str


@dataclass
class Record(MessageSegment):
    data: Union[IncomingRecordData, OutgoingRecordData] = field(default_factory=dict)  # type: ignore


class IncomingVideoData(TypedDict):
    resource_id: str
    temp_url: str


class OutgoingVideoData(TypedDict):
    uri: str
    thumb_url: Optional[str]


@dataclass
class Video(MessageSegment):
    data: Union[IncomingVideoData, OutgoingVideoData] = field(default_factory=dict)  # type: ignore


class IncomingForwardData(TypedDict):
    forward_id: str


@dataclass
class OutgoingForwardedMessage:
    user_id: int
    name: str
    segments: list[MessageSegment]


class OutgoingForwardData(TypedDict):
    messages: list[OutgoingForwardedMessage]


@dataclass
class Forward(MessageSegment):
    data: Union[IncomingForwardData, OutgoingForwardData] = field(default_factory=dict)  # type: ignore

    @classmethod
    def parse(cls, data: dict[str, Any]) -> "Forward":
        if "forward_id" not in data:
            return cls(
                "forward",
                {
                    "messages": [
                        OutgoingForwardedMessage(
                            user_id=msg["user_id"],
                            name=msg["name"],
                            segments=Message.from_elements(msg["segments"]),
                        )
                        for msg in data["messages"]
                    ],
                },
            )
        return cls("forward", {"forward_id": data["forward_id"]})

    def dump(self):
        if "messages" not in self.data:
            return {"type": self.type, "data": {"forward_id": self.data["forward_id"]}}
        return {
            "type": self.type,
            "data": {
                "messages": [
                    {
                        "user_id": message.user_id,
                        "name": message.name,
                        "segments": [seg.dump() for seg in message.segments],
                    }
                    for message in self.data["messages"]
                ]
            },
        }


class MarketFaceData(TypedDict):
    url: str


@dataclass
class MarketFace(MessageSegment, element_type="market_face"):
    data: MarketFaceData = field(default_factory=dict)  # type: ignore


class LightAPPData(TypedDict):
    app_name: str
    json_payload: str


@dataclass
class LightAPP(MessageSegment, element_type="light_app"):
    data: LightAPPData = field(default_factory=dict)  # type: ignore


class XMLData(TypedDict):
    service_id: int
    xml_payload: str


@dataclass
class XML(MessageSegment, element_type="xml"):
    data: XMLData = field(default_factory=dict)  # type: ignore


TYPE_MAPPING = {cls.__element_type__: cls for cls in MessageSegment.__subclasses__()}  # type: ignore


class Message(BaseMessage[MessageSegment]):
    @classmethod
    @override
    def get_segment_class(cls) -> type[MessageSegment]:
        # 返回适配器的 MessageSegment 类型本身
        return MessageSegment

    @staticmethod
    @override
    def _construct(msg: str) -> Iterable[MessageSegment]:
        yield MessageSegment.text(msg)

    @classmethod
    def from_elements(cls, elements: list[dict]) -> "Message":
        msg = Message()
        for element in elements:
            msg.append(TYPE_MAPPING[element["type"]].parse(element["data"]))
        return msg

    def to_elements(self) -> list[dict]:
        res = []
        for seg in self:
            res.append(seg.dump())
        return res

    async def sendable(self, bot: "Bot", refresh_resources: bool = False) -> "Message":
        """确保消息段可发送

        Args:
            bot: 机器人实例
            refresh_resources: 是否刷新资源链接，默认为 False
        """
        new = self.__class__()
        for seg in self:
            if isinstance(seg, (Image, Record, Video)) and "resource_id" in seg.data and "uri" not in seg.data:
                data = seg.dump()["data"]
                if "temp_url" not in data or refresh_resources:
                    data["uri"] = await bot.get_resource_temp_url(resource_id=data["resource_id"])
                else:
                    data["uri"] = data["temp_url"]
                new.append(seg.parse(data))
            elif isinstance(seg, Forward) and "forward_id" in seg.data:
                forward_id = seg.data["forward_id"]
                messages = await bot.get_forwarded_messages(forward_id=forward_id)
                new.append(
                    MessageSegment.forward(
                        # TODO: 拿 user_id
                        [MessageSegment.node(int(bot.self_id), msg.name, msg.message) for msg in messages]
                    )
                )
            elif isinstance(seg, (MarketFace, LightAPP, XML)):
                continue
            else:
                new.append(seg)
        return new
