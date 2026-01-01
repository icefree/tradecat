#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 快照工具 v4（适配数据合成器 v5）
- 完整字段支持（OHLCV + quote_volume + trade_count + taker_buy_*）
- 使用 Hash 存储，时间戳作为 field，自动去重
- 支持 Pub/Sub 实时推送
"""
from __future__ import annotations

import json
import msgpack
import redis
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from libs.common.utils.数据合成器 import Bar, UnclosedState, Metrics

LOG = logging.getLogger("redis_snapshot")

# Pub/Sub 频道前缀
PUBSUB_PREFIX = "kline"


class RedisSnapshot:
    PREFIX = "kfuser"

    def __init__(self, redis_url: str, enable_pubsub: bool = True):
        self.enable_pubsub = enable_pubsub
        try:
            self.r = redis.from_url(redis_url, decode_responses=False)
        except Exception as exc:
            LOG.warning("Redis 初始化失败: %s，降级为纯内存模式", exc)
            self.r = None
        self._pubsub_conn = None
        if enable_pubsub and self.r is not None:
            try:
                # 单独的连接用于 pub/sub（避免阻塞）
                self._pubsub_conn = redis.from_url(redis_url, decode_responses=True)
            except Exception as exc:
                LOG.warning("Redis pubsub 初始化失败: %s，禁用 pubsub", exc)
                self._pubsub_conn = None
                self.enable_pubsub = False

    # ========== 工具 ==========
    def _safe(self, desc: str, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            LOG.debug("%s 失败: %s", desc, exc)
            return None

    # ========== 元数据 ==========
    def get_last_seen(self) -> Optional[datetime]:
        if not self.r:
            return None
        val = self._safe("get_last_seen", self.r.hget, f"{self.PREFIX}:meta", "last_seen")
        if not val:
            return None
        try:
            return datetime.fromtimestamp(float(val), tz=timezone.utc)
        except Exception:
            return None

    def set_last_seen(self, ts: datetime, pipe=None):
        if not self.r and pipe is None:
            return
        target = pipe or self.r
        self._safe("set_last_seen", target.hset, f"{self.PREFIX}:meta", "last_seen", ts.timestamp())

    def is_valid(self, max_age_hours: int = 24) -> bool:
        last_seen = self.get_last_seen()
        if not last_seen:
            return False
        age = (datetime.now(timezone.utc) - last_seen).total_seconds() / 3600
        return age < max_age_hours

    # ========== Pub/Sub 推送 ==========
    def publish_bar(self, period: str, bar: "Bar"):
        """兼容旧接口：需显式传入 period"""
        return self.publish_bar_update(bar.symbol, period, bar)
    
    def publish_bar_update(self, symbol: str, period: str, bar: "Bar"):
        """发布 K线更新"""
        if not self.enable_pubsub or not self._pubsub_conn:
            return
        
        try:
            channel = f"{PUBSUB_PREFIX}:{symbol}:{period}"
            msg = json.dumps({
                "symbol": symbol,
                "period": period,
                "datetime": bar.datetime.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "quote_volume": bar.quote_volume,
                "trade_count": bar.trade_count,
                "taker_buy_volume": bar.taker_buy_volume,
                "taker_buy_quote_volume": bar.taker_buy_quote_volume,
                "is_closed": bar.is_closed,
                "ts": bar.datetime.timestamp()
            })
            self._safe("publish_bar_update", self._pubsub_conn.publish, channel, msg)
        except Exception as e:
            LOG.debug("Pub/Sub 发布失败: %s", e)
    
    def publish_batch(self, updates: List[tuple]):
        """批量发布 [(symbol, period, bar), ...]"""
        if not self.enable_pubsub or not self._pubsub_conn:
            return
        
        pipe = self._pubsub_conn.pipeline()
        for symbol, period, bar in updates:
            channel = f"{PUBSUB_PREFIX}:{symbol}:{period}"
            msg = json.dumps({
                "symbol": symbol,
                "period": period,
                "datetime": bar.datetime.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "quote_volume": bar.quote_volume,
                "trade_count": bar.trade_count,
                "taker_buy_volume": bar.taker_buy_volume,
                "taker_buy_quote_volume": bar.taker_buy_quote_volume,
                "is_closed": bar.is_closed,
                "ts": bar.datetime.timestamp()
            })
            pipe.publish(channel, msg)
        self._safe("publish_batch", pipe.execute)

    def publish_metrics_update(self, symbol: str, period: str, metrics: "Metrics"):
        """发布期货元数据更新"""
        if not self.enable_pubsub or not self._pubsub_conn:
            return
        
        try:
            channel = f"metrics:{symbol}:{period}"
            def _f(v):
                from decimal import Decimal
                if isinstance(v, Decimal):
                    return float(v)
                return v
            msg = json.dumps({
                "symbol": symbol,
                "period": period,
                "datetime": metrics.datetime.isoformat(),
                "open_interest": _f(metrics.open_interest),
                "open_interest_value": _f(metrics.open_interest_value),
                "count_toptrader_long_short_ratio": _f(metrics.count_toptrader_long_short_ratio),
                "toptrader_long_short_ratio": _f(metrics.toptrader_long_short_ratio),
                "long_short_ratio": _f(metrics.long_short_ratio),
                "taker_long_short_vol_ratio": _f(metrics.taker_long_short_vol_ratio),
                "is_closed": metrics.is_closed,
                "ts": metrics.datetime.timestamp()
            })
            self._safe("publish_metrics_update", self._pubsub_conn.publish, channel, msg)
        except Exception as e:
            LOG.debug("Pub/Sub 元数据发布失败: %s", e)
    
    def publish_metrics_batch(self, updates: List[tuple]):
        """批量发布元数据 [(symbol, period, metrics), ...]"""
        if not self.enable_pubsub or not self._pubsub_conn:
            return
        from decimal import Decimal
        def _f(v):
            if isinstance(v, Decimal):
                return float(v)
            return v
        
        pipe = self._pubsub_conn.pipeline()
        for symbol, period, metrics in updates:
            channel = f"metrics:{symbol}:{period}"
            msg = json.dumps({
                "symbol": symbol,
                "period": period,
                "datetime": metrics.datetime.isoformat(),
                "open_interest": _f(metrics.open_interest),
                "open_interest_value": _f(metrics.open_interest_value),
                "count_toptrader_long_short_ratio": _f(metrics.count_toptrader_long_short_ratio),
                "toptrader_long_short_ratio": _f(metrics.toptrader_long_short_ratio),
                "long_short_ratio": _f(metrics.long_short_ratio),
                "taker_long_short_vol_ratio": _f(metrics.taker_long_short_vol_ratio),
                "is_closed": metrics.is_closed,
                "ts": metrics.datetime.timestamp()
            })
            pipe.publish(channel, msg)
        self._safe("publish_metrics_batch", pipe.execute)

    # ========== 未闭合状态 ==========
    def save_unclosed(self, symbol: str, period: str, state: "UnclosedState", pipe=None):
        if not self.r and pipe is None:
            return
        target = pipe or self.r
        key = f"{self.PREFIX}:unclosed:{period}:{symbol}"
        self._safe("save_unclosed_hset", target.hset, key, mapping={
            "period_start": state.period_start.timestamp(),
            "o": state.open,
            "h": state.high,
            "l": state.low,
            "c": state.close,
            "v": state.volume,
            "qv": state.quote_volume,
            "tc": state.trade_count,
            "tbv": state.taker_buy_volume,
            "tbqv": state.taker_buy_quote_volume,
        })
        self._safe("save_unclosed_expire", target.expire, key, self._ttl_for_period(period))

    def load_unclosed(self, symbol: str, period: str) -> Optional[dict]:
        if not self.r:
            return None
        data = self._safe("load_unclosed", self.r.hgetall, f"{self.PREFIX}:unclosed:{period}:{symbol}")
        if not data:
            return None
        try:
            return {
                "period_start": datetime.fromtimestamp(float(data[b"period_start"]), tz=timezone.utc),
                "open": float(data[b"o"]),
                "high": float(data[b"h"]),
                "low": float(data[b"l"]),
                "close": float(data[b"c"]),
                "volume": float(data[b"v"]),
                "quote_volume": float(data.get(b"qv", 0)),
                "trade_count": int(float(data.get(b"tc", 0))),
                "taker_buy_volume": float(data.get(b"tbv", 0)),
                "taker_buy_quote_volume": float(data.get(b"tbqv", 0)),
            }
        except Exception:
            return None

    # ========== 缓存操作 ==========
    def save_bars(self, period: str, symbol: str, bars: List["Bar"], max_len: int, pipe=None):
        """保存 K线到 Redis（只保存已闭合 + 最新一条未闭合）"""
        if not bars or (self.r is None and pipe is None):
            return
        target = pipe or self.r.pipeline()
        key = f"{self.PREFIX}:hc:{period}:{symbol}"
        
        # 过滤：只保留已闭合的 + 最新一条未闭合
        closed_bars = [b for b in bars if b.is_closed]
        unclosed_bars = [b for b in bars if not b.is_closed]
        
        # 取最新的未闭合（如果有）
        latest_unclosed = None
        if unclosed_bars:
            latest_unclosed = max(unclosed_bars, key=lambda b: b.datetime)
        
        # 合并：已闭合 + 最新未闭合
        final_bars = closed_bars
        if latest_unclosed:
            final_bars = closed_bars + [latest_unclosed]
        
        # 去重（按时间戳）
        unique_bars = {}
        for bar in final_bars:
            ts = int(bar.datetime.timestamp())
            unique_bars[ts] = bar
        
        sorted_items = sorted(unique_bars.items(), key=lambda x: x[0])[-max_len:]
        
        self._safe("save_bars_delete", target.delete, key)
        if sorted_items:
            mapping = {str(ts): self._pack_bar(bar) for ts, bar in sorted_items}
            self._safe("save_bars_hset", target.hset, key, mapping=mapping)
        self._safe("save_bars_expire", target.expire, key, self._ttl_for_period(period))
        
        if pipe is None and self.r:
            self._safe("save_bars_execute", target.execute)

    def append_bars(self, period: str, symbol: str, bars: List["Bar"], pipe=None):
        if not bars:
            return
        if self.r is None and pipe is None:
            return
        target = pipe or self.r
        key = f"{self.PREFIX}:hc:{period}:{symbol}"
        
        mapping = {}
        for bar in bars:
            ts = str(int(bar.datetime.timestamp()))
            mapping[ts] = self._pack_bar(bar)
        
        if mapping:
            self._safe("append_bars_hset", target.hset, key, mapping=mapping)
            self._safe("append_bars_expire", target.expire, key, self._ttl_for_period(period))

    def load_bars(self, period: str, symbol: str) -> List[dict]:
        key = f"{self.PREFIX}:hc:{period}:{symbol}"
        if not self.r:
            return []
        items = self._safe("load_bars_hgetall", self.r.hgetall, key) or {}
        bars = []
        for ts_bytes, data in sorted(items.items(), key=lambda x: int(x[0])):
            bars.append(self._unpack_bar(data))
        return bars

    # ========== 批量操作 ==========
    def save_all(self, cache_store: dict, unclosed_store: dict, last_1m_time: dict, max_len: int):
        if self.r is None:
            return
        pipe = self.r.pipeline()
        
        for period, symbol_dict in cache_store.items():
            for symbol, bars_dict in symbol_dict.items():
                # cache_store 现在是 {period: {symbol: {datetime: Bar}}}
                self.save_bars(period, symbol, list(bars_dict.values()), max_len, pipe)
        
        for symbol, period_dict in unclosed_store.items():
            for period, state in period_dict.items():
                self.save_unclosed(symbol, period, state, pipe)
        
        if last_1m_time:
            max_ts = max(last_1m_time.values())
            self.set_last_seen(max_ts, pipe)
        
        self._safe("save_all_execute", pipe.execute)
        LOG.debug("Redis 快照保存完成")

    def restore_all(self, symbols: List[str], periods: List[str]) -> dict:
        if self.r is None:
            return {"cache": {}, "unclosed": {}, "last_seen": None}
        pipe = self.r.pipeline()
        
        cache_keys = []
        for period in periods:
            for symbol in symbols:
                cache_keys.append((period, symbol))
                pipe.hgetall(f"{self.PREFIX}:hc:{period}:{symbol}")
        
        unclosed_keys = []
        for symbol in symbols:
            for period in periods:
                unclosed_keys.append((symbol, period))
                pipe.hgetall(f"{self.PREFIX}:unclosed:{period}:{symbol}")
        
        pipe.hget(f"{self.PREFIX}:meta", "last_seen")
        
        results = pipe.execute()
        
        cache = {p: {} for p in periods}
        idx = 0
        for (period, symbol) in cache_keys:
            raw = results[idx]
            bars = []
            for ts_bytes, data in sorted(raw.items(), key=lambda x: int(x[0])):
                bars.append(self._unpack_bar(data))
            if bars:
                cache[period][symbol] = bars
            idx += 1
        
        unclosed = {}
        for (symbol, period) in unclosed_keys:
            raw = results[idx]
            idx += 1
            if not raw:
                continue
            try:
                state_dict = {
                    "period_start": datetime.fromtimestamp(float(raw[b"period_start"]), tz=timezone.utc),
                    "open": float(raw[b"o"]),
                    "high": float(raw[b"h"]),
                    "low": float(raw[b"l"]),
                    "close": float(raw[b"c"]),
                    "volume": float(raw[b"v"]),
                    "quote_volume": float(raw.get(b"qv", 0)),
                    "trade_count": int(float(raw.get(b"tc", 0))),
                    "taker_buy_volume": float(raw.get(b"tbv", 0)),
                    "taker_buy_quote_volume": float(raw.get(b"tbqv", 0)),
                }
                if symbol not in unclosed:
                    unclosed[symbol] = {}
                unclosed[symbol][period] = state_dict
            except Exception:
                continue
        
        last_seen_raw = results[idx]
        last_seen = None
        if last_seen_raw:
            try:
                last_seen = datetime.fromtimestamp(float(last_seen_raw), tz=timezone.utc)
            except Exception:
                pass
        
        return {"cache": cache, "unclosed": unclosed, "last_seen": last_seen}

    # ========== 工具方法 ==========
    def pipeline(self):
        return self.r.pipeline() if self.r else None

    def _pack_bar(self, bar: "Bar") -> bytes:
        return msgpack.packb({
            "t": int(bar.datetime.timestamp()),
            "o": bar.open,
            "h": bar.high,
            "l": bar.low,
            "c": bar.close,
            "v": bar.volume,
            "qv": bar.quote_volume,
            "tc": bar.trade_count,
            "tbv": bar.taker_buy_volume,
            "tbqv": bar.taker_buy_quote_volume,
            "x": bar.is_closed,
            "ps": bar.period_start.timestamp() if bar.period_start else None,
        })

    def _unpack_bar(self, data: bytes) -> dict:
        d = msgpack.unpackb(data)
        return {
            "datetime": datetime.fromtimestamp(d["t"], tz=timezone.utc),
            "open": d["o"],
            "high": d["h"],
            "low": d["l"],
            "close": d["c"],
            "volume": d.get("v", 0.0),
            "quote_volume": d.get("qv", 0.0),
            "trade_count": d.get("tc", 0),
            "taker_buy_volume": d.get("tbv", 0.0),
            "taker_buy_quote_volume": d.get("tbqv", 0.0),
            "is_closed": d.get("x", True),
            "period_start": datetime.fromtimestamp(d["ps"], tz=timezone.utc) if d.get("ps") else None,
        }

    def _pack_metrics(self, metrics: "Metrics") -> bytes:
        from decimal import Decimal
        def _f(v):
            if isinstance(v, Decimal):
                return float(v)
            return v
        return msgpack.packb({
            "t": int(metrics.datetime.timestamp()),
            "oi": _f(metrics.open_interest),
            "oiv": _f(metrics.open_interest_value),
            "ctlsr": _f(metrics.count_toptrader_long_short_ratio),
            "tlsr": _f(metrics.toptrader_long_short_ratio),
            "lsr": _f(metrics.long_short_ratio),
            "tlsvr": _f(metrics.taker_long_short_vol_ratio),
            "x": metrics.is_closed,
            "ps": metrics.period_start.timestamp() if metrics.period_start else None,
        })

    def _unpack_metrics(self, data: bytes) -> dict:
        d = msgpack.unpackb(data)
        return {
            "datetime": datetime.fromtimestamp(d["t"], tz=timezone.utc),
            "open_interest": d.get("oi", 0.0),
            "open_interest_value": d.get("oiv", 0.0),
            "count_toptrader_long_short_ratio": d.get("ctlsr", 0.0),
            "toptrader_long_short_ratio": d.get("tlsr", 0.0),
            "long_short_ratio": d.get("lsr", 0.0),
            "taker_long_short_vol_ratio": d.get("tlsvr", 0.0),
            "is_closed": d.get("x", True),
            "period_start": datetime.fromtimestamp(d["ps"], tz=timezone.utc) if d.get("ps") else None,
        }

    # ========== 元数据缓存操作 ==========
    def save_metrics(self, period: str, symbol: str, metrics_list: List["Metrics"], max_len: int, pipe=None):
        """保存元数据到 Redis（只保存已闭合 + 最新一条未闭合）"""
        if not metrics_list or (self.r is None and pipe is None):
            return
        target = pipe or self.r.pipeline()
        key = f"{self.PREFIX}:metrics:{period}:{symbol}"

        # 1) 读取已有窗口并合并（避免每次写入覆盖历史）
        # 注意：无论是否传入 pipe，都用 self.r 读取（pipeline 的 hgetall 返回 pipeline 本身）
        existing_items = {}
        try:
            existing_items = self.r.hgetall(key) or {}
        except Exception:
            existing_items = {}

        def _merge(existing: dict) -> dict:
            from types import SimpleNamespace
            merged = {}
            # 先放历史
            for ts_bytes, data in existing.items():
                try:
                    ts_int = int(ts_bytes.decode() if isinstance(ts_bytes, bytes) else ts_bytes)
                except Exception:
                    continue
                try:
                    d = self._unpack_metrics(data)
                    m = SimpleNamespace(
                        datetime=d["datetime"],
                        open_interest=d.get("open_interest", 0.0),
                        open_interest_value=d.get("open_interest_value", 0.0),
                        count_toptrader_long_short_ratio=d.get("count_toptrader_long_short_ratio", 0.0),
                        toptrader_long_short_ratio=d.get("toptrader_long_short_ratio", 0.0),
                        long_short_ratio=d.get("long_short_ratio", 0.0),
                        taker_long_short_vol_ratio=d.get("taker_long_short_vol_ratio", 0.0),
                        is_closed=d.get("is_closed", True),
                        period_start=d.get("period_start"),
                    )
                    merged[ts_int] = m
                except Exception:
                    continue
            # 再放新增（去重时间戳）
            for m in metrics_list:
                ts_int = int(m.datetime.timestamp())
                merged[ts_int] = m
            # 截断窗口
            latest = dict(sorted(merged.items(), key=lambda x: x[0])[-max_len:])
            return latest

        merged_items = _merge(existing_items)

        # 2) 重新写回
        self._safe("save_metrics_delete", target.delete, key)
        if merged_items:
            mapping = {str(ts): self._pack_metrics(m) for ts, m in merged_items.items()}
            self._safe("save_metrics_hset", target.hset, key, mapping=mapping)
        self._safe("save_metrics_expire", target.expire, key, self._ttl_for_period(period))

        if pipe is None and self.r:
            self._safe("save_metrics_execute", target.execute)

    def load_metrics(self, period: str, symbol: str) -> List[dict]:
        """加载元数据"""
        key = f"{self.PREFIX}:metrics:{period}:{symbol}"
        if not self.r:
            return []
        items = self._safe("load_metrics_hgetall", self.r.hgetall, key) or {}
        result = []
        for ts_bytes, data in sorted(items.items(), key=lambda x: int(x[0])):
            result.append(self._unpack_metrics(data))
        return result

    def _ttl_for_period(self, period: str) -> int:
        return {
            "1m": 86400,
            "5m": 3 * 86400,
            "15m": 7 * 86400,
            "1h": 30 * 86400,
            "4h": 60 * 86400,
            "1d": 365 * 86400,
            "1w": 365 * 86400,
        }.get(period, 86400)
