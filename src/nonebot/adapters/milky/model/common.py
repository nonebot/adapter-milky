from typing import Literal, Optional

from .base import ModelBase


class FriendCategory(ModelBase):
    """好友分组"""

    category_id: int
    """分组 ID"""

    category_name: str
    """分组名称"""


class Profile(ModelBase):
    """用户信息"""

    nickname: str
    """用户昵称"""

    qid: str
    """用户 QID"""

    age: int
    """用户年龄"""

    sex: Literal["male", "female", "unknown"]
    """用户性别"""

    remark: str
    """用户备注"""

    bio: str
    """用户个性签名"""

    level: int
    """用户等级"""

    country: str
    """用户所在国家"""

    city: str
    """用户所在城市"""

    school: str
    """用户所在学校"""


class Friend(ModelBase):
    """好友实体"""

    user_id: int
    """用户 QQ号"""

    nickname: str
    """用户昵称"""

    sex: Literal["male", "female", "unknown"]
    """用户性别"""

    qid: str
    """用户 QID"""

    remark: str
    """好友备注"""

    category: FriendCategory
    """好友分组"""


class Group(ModelBase):
    """群组信息"""

    group_id: int
    """群号"""

    group_name: str
    """群名"""

    member_count: int
    """群成员人数"""

    max_member_count: int
    """群最大成员人数"""


class Member(ModelBase):
    """群成员信息"""

    user_id: int
    """用户 QQ号"""

    nickname: str
    """用户昵称"""

    sex: Literal["male", "female", "unknown"]
    """用户性别"""

    group_id: int
    """群号"""

    card: str
    """成员备注"""

    title: str
    """成员头衔"""

    level: int
    """成员的群等级"""

    role: Literal["member", "admin", "owner"]
    """成员角色"""

    join_time: int
    """成员入群时间"""

    last_sent_time: int
    """成员最后发言时间"""

    shut_up_end_time: Optional[int] = None
    """成员禁言结束时间"""
