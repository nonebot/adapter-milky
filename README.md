<p align="center">
  <a href="https://nonebot.dev/"><img src="https://camo.githubusercontent.com/32db41bc55fa37e0d0085e4fd70e4e74fd34307f6bb4ebdad235bd1b0c8f4126/68747470733a2f2f6e6f6e65626f742e6465762f6c6f676f2e706e67" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# NoneBot-Adapter-Milky

_✨ NoneBot2 Milky 协议适配 / Milky Protocol Adapter for NoneBot2 ✨_

</div>

## 协议介绍

[Milky 协议](https://milky.ntqqrev.org/)

### 协议端

[Lagrange,Milky (WIP)](https://github.com/LagrangeDev/LagrangeV2/)

## 配置

修改 NoneBot 配置文件 `.env` 或者 `.env.*`。

### Driver

参考 [driver](https://nonebot.dev/docs/appendices/config#driver) 配置项，添加 `HTTPClient` 和 `WebSocketClient` 支持。

如：

```dotenv
DRIVER=~httpx+~websockets
```

或

```dotenv
DRIVER=~aiohttp
```

### MILKY_CLIENTS

配置连接配置，如：

```dotenv
SATORI_CLIENTS='
[
  {
    "host": "localhost",
    "port": "8080",
    "access_token": "xxx"
  }
]
'
```

`host` 与 `port` 为 Milky 协议端设置的监听地址与端口，

`access_token` 为可选项，具体情况以 Milky 协议端为准。

## 示例

```python
from nonebot import on_command
from nonebot.adapters.milky import Bot
from nonebot.adapters.milky.event import MessageEvent
from nonebot.adapters.milky.message import MessageSegment


matcher = on_command("test")

@matcher.handle()
async def handle_receive(bot: Bot, event: MessageEvent):
    if event.is_private:
        await bot.send(event, MessageSegment.text("Hello, world!"))
```
