"""Milky 数据模型."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel
from nonebot.compat import PYDANTIC_V2, ConfigDict, model_dump


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
