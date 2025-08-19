from datetime import datetime

import pytest
from nonebug import App
from nonebot.compat import type_validate_python


@pytest.mark.asyncio()
async def test_adapter(app: App):
    import nonebot
    from nonebot.adapters.milky import Bot, Adapter
    from nonebot.adapters.milky.event import MessageEvent

    cmd = nonebot.on_command("test")

    @cmd.handle()
    async def handle(bot: Bot):
        await bot.send_group_message(group_id=67890, message="hello")

    async with app.test_matcher(cmd) as ctx:
        adapter: Adapter = nonebot.get_adapter(Adapter)
        bot: Bot = ctx.create_bot(
            base=Bot,
            adapter=adapter,
            self_id="12345",
            info=None,
        )

        ctx.receive_event(
            bot,
            type_validate_python(
                MessageEvent,
                {
                    "time": int(datetime.now().timestamp()),
                    "self_id": 12345,
                    "data": {
                        "message_scene": "group",
                        "peer_id": 67890,
                        "message_id": 1,
                        "message_seq": 100,
                        "sender_id": 54321,
                        "time": int(datetime.now().timestamp()),
                        "segments": [{"type": "text", "data": {"text": "/test"}}],
                        "group": {
                            "group_id": 67890,
                            "group_name": "Test Group",
                            "member_count": 10,
                            "max_member_count": 100,
                        },
                        "group_member": {
                            "user_id": 54321,
                            "nickname": "TestUser",
                            "sex": "unknown",
                            "group_id": 67890,
                            "card": "",
                            "title": "",
                            "level": 100,
                            "role": "member",
                            "join_time": int(datetime.now().timestamp()),
                            "last_sent_time": int(datetime.now().timestamp()),
                        },
                    },
                },
            ),
        )
        ctx.should_call_api("send_group_message", {"group_id": 67890, "message": "hello"})
