#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""并行数据补齐器

核心思路：
- 时间×符号分片 + 多进程 COPY 加速读取
- pandas 向量化聚合生成高周期 OHLCV
- 直接写入 FusionEngine 的 HistoryCache，保持下游兼容
"""

from __future__ import annotations

import os
import sys
import io
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional, Any, TYPE_CHECKING
from multiprocessing import Pool, cpu_count
from dataclasses import dataclass

import pandas as pd
import psycopg2
import psycopg2.extras

from libs.common.utils.数据合成器 import Bar, HistoryCache, UnclosedState

if TYPE_CHECKING:
    from libs.common.utils.Redis缓存写入器 import RedisSnapshot

LOG = logging.getLogger("parallel_catchup")

COPY_COLUMNS = [
    "symbol",
    "bucket_ts",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "trade_count",
    "taker_buy_volume",
    "taker_buy_quote_volume",
]

# 周期定义（秒数）
PERIOD_SECONDS = {
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}

# 周期列表（包含1m）
PERIODS = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]


# 默认配置
DEFAULT_WORKERS = min(cpu_count(), 8)  # 最大8进程
DEFAULT_TIME_SEGMENT_HOURS = 6  # 每6小时一个时间分片
DEFAULT_SYMBOL_BATCH_SIZE = 70  # 每批70个符号


@dataclass
class ParallelConfig:
    """并行配置"""
    workers: int = DEFAULT_WORKERS
    time_segment_hours: int = DEFAULT_TIME_SEGMENT_HOURS
    symbol_batch_size: int = DEFAULT_SYMBOL_BATCH_SIZE
    use_binary_copy: bool = False  # CSV 更稳健，性能仍优于游标
    enable_vectorized_synthesis: bool = True


def _parse_copy_csv(buffer: io.BytesIO) -> pd.DataFrame:
    """解析 COPY CSV 数据为 DataFrame（独立函数便于多进程 pickle）"""
    if buffer.getbuffer().nbytes == 0:
        return pd.DataFrame()

    text_io = io.StringIO(buffer.getvalue().decode("utf-8"))
    df = pd.read_csv(
        text_io,
        header=None,
        names=COPY_COLUMNS,
        parse_dates=["bucket_ts"],
        dtype={
            "symbol": "string",
            "open": "float64",
            "high": "float64",
            "low": "float64",
            "close": "float64",
            "volume": "float64",
            "quote_volume": "float64",
            "trade_count": "int64",
            "taker_buy_volume": "float64",
            "taker_buy_quote_volume": "float64",
        },
    )
    if df.empty:
        return df

    # 强制 UTC tz-aware，避免后续 period_bucket 计算混用 naive
    df["bucket_ts"] = pd.to_datetime(df["bucket_ts"], utc=True)
    return df


def _copy_worker_task(task: Tuple[str, datetime, datetime, List[str]]) -> pd.DataFrame:
    """
    独立的工作进程函数，避免 pickle self 中的锁（HistoryCache/Redis）

    Args:
        task: (db_url, start_ts, end_ts, symbol_batch)
    """
    db_url, start_ts, end_ts, symbol_batch = task

    try:
        conn = psycopg2.connect(db_url)
        conn.set_session(readonly=True, autocommit=True)

        with conn.cursor() as cur:
            cur.execute("SET max_parallel_workers_per_gather = 8")
            cur.execute("SET work_mem = '256MB'")
            cur.execute("SET effective_io_concurrency = 200")

        buffer = io.BytesIO()
        with conn.cursor() as cur:
            copy_sql = """
                COPY (
                    SELECT symbol, bucket_ts, open, high, low, close, volume,
                           COALESCE(quote_volume, 0) as quote_volume,
                           COALESCE(trade_count, 0) as trade_count,
                           COALESCE(taker_buy_volume, 0) as taker_buy_volume,
                           COALESCE(taker_buy_quote_volume, 0) as taker_buy_quote_volume
                    FROM market_data.candles_1m
                    WHERE is_closed = true
                      AND bucket_ts > %s
                      AND bucket_ts <= %s
                      AND symbol = ANY(%s::text[])
                    ORDER BY bucket_ts, symbol
                ) TO STDOUT WITH (FORMAT csv, HEADER false)
            """
            cur.copy_expert(
                cur.mogrify(copy_sql, (start_ts, end_ts, symbol_batch)),
                buffer
            )

        buffer.seek(0)
        df = _parse_copy_csv(buffer)
        conn.close()

        if not df.empty:
            LOG.debug(
                "工作进程完成: %d 条 (时间: %s ~ %s, 符号: %d个)",
                len(df), start_ts, end_ts, len(symbol_batch)
            )

        return df

    except Exception as e:
        LOG.error("COPY 工作进程失败: %s", e)
        return pd.DataFrame()


class ParallelCatchupEngine:
    """并行补齐引擎"""

    def __init__(
        self,
        db_url: str,
        cache: HistoryCache,
        config: Optional[ParallelConfig] = None,
        snapshot: Optional["RedisSnapshot"] = None,
    ):
        self.db_url = db_url
        self.cache = cache
        self.config = config or ParallelConfig()
        self.snapshot = snapshot

        # 内部状态
        self.last_seen: Optional[datetime] = None
        self.last_1m_time: Dict[str, datetime] = {}
        self.unclosed: Dict[str, Dict[str, UnclosedState]] = {}

    def catchup_since_last_seen(
        self,
        last_seen: datetime,
        symbols: List[str],
        return_dataframe: bool = False
    ) -> Tuple[int, Optional[datetime], Optional[pd.DataFrame]]:
        """
        从last_seen开始并行补齐

        Args:
            last_seen: 最后已见时间戳
            symbols: 需要补齐的符号列表
            return_dataframe: 是否返回DataFrame（调试用）

        Returns:
            (处理条数, 新的last_seen, DataFrame或None)
        """
        if not last_seen:
            return 0, None, None

        LOG.info("=" * 70)
        LOG.info("并行补齐启动")
        LOG.info("起始时间: %s", last_seen.isoformat())
        LOG.info("符号数量: %d", len(symbols))
        LOG.info("并行配置: workers=%d, time_segment=%dh, symbol_batch=%d",
                 self.config.workers, self.config.time_segment_hours, self.config.symbol_batch_size)
        LOG.info("=" * 70)

        start_time = datetime.now()

        # 1. 并行COPY读取数据
        df = self._parallel_copy_read(last_seen, symbols)

        if df.empty:
            LOG.warning("未读取到任何数据")
            return 0, last_seen, df if return_dataframe else None

        read_time = (datetime.now() - start_time).total_seconds()
        LOG.info("并行读取完成: %d 条, %.2f 秒", len(df), read_time)

        # 2. 向量化合成
        synthesis_start = datetime.now()
        self._vectorized_synthesis(df)
        synthesis_time = (datetime.now() - synthesis_start).total_seconds()
        LOG.info("向量化合成完成: %.2f 秒", synthesis_time)

        # 3. 更新last_seen
        new_last_seen = df['bucket_ts'].max()
        self.last_seen = new_last_seen

        total_time = (datetime.now() - start_time).total_seconds()
        LOG.info("=" * 70)
        LOG.info("并行补齐总完成")
        LOG.info("处理条数: %d", len(df))
        LOG.info("新的last_seen: %s", new_last_seen.isoformat())
        LOG.info("总耗时: %.2f 秒", total_time)
        LOG.info("性能: %.2f 条/秒", len(df) / total_time if total_time > 0 else 0)
        LOG.info("=" * 70)

        return len(df), new_last_seen, df if return_dataframe else None

    def _parallel_copy_read(self, last_seen: datetime, symbols: List[str]) -> pd.DataFrame:
        """并行COPY读取数据"""

        # 1. 构建时间分片
        end_ts = datetime.now(timezone.utc)
        time_segments = self._build_time_segments(last_seen, end_ts)
        LOG.info("时间分片: %d 个", len(time_segments))

        # 2. 构建符号分片
        symbol_batches = self._build_symbol_batches(symbols)
        LOG.info("符号分片: %d 个", len(symbol_batches))

        # 3. 构建所有任务 (时间片 × 符号片)
        tasks = []
        for time_seg in time_segments:
            for symbol_batch in symbol_batches:
                tasks.append((time_seg[0], time_seg[1], symbol_batch))

        LOG.info("总任务数: %d", len(tasks))

        # 4. 并行执行
        dispatch_tasks = [(self.db_url, *task) for task in tasks]
        with Pool(processes=self.config.workers) as pool:
            results = pool.map(_copy_worker_task, dispatch_tasks)

        # 5. 合并所有DataFrame
        dfs = [df for df in results if not df.empty]
        if not dfs:
            return pd.DataFrame()

        combined_df = pd.concat(dfs, ignore_index=True)

        # 排序
        combined_df = combined_df.sort_values(['bucket_ts', 'symbol']).reset_index(drop=True)

        return combined_df

    def _build_time_segments(self, start_ts: datetime, end_ts: datetime) -> List[Tuple[datetime, datetime]]:
        """构建时间分片"""
        segments = []
        delta = timedelta(hours=self.config.time_segment_hours)

        current = start_ts
        while current < end_ts:
            segment_end = min(current + delta, end_ts)
            segments.append((current, segment_end))
            current = segment_end

        return segments

    def _build_symbol_batches(self, symbols: List[str]) -> List[List[str]]:
        """构建符号分片"""
        batches = []
        batch_size = self.config.symbol_batch_size

        for i in range(0, len(symbols), batch_size):
            batches.append(symbols[i:i+batch_size])

        return batches

    def _vectorized_synthesis(self, df: pd.DataFrame):
        """向量化合成所有周期"""
        if df.empty:
            return

        LOG.info("开始向量化合成: %d 条数据", len(df))

        # 1. 更新1m缓存（直接追加）
        self._update_1m_cache(df)

        # 2. 对每个周期进行向量化合成（区分闭合/未闭合）
        now = datetime.now(timezone.utc)
        for period, seconds in PERIOD_SECONDS.items():
            LOG.info("  合成 %s 周期", period)
            self._vectorized_synthesis_period(df, period, seconds, now)

    def _update_1m_cache(self, df: pd.DataFrame):
        """更新1m缓存"""
        for row in df.itertuples(index=False):
            symbol = row.symbol
            ts = row.bucket_ts

            if symbol not in self.last_1m_time or ts > self.last_1m_time[symbol]:
                self.last_1m_time[symbol] = ts

            bar = Bar(
                symbol=symbol,
                datetime=ts,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                quote_volume=float(row.quote_volume),
                trade_count=int(row.trade_count),
                taker_buy_volume=float(row.taker_buy_volume),
                taker_buy_quote_volume=float(row.taker_buy_quote_volume),
                is_closed=True
            )
            self.cache.append('1m', bar)

    def _vectorized_synthesis_period(self, df: pd.DataFrame, period: str, seconds: int, now: datetime):
        """向量化合成指定周期，区分闭合/未闭合"""

        df_local = df.copy()
        df_local['period_bucket'] = (df_local['bucket_ts'].astype('int64') // (seconds * 10**9)) * (seconds * 10**9)
        df_local['period_bucket'] = pd.to_datetime(df_local['period_bucket'], utc=True)

        grouped = df_local.groupby(['symbol', 'period_bucket'])

        agg_df = grouped.agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'quote_volume': 'sum',
            'trade_count': 'sum',
            'taker_buy_volume': 'sum',
            'taker_buy_quote_volume': 'sum',
        }).reset_index()

        bars_closed: List[Bar] = []
        unclosed_map: Dict[str, Bar] = {}

        for row in agg_df.itertuples(index=False):
            period_start = row.period_bucket.to_pydatetime()
            closed = (period_start + timedelta(seconds=seconds)) <= now
            bar = Bar(
                symbol=row.symbol,
                datetime=row.period_bucket.to_pydatetime(),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                quote_volume=float(row.quote_volume),
                trade_count=int(row.trade_count),
                taker_buy_volume=float(row.taker_buy_volume),
                taker_buy_quote_volume=float(row.taker_buy_quote_volume),
                is_closed=closed,
                period_start=period_start,
            )
            if closed:
                bars_closed.append(bar)
            else:
                unclosed_map[row.symbol] = bar

        for bar in bars_closed:
            self.cache.append(period, bar)

        # 保存未闭合状态，供回调/Redis 使用
        for symbol, bar in unclosed_map.items():
            self._update_unclosed_state(symbol, period, bar)

    def _update_unclosed_state(self, symbol: str, period: str, bar: Bar):
        """记录未闭合状态并写入缓存（不推送）"""
        # 兼容：如果外部没有 unclosed 结构，则仅写缓存
        if not hasattr(self, "unclosed"):
            self.cache.append(period, bar)
            return

        state = self.unclosed.get(symbol, {}).get(period)
        if state is None or state.period_start != bar.period_start:
            self.unclosed.setdefault(symbol, {})[period] = UnclosedState(
                period_start=bar.period_start,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                quote_volume=bar.quote_volume,
                trade_count=bar.trade_count,
                taker_buy_volume=bar.taker_buy_volume,
                taker_buy_quote_volume=bar.taker_buy_quote_volume,
            )
        else:
            st = self.unclosed[symbol][period]
            st.high = max(st.high, bar.high)
            st.low = min(st.low, bar.low)
            st.close = bar.close
            st.volume += bar.volume
            st.quote_volume += bar.quote_volume
            st.trade_count += bar.trade_count
            st.taker_buy_volume += bar.taker_buy_volume
            st.taker_buy_quote_volume += bar.taker_buy_quote_volume

        # 始终写缓存中的未闭合条目
        self.cache.append(period, bar)

        # 可选 Redis 持久/推送
        if self.snapshot:
            try:
                self.snapshot.append_bars(period, symbol, [bar])
                self.snapshot.publish_batch([(symbol, period, bar)])
            except Exception as exc:
                LOG.debug("Redis 未闭合写入失败: %s", exc)


# 兼容性包装函数（直接替换生产代码中的_catchup_since_last_seen）
def parallel_catchup_compat(
    engine: Any,
    last_seen: datetime,
    symbols: List[str],
    db_url: str
) -> Tuple[int, datetime]:
    """
    与生产代码兼容的并行补齐包装函数

    Args:
        engine: 数据合成器实例（有cache和unclosed属性）
        last_seen: 最后已见时间
        symbols: 符号列表
        db_url: 数据库连接URL

    Returns:
        (处理条数, 新的last_seen)
    """

    # 创建临时引擎
    temp_engine = ParallelCatchupEngine(db_url, engine.cache)

    # 执行补齐
    count, new_last_seen, _ = temp_engine.catchup_since_last_seen(
        last_seen, symbols, return_dataframe=False
    )

    # 更新原引擎状态
    engine.last_seen = new_last_seen

    return count, new_last_seen
