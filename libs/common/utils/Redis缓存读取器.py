#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 缓存读取器
- 提供与 数据库操作工具 完全兼容的接口
- 从 K线合成服务的 Redis 缓存读取数据
- 支持回退到数据库（可选）

用法：
    from libs.common.utils.Redis缓存读取器 import 创建Redis数据读取器
    
    reader = 创建Redis数据读取器()
    rows = reader.批量获取K线窗口("binance_futures_um", ["BTCUSDT"], "1h", 500)
"""
from __future__ import annotations

import os
import logging
import msgpack
import redis
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

LOG = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PREFIX = "kfuser"


@dataclass(slots=True)
class K线数据:
    """K线数据结构（与数据库操作工具对齐）"""
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


class Redis数据读取器:
    """从 Redis 缓存读取 K线数据，接口兼容 数据库操作器"""

    def __init__(self, redis_url: Optional[str] = None, fallback_to_db: bool = False):
        """
        Args:
            redis_url: Redis 连接串，默认从环境变量 REDIS_URL 读取
            fallback_to_db: 当 Redis 无数据时是否回退到数据库
        """
        self.redis_url = redis_url or REDIS_URL
        self.r = redis.from_url(self.redis_url, decode_responses=False)
        self.fallback_to_db = fallback_to_db
        self._db = None

    def _get_db(self):
        """懒加载数据库连接（仅在需要回退时使用）"""
        if self._db is None and self.fallback_to_db:
            from libs.common.utils.数据库操作工具 import 创建数据库操作器
            self._db = 创建数据库操作器()
        return self._db

    def 获取K线窗口(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        limit: int,
        only_closed: bool = True,
    ) -> List[K线数据]:
        """
        获取单个符号的 K线数据（接口与数据库操作工具对齐）

        Args:
            exchange: 交易所（用于返回数据，默认 binance_futures_um）
            symbol: 交易对，如 BTCUSDT
            interval: 周期，如 1m, 5m, 1h, 4h, 1d, 1w
            limit: 最大返回数量
            only_closed: 是否只返回已闭合的 K线

        Returns:
            K线数据列表
        """
        bars = self._load_from_redis(exchange, symbol, interval, limit, only_closed)
        
        if not bars and self.fallback_to_db:
            LOG.debug(f"Redis 无数据，回退到数据库: {symbol} {interval}")
            db = self._get_db()
            if db:
                return db.获取K线窗口(exchange, symbol, interval, limit, only_closed)
        
        return bars

    def 批量获取K线窗口(
        self,
        exchange: str,
        symbols: Sequence[str],
        interval: str,
        limit: int,
        only_closed: bool = True,
    ) -> Dict[str, List[K线数据]]:
        """
        批量获取多个符号的 K线数据（接口与数据库操作工具对齐）

        Args:
            exchange: 交易所（用于返回数据）
            symbols: 交易对列表
            interval: 周期
            limit: 最大返回数量
            only_closed: 是否只返回已闭合的 K线

        Returns:
            {symbol: [K线数据列表]}
        """
        result = {}
        missing_symbols = []

        # 批量从 Redis 读取
        pipe = self.r.pipeline()
        for symbol in symbols:
            key = f"{PREFIX}:hc:{interval}:{symbol}"
            pipe.hgetall(key)
        
        redis_results = pipe.execute()

        for i, symbol in enumerate(symbols):
            raw = redis_results[i]
            if raw:
                bars = self._parse_bars(exchange, symbol, raw, limit, only_closed)
                if bars:
                    result[symbol] = bars
                else:
                    missing_symbols.append(symbol)
            else:
                missing_symbols.append(symbol)

        # 回退到数据库获取缺失数据
        if missing_symbols and self.fallback_to_db:
            LOG.debug(f"Redis 缺失 {len(missing_symbols)} 个符号，回退到数据库")
            db = self._get_db()
            if db:
                db_result = db.批量获取K线窗口(exchange, missing_symbols, interval, limit, only_closed)
                result.update(db_result)

        return result

    def _load_from_redis(
        self, exchange: str, symbol: str, interval: str, limit: int, only_closed: bool
    ) -> List[K线数据]:
        """从 Redis 加载单个符号的 K线"""
        key = f"{PREFIX}:hc:{interval}:{symbol}"
        raw = self.r.hgetall(key)
        return self._parse_bars(exchange, symbol, raw, limit, only_closed)

    def _parse_bars(
        self, exchange: str, symbol: str, raw: dict, limit: int, only_closed: bool
    ) -> List[K线数据]:
        """解析 Redis 数据为 K线数据 格式"""
        if not raw:
            return []
        
        bars = []
        for ts_bytes, data in sorted(raw.items(), key=lambda x: int(x[0])):
            try:
                d = msgpack.unpackb(data)
                is_closed = d.get("x", True)
                
                # 过滤未闭合数据
                if only_closed and not is_closed:
                    continue
                
                bars.append(K线数据(
                    exchange=exchange or "binance_futures_um",
                    symbol=symbol,
                    bucket_ts=datetime.fromtimestamp(d["t"], tz=timezone.utc),
                    open=d["o"],
                    high=d["h"],
                    low=d["l"],
                    close=d["c"],
                    volume=d.get("v", 0.0),
                    quote_volume=d.get("qv", 0.0),
                    trade_count=d.get("tc", 0),
                    is_closed=is_closed,
                    source="redis_cache",
                    ingested_at=None,
                    updated_at=None,
                    taker_buy_volume=d.get("tbv", 0.0),
                    taker_buy_quote_volume=d.get("tbqv", 0.0),
                ))
            except Exception as e:
                LOG.warning(f"解析 K线失败: {e}")
                continue
        
        # 返回最后 limit 条
        return bars[-limit:] if len(bars) > limit else bars

    def 获取最新K线(self, symbol: str, interval: str, only_closed: bool = True) -> Optional[K线数据]:
        """获取最新一根 K线"""
        bars = self.获取K线窗口("binance_futures_um", symbol, interval, 1, only_closed)
        return bars[-1] if bars else None

    # ========== 元数据读取 ==========
    def 获取元数据窗口(self, symbol: str, interval: str, limit: int = 500) -> List[dict]:
        """获取元数据窗口"""
        key = f"{PREFIX}:metrics:{interval}:{symbol}"
        items = self.r.hgetall(key)
        
        if not items:
            return []
        
        result = []
        # key 可能是时间戳整数或 ISO 日期字符串
        def sort_key(x):
            k = x[0]
            if isinstance(k, bytes):
                k = k.decode()
            try:
                return int(k)
            except ValueError:
                # ISO 格式日期字符串，按字符串排序
                return k
        
        for ts_bytes, data in sorted(items.items(), key=sort_key):
            try:
                # 尝试 msgpack 解析（新格式）
                d = msgpack.unpackb(data)
                dt = datetime.fromtimestamp(d["t"], tz=timezone.utc)
                result.append({
                    "symbol": symbol,
                    "datetime": dt,
                    "open_interest": d.get("oi", 0.0),
                    "open_interest_value": d.get("oiv", 0.0),
                    "count_toptrader_long_short_ratio": d.get("ctlsr", 0.0),
                    "toptrader_long_short_ratio": d.get("tlsr", 0.0),
                    "long_short_ratio": d.get("lsr", 0.0),
                    "taker_long_short_vol_ratio": d.get("tlsvr", 0.0),
                    "is_closed": d.get("x", True),
                })
            except:
                try:
                    # 尝试 JSON 解析（旧格式）
                    import json
                    if isinstance(data, bytes):
                        data = data.decode()
                    d = json.loads(data)
                    dt_str = d.get("datetime")
                    if dt_str:
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = None
                    result.append({
                        "symbol": symbol,
                        "datetime": dt,
                        "open_interest": d.get("open_interest", 0.0),
                        "open_interest_value": d.get("open_interest_value", 0.0),
                        "count_toptrader_long_short_ratio": d.get("count_toptrader_long_short_ratio", 0.0),
                        "toptrader_long_short_ratio": d.get("toptrader_long_short_ratio", 0.0),
                        "long_short_ratio": d.get("long_short_ratio", 0.0),
                        "taker_long_short_vol_ratio": d.get("taker_long_short_vol_ratio", 0.0),
                        "is_closed": d.get("is_closed", True),
                    })
                except:
                    continue
        
        return result[-limit:] if len(result) > limit else result

    def 获取最新元数据(self, symbol: str, interval: str) -> Optional[dict]:
        """获取最新一条元数据"""
        data = self.获取元数据窗口(symbol, interval, 1)
        return data[-1] if data else None

    def 获取所有符号(self, interval: str = "5m") -> List[str]:
        """获取所有有缓存数据的符号列表
        
        Args:
            interval: 周期，用于扫描对应的 key
            
        Returns:
            符号列表（大写）
        """
        # 扫描 kfuser:metrics:{interval}:* 或 kfuser:kline:{interval}:*
        pattern = f"{PREFIX}:metrics:{interval}:*"
        keys = self.r.keys(pattern)
        
        symbols = set()
        for key in keys:
            # key 格式: kfuser:metrics:5m:BTCUSDT
            if isinstance(key, bytes):
                key = key.decode()
            parts = key.split(":")
            if len(parts) >= 4:
                symbols.add(parts[3].upper())
        
        return sorted(symbols)

    def 检查缓存状态(self) -> Dict:
        """检查 Redis 缓存状态"""
        try:
            # 获取 last_seen
            last_seen_raw = self.r.hget(f"{PREFIX}:meta", "last_seen")
            last_seen = None
            if last_seen_raw:
                last_seen = datetime.fromtimestamp(float(last_seen_raw), tz=timezone.utc)
            
            # 统计缓存键数量
            keys = self.r.keys(f"{PREFIX}:hc:*")
            
            return {
                "available": last_seen is not None,
                "last_seen": last_seen,
                "cache_keys": len(keys),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def 创建Redis数据读取器(
    redis_url: Optional[str] = None,
    fallback_to_db: bool = False,
) -> Redis数据读取器:
    """
    创建 Redis 数据读取器

    Args:
        redis_url: Redis 连接串
        fallback_to_db: 当 Redis 无数据时是否回退到数据库

    Returns:
        Redis数据读取器 实例
    """
    return Redis数据读取器(redis_url=redis_url, fallback_to_db=fallback_to_db)
