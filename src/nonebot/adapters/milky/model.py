"""Milky 数据模型."""

from datetime import datetime
from typing import Any, Optional, Literal

from pydantic import BaseModel
from nonebot.compat import PYDANTIC_V2, ConfigDict, model_dump

from .message import Reply


class ModelBase(BaseModel):
    """适配器数据模型的基类."""

    def __init__(self, **data: Any) -> None:
        """初始化模型. 直接向 pydantic 转发."""
        super().__init__(**data)

    def dict_(
        self,
        *,
        include: Optional[set[str]] = None,
        exclude: Optional[set[str]] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        """转化为字典, 直接向 pydantic 转发."""
        _, *_ = by_alias, exclude_none
        res = model_dump(self, include, exclude, True, exclude_unset, exclude_defaults, True)
        return res

    if PYDANTIC_V2:

        model_config: ConfigDict = ConfigDict(
            extra="allow",
            arbitrary_types_allowed=True,
            json_encoders={datetime: lambda dt: int(dt.timestamp())},
        )
    else:

        class Config:
            extra = "allow"
            arbitrary_types_allowed = True
            copy_on_model_validation = "none"
            json_encoders = {
                datetime: lambda dt: int(dt.timestamp()),
            }


class FriendCategory(ModelBase):
    """好友分组"""

    category_id: int
    """分组 ID"""

    category_name: str
    """分组名称"""


class Friend(ModelBase):
    """好友信息"""

    user_id: int
    """好友 QQ号"""

    qid: Optional[str] = None
    """好友 QID"""

    nickname: str
    """好友昵称"""

    remark: str
    """好友备注"""

    category: Optional[FriendCategory] = None
    """好友分组"""


class Group(ModelBase):
    """群组信息"""

    group_id: int
    """群号"""

    name: str
    """群名"""

    member_count: int
    """群成员人数"""

    max_member_count: int
    """群最大成员人数"""


class Member(ModelBase):
    """群成员信息"""

    group_id: int
    """群号"""

    user_id: int
    """成员 QQ号"""

    nickname: str
    """成员昵称"""

    card: str
    """成员备注"""

    title: Optional[str] = None
    """成员头衔"""

    sex: Literal["male", "female", "unknown"]
    """成员性别"""

    level: int
    """成员的群等级"""

    role: Literal["member", "admin", "owner"]
    """成员角色"""

    join_time: int
    """成员入群时间"""

    last_sent_time: int
    """成员最后发言时间"""


class Announcement(ModelBase):
    """群公告"""

    group_id: int
    """群号"""

    announcement_id: str
    """公告 ID"""

    user_id: int
    """发送者 QQ号"""

    time: int
    """公告发布时间"""

    content: str
    """公告内容"""

    image_url: Optional[str] = None
    """公告图片 URL"""


class FileInfo(ModelBase):
    """群组文件详细信息"""

    group_id: int
    """群号"""

    file_id: str
    """文件 ID"""

    file_name: str
    """文件名"""

    parent_folder_id: Optional[str] = None
    """父文件夹 ID"""

    file_size: int
    """文件大小 (字节)"""

    uploaded_time: int
    """上传时间"""

    expire_time: int
    """过期时间"""

    uploader_id: int
    """上传者 QQ 号"""

    downloaded_times: int
    """下载次数"""


class FolderInfo(ModelBase):
    """群组文件夹详细信息"""

    group_id: int
    """群号"""

    folder_id: str
    """文件夹 ID"""

    folder_name: str
    """文件夹名"""

    parent_folder_id: Optional[str] = None
    """父文件夹 ID"""

    created_time: int
    """创建时间"""

    last_modified_time: int
    """最后修改时间"""

    creator_id: int
    """创建者 QQ 号"""

    file_count: int
    """文件数量"""


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
