#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据合成器 v5（K线 + 期货元数据，纯 1m/5m 合成 + 事件驱动）

核心逻辑：
1. 预热：从物化视图读各周期历史（已闭合）
2. 合成未闭合：只用当前各周期内的 1m 合成（无累加问题）
3. 实时：每根新 1m 驱动更新所有周期

字段完整支持：
- OHLCV（open/high/low/close/volume）
- quote_volume（成交额）
- trade_count（成交笔数）
- taker_buy_volume（主买成交量）
- taker_buy_quote_volume（主买成交额）

特性：
- 未闭合K线时间戳显示为最新1m时间（非周期起点）
- 逻辑简单，无累加问题
- 支持 PG LISTEN/NOTIFY 事件驱动
- 支持 Redis 快照恢复
"""
from __future__ import annotations

import os
import sys
import json
import signal
import select
import time as time_module
import logging
import csv
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Callable, Dict, List, Optional

import psycopg2
import psycopg2.extras
import psycopg2.extensions

from psycopg2 import pool as pg_pool

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from libs.common.utils.Redis缓存写入器 import RedisSnapshot
from libs.common.utils.ccxt币安永续合约工具 import 获取统一币安永续符号列表

LOG = logging.getLogger("kline_fuser")

# 全局连接池（线程安全）
_DB_POOL: Optional[pg_pool.ThreadedConnectionPool] = None
_POOL_LOCK = threading.Lock()

def get_db_pool(min_conn=5, max_conn=20) -> pg_pool.ThreadedConnectionPool:
    """获取或创建数据库连接池"""
    global _DB_POOL
    if _DB_POOL is None:
        with _POOL_LOCK:
            if _DB_POOL is None:
                db_url = os.getenv("DATABASE_URL", "")
                if db_url:
                    _DB_POOL = pg_pool.ThreadedConnectionPool(min_conn, max_conn, db_url)
                    LOG.info(f"数据库连接池已创建: min={min_conn}, max={max_conn}")
    return _DB_POOL

def get_pooled_conn():
    """从连接池获取连接"""
    pool = get_db_pool()
    if pool:
        return pool.getconn()
    return psycopg2.connect(os.getenv("DATABASE_URL", ""), connect_timeout=10)

def return_pooled_conn(conn):
    """归还连接到连接池"""
    pool = get_db_pool()
    if pool and conn:
        pool.putconn(conn)
LOG_LEVEL = os.getenv("KLINE_FUSER_LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.DEBUG), force=True, format="%(asctime)s %(levelname)s %(message)s")
LOG.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://opentd:OpenTD_pass@localhost:5433/market_data")
EXCHANGE_IN_DB = os.getenv("EXCHANGE_IN_DB", "binance_futures_um")
# 期货情绪聚合/缓存的默认窗口（可覆盖）
METRICS_WINDOW = int(os.getenv("METRICS_WINDOW", "240"))
# 缓存窗口：
# - 1m 由逻辑动态保证“本周全量”，不靠此上限
# - 其他周期默认上限 500，可用 CACHE_WINDOW 调大
_cache_env = int(os.getenv("CACHE_WINDOW", "0")) or 0
CACHE_WINDOW = _cache_env if _cache_env > 0 else 500
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.0"))
POLL_FALLBACK = os.getenv("POLL_FALLBACK", "0") == "1"
_redis_env = os.getenv("REDIS_URL", "").strip()
# 若未显式配置或传入空字符串，按文档默认本地 Redis
REDIS_URL = _redis_env or "redis://localhost:6379/0"
REDIS_SYNC_EVERY = float(os.getenv("REDIS_SYNC_EVERY", "5"))
REDIS_RESTORE_MAX_AGE_HOURS = int(os.getenv("REDIS_RESTORE_MAX_AGE_HOURS", "168"))
NOTIFY_CHANNEL = os.getenv("NOTIFY_CHANNEL", "candle_1m_update")
NOTIFY_CHANNEL_METRICS = os.getenv("NOTIFY_CHANNEL_METRICS", "metrics_5m_update")

BASE_PERIOD = os.getenv("BASE_PERIOD", "1m")
PERIODS = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
DERIVED_PERIODS = [p for p in PERIODS if p != BASE_PERIOD]

PERIOD_TABLES = {
    "1m": "candles_1m",
    "5m": "candles_5m",
    "15m": "candles_15m",
    "1h": "candles_1h",
    "4h": "candles_4h",
    "1d": "candles_1d",
    "1w": "candles_1w",
}

# 各周期历史加载条数
PERIOD_LOOKBACK = {
    "1m": 10080,  # 7天
    "5m": 2016,   # 7天
    "15m": 672,   # 7天
    "1h": 168,    # 7天
    "4h": 42,     # 7天
    "1d": 30,     # 30天
    "1w": 12,     # 12周
}
METRICS_LOOKBACK = {
    "5m": 2016,
    "15m": 672,
    "1h": 168,
    "4h": 42,
    "1d": 30,
    "1w": 12,
}

# 期货元数据配置（基于 5m）
METRICS_BASE_PERIOD = "5m"
METRICS_PERIODS = ["5m", "15m", "1h", "4h", "1d", "1w"]
METRICS_DERIVED_PERIODS = [p for p in METRICS_PERIODS if p != METRICS_BASE_PERIOD]
METRICS_TABLES = {
    "5m": "binance_futures_metrics_5m",
    "15m": "binance_futures_metrics_15m_last",
    "1h": "binance_futures_metrics_1h_last",
    "4h": "binance_futures_metrics_4h_last",
    "1d": "binance_futures_metrics_1d_last",
    "1w": "binance_futures_metrics_1w_last",
}


@dataclass
class Bar:
    """K线数据结构（完整字段）"""
    symbol: str
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float = 0.0
    trade_count: int = 0
    taker_buy_volume: float = 0.0
    taker_buy_quote_volume: float = 0.0
    is_closed: bool = True
    period_start: Optional[datetime] = None


@dataclass
class UnclosedState:
    """未闭合K线状态（完整字段）"""
    period_start: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float = 0.0
    trade_count: int = 0
    taker_buy_volume: float = 0.0
    taker_buy_quote_volume: float = 0.0


@dataclass
class Metrics:
    """期货元数据结构"""
    symbol: str
    datetime: datetime
    open_interest: float
    open_interest_value: float
    count_toptrader_long_short_ratio: float  # 大户账户数多空比
    toptrader_long_short_ratio: float  # 大户持仓多空比
    long_short_ratio: float  # 全体多空比
    taker_long_short_vol_ratio: float  # 主动成交多空比
    is_closed: bool = True
    period_start: Optional[datetime] = None


@dataclass
class MetricsState:
    """未闭合期货元数据状态（快照类型，取最新值）"""
    period_start: datetime
    last_update: datetime
    open_interest: float
    open_interest_value: float
    count_toptrader_long_short_ratio: float
    toptrader_long_short_ratio: float
    long_short_ratio: float
    taker_long_short_vol_ratio: float


def week_start_for(ts: datetime) -> datetime:
    """计算周起点（周一零点UTC）"""
    return ts.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=ts.weekday())


def floor_to_period(period: str, ts: datetime) -> datetime:
    """计算周期起点"""
    if period == "1m":
        return ts.replace(second=0, microsecond=0)
    if period == "5m":
        return ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)
    if period == "15m":
        return ts.replace(minute=(ts.minute // 15) * 15, second=0, microsecond=0)
    if period == "1h":
        return ts.replace(minute=0, second=0, microsecond=0)
    if period == "4h":
        return ts.replace(hour=(ts.hour // 4) * 4, minute=0, second=0, microsecond=0)
    if period == "1d":
        return ts.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "1w":
        return week_start_for(ts)
    return ts


PERIOD_DURATION = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
}


def is_period_closed(period: str, bucket_ts: datetime, now: datetime = None) -> bool:
    """判断某个周期是否已闭合（下一周期已开始）"""
    if now is None:
        now = datetime.now(timezone.utc)
    next_period_start = bucket_ts + PERIOD_DURATION[period]
    return now >= next_period_start


def _history_store_factory() -> Dict[str, Dict[datetime, "Bar"]]:
    """为 HistoryCache 提供可 picklable 的嵌套 dict 工厂"""
    return defaultdict(dict)


def _metrics_store_factory() -> Dict[str, Dict[datetime, "Metrics"]]:
    """为 MetricsCache 提供可 picklable 的嵌套 dict 工厂"""
    return defaultdict(dict)


class HistoryCache:
    """K线缓存（用 dict 存储，自动去重）"""

    def __init__(self, window: int, window_1m: Optional[int] = None):
        self.window = window          # 非 1m 周期的上限
        self.window_1m = window_1m    # 1m 上限；None 表示不截断
        # 用 dict 存储，key 是 datetime（已闭合）或 period_start（未闭合）
        # 注意：defaultdict 需要可 picklable 的工厂函数，否则多进程下会因 lambda 无法序列化而失败
        self.store: Dict[str, Dict[str, Dict[datetime, Bar]]] = defaultdict(_history_store_factory)

    def append(self, period: str, bar: Bar):
        """添加或更新 K 线（自动去重）
        
        - 已闭合：用 datetime 作为 key
        - 未闭合：用 period_start 作为 key（同一周期只保留一条）
        """
        symbol_store = self.store[period][bar.symbol]
        
        # 未闭合数据用 period_start 作为 key，确保同一周期只有一条
        if not bar.is_closed and bar.period_start:
            # 删除该 period_start 对应的旧数据（如果有）
            keys_to_remove = [
                k for k, v in symbol_store.items() 
                if not v.is_closed and v.period_start == bar.period_start
            ]
            for k in keys_to_remove:
                del symbol_store[k]
            symbol_store[bar.datetime] = bar
        else:
            symbol_store[bar.datetime] = bar
        
        # 超过窗口大小时，删除最旧的
        limit = self.window_1m if period == "1m" else self.window
        if limit and len(symbol_store) > limit:
            oldest_ts = min(symbol_store.keys())
            del symbol_store[oldest_ts]

    def get(self, period: str, symbol: str) -> List[Bar]:
        """获取 K 线列表（按时间排序）"""
        symbol_store = self.store.get(period, {}).get(symbol, {})
        return [symbol_store[ts] for ts in sorted(symbol_store.keys())]

    def clear(self):
        self.store.clear()

    def get_all_symbols(self, period: str) -> List[str]:
        return list(self.store.get(period, {}).keys())

    def count(self, period: str) -> int:
        return sum(len(d) for d in self.store.get(period, {}).values())


class MetricsCache:
    """期货元数据缓存（用 dict 存储，自动去重）"""

    def __init__(self, window: int):
        self.window = window
        self.store: Dict[str, Dict[str, Dict[datetime, Metrics]]] = defaultdict(_metrics_store_factory)

    def append(self, period: str, metrics: Metrics):
        """添加或更新元数据（自动去重）"""
        symbol_store = self.store[period][metrics.symbol]
        symbol_store[metrics.datetime] = metrics
        
        if len(symbol_store) > self.window:
            oldest_ts = min(symbol_store.keys())
            del symbol_store[oldest_ts]

    def get(self, period: str, symbol: str) -> List[Metrics]:
        """获取元数据列表（按时间排序）"""
        symbol_store = self.store.get(period, {}).get(symbol, {})
        return [symbol_store[ts] for ts in sorted(symbol_store.keys())]

    def clear(self):
        self.store.clear()

    def get_latest(self, period: str, symbol: str) -> Optional[Metrics]:
        """获取最新一条"""
        items = self.get(period, symbol)
        return items[-1] if items else None

    def count(self, period: str) -> int:
        return sum(len(d) for d in self.store.get(period, {}).values())


class FusionEngine:
    """K线合成引擎（纯 1m 合成 + 期货元数据）"""

    def __init__(self, conn, listen_conn=None):
        self.conn = conn
        self.listen_conn = listen_conn
        self.last_seen: Optional[datetime] = None
        self.last_1m_time: Dict[str, datetime] = {}
        
        # K线缓存
        # 1m 不截断（本周全量），其他周期上限 500
        self.cache = HistoryCache(window=500, window_1m=None)
        self.unclosed: Dict[str, Dict[str, UnclosedState]] = defaultdict(dict)
        
        # 期货元数据缓存
        self.metrics_cache = MetricsCache(CACHE_WINDOW)
        self.metrics_unclosed: Dict[str, Dict[str, MetricsState]] = defaultdict(dict)
        self.last_5m_time: Dict[str, datetime] = {}
        
        self.callbacks: Dict[str, List[Callable[[Bar], None]]] = {p: [] for p in PERIODS}
        
        self.snapshot: Optional[RedisSnapshot] = None
        self._last_sync_ts: float = 0.0

        if REDIS_URL:
            try:
                self.snapshot = RedisSnapshot(REDIS_URL)
                LOG.info("Redis 快照已启用：%s", REDIS_URL)
            except Exception:
                LOG.exception("Redis 初始化失败，降级为纯内存模式")
                self.snapshot = None

    def on_close(self, period: str, cb: Callable[[Bar], None]):
        self.callbacks[period].append(cb)

    # ==================== 预热 ====================

    def warmup(self):
        """预热：加载历史 + 合成未闭合"""
        LOG.info("预热开始...")
        
        symbols = self._list_symbols()
        LOG.info("符号列表：%d 个", len(symbols))
        
        if self._try_restore_from_redis(symbols):
            LOG.info("从 Redis 恢复成功")
            need_1m = int((datetime.now(timezone.utc) - floor_to_period("1w", datetime.now(timezone.utc))).total_seconds() // 60) + 1
            actual_1m = self.cache.count("1m")
            if actual_1m < need_1m:
                LOG.info("Redis 恢复数据不足（1m=%d < 需要=%d），执行全量预热", actual_1m, need_1m)
                self.cache.clear()
                self.metrics_cache.clear()
                self.last_seen = None
                self.last_1m_time.clear()
                self.unclosed.clear()
                self._full_warmup(symbols)
            else:
                self._catchup_since_last_seen()
                # Redis 恢复后也要加载元数据（Redis 只存 K线）
                self._load_and_synthesize_metrics(symbols)
        else:
            self._full_warmup(symbols)
        
        LOG.info("预热完成，last_seen=%s", self.last_seen)
        LOG.info("K线缓存:")
        for period in PERIODS:
            LOG.info("  %s: %d 条", period, self.cache.count(period))
        LOG.info("期货元数据缓存:")
        for period in METRICS_PERIODS:
            LOG.info("  %s: %d 条", period, self.metrics_cache.count(period))
        
        # 预热完成后全量同步到 Redis
        self._full_sync_to_redis()
        LOG.info("Redis 同步完成")

    def _load_and_synthesize_metrics(self, symbols: List[str]):
        """加载并合成期货元数据（并行优化版）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        now = datetime.now(timezone.utc)
        
        LOG.info("并行加载期货元数据历史...")
        start = time_module.time()
        
        def load_metrics_with_pool(period):
            conn = get_pooled_conn()
            try:
                self._load_metrics_history_with_conn(period, symbols, conn)
                return period, True
            except Exception as e:
                LOG.error(f"加载 metrics {period} 失败: {e}")
                return period, False
            finally:
                return_pooled_conn(conn)
        
        with ThreadPoolExecutor(max_workers=min(len(METRICS_PERIODS), 6)) as executor:
            futures = {executor.submit(load_metrics_with_pool, p): p for p in METRICS_PERIODS}
            for future in as_completed(futures):
                period, ok = future.result()
                LOG.info(f"  metrics {period}: {'OK' if ok else 'FAIL'}")
        
        LOG.info(f"期货元数据加载完成，耗时 {time_module.time() - start:.1f}s")
        
        LOG.info("合成未闭合期货元数据（纯 5m）...")
        self._synthesize_metrics_from_5m(symbols, now)
        
        LOG.info("刷新未闭合期货元数据到缓存...")
        start = time_module.time()
        with ThreadPoolExecutor(max_workers=min(len(symbols), 50)) as executor:
            list(executor.map(self._flush_metrics_unclosed_to_cache, symbols))
        LOG.info(f"刷新完成，耗时 {time_module.time() - start:.1f}s")

    def _full_warmup(self, symbols: List[str]):
        """完整预热（并行优化版 + 连接池）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        now = datetime.now(timezone.utc)
        
        # 1. 并行加载各周期 K线历史
        LOG.info("并行加载各周期 K线历史...")
        start = time_module.time()
        
        def load_period_with_pool(period):
            conn = get_pooled_conn()
            try:
                self._load_period_history_with_conn(period, symbols, conn)
                return period, True
            except Exception as e:
                LOG.error(f"加载 {period} 失败: {e}")
                return period, False
            finally:
                return_pooled_conn(conn)
        
        with ThreadPoolExecutor(max_workers=min(len(PERIODS), 7)) as executor:
            futures = {executor.submit(load_period_with_pool, p): p for p in PERIODS}
            for future in as_completed(futures):
                period, ok = future.result()
                LOG.info(f"  {period}: {'OK' if ok else 'FAIL'}")
        
        LOG.info(f"K线历史加载完成，耗时 {time_module.time() - start:.1f}s")
        
        # 2. 合成未闭合 K线（依赖1m数据，必须串行）
        LOG.info("合成未闭合 K线（纯 1m）...")
        self._synthesize_from_1m(symbols, now)
        
        # 3. 并行刷新未闭合 K线到缓存
        LOG.info("刷新未闭合 K线到缓存...")
        start = time_module.time()
        with ThreadPoolExecutor(max_workers=min(len(symbols), 50)) as executor:
            list(executor.map(self._flush_unclosed_to_cache, symbols))
        LOG.info(f"刷新完成，耗时 {time_module.time() - start:.1f}s")
        
        # 4. 并行加载期货元数据历史
        LOG.info("并行加载期货元数据历史...")
        start = time_module.time()
        
        def load_metrics_with_pool(period):
            conn = get_pooled_conn()
            try:
                self._load_metrics_history_with_conn(period, symbols, conn)
                return period, True
            except Exception as e:
                LOG.error(f"加载 metrics {period} 失败: {e}")
                return period, False
            finally:
                return_pooled_conn(conn)
        
        with ThreadPoolExecutor(max_workers=min(len(METRICS_PERIODS), 6)) as executor:
            futures = {executor.submit(load_metrics_with_pool, p): p for p in METRICS_PERIODS}
            for future in as_completed(futures):
                period, ok = future.result()
                LOG.info(f"  metrics {period}: {'OK' if ok else 'FAIL'}")
        
        LOG.info(f"期货元数据加载完成，耗时 {time_module.time() - start:.1f}s")
        
        # 5. 合成未闭合期货元数据
        LOG.info("合成未闭合期货元数据（纯 5m）...")
        self._synthesize_metrics_from_5m(symbols, now)
        
        # 6. 并行刷新未闭合期货元数据到缓存
        LOG.info("刷新未闭合期货元数据到缓存...")
        start = time_module.time()
        with ThreadPoolExecutor(max_workers=min(len(symbols), 50)) as executor:
            list(executor.map(self._flush_metrics_unclosed_to_cache, symbols))
        LOG.info(f"刷新完成，耗时 {time_module.time() - start:.1f}s")
    
    def _load_period_history_with_conn(self, period: str, symbols: List[str], conn):
        """使用指定连接加载周期历史"""
        table = PERIOD_TABLES[period]
        now = datetime.now(timezone.utc)
        
        if period == "1m":
            week_start = floor_to_period("1w", now)
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT symbol, bucket_ts, open, high, low, close, volume,
                           COALESCE(quote_volume, 0) as quote_volume,
                           COALESCE(trade_count, 0) as trade_count,
                           COALESCE(taker_buy_volume, 0) as taker_buy_volume,
                           COALESCE(taker_buy_quote_volume, 0) as taker_buy_quote_volume
                    FROM market_data.{table}
                    WHERE symbol = ANY(%s) AND exchange = %s AND is_closed = true AND bucket_ts >= %s
                    ORDER BY symbol, bucket_ts
                """, (symbols, EXCHANGE_IN_DB, week_start))
                for row in cur:
                    bar = Bar(
                        datetime=row["bucket_ts"].replace(tzinfo=timezone.utc),
                        open=float(row["open"]), high=float(row["high"]),
                        low=float(row["low"]), close=float(row["close"]),
                        volume=float(row["volume"]), quote_volume=float(row["quote_volume"]),
                        trade_count=int(row["trade_count"]), taker_buy_volume=float(row["taker_buy_volume"]),
                        taker_buy_quote_volume=float(row["taker_buy_quote_volume"]), is_closed=True
                    )
                    self.cache.append(period, row["symbol"], bar)
        else:
            lookback = PERIOD_LOOKBACK.get(period, 500)
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT symbol, bucket_ts, open, high, low, close, volume,
                           COALESCE(quote_volume, 0) as quote_volume,
                           COALESCE(trade_count, 0) as trade_count,
                           COALESCE(taker_buy_volume, 0) as taker_buy_volume,
                           COALESCE(taker_buy_quote_volume, 0) as taker_buy_quote_volume
                    FROM (
                        SELECT *, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY bucket_ts DESC) as rn
                        FROM market_data.{table}
                        WHERE symbol = ANY(%s) AND exchange = %s AND is_closed = true
                    ) t WHERE rn <= %s ORDER BY symbol, bucket_ts
                """, (symbols, EXCHANGE_IN_DB, lookback))
                for row in cur:
                    bar = Bar(
                        datetime=row["bucket_ts"].replace(tzinfo=timezone.utc),
                        open=float(row["open"]), high=float(row["high"]),
                        low=float(row["low"]), close=float(row["close"]),
                        volume=float(row["volume"]), quote_volume=float(row["quote_volume"]),
                        trade_count=int(row["trade_count"]), taker_buy_volume=float(row["taker_buy_volume"]),
                        taker_buy_quote_volume=float(row["taker_buy_quote_volume"]), is_closed=True
                    )
                    self.cache.append(period, row["symbol"], bar)
    
    def _load_metrics_history_with_conn(self, period: str, symbols: List[str], conn):
        """使用指定连接加载期货元数据历史"""
        lookback = METRICS_LOOKBACK.get(period, 240)
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT symbol, create_time, open_interest, open_interest_value,
                       top_trader_long_short_ratio_accounts, top_trader_long_short_ratio_positions,
                       long_short_ratio_accounts, taker_buy_sell_ratio
                FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY create_time DESC) as rn
                    FROM market_data.binance_futures_metrics_5m
                    WHERE symbol = ANY(%s) AND exchange = %s
                ) t WHERE rn <= %s ORDER BY symbol, create_time
            """, (symbols, EXCHANGE_IN_DB, lookback))
            for row in cur:
                bar = MetricsBar(
                    datetime=row["create_time"].replace(tzinfo=timezone.utc),
                    open_interest=float(row["open_interest"] or 0),
                    open_interest_value=float(row["open_interest_value"] or 0),
                    top_long_short_accounts=float(row["top_trader_long_short_ratio_accounts"] or 0),
                    top_long_short_positions=float(row["top_trader_long_short_ratio_positions"] or 0),
                    long_short_accounts=float(row["long_short_ratio_accounts"] or 0),
                    taker_buy_sell_ratio=float(row["taker_buy_sell_ratio"] or 0),
                    is_closed=True
                )
                self.metrics_cache.append(period, row["symbol"], bar)

    def _load_period_history(self, period: str, symbols: List[str]):
        """加载周期历史（混合策略）"""
        table = PERIOD_TABLES[period]
        cnt = 0
        now = datetime.now(timezone.utc)
        
        if period == "1m":
            # 1m：加载“本周起点到当前”的全部已闭合 1m
            week_start = floor_to_period("1w", now)
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT symbol, bucket_ts, open, high, low, close, volume,
                           COALESCE(quote_volume, 0) as quote_volume,
                           COALESCE(trade_count, 0) as trade_count,
                           COALESCE(taker_buy_volume, 0) as taker_buy_volume,
                           COALESCE(taker_buy_quote_volume, 0) as taker_buy_quote_volume
                    FROM market_data.{table}
                    WHERE symbol = ANY(%s) AND exchange = %s AND is_closed = true AND bucket_ts >= %s
                    ORDER BY symbol, bucket_ts
                """, (symbols, EXCHANGE_IN_DB, week_start))

                for r in cur:
                    bar = self._row_to_bar(r, r["symbol"])
                    self.cache.append(period, bar)
                    self.last_1m_time[r["symbol"]] = r["bucket_ts"]
                    if self.last_seen is None or r["bucket_ts"] > self.last_seen:
                        self.last_seen = r["bucket_ts"]
                    cnt += 1

        elif period == "5m":
            # 5m：用时间范围替代 ROW_NUMBER（更快）
            lookback_start = now - timedelta(minutes=5 * min(CACHE_WINDOW, 500))
            with self.conn.cursor(name="load_5m", cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.itersize = 250000  # 每次从数据库取25万条
                cur.execute(f"""
                    SELECT symbol, bucket_ts, open, high, low, close, volume,
                           COALESCE(quote_volume, 0) as quote_volume,
                           COALESCE(trade_count, 0) as trade_count,
                           COALESCE(taker_buy_volume, 0) as taker_buy_volume,
                           COALESCE(taker_buy_quote_volume, 0) as taker_buy_quote_volume
                    FROM market_data.{table}
                    WHERE symbol = ANY(%s) AND exchange = %s AND is_closed = true
                      AND bucket_ts >= %s
                    ORDER BY symbol, bucket_ts
                """, (symbols, EXCHANGE_IN_DB, lookback_start))

                for r in cur:
                    bar = self._row_to_bar(r, r["symbol"])
                    self.cache.append(period, bar)
                    cnt += 1
        else:
            # 高周期批量查询（优化：用时间范围替代 ROW_NUMBER）
            current_period_start = floor_to_period(period, now)
            # 根据周期计算回溯时间（500条 × 周期时长）
            period_seconds = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400, "1w": 604800}
            lookback_seconds = period_seconds.get(period, 3600) * min(CACHE_WINDOW, 500)
            lookback_start = current_period_start - timedelta(seconds=lookback_seconds)
            
            with self.conn.cursor(name=f"load_{period}", cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.itersize = 250000  # 每次从数据库取25万条
                cur.execute(f"""
                    SELECT symbol, bucket_ts, open, high, low, close, volume,
                           COALESCE(quote_volume, 0) as quote_volume,
                           COALESCE(trade_count, 0) as trade_count,
                           COALESCE(taker_buy_volume, 0) as taker_buy_volume,
                           COALESCE(taker_buy_quote_volume, 0) as taker_buy_quote_volume
                    FROM market_data.{table}
                    WHERE symbol = ANY(%s) AND exchange = %s 
                      AND bucket_ts >= %s AND bucket_ts < %s
                    ORDER BY symbol, bucket_ts
                """, (symbols, EXCHANGE_IN_DB, lookback_start, current_period_start))
                
                for r in cur:
                    bar = self._row_to_bar(r, r["symbol"])
                    self.cache.append(period, bar)
                    cnt += 1
        
        LOG.info("  %s: %d 条", period, cnt)

    def _row_to_bar(self, r, symbol: str) -> Bar:
        """数据库行转 Bar（历史数据都是已闭合的）"""
        return Bar(
            symbol=symbol,
            datetime=r["bucket_ts"],
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
            volume=float(r["volume"]),
            quote_volume=float(r["quote_volume"]),
            trade_count=int(r["trade_count"]),
            taker_buy_volume=float(r["taker_buy_volume"]),
            taker_buy_quote_volume=float(r["taker_buy_quote_volume"]),
            is_closed=True
        )

    def _synthesize_from_1m(self, symbols: List[str], now: datetime):
        """从 1m 合成所有周期的未闭合（核心：无累加问题）"""
        # 找到最大周期（1w）的起点，加载这段时间内的 1m
        week_start = floor_to_period("1w", now)
        
        LOG.info("  加载本周 1m（从 %s）...", week_start.isoformat())
        
        # 性能优化：批量查询替代逐符号查询（547次 → 1次）
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(f"""
                SELECT symbol, bucket_ts, open, high, low, close, volume,
                       COALESCE(quote_volume, 0) as quote_volume,
                       COALESCE(trade_count, 0) as trade_count,
                       COALESCE(taker_buy_volume, 0) as taker_buy_volume,
                       COALESCE(taker_buy_quote_volume, 0) as taker_buy_quote_volume
                FROM market_data.candles_1m
                WHERE symbol = ANY(%s) AND is_closed = true AND bucket_ts >= %s
                ORDER BY bucket_ts ASC
            """, (symbols, week_start))
            
            for r in cur:
                symbol = r["symbol"]
                ts = r["bucket_ts"]
                self.last_1m_time[symbol] = ts
                if self.last_seen is None or ts > self.last_seen:
                    self.last_seen = ts
                
                # 同时更新 1m 缓存（确保与 unclosed 同步）
                bar_1m = Bar(
                    symbol=symbol, datetime=ts,
                    open=float(r["open"]), high=float(r["high"]),
                    low=float(r["low"]), close=float(r["close"]),
                    volume=float(r["volume"]), quote_volume=float(r["quote_volume"]),
                    trade_count=int(r["trade_count"]),
                    taker_buy_volume=float(r["taker_buy_volume"]),
                    taker_buy_quote_volume=float(r["taker_buy_quote_volume"]),
                    is_closed=True
                )
                self.cache.append("1m", bar_1m)
                
                # 更新各周期未闭合
                for period in DERIVED_PERIODS:
                    self._update_unclosed(
                        symbol, period, ts,
                        o=float(r["open"]), h=float(r["high"]), l=float(r["low"]), c=float(r["close"]),
                        v=float(r["volume"]), qv=float(r["quote_volume"]),
                        tc=int(r["trade_count"]), tbv=float(r["taker_buy_volume"]),
                        tbqv=float(r["taker_buy_quote_volume"])
                    )

    def _update_unclosed(self, symbol: str, period: str, ts: datetime,
                         o: float, h: float, l: float, c: float, v: float,
                         qv: float, tc: int, tbv: float, tbqv: float):
        """更新未闭合状态（核心逻辑）"""
        period_start = floor_to_period(period, ts)
        states = self.unclosed[symbol]
        
        if period not in states or states[period].period_start != period_start:
            # 新周期，重新开始（无累加问题）
            states[period] = UnclosedState(
                period_start=period_start,
                open=o, high=h, low=l, close=c, volume=v,
                quote_volume=qv, trade_count=tc,
                taker_buy_volume=tbv, taker_buy_quote_volume=tbqv
            )
        else:
            # 同一周期，累加
            state = states[period]
            state.high = max(state.high, h)
            state.low = min(state.low, l)
            state.close = c
            state.volume += v
            state.quote_volume += qv
            state.trade_count += tc
            state.taker_buy_volume += tbv
            state.taker_buy_quote_volume += tbqv

    # ==================== 实时更新 ====================

    def _process_1m(self, symbol: str, ts: datetime, o: float, h: float, l: float, c: float,
                    v: float, qv: float = 0, tc: int = 0, tbv: float = 0, tbqv: float = 0):
        """处理一根 1m，更新所有周期"""
        self.last_1m_time[symbol] = ts
        
        # 1m 存入缓存
        bar_1m = Bar(
            symbol=symbol, datetime=ts, open=o, high=h, low=l, close=c,
            volume=v, quote_volume=qv, trade_count=tc,
            taker_buy_volume=tbv, taker_buy_quote_volume=tbqv, is_closed=True
        )
        self.cache.append("1m", bar_1m)
        for cb in self.callbacks.get("1m", []):
            cb(bar_1m)
        # Pub/Sub 推送 + 立即写入 Redis
        if self.snapshot:
            self.snapshot.publish_bar_update(symbol, "1m", bar_1m)
            self.snapshot.append_bars("1m", symbol, [bar_1m])
        
        # 更新合成周期
        for period in DERIVED_PERIODS:
            self._update_period(symbol, period, ts, o, h, l, c, v, qv, tc, tbv, tbqv)

    def _update_period(self, symbol: str, period: str, ts: datetime,
                       o: float, h: float, l: float, c: float, v: float,
                       qv: float, tc: int, tbv: float, tbqv: float):
        """更新指定周期"""
        period_start = floor_to_period(period, ts)
        states = self.unclosed[symbol]
        
        if period not in states:
            states[period] = UnclosedState(
                period_start=period_start,
                open=o, high=h, low=l, close=c, volume=v,
                quote_volume=qv, trade_count=tc,
                taker_buy_volume=tbv, taker_buy_quote_volume=tbqv
            )
        elif states[period].period_start != period_start:
            # 闭合旧的
            old = states[period]
            closed_bar = Bar(
                symbol=symbol, datetime=old.period_start,
                open=old.open, high=old.high, low=old.low, close=old.close,
                volume=old.volume, quote_volume=old.quote_volume,
                trade_count=old.trade_count, taker_buy_volume=old.taker_buy_volume,
                taker_buy_quote_volume=old.taker_buy_quote_volume, is_closed=True
            )
            self.cache.append(period, closed_bar)
            for cb in self.callbacks.get(period, []):
                cb(closed_bar)
            # Pub/Sub 推送 + 立即写入 Redis
            if self.snapshot:
                self.snapshot.publish_bar_update(symbol, period, closed_bar)
                self.snapshot.append_bars(period, symbol, [closed_bar])
            
            # 开新的
            states[period] = UnclosedState(
                period_start=period_start,
                open=o, high=h, low=l, close=c, volume=v,
                quote_volume=qv, trade_count=tc,
                taker_buy_volume=tbv, taker_buy_quote_volume=tbqv
            )
        else:
            state = states[period]
            state.high = max(state.high, h)
            state.low = min(state.low, l)
            state.close = c
            state.volume += v
            state.quote_volume += qv
            state.trade_count += tc
            state.taker_buy_volume += tbv
            state.taker_buy_quote_volume += tbqv

    def _flush_unclosed_to_cache(self, symbol: str):
        """将未闭合写入缓存（时间戳用最新 1m）+ 推送"""
        updates = self._flush_unclosed_to_cache_batch(symbol)
        if updates and self.snapshot:
            self.snapshot.publish_batch(updates)

    def _flush_unclosed_to_cache_batch(self, symbol: str) -> List[tuple]:
        """将未闭合写入缓存（批量模式，不推送，返回更新列表）
        
        返回: [(symbol, period, bar), ...]
        """
        if symbol not in self.last_1m_time:
            return []
        latest_ts = self.last_1m_time[symbol]
        
        updates = []
        for period in DERIVED_PERIODS:
            if period in self.unclosed[symbol]:
                state = self.unclosed[symbol][period]
                unclosed_bar = Bar(
                    symbol=symbol, datetime=latest_ts,
                    open=state.open, high=state.high, low=state.low, close=state.close,
                    volume=state.volume, quote_volume=state.quote_volume,
                    trade_count=state.trade_count, taker_buy_volume=state.taker_buy_volume,
                    taker_buy_quote_volume=state.taker_buy_quote_volume,
                    is_closed=False, period_start=state.period_start
                )
                self.cache.append(period, unclosed_bar)
                updates.append((symbol, period, unclosed_bar))
                
                # 写入 Redis（不推送）
                if self.snapshot:
                    self.snapshot.append_bars(period, symbol, [unclosed_bar])
        
        return updates

    # ==================== 期货元数据 ====================

    def _load_metrics_history(self, period: str, symbols: List[str]):
        """加载期货元数据历史"""
        table = METRICS_TABLES[period]
        cnt = 0
        
        if period == METRICS_BASE_PERIOD:
            # 5m 基础表逐符号查询：对齐 1m 逻辑，拉取本周起点→当前的全部已闭合 5m
            for symbol in symbols:
                week_start = floor_to_period("1w", datetime.now(timezone.utc))
                with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(f"""
                        SELECT create_time, symbol,
                               COALESCE(sum_open_interest, 0) as oi,
                               COALESCE(sum_open_interest_value, 0) as oiv,
                               COALESCE(count_toptrader_long_short_ratio, 0) as ctlsr,
                               COALESCE(sum_toptrader_long_short_ratio, 0) as tlsr,
                               COALESCE(count_long_short_ratio, 0) as lsr,
                               COALESCE(sum_taker_long_short_vol_ratio, 0) as tlsvr
                        FROM market_data.{table}
                        WHERE symbol = %s AND exchange = %s AND is_closed = true
                          AND create_time >= %s
                        ORDER BY create_time ASC
                    """, (symbol, EXCHANGE_IN_DB, week_start))
                    rows = cur.fetchall()
                
                for r in rows:
                    metrics = Metrics(
                        symbol=symbol,
                        datetime=r["create_time"].replace(tzinfo=timezone.utc),
                        open_interest=float(r["oi"]),
                        open_interest_value=float(r["oiv"]),
                        count_toptrader_long_short_ratio=float(r["ctlsr"]),
                        toptrader_long_short_ratio=float(r["tlsr"]),
                        long_short_ratio=float(r["lsr"]),
                        taker_long_short_vol_ratio=float(r["tlsvr"]),
                        is_closed=True
                    )
                    self.metrics_cache.append(period, metrics)
                    self.last_5m_time[symbol] = r["create_time"].replace(tzinfo=timezone.utc)
                    cnt += 1
        else:
            # 高周期物化视图（bucket 字段）
            # 注意：complete 字段表示数据完整性，不是闭合状态
            # 物化视图的历史数据都视为已闭合
            for symbol in symbols:
                with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(f"""
                        SELECT bucket, symbol,
                               COALESCE(sum_open_interest, 0) as oi,
                               COALESCE(sum_open_interest_value, 0) as oiv,
                               COALESCE(count_toptrader_long_short_ratio, 0) as ctlsr,
                               COALESCE(sum_toptrader_long_short_ratio, 0) as tlsr,
                               COALESCE(count_long_short_ratio, 0) as lsr,
                               COALESCE(sum_taker_long_short_vol_ratio, 0) as tlsvr
                        FROM market_data.{table}
                        WHERE symbol = %s
                        ORDER BY bucket DESC
                        LIMIT %s
                    """, (symbol, min(METRICS_WINDOW, CACHE_WINDOW)))
                    rows = list(reversed(cur.fetchall()))
                
                for r in rows:
                    metrics = Metrics(
                        symbol=symbol,
                        datetime=r["bucket"].replace(tzinfo=timezone.utc),
                        open_interest=float(r["oi"]),
                        open_interest_value=float(r["oiv"]),
                        count_toptrader_long_short_ratio=float(r["ctlsr"]),
                        toptrader_long_short_ratio=float(r["tlsr"]),
                        long_short_ratio=float(r["lsr"]),
                        taker_long_short_vol_ratio=float(r["tlsvr"]),
                        is_closed=True  # 物化视图历史数据都是已闭合的
                    )
                    self.metrics_cache.append(period, metrics)
                    cnt += 1
        
        LOG.info("  %s 元数据: %d 条", period, cnt)

    def _synthesize_metrics_from_5m(self, symbols: List[str], now: datetime):
        """从 5m 合成所有周期的未闭合期货元数据（快照类型，取最新值）"""
        week_start = floor_to_period("1w", now)
        
        LOG.info("  加载本周 5m 元数据（从 %s）...", week_start.isoformat())
        
        for symbol in symbols:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT create_time,
                           COALESCE(sum_open_interest, 0) as oi,
                           COALESCE(sum_open_interest_value, 0) as oiv,
                           COALESCE(count_toptrader_long_short_ratio, 0) as ctlsr,
                           COALESCE(sum_toptrader_long_short_ratio, 0) as tlsr,
                           COALESCE(count_long_short_ratio, 0) as lsr,
                           COALESCE(sum_taker_long_short_vol_ratio, 0) as tlsvr
                    FROM market_data.binance_futures_metrics_5m
                    WHERE symbol = %s AND is_closed = true AND create_time >= %s
                    ORDER BY create_time ASC
                """, (symbol, week_start))
                
                for r in cur:
                    ts = r["create_time"].replace(tzinfo=timezone.utc)
                    self.last_5m_time[symbol] = ts
                    
                    # 同时更新 5m 缓存
                    metrics_5m = Metrics(
                        symbol=symbol, datetime=ts,
                        open_interest=float(r["oi"]),
                        open_interest_value=float(r["oiv"]),
                        count_toptrader_long_short_ratio=float(r["ctlsr"]),
                        toptrader_long_short_ratio=float(r["tlsr"]),
                        long_short_ratio=float(r["lsr"]),
                        taker_long_short_vol_ratio=float(r["tlsvr"]),
                        is_closed=True
                    )
                    self.metrics_cache.append("5m", metrics_5m)
                    # Pub/Sub 推送 + 立即写入 Redis
                    if self.snapshot:
                        self.snapshot.publish_metrics_update(symbol, "5m", metrics_5m)
                        self.snapshot.save_metrics("5m", symbol, [metrics_5m], CACHE_WINDOW)
                    
                    # 更新各周期未闭合状态
                    for period in METRICS_DERIVED_PERIODS:
                        self._update_metrics_unclosed(
                            symbol, period, ts,
                            oi=float(r["oi"]), oiv=float(r["oiv"]),
                            ctlsr=float(r["ctlsr"]),
                            tlsr=float(r["tlsr"]), lsr=float(r["lsr"]), tlsvr=float(r["tlsvr"])
                        )

    def _update_metrics_unclosed(self, symbol: str, period: str, ts: datetime,
                                  oi: float, oiv: float, ctlsr: float, tlsr: float, lsr: float, tlsvr: float):
        """更新期货元数据未闭合状态（快照类型，直接覆盖）"""
        period_start = floor_to_period(period, ts)
        states = self.metrics_unclosed[symbol]
        
        # 快照类型：直接覆盖（取最新值）
        if period not in states or states[period].period_start != period_start:
            # 新周期
            states[period] = MetricsState(
                period_start=period_start,
                last_update=ts,
                open_interest=oi,
                open_interest_value=oiv,
                count_toptrader_long_short_ratio=ctlsr,
                toptrader_long_short_ratio=tlsr,
                long_short_ratio=lsr,
                taker_long_short_vol_ratio=tlsvr
            )
        else:
            # 同周期，更新为最新值
            state = states[period]
            state.last_update = ts
            state.open_interest = oi
            state.open_interest_value = oiv
            state.count_toptrader_long_short_ratio = ctlsr
            state.toptrader_long_short_ratio = tlsr
            state.long_short_ratio = lsr
            state.taker_long_short_vol_ratio = tlsvr

    def _flush_metrics_unclosed_to_cache(self, symbol: str):
        """将未闭合期货元数据写入缓存（时间戳用最新 5m）+ 推送"""
        updates = self._flush_metrics_unclosed_to_cache_batch(symbol)
        # 推送
        if updates and self.snapshot:
            self.snapshot.publish_metrics_batch(updates)

    def _flush_metrics_unclosed_to_cache_batch(self, symbol: str) -> List[tuple]:
        """将未闭合期货元数据写入缓存（批量模式，不推送，返回更新列表）
        
        返回: [(symbol, period, metrics), ...]
        """
        if symbol not in self.last_5m_time:
            return []
        latest_ts = self.last_5m_time[symbol]
        
        updates = []
        for period in METRICS_DERIVED_PERIODS:
            if period in self.metrics_unclosed[symbol]:
                state = self.metrics_unclosed[symbol][period]
                unclosed_metrics = Metrics(
                    symbol=symbol, datetime=latest_ts,
                    open_interest=state.open_interest,
                    open_interest_value=state.open_interest_value,
                    count_toptrader_long_short_ratio=state.count_toptrader_long_short_ratio,
                    toptrader_long_short_ratio=state.toptrader_long_short_ratio,
                    long_short_ratio=state.long_short_ratio,
                    taker_long_short_vol_ratio=state.taker_long_short_vol_ratio,
                    is_closed=False, period_start=state.period_start
                )
                self.metrics_cache.append(period, unclosed_metrics)
                updates.append((symbol, period, unclosed_metrics))
                
                # 写入 Redis（不推送）
                if self.snapshot:
                    self.snapshot.save_metrics(period, symbol, [unclosed_metrics], CACHE_WINDOW)
        
        return updates

    # ==================== Redis ====================

    def _try_restore_from_redis(self, symbols: List[str]) -> bool:
        if not self.snapshot or not self.snapshot.is_valid(REDIS_RESTORE_MAX_AGE_HOURS):
            return False
        
        try:
            LOG.info("从 Redis 恢复...")
            result = self.snapshot.restore_all(symbols, PERIODS)
            
            for period, symbol_dict in result["cache"].items():
                for symbol, bar_dicts in symbol_dict.items():
                    for bd in bar_dicts:
                        bar = Bar(
                            symbol=symbol, datetime=bd["datetime"],
                            open=bd["open"], high=bd["high"], low=bd["low"], close=bd["close"],
                            volume=bd["volume"], quote_volume=bd.get("quote_volume", 0),
                            trade_count=bd.get("trade_count", 0),
                            taker_buy_volume=bd.get("taker_buy_volume", 0),
                            taker_buy_quote_volume=bd.get("taker_buy_quote_volume", 0),
                            is_closed=bd["is_closed"], period_start=bd.get("period_start")
                        )
                        self.cache.append(period, bar)
                        if period == BASE_PERIOD:
                            self.last_1m_time[symbol] = bd["datetime"]
            
            for symbol, period_dict in result["unclosed"].items():
                for period, sd in period_dict.items():
                    self.unclosed[symbol][period] = UnclosedState(
                        period_start=sd["period_start"],
                        open=sd["open"], high=sd["high"], low=sd["low"], close=sd["close"],
                        volume=sd["volume"], quote_volume=sd.get("quote_volume", 0),
                        trade_count=sd.get("trade_count", 0),
                        taker_buy_volume=sd.get("taker_buy_volume", 0),
                        taker_buy_quote_volume=sd.get("taker_buy_quote_volume", 0)
                    )
            
            if result["last_seen"]:
                self.last_seen = result["last_seen"]
            
            return True
        except Exception:
            LOG.exception("Redis 恢复失败")
            return False

    def _catchup_since_last_seen(self):
        """增量补齐"""
        if not self.last_seen:
            return
        
        LOG.info("增量补齐：从 %s", self.last_seen.isoformat())
        
        cnt = 0
        max_ts = self.last_seen
        
        orig_autocommit = self.conn.autocommit
        try:
            self.conn.autocommit = False
            with self.conn.cursor(name="catchup", cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.itersize = 10000
                cur.execute(f"""
                    SELECT symbol, bucket_ts, open, high, low, close, volume,
                           COALESCE(quote_volume, 0) as quote_volume,
                           COALESCE(trade_count, 0) as trade_count,
                           COALESCE(taker_buy_volume, 0) as taker_buy_volume,
                           COALESCE(taker_buy_quote_volume, 0) as taker_buy_quote_volume
                    FROM market_data.candles_{BASE_PERIOD}
                    WHERE is_closed = true AND bucket_ts > %s
                    ORDER BY bucket_ts, symbol
                """, (self.last_seen,))
                
                for r in cur:
                    self._process_1m(
                        symbol=r["symbol"], ts=r["bucket_ts"],
                        o=float(r["open"]), h=float(r["high"]), l=float(r["low"]), c=float(r["close"]),
                        v=float(r["volume"]), qv=float(r["quote_volume"]),
                        tc=int(r["trade_count"]), tbv=float(r["taker_buy_volume"]),
                        tbqv=float(r["taker_buy_quote_volume"])
                    )
                    self._flush_unclosed_to_cache(r["symbol"])
                    if r["bucket_ts"] > max_ts:
                        max_ts = r["bucket_ts"]
                    cnt += 1
        finally:
            self.conn.rollback()
            self.conn.autocommit = orig_autocommit
        
        self.last_seen = max_ts
        LOG.info("  补齐 %d 条", cnt)

    def _full_sync_to_redis(self):
        """全量同步到 Redis（仅用于预热后）"""
        if not self.snapshot:
            return
        try:
            # K线
            self.snapshot.save_all(
                self.cache.store,
                dict(self.unclosed),
                self.last_1m_time,
                CACHE_WINDOW
            )
            # 元数据
            pipe = self.snapshot.pipeline()
            for period, symbol_dict in self.metrics_cache.store.items():
                for symbol, metrics_dict in symbol_dict.items():
                    metrics_list = list(metrics_dict.values())
                    self.snapshot.save_metrics(period, symbol, metrics_list, CACHE_WINDOW, pipe)
            pipe.execute()
        except Exception:
            LOG.exception("Redis 全量同步失败")

    def _sync_to_redis(self):
        """更新 Redis last_seen 时间戳（数据已在事件中实时写入）"""
        if not self.snapshot:
            return
        try:
            if self.last_1m_time:
                max_ts = max(self.last_1m_time.values())
                self.snapshot.set_last_seen(max_ts)
        except Exception:
            LOG.debug("Redis last_seen 更新失败")

    # ==================== 运行 ====================

    def _list_symbols(self) -> List[str]:
        """获取符号列表（使用项目统一工具）"""
        return 获取统一币安永续符号列表(
            db_url=DATABASE_URL,
            exchange_in_db="binance_futures_um",
            interval="1m"
        )

    def run(self):
        if self.listen_conn and not POLL_FALLBACK:
            self._run_listen()
        else:
            LOG.info("轮询模式，间隔 %.2fs", POLL_INTERVAL)
            self._run_poll()

    def _run_listen(self):
        LOG.info("监听 PG 通道: %s, %s", NOTIFY_CHANNEL, NOTIFY_CHANNEL_METRICS)
        self.listen_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        with self.listen_conn.cursor() as cur:
            cur.execute(f"LISTEN {NOTIFY_CHANNEL};")
            cur.execute(f"LISTEN {NOTIFY_CHANNEL_METRICS};")

        while True:
            if select.select([self.listen_conn], [], [], POLL_INTERVAL) == ([], [], []):
                continue

            self.listen_conn.poll()
            
            # 收集一批 NOTIFY（聚合处理）
            kline_payloads = []
            metrics_payloads = []
            while self.listen_conn.notifies:
                notify = self.listen_conn.notifies.pop(0)
                try:
                    payload = json.loads(notify.payload)
                    if notify.channel == NOTIFY_CHANNEL:
                        kline_payloads.append(payload)
                    elif notify.channel == NOTIFY_CHANNEL_METRICS:
                        metrics_payloads.append(payload)
                except Exception:
                    LOG.exception("NOTIFY 解析失败: %s", notify.channel)
            
            # 批量处理 K线（不逐条推送）
            kline_updates = []
            for payload in kline_payloads:
                updates = self._handle_notify_batch(payload)
                if updates:
                    kline_updates.extend(updates)
            
            # 批量推送 K线
            if kline_updates and self.snapshot:
                self.snapshot.publish_batch(kline_updates)
                LOG.info("批量推送K线: %d 条", len(kline_updates))
            
            # 批量处理元数据（不逐条推送）
            metrics_updates = []
            for payload in metrics_payloads:
                updates = self._handle_metrics_notify_batch(payload)
                if updates:
                    metrics_updates.extend(updates)
            
            # 批量推送元数据
            if metrics_updates and self.snapshot:
                self.snapshot.publish_metrics_batch(metrics_updates)
                LOG.info("批量推送元数据: %d 条", len(metrics_updates))

    def _handle_notify(self, payload: dict):
        """处理 K线 NOTIFY（单条，带推送）"""
        updates = self._handle_notify_batch(payload)
        if updates and self.snapshot:
            self.snapshot.publish_batch(updates)

    def _handle_notify_batch(self, payload: dict) -> List[tuple]:
        """处理 K线 NOTIFY（批量模式，不推送，返回更新列表）
        
        返回: [(symbol, period, bar), ...]
        """
        symbol = payload.get("symbol")
        bucket_ts_str = payload.get("bucket_ts")
        is_closed = payload.get("is_closed", True)

        if not symbol or not bucket_ts_str or not is_closed:
            return []

        bucket_ts = datetime.fromisoformat(bucket_ts_str.replace("Z", "+00:00"))
        bar = self._fetch_single_bar(symbol, bucket_ts)
        if not bar:
            return []
        
        self._process_1m(
            symbol=bar["symbol"], ts=bar["bucket_ts"],
            o=float(bar["open"]), h=float(bar["high"]), l=float(bar["low"]), c=float(bar["close"]),
            v=float(bar["volume"]), qv=float(bar["quote_volume"]),
            tc=int(bar["trade_count"]), tbv=float(bar["taker_buy_volume"]),
            tbqv=float(bar["taker_buy_quote_volume"])
        )
        
        # 刷新未闭合到缓存，收集更新（不推送）
        updates = self._flush_unclosed_to_cache_batch(symbol)
        
        if self.last_seen is None or bucket_ts > self.last_seen:
            self.last_seen = bucket_ts
        self._sync_to_redis()
        
        return updates

    def _handle_metrics_notify(self, payload: dict):
        """处理元数据 NOTIFY（单条，带推送）"""
        updates = self._handle_metrics_notify_batch(payload)
        # 单条推送
        if updates and self.snapshot:
            self.snapshot.publish_metrics_batch(updates)

    def _handle_metrics_notify_batch(self, payload: dict) -> List[tuple]:
        """处理元数据 NOTIFY（批量模式，不推送，返回更新列表）
        
        返回: [(symbol, period, metrics), ...]
        """
        symbol = payload.get("symbol")
        create_time_str = payload.get("create_time")
        is_closed = payload.get("is_closed", True)

        if not symbol or not create_time_str or not is_closed:
            return []

        create_time = datetime.fromisoformat(create_time_str.replace("Z", "+00:00"))
        if create_time.tzinfo is None:
            create_time = create_time.replace(tzinfo=timezone.utc)
        metrics = self._fetch_single_metrics(symbol, create_time)
        if not metrics:
            return []
        
        self.last_5m_time[symbol] = create_time
        updates = []
        
        # 更新 5m 缓存
        metrics_5m = Metrics(
            symbol=symbol, datetime=create_time,
            open_interest=metrics["oi"],
            open_interest_value=metrics["oiv"],
            count_toptrader_long_short_ratio=metrics["ctlsr"],
            toptrader_long_short_ratio=metrics["tlsr"],
            long_short_ratio=metrics["lsr"],
            taker_long_short_vol_ratio=metrics["tlsvr"],
            is_closed=True
        )
        self.metrics_cache.append("5m", metrics_5m)
        updates.append((symbol, "5m", metrics_5m))
        
        # 写入 Redis（不推送）
        if self.snapshot:
            self.snapshot.save_metrics("5m", symbol, [metrics_5m], CACHE_WINDOW)
        
        # 更新各周期未闭合状态
        for period in METRICS_DERIVED_PERIODS:
            self._update_metrics_unclosed(
                symbol, period, create_time,
                oi=metrics["oi"], oiv=metrics["oiv"],
                ctlsr=metrics["ctlsr"],
                tlsr=metrics["tlsr"], lsr=metrics["lsr"], tlsvr=metrics["tlsvr"]
            )
        
        # 刷新未闭合到缓存，收集更新
        unclosed_updates = self._flush_metrics_unclosed_to_cache_batch(symbol)
        updates.extend(unclosed_updates)
        
        return updates

    def _fetch_single_metrics(self, symbol: str, create_time: datetime) -> Optional[dict]:
        """获取单条元数据"""
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT symbol,
                       COALESCE(sum_open_interest, 0) as oi,
                       COALESCE(sum_open_interest_value, 0) as oiv,
                       COALESCE(count_toptrader_long_short_ratio, 0) as ctlsr,
                       COALESCE(sum_toptrader_long_short_ratio, 0) as tlsr,
                       COALESCE(count_long_short_ratio, 0) as lsr,
                       COALESCE(sum_taker_long_short_vol_ratio, 0) as tlsvr
                FROM market_data.binance_futures_metrics_5m
                WHERE symbol = %s AND create_time = %s AND is_closed = true
            """, (symbol, create_time))
            row = cur.fetchone()
        return dict(row) if row else None

    def _fetch_single_bar(self, symbol: str, bucket_ts: datetime) -> Optional[dict]:
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(f"""
                SELECT symbol, bucket_ts, open, high, low, close, volume,
                       COALESCE(quote_volume, 0) as quote_volume,
                       COALESCE(trade_count, 0) as trade_count,
                       COALESCE(taker_buy_volume, 0) as taker_buy_volume,
                       COALESCE(taker_buy_quote_volume, 0) as taker_buy_quote_volume
                FROM market_data.candles_{BASE_PERIOD}
                WHERE symbol = %s AND bucket_ts = %s AND is_closed = true
            """, (symbol, bucket_ts))
            row = cur.fetchone()
        return dict(row) if row else None

    def _run_poll(self):
        while True:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if self.last_seen is None:
                    cur.execute(f"SELECT max(bucket_ts) FROM market_data.candles_{BASE_PERIOD} WHERE is_closed = true")
                    (ts,) = cur.fetchone()
                    self.last_seen = ts or datetime.now(timezone.utc)
                
                cur.execute(f"""
                    SELECT symbol, bucket_ts, open, high, low, close, volume,
                           COALESCE(quote_volume, 0) as quote_volume,
                           COALESCE(trade_count, 0) as trade_count,
                           COALESCE(taker_buy_volume, 0) as taker_buy_volume,
                           COALESCE(taker_buy_quote_volume, 0) as taker_buy_quote_volume
                    FROM market_data.candles_{BASE_PERIOD}
                    WHERE is_closed = true AND bucket_ts > %s
                    ORDER BY bucket_ts ASC LIMIT 5000
                """, (self.last_seen,))
                rows = cur.fetchall()
            
            if not rows:
                time_module.sleep(POLL_INTERVAL)
                continue
            
            for r in rows:
                self._process_1m(
                    symbol=r["symbol"], ts=r["bucket_ts"],
                    o=float(r["open"]), h=float(r["high"]), l=float(r["low"]), c=float(r["close"]),
                    v=float(r["volume"]), qv=float(r["quote_volume"]),
                    tc=int(r["trade_count"]), tbv=float(r["taker_buy_volume"]),
                    tbqv=float(r["taker_buy_quote_volume"])
                )
                self._flush_unclosed_to_cache(r["symbol"])
                self.last_seen = r["bucket_ts"]
            
            self._sync_to_redis()

    # ==================== API ====================

    def get_bars(self, period: str, symbol: str) -> List[Bar]:
        """获取 K 线列表"""
        return self.cache.get(period, symbol)

    def get_latest(self, period: str, symbol: str) -> Optional[Bar]:
        """获取最新 K 线"""
        bars = self.cache.get(period, symbol)
        return bars[-1] if bars else None

    def get_metrics(self, period: str, symbol: str) -> List[Metrics]:
        """获取期货元数据列表"""
        return self.metrics_cache.get(period, symbol)

    def get_latest_metrics(self, period: str, symbol: str) -> Optional[Metrics]:
        """获取最新期货元数据"""
        return self.metrics_cache.get_latest(period, symbol)

    def export_csv(self, symbol: str, output_dir: str, count: int = 3):
        for period in PERIODS:
            bars = self.cache.get(period, symbol)
            if not bars:
                continue
            
            latest = bars[-count:] if len(bars) >= count else bars
            filename = os.path.join(output_dir, f"{symbol}_{period}.csv")
            
            with open(filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["datetime", "open", "high", "low", "close", "volume", 
                                "quote_volume", "trade_count", "taker_buy_volume", 
                                "taker_buy_quote_volume", "is_closed"])
                for bar in latest:
                    writer.writerow([
                        bar.datetime.isoformat(), bar.open, bar.high, bar.low, bar.close,
                        bar.volume, bar.quote_volume, bar.trade_count,
                        bar.taker_buy_volume, bar.taker_buy_quote_volume, bar.is_closed
                    ])
            
            LOG.info("导出 %s: %d 条", filename, len(latest))


def main():
    """数据合成服务入口"""
    LOG.info("数据合成服务启动...")
    
    # 信号处理
    def signal_handler(sig, frame):
        LOG.info("收到停止信号，正在退出...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        conn.set_session(readonly=True, autocommit=True)
    except Exception:
        LOG.exception("数据库连接失败")
        raise

    listen_conn = None
    if not POLL_FALLBACK:
        try:
            listen_conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
            LOG.info("LISTEN 连接建立")
        except Exception:
            LOG.warning("LISTEN 连接失败，使用轮询")

    engine = FusionEngine(conn, listen_conn)

    try:
        engine.warmup()
        LOG.info("开始运行，窗口=%d", CACHE_WINDOW)
        engine.run()
    except KeyboardInterrupt:
        LOG.info("用户中断")
    except SystemExit:
        pass
    except Exception:
        LOG.exception("运行出错")
        raise
    finally:
        conn.close()
        if listen_conn:
            listen_conn.close()
        LOG.info("数据合成服务已停止")


if __name__ == "__main__":
    main()
