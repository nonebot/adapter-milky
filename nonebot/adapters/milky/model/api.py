from enum import Enum
from typing import Union, Literal, Optional

from ..message import Reply
from .base import ModelBase


class MessageResponse(ModelBase):
    """消息响应"""

    message_seq: int
    """消息序列号"""

    time: int
    """消息发送时间"""

    def get_reply(self) -> Reply:
        """获取回复消息"""
        return Reply("reply", {"message_seq": self.message_seq})


class LoginInfo(ModelBase):
    """登录信息"""

    uin: int
    """登录 QQ号"""

    nickname: str
    """登录昵称"""


class QQProtocolType(str, Enum):
    """QQ 协议平台"""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    ANDROID_PAD = "android_pad"
    ANDROID_PHONE = "android_phone"
    IPAD = "ipad"
    IPHONE = "iphone"
    HARMONY = "harmony"
    WATCH = "watch"


class ImplInfo(ModelBase):
    """协议端信息"""

    impl_name: str
    """协议端名称"""

    impl_version: str
    """协议端版本"""

    qq_protocol_version: str
    """协议端使用的 QQ 协议版本"""

    qq_protocol_type: QQProtocolType
    """协议端使用的 QQ 协议类型"""

    milky_version: str
    """协议端实现的 Milky 协议版本，目前为 1.0"""


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

    parent_folder_id: str
    """父文件夹 ID"""

    file_size: int
    """文件大小 (字节)"""

    uploaded_time: int
    """上传时间"""

    expire_time: Optional[int] = None
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

    parent_folder_id: str
    """父文件夹 ID"""

    created_time: int
    """创建时间"""

    last_modified_time: int
    """最后修改时间"""

    creator_id: int
    """创建者 QQ 号"""

    file_count: int
    """文件数量"""


class FilesInfo(ModelBase):
    """文件列表信息"""

    files: list[FileInfo]
    """文件列表"""

    folders: list[FolderInfo]
    """文件夹列表"""


class GroupEssenceMessage(ModelBase):
    """群精华消息"""

    group_id: int
    """群号"""

    message_seq: int
    """消息序列号"""

    message_time: int
    """消息发送时的 Unix 时间戳（秒）"""

    sender_id: int
    """发送者 QQ 号"""

    sender_name: str
    """发送者名称"""

    operator_id: int
    """设置精华的操作者 QQ 号"""

    operator_name: str
    """设置精华的操作者名称"""

    operation_time: int
    """消息被设置精华时的 Unix 时间戳（秒）"""

    segments: list[dict]
    """消息段列表"""


class FriendRequest(ModelBase):
    """好友请求"""

    time: int
    """请求发起时间"""

    initiator_id: int
    """请求发起者 QQ 号"""

    initiator_uid: str
    """请求发起者 UID"""

    target_user_id: int
    """目标用户 QQ 号"""

    target_user_uid: str
    """目标用户 UID"""

    state: Literal["pending", "accepted", "rejected", "ignored"]
    """请求状态"""

    comment: str
    """申请附加信息"""

    via: str
    """申请来源"""

    is_filtered: bool
    """请求是否被过滤（发起自风险账户）"""


class GroupJoinRequestNotification(ModelBase):
    """用户入群请求"""

    type: Literal["join_request"] = "join_request"
    group_id: int
    """群号"""

    notification_seq: int
    """通知序列号"""

    is_filtered: bool
    """请求是否被过滤（发起自风险账户）"""

    initiator_id: int
    """发起者 QQ 号"""

    state: Literal["pending", "accepted", "rejected", "ignored"]
    """请求状态"""

    operator_id: Optional[int] = None
    """处理请求的管理员 QQ 号"""

    comment: str
    """入群请求附加信息"""


class GroupAdminChangeNotification(ModelBase):
    """群管理员变更通知"""

    type: Literal["admin_change"] = "admin_change"
    group_id: int
    """群号"""

    notification_seq: int
    """通知序列号"""

    target_user_id: int
    """被设置/取消用户 QQ 号"""

    is_set: bool
    """是否被设置为管理员，`false` 表示被取消管理员"""

    operator_id: int
    """操作者（群主）QQ 号"""


class GroupKickNotification(ModelBase):
    """群成员被移除通知"""

    type: Literal["kick"] = "kick"
    group_id: int
    """群号"""

    notification_seq: int
    """通知序列号"""

    target_user_id: int
    """被移除用户 QQ 号"""

    operator_id: int
    """移除用户的管理员 QQ 号"""


class GroupQuitNotification(ModelBase):
    """群成员退群通知"""

    type: Literal["quit"] = "quit"
    group_id: int
    """群号"""

    notification_seq: int
    """通知序列号"""

    target_user_id: int
    """退群用户 QQ 号"""


class GroupInvitedJoinRequestNotification(ModelBase):
    """群成员邀请他人入群请求"""

    type: Literal["invited_join_request"] = "invited_join_request"
    group_id: int
    """群号"""

    notification_seq: int
    """通知序列号"""

    initiator_id: int
    """邀请者 QQ 号"""

    target_user_id: int
    """被邀请用户 QQ 号"""

    state: Literal["pending", "accepted", "rejected", "ignored"]
    """请求状态"""

    operator_id: Optional[int] = None
    """处理请求的管理员 QQ 号"""


# Union type for all group notifications
GroupNotification = Union[
    GroupJoinRequestNotification,
    GroupAdminChangeNotification,
    GroupKickNotification,
    GroupQuitNotification,
    GroupInvitedJoinRequestNotification,
]
"""群通知"""
