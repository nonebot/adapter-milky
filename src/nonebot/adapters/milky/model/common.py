from typing import Literal, Optional

from .base import ModelBase


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
