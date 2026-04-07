from pydantic import BaseModel, Field
from yarl import URL


class ClientInfo(BaseModel):
    host: str = "localhost"
    """Milky 协议端地址"""
    port: int = 8080
    """Milky 协议端端口"""
    access_token: str | None = None
    """Milky 协议端 验证密钥"""
    secure: bool = False
    """是否使用 HTTPS 和 WSS 协议"""

    def get_url(self, route: str) -> str:
        return str(URL(f"http{'s' if self.secure else ''}://{self.host}:{self.port}") / "api" / route)

    def ws_url(self):
        return (URL(f"ws{'s' if self.secure else ''}://{self.host}:{self.port}") / "event").with_query(
            None if self.access_token is None else {"access_token": self.access_token}
        )


class Config(BaseModel):
    milky_clients: list[ClientInfo] = Field(default_factory=list)
    """Milky 客户端配置"""
    milky_webhook: ClientInfo | None = None
    """Milky Webhook 配置"""
