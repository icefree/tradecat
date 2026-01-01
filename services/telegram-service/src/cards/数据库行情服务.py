"""基于 TimescaleDB 的排行榜数据读取服务"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from services.币安数据库指标服务 import 币安数据库指标服务

LOGGER = logging.getLogger(__name__)


class 数据库行情服务:
    """调用币安数据库指标服务获取排行榜数据"""

    def __init__(self) -> None:
        self.metric_service = 币安数据库指标服务()

    def top_volume(self, market_type: str, period: str, limit: int) -> List[Dict[str, Any]]:
        return self.metric_service.获取交易量排行(
            market_type=market_type,
            period=period,
            sort_order="desc",
            limit=limit,
        )


@lru_cache(maxsize=1)
def 获取数据库行情服务() -> Optional[数据库行情服务]:
    try:
        return 数据库行情服务()
    except Exception as exc:  # pragma: no cover - 保证主流程不中断
        LOGGER.warning("数据库行情服务不可用: %s", exc)
        return None
