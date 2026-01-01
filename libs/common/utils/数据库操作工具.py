#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库操作工具
---------------------------------
从策略运行基座中提取的数据库读取与操作通用工具
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, List, MutableMapping, Optional, Sequence

try:
    from dotenv import load_dotenv
    from libs.common.utils.路径助手 import 获取仓库根目录

    env_path = 获取仓库根目录() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

try:
    from psycopg_pool import ConnectionPool
except ModuleNotFoundError as exc:
    raise RuntimeError("运行策略前需要安装 psycopg[binary] 依赖") from exc

from psycopg import sql
from psycopg.rows import dict_row


# --- 常量配置 ---------------------------------------------------------
ALLOWED_INTERVALS = {
    "1m", "5m", "15m", "1h", "4h", "1d", "1w", "1M",
}
# 指标表目前仅覆盖 5m 物理表及其上推聚合视图
METRICS_INTERVALS = {"5m", "15m", "1h", "4h", "1d", "1w"}
TIMESCALE_SCHEMA = os.getenv("KLINE_DB_SCHEMA", "market_data")
DEFAULT_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://opentd:OpenTD_pass@localhost:5433/market_data",
)


# --- 辅助函数 ---------------------------------------------------------
def 标准化周期(interval: str) -> str:
    """标准化周期字符串"""
    interval = interval.strip()
    if interval == "1M":
        return "1M"
    normalized = interval.lower()
    if normalized not in (val.lower() for val in ALLOWED_INTERVALS):
        raise ValueError(f"不支持的周期: {interval}")
    return normalized


def 获取周期后缀(interval: str) -> str:
    """获取周期后缀(用于表名)"""
    return "1M" if interval == "1M" else interval


def 解析符号列表(raw: str) -> List[str]:
    """解析逗号分隔的符号列表"""
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


def 转换浮点值(value: Optional[Decimal | float | int]) -> Optional[float]:
    """转换为浮点数"""
    if value is None:
        return None
    return float(value)


# --- 数据结构 ---------------------------------------------------------
@dataclass(slots=True)
class K线数据:
    """K线数据结构"""
    exchange: str
    symbol: str
    bucket_ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float]
    trade_count: Optional[int]
    is_closed: bool
    source: str
    ingested_at: Optional[datetime]
    updated_at: Optional[datetime]
    taker_buy_volume: Optional[float]
    taker_buy_quote_volume: Optional[float]


@dataclass(slots=True)
class 指标数据:
    """合约持仓/多空占比等指标数据结构"""

    exchange: str
    symbol: str
    create_time: datetime
    sum_open_interest: Optional[float]
    sum_open_interest_value: Optional[float]
    count_toptrader_long_short_ratio: Optional[float]
    sum_toptrader_long_short_ratio: Optional[float]
    count_long_short_ratio: Optional[float]
    sum_taker_long_short_vol_ratio: Optional[float]
    source: str
    is_closed: bool
    ingested_at: Optional[datetime]
    updated_at: Optional[datetime]


# --- 数据库操作类 -----------------------------------------------------
class 数据库操作器:
    """封装TimescaleDB的数据库读取操作"""

    def __init__(
        self,
        连接串: Optional[str] = None,
        *,
        schema: str = TIMESCALE_SCHEMA,
        pool_min: int = 1,
        pool_max: int = 4,
        pool_timeout: float = 30.0,
    ) -> None:
        """初始化数据库操作器

        参数:
            连接串: 数据库连接字符串，默认为环境变量 DATABASE_URL
            schema: 数据库schema，默认为 "market_data"
            pool_min: 连接池最小连接数
            pool_max: 连接池最大连接数
            pool_timeout: 连接超时时间（秒）
        """
        if not 连接串 and not DEFAULT_DB_URL:
            raise RuntimeError("未配置数据库连接串，无法读取行情")

        self.schema = schema
        self.conninfo = 连接串 or DEFAULT_DB_URL
        self.pool = ConnectionPool(
            conninfo=self.conninfo,
            min_size=pool_min,
            max_size=pool_max,
            timeout=pool_timeout,
            kwargs={"row_factory": dict_row},
        )
        self.pool.wait()

    def 关闭(self) -> None:
        """关闭数据库连接池"""
        self.pool.close()

    def __enter__(self) -> "数据库操作器":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.关闭()

    # ---- 符号查询 ---------------------------------------------------
    def 获取符号列表(
        self,
        exchange: str,
        interval: str = "1m",
        limit: Optional[int] = None
    ) -> List[str]:
        """获取指定交易所的符号列表

        参数:
            exchange: 交易所名称（如 "binance_futures_um"）
            interval: K线周期，默认为 "1m"
            limit: 返回结果数量限制

        返回:
            交易对符号列表
        """
        interval = 标准化周期(interval)

        # 对于币安合约，从 candles_{interval} 表查询
        if exchange == "binance_futures_um":
            表名 = f"candles_{interval}"
            query = sql.SQL(
                """
                SELECT DISTINCT symbol
                FROM {schema}.{table}
                WHERE exchange = %s
                ORDER BY symbol
                """
            ).format(
                schema=sql.Identifier(self.schema),
                table=sql.Identifier(表名)
            )
            params: List[object] = [exchange]
        else:
            # 对于其他交易所（现货），从 ingest_offsets 表查询
            query = sql.SQL(
                """
                SELECT symbol
                FROM {schema}.ingest_offsets
                WHERE exchange = %s AND interval = %s
                ORDER BY last_closed_ts DESC NULLS LAST
                """
            ).format(schema=sql.Identifier(self.schema))
            params = [exchange, interval]

        if limit:
            query += sql.SQL(" LIMIT %s")
            params.append(limit)

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return [row["symbol"] for row in cur.fetchall() if row.get("symbol")]

    def 获取最新闭合时间(self, exchange: str, interval: str = "1m") -> datetime:
        """获取指定交易所和周期的最新闭合时间

        参数:
            exchange: 交易所名称
            interval: K线周期，默认为 "1m"

        返回:
            最新K线闭合时间
        """
        interval = 标准化周期(interval)

        # 对于币安合约，从 candles_{interval} 表查询
        if exchange == "binance_futures_um":
            表名 = f"candles_{interval}"
            query = sql.SQL(
                """
                SELECT MAX(bucket_ts) AS last_ts
                FROM {schema}.{table}
                WHERE exchange = %s AND is_closed = true
                """
            ).format(
                schema=sql.Identifier(self.schema),
                table=sql.Identifier(表名)
            )
            params = [exchange]
        else:
            # 对于其他交易所（现货），从 ingest_offsets 表查询
            query = sql.SQL(
                """
                SELECT MAX(last_closed_ts) AS last_ts
                FROM {schema}.ingest_offsets
                WHERE exchange = %s AND interval = %s
                """
            ).format(schema=sql.Identifier(self.schema))
            params = [exchange, interval]

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                if not row or not row.get("last_ts"):
                    raise RuntimeError("无法获取最新闭合时间")
                return row["last_ts"]

    # ---- 指标数据查询 ---------------------------------------------
    def 获取指标窗口(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        limit: int = 200,
        only_closed: bool = True,
    ) -> List[指标数据]:
        """获取单个交易对的指标数据窗口（基于 metrics_* 表/视图）"""

        表 = self._指标表标识(interval)
        条件 = sql.SQL(" AND is_closed = true") if only_closed else sql.SQL("")
        query = sql.SQL(
            """
            SELECT exchange, symbol, create_time,
                   sum_open_interest, sum_open_interest_value,
                   count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio,
                   count_long_short_ratio, sum_taker_long_short_vol_ratio,
                   source, is_closed, ingested_at, updated_at
            FROM {table}
            WHERE exchange = %s AND symbol = %s{closed}
            ORDER BY create_time DESC
            LIMIT %s
            """
        ).format(table=表, closed=条件)

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (exchange, symbol, limit))
                rows = cur.fetchall()
        return [self._行转指标(row) for row in reversed(rows)]

    def 批量获取指标窗口(
        self,
        exchange: str,
        symbols: Sequence[str],
        interval: str,
        limit: int = 200,
        only_closed: bool = True,
    ) -> Dict[str, List[指标数据]]:
        """批量获取多个交易对的指标数据窗口"""

        if not symbols:
            return {}

        表 = self._指标表标识(interval)
        条件 = sql.SQL(" AND is_closed = true") if only_closed else sql.SQL("")
        query = sql.SQL(
            """
            WITH target(symbol) AS (SELECT unnest(%s::text[]))
            SELECT m.*
            FROM target t
            CROSS JOIN LATERAL (
                SELECT exchange, symbol, create_time,
                       sum_open_interest, sum_open_interest_value,
                       count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio,
                       count_long_short_ratio, sum_taker_long_short_vol_ratio,
                       source, is_closed, ingested_at, updated_at
                FROM {table}
                WHERE exchange = %s AND symbol = t.symbol{closed}
                ORDER BY create_time DESC
                LIMIT %s
            ) AS m
            ORDER BY m.symbol, m.create_time
            """
        ).format(table=表, closed=条件)

        data: Dict[str, List[指标数据]] = {sym: [] for sym in symbols}
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (list(symbols), exchange, limit))
                for row in cur.fetchall():
                    data.setdefault(row.get("symbol"), []).append(self._行转指标(row))
        return data

    # ---- K线数据查询 -----------------------------------------------
    def 获取K线窗口(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        limit: int,
        only_closed: bool = True,
    ) -> List[K线数据]:
        """获取单个交易对的K线数据窗口

        参数:
            exchange: 交易所名称
            symbol: 交易对符号
            interval: K线周期
            limit: 返回K线数量
            only_closed: 只返回已闭合的K线

        返回:
            K线数据列表（按时间升序排列）
        """
        表 = self._表标识(interval)
        条件 = sql.SQL(" AND is_closed = true") if only_closed else sql.SQL("")
        query = sql.SQL(
            """
            SELECT exchange, symbol, bucket_ts, open, high, low, close,
                   volume, quote_volume, trade_count,
                   is_closed, source, ingested_at, updated_at,
                   taker_buy_volume, taker_buy_quote_volume
            FROM {table}
            WHERE exchange = %s AND symbol = %s{closed}
            ORDER BY bucket_ts DESC
            LIMIT %s
            """
        ).format(table=表, closed=条件)

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (exchange, symbol, limit))
                rows = cur.fetchall()
        return [self._行转K线(row) for row in reversed(rows)]

    def 批量获取K线窗口(
        self,
        exchange: str,
        symbols: Sequence[str],
        interval: str,
        limit: int,
        only_closed: bool = True,
    ) -> Dict[str, List[K线数据]]:
        """批量获取多个交易对的K线数据窗口

        参数:
            exchange: 交易所名称
            symbols: 交易对符号列表
            interval: K线周期
            limit: 每个交易对返回K线数量
            only_closed: 只返回已闭合的K线

        返回:
            字典，键是交易对符号，值是K线数据列表
        """
        if not symbols:
            return {}

        表 = self._表标识(interval)
        条件 = sql.SQL(" AND is_closed = true") if only_closed else sql.SQL("")
        query = sql.SQL(
            """
            WITH target(symbol) AS (SELECT unnest(%s::text[]))
            SELECT c.*
            FROM target t
            CROSS JOIN LATERAL (
                SELECT exchange, symbol, bucket_ts, open, high, low, close,
                       volume, quote_volume, trade_count,
                       is_closed, source, ingested_at, updated_at,
                       taker_buy_volume, taker_buy_quote_volume
                FROM {table}
                WHERE exchange = %s AND symbol = t.symbol{closed}
                ORDER BY bucket_ts DESC
                LIMIT %s
            ) AS c
            ORDER BY c.symbol, c.bucket_ts
            """
        ).format(table=表, closed=条件)

        data: Dict[str, List[K线数据]] = {sym: [] for sym in symbols}
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (list(symbols), exchange, limit))
                for row in cur.fetchall():
                    data.setdefault(row.get("symbol"), []).append(self._行转K线(row))
        return data

    # ---- 数据转换 ---------------------------------------------------
    def 转换为数据框(self, K线序列: Sequence[K线数据]):
        """将K线数据转换为pandas DataFrame

        参数:
            K线序列: K线数据列表

        返回:
            pandas DataFrame，以bucket_ts为索引
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError("需要安装 pandas 才能导出 DataFrame") from exc

        records = [
            {
                "bucket_ts": k线.bucket_ts,
                "open": k线.open,
                "high": k线.high,
                "low": k线.low,
                "close": k线.close,
                "volume": k线.volume,
                "quote_volume": k线.quote_volume,
                "trade_count": k线.trade_count,
                "taker_buy_volume": k线.taker_buy_volume,
                "taker_buy_quote_volume": k线.taker_buy_quote_volume,
            }
            for k线 in K线序列
        ]
        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df.set_index("bucket_ts", inplace=True)
        return df

    # ---- 私有工具 ---------------------------------------------------
    def _表标识(self, interval: str) -> sql.Composed:
        """生成表标识符"""
        suffix = 获取周期后缀(标准化周期(interval))
        return sql.Identifier(self.schema, f"candles_{suffix}")

    def _指标表标识(self, interval: str) -> sql.Composed:
        """生成指标表/视图标识符（metrics_*）"""
        normalized = 标准化周期(interval)
        if normalized not in (val.lower() for val in METRICS_INTERVALS):
            raise ValueError(f"指标表仅支持周期: {sorted(METRICS_INTERVALS)}")
        return sql.Identifier(self.schema, f"metrics_{获取周期后缀(normalized)}")

    @staticmethod
    def _行转K线(row: Dict[str, object]) -> K线数据:
        """将数据库行转换为K线数据结构"""
        return K线数据(
            exchange=row.get("exchange", "binance"),
            symbol=row.get("symbol", ""),
            bucket_ts=row["bucket_ts"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
            quote_volume=转换浮点值(row.get("quote_volume")),
            trade_count=int(row["trade_count"]) if row.get("trade_count") is not None else None,
            is_closed=bool(row["is_closed"]),
            source=row.get("source", "strategy"),
            ingested_at=row.get("ingested_at"),
            updated_at=row.get("updated_at"),
            taker_buy_volume=转换浮点值(row.get("taker_buy_volume")),
            taker_buy_quote_volume=转换浮点值(row.get("taker_buy_quote_volume")),
        )

    @staticmethod
    def _行转指标(row: Dict[str, object]) -> 指标数据:
        """将数据库行转换为指标数据结构"""

        return 指标数据(
            exchange=row.get("exchange", "binance_futures_um"),
            symbol=row.get("symbol", ""),
            create_time=row["create_time"],
            sum_open_interest=转换浮点值(row.get("sum_open_interest")),
            sum_open_interest_value=转换浮点值(row.get("sum_open_interest_value")),
            count_toptrader_long_short_ratio=转换浮点值(row.get("count_toptrader_long_short_ratio")),
            sum_toptrader_long_short_ratio=转换浮点值(row.get("sum_toptrader_long_short_ratio")),
            count_long_short_ratio=转换浮点值(row.get("count_long_short_ratio")),
            sum_taker_long_short_vol_ratio=转换浮点值(row.get("sum_taker_long_short_vol_ratio")),
            source=row.get("source", "unknown"),
            is_closed=bool(row.get("is_closed", True)),
            ingested_at=row.get("ingested_at"),
            updated_at=row.get("updated_at"),
        )


# --- 便捷函数 ---------------------------------------------------------
def 创建数据库操作器(
    连接串: Optional[str] = None,
    schema: str = TIMESCALE_SCHEMA,
) -> 数据库操作器:
    """便捷函数：创建数据库操作器实例

    参数:
        连接串: 数据库连接字符串
        schema: 数据库schema

    返回:
        数据库操作器实例
    """
    return 数据库操作器(连接串, schema=schema)


def 批量获取交易对数据(
    exchange: str,
    symbols: Sequence[str],
    interval: str = "1m",
    limit: int = 100,
    only_closed: bool = True,
    连接串: Optional[str] = None,
) -> Dict[str, List[K线数据]]:
    """便捷函数：一次性批量获取多个交易对的K线数据

    参数:
        exchange: 交易所名称
        symbols: 交易对符号列表
        interval: K线周期
        limit: 每个交易对返回K线数量
        only_closed: 只返回已闭合的K线
        连接串: 数据库连接字符串

    返回:
        字典，键是交易对符号，值是K线数据列表
    """
    with 数据库操作器(连接串) as db:
        return db.批量获取K线窗口(exchange, symbols, interval, limit, only_closed)


def 获取单个交易对数据(
    exchange: str,
    symbol: str,
    interval: str = "1m",
    limit: int = 100,
    only_closed: bool = True,
    连接串: Optional[str] = None,
) -> List[K线数据]:
    """便捷函数：获取单个交易对的K线数据

    参数:
        exchange: 交易所名称
        symbol: 交易对符号
        interval: K线周期
        limit: 返回K线数量
        only_closed: 只返回已闭合的K线
        连接串: 数据库连接字符串

    返回:
        K线数据列表
    """
    with 数据库操作器(连接串) as db:
        return db.获取K线窗口(exchange, symbol, interval, limit, only_closed)
