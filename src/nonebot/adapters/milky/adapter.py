import json
import asyncio
from typing import Any, Optional, cast
from typing_extensions import override

from nonebot.internal.driver import Response
from nonebot.exception import WebSocketClosed
from nonebot.compat import type_validate_python
from nonebot.utils import DataclassEncoder, escape_tag
from nonebot.drivers import (
    URL,
    Driver,
    Request,
    ASGIMixin,
    WebSocket,
    HTTPClientMixin,
    HTTPServerSetup,
    WebSocketClientMixin,
)

from nonebot import get_plugin_config
from nonebot.adapters import Adapter as BaseAdapter

from .bot import Bot
from .model import ModelBase
from .config import Config, ClientInfo
from .event import EVENT_CLASSES, Event, MessageEvent
from .exception import NetworkError, ApiNotAvailable, MilkyAdapterException
from .utils import API, log, clean_params, handle_api_result, raise_api_response

RECONNECT_INTERVAL = 3.0


class Adapter(BaseAdapter):

    @override
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.milky_config: Config = get_plugin_config(Config)
        self.connections: dict[str, WebSocket] = {}
        self.tasks: set["asyncio.Task"] = set()
        self._setup()

    @classmethod
    @override
    def get_name(cls) -> str:
        return "Milky"

    def _setup(self) -> None:
        if self.milky_config.milky_clients:
            if not isinstance(self.driver, WebSocketClientMixin):
                log(
                    "WARNING",
                    f"Current driver {self.config.driver} does not support websocket client connections! Ignored",
                )
            elif not isinstance(self.driver, HTTPClientMixin):
                log(
                    "WARNING",
                    f"Current driver {self.config.driver} does not support http client connections! Ignored",
                )
            else:
                self.on_ready(self._start_forward)
        if self.milky_config.milky_webhook:
            if not isinstance(self.driver, ASGIMixin):
                log(
                    "WARNING",
                    f"Current driver {self.config.driver} does not support http server! Ignored",
                )
            else:
                http_setup = HTTPServerSetup(
                    URL("/milky/"),
                    "POST",
                    f"{self.get_name()} Root HTTP",
                    self._handle_http,
                )
                self.setup_http_server(http_setup)

        self.driver.on_shutdown(self._stop)

    async def _handle_http(self, request: Request) -> Response:
        assert self.milky_config.milky_webhook, "Milky webhook config is not set"
        if data := request.content:
            json_data = json.loads(data)
            if event := self.json_to_event(json_data):
                self_id = str(event.self_id)
                if not (bot := self.bots.get(self_id, None)):
                    bot = Bot(self, self_id, self.milky_config.milky_webhook)
                    self.bot_connect(bot)
                    log("INFO", f"<y>Bot {escape_tag(self_id)}</y> connected")
                bot = cast(Bot, bot)
                task = asyncio.create_task(bot.handle_event(event))
                task.add_done_callback(self.tasks.discard)
                self.tasks.add(task)
        else:
            return Response(400, content="Invalid request body")
        return Response(204)

    async def _start_forward(self) -> None:
        for info in self.milky_config.milky_clients:
            try:
                task = asyncio.create_task(self.ws_connect(info))
                task.add_done_callback(self.tasks.discard)
                self.tasks.add(task)
            except Exception as e:
                log(
                    "ERROR",
                    f"<r><bg #f8bbd0>Bad url {info.ws_url()!s} " "in milky forward websocket config</bg #f8bbd0></r>",
                    e,
                )

    async def _stop(self) -> None:
        for task in self.tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(
            *(asyncio.wait_for(task, timeout=10) for task in self.tasks),
            return_exceptions=True,
        )

    @override
    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Any:
        log("DEBUG", f"Bot {bot.self_id} calling API <y>{api}</y>")
        api_handler: Optional[API] = getattr(bot.__class__, api, None)
        if api_handler is None:
            raise ApiNotAvailable(api)
        return await api_handler(bot, **data)

    async def call_http(
        self,
        info: ClientInfo,
        action: str,
        params: Optional[dict] = None,
    ) -> dict:
        data = clean_params(params or {})
        timeout: float = data.get("_timeout", self.config.api_timeout)
        data = {k: v.dict_() if isinstance(v, ModelBase) else v for k, v in data.items()}
        header = {"Content-Type": "application/json"}
        if info.access_token:
            header["Authorization"] = f"Bearer {info.access_token}"
        req = Request(
            "POST",
            info.get_url(action),
            content=json.dumps(data, cls=DataclassEncoder),
            headers=header,
            timeout=timeout,
        )

        try:
            response = await self.request(req)
            raise_api_response(response.status_code, str(response.content))
            if not response.content:
                raise ValueError("Empty response")
            return handle_api_result(json.loads(response.content))  # type: ignore
        except MilkyAdapterException:
            raise
        except Exception as e:
            raise NetworkError(f"HTTP request failed: {e!r}") from e

    async def ws_connect(self, client: ClientInfo) -> None:
        headers = {}
        ws_url = client.ws_url()
        request = Request("GET", ws_url, headers=headers, timeout=30.0)

        bot: Optional[Bot] = None

        while True:
            try:
                async with self.websocket(request) as ws:
                    log(
                        "DEBUG",
                        f"WebSocket Connection to {ws_url!s} established",
                    )
                    if not bot:
                        info = await self.call_http(client, "get_login_info")
                        bot = Bot(self, str(info["uin"]), client)
                        self.bot_connect(bot)
                        self.connections[bot.self_id] = ws
                        log(
                            "INFO",
                            f"<y>Bot {escape_tag(bot.self_id)}</y> connected",
                        )
                    try:
                        while True:
                            data: dict[str, Any] = json.loads(await ws.receive())
                            event = self.json_to_event(data)
                            if not event:
                                continue
                            task = asyncio.create_task(bot.handle_event(event))
                            task.add_done_callback(self.tasks.discard)
                            self.tasks.add(task)
                    except WebSocketClosed as e:
                        log(
                            "ERROR",
                            "<r><bg #f8bbd0>WebSocket Closed</bg #f8bbd0></r>",
                            e,
                        )
                    except Exception as e:
                        log(
                            "ERROR",
                            (
                                "<r><bg #f8bbd0>"
                                "Error while process data from websocket"
                                f"{ws_url!s}. Trying to reconnect..."
                                "</bg #f8bbd0></r>"
                            ),
                            e,
                        )
                    finally:
                        if bot:
                            self.connections.pop(bot.self_id, None)
                            self.bot_disconnect(bot)
                            bot = None

            except Exception as e:
                log(
                    "ERROR",
                    "<r><bg #f8bbd0>Error while setup websocket to "
                    f"{ws_url!s}. Trying to reconnect...</bg #f8bbd0></r>",
                    e,
                )
                await asyncio.sleep(RECONNECT_INTERVAL)

    @classmethod
    def json_to_event(cls, json_data: Any) -> Optional[Event]:
        """将 json 数据转换为 Event 对象。

        如果为 API 调用返回数据且提供了 Event 对应 Bot，则将数据存入 ResultStore。

        参数:
            json_data: json 数据
            self_id: 当前 Event 对应的 Bot

        返回:
            Event 对象，如果解析失败或为 API 调用返回数据，则返回 None
        """
        if not isinstance(json_data, dict):
            return None

        event_type = json_data.pop("event_type")

        try:
            if event_type not in EVENT_CLASSES:
                log(
                    "WARNING",
                    f"received unsupported event <r><bg #f8bbd0>{event_type}"
                    f"</bg #f8bbd0></r>: {escape_tag(str(json_data))}",
                )
                event = type_validate_python(Event, json_data)
                event.__event_type__ = event_type  # type: ignore
            else:
                event = type_validate_python(EVENT_CLASSES[event_type], json_data)
                if isinstance(event, MessageEvent):
                    event = event.convert()
            return event
        except Exception as e:
            log(
                "ERROR",
                "<r><bg #f8bbd0>Failed to parse event. " f"Raw: {escape_tag(str(json_data))}</bg #f8bbd0></r>",
                e,
            )
