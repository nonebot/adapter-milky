"""Milky 权限辅助。"""

from nonebot.permission import Permission

from .bot import Bot
from .event import TempMessageEvent, GroupMessageEvent, FriendMessageEvent


async def _private(event: FriendMessageEvent | TempMessageEvent) -> bool:
    return True


async def _private_friend(event: FriendMessageEvent) -> bool:
    return True


async def _private_group(event: TempMessageEvent) -> bool:
    return True


PRIVATE: Permission = Permission(_private)
""" 匹配任意私聊消息类型事件"""
PRIVATE_FRIEND: Permission = Permission(_private_friend)
"""匹配任意好友私聊消息类型事件"""
PRIVATE_GROUP: Permission = Permission(_private_group)
"""匹配任意群临时私聊消息类型事件"""


async def _group(event: GroupMessageEvent) -> bool:
    return True


async def _group_member(bot: Bot, event: GroupMessageEvent) -> bool:
    if event.data.group_member:
        return event.data.group_member.role == "member"
    prof = await bot.get_group_member_info(group_id=event.data.peer_id, user_id=event.data.sender_id)
    return prof.role == "member"


async def _group_admin(bot: Bot, event: GroupMessageEvent) -> bool:
    if event.data.group_member:
        return event.data.group_member.role == "admin"
    prof = await bot.get_group_member_info(group_id=event.data.peer_id, user_id=event.data.sender_id)
    return prof.role == "admin"


async def _group_owner(bot: Bot, event: GroupMessageEvent) -> bool:
    if event.data.group_member:
        return event.data.group_member.role == "owner"
    prof = await bot.get_group_member_info(group_id=event.data.peer_id, user_id=event.data.sender_id)
    return prof.role == "owner"


GROUP: Permission = Permission(_group)
"""匹配任意群聊消息类型事件"""
GROUP_MEMBER: Permission = Permission(_group_member)
"""匹配任意群员群聊消息类型事件

:::warning 警告
该权限通过 event.sender 进行判断且不包含管理员以及群主！
:::
"""
GROUP_ADMIN: Permission = Permission(_group_admin)
"""匹配任意群管理员群聊消息类型事件"""
GROUP_OWNER: Permission = Permission(_group_owner)
"""匹配任意群主群聊消息类型事件"""

__all__ = [
    "GROUP",
    "GROUP_ADMIN",
    "GROUP_MEMBER",
    "GROUP_OWNER",
    "PRIVATE",
    "PRIVATE_FRIEND",
    "PRIVATE_GROUP",
]
