from typing import Union

from nonebot.permission import Permission

from .event import FriendMessageEvent, GroupMessageEvent, TempMessageEvent


async def _private(event: Union[FriendMessageEvent, TempMessageEvent]) -> bool:
    return True


async def _private_friend(event: FriendMessageEvent) -> bool:
    return True


async def _private_temp(event: TempMessageEvent) -> bool:
    return True


PRIVATE: Permission = Permission(_private)
"""匹配任意私聊消息类型事件"""
PRIVATE_FRIEND: Permission = Permission(_private_friend)
"""匹配任意好友私聊消息类型事件"""
PRIVATE_TEMP: Permission = Permission(_private_temp)
"""匹配任意临时私聊消息类型事件"""


async def _group(event: GroupMessageEvent) -> bool:
    return True


async def _group_member(event: GroupMessageEvent) -> bool:
    return event.data.sender.role == "member"  # type: ignore


async def _group_admin(event: GroupMessageEvent) -> bool:
    return event.data.sender.role == "admin"  # type: ignore


async def _group_owner(event: GroupMessageEvent) -> bool:
    return event.data.sender.role == "owner"  # type: ignore


GROUP: Permission = Permission(_group)
"""匹配任意群聊消息类型事件"""
GROUP_MEMBER: Permission = Permission(_group_member)
"""匹配任意群员群聊消息类型事件"""
GROUP_ADMIN: Permission = Permission(_group_admin)
"""匹配任意群管理员群聊消息类型事件"""
GROUP_OWNER: Permission = Permission(_group_owner)
"""匹配任意群主群聊消息类型事件"""

__all__ = [
    "PRIVATE",
    "PRIVATE_FRIEND",
    "PRIVATE_TEMP",
    "GROUP",
    "GROUP_MEMBER",
    "GROUP_ADMIN",
    "GROUP_OWNER",
]
