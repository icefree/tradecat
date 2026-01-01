"""
数据库读写（高性能版）

优化点：
1. PG 连接池复用 + 扩大池大小
2. 多周期并行查询
3. 批量 SQL 查询（IN 子句）
4. SQLite 连接复用 + WAL 模式
5. 批量写入
"""
import sqlite3
import threading
import logging
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from ..config import config

_sqlite_lock = threading.Lock()
LOG = logging.getLogger("indicator_service.db")


class DataReader:
    """从 TimescaleDB 读取 K 线数据（高性能版）"""
    
    def __init__(self, db_url: str = None, pool_size: int = 10):
        self.db_url = db_url or config.db_url
        self._pool = None
        self._pool_size = pool_size
        self._pool_lock = threading.Lock()
    
    @property
    def pool(self):
        """懒加载连接池（线程安全）"""
        if self._pool is None:
            with self._pool_lock:
                if self._pool is None:
                    self._pool = ConnectionPool(
                        self.db_url,
                        min_size=2,
                        max_size=self._pool_size,
                        kwargs={"row_factory": dict_row},
                        timeout=120,
                    )
        return self._pool
    
    @contextmanager
    def _conn(self):
        """从连接池获取连接"""
        with self.pool.connection() as conn:
            yield conn
    
    def get_klines(self, symbols: Sequence[str], interval: str, limit: int = 300, exchange: str = None) -> Dict[str, pd.DataFrame]:
        """批量获取 K 线数据 - 并行查询"""
        exchange = exchange or config.exchange
        if not symbols:
            return {}
        
        table = f"candles_{interval}"
        symbols_list = list(symbols)
        
        # 根据周期计算时间范围，避免扫描全部分区
        interval_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
        minutes = interval_minutes.get(interval, 5) * limit * 2
        
        # 对于大量币种，使用并行单币种查询更快
        if len(symbols_list) > 50:
            return self._get_klines_parallel(symbols_list, interval, limit, exchange)
        
        # 小批量使用窗口函数
        sql = f"""
            WITH ranked AS (
                SELECT symbol, bucket_ts, open, high, low, close, volume,
                       quote_volume, trade_count, taker_buy_volume, taker_buy_quote_volume,
                       ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY bucket_ts DESC) as rn
                FROM market_data.{table}
                WHERE symbol = ANY(%s) AND exchange = %s AND bucket_ts > NOW() - INTERVAL '{minutes} minutes'
            )
            SELECT symbol, bucket_ts, open, high, low, close, volume,
                   quote_volume, trade_count, taker_buy_volume, taker_buy_quote_volume
            FROM ranked WHERE rn <= %s
            ORDER BY symbol, bucket_ts ASC
        """
        
        result = {}
        try:
            with self._conn() as conn:
                rows = conn.execute(sql, (symbols_list, exchange, limit)).fetchall()
                if rows:
                    from itertools import groupby
                    for symbol, group in groupby(rows, key=lambda x: x['symbol']):
                        row_list = list(group)
                        if row_list:
                            result[symbol] = self._rows_to_df(row_list)
        except Exception as e:
            LOG.warning(f"批量查询失败，回退并行查询: {e}")
            result = self._get_klines_parallel(symbols_list, interval, limit, exchange)
        
        return result
    
    def _get_klines_parallel(self, symbols: Sequence[str], interval: str, limit: int, exchange: str) -> Dict[str, pd.DataFrame]:
        """并行查询多币种"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        result = {}
        table = f"candles_{interval}"
        
        # 根据周期计算时间范围，避免扫描全部分区
        interval_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
        minutes = interval_minutes.get(interval, 5) * limit * 2  # 2倍余量
        
        def fetch_one(symbol: str):
            try:
                with self.pool.connection() as conn:
                    sql = f"""
                        SELECT bucket_ts, open, high, low, close, volume, 
                               quote_volume, trade_count, taker_buy_volume, taker_buy_quote_volume
                        FROM market_data.{table}
                        WHERE symbol = %s AND exchange = %s AND bucket_ts > NOW() - INTERVAL '{minutes} minutes'
                        ORDER BY bucket_ts DESC
                        LIMIT %s
                    """
                    rows = conn.execute(sql, (symbol, exchange, limit)).fetchall()
                    if rows:
                        return symbol, self._rows_to_df(list(reversed(rows)))
            except Exception:
                pass
            return symbol, None
        
        workers = min(self._pool_size - 1, 8)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(fetch_one, s) for s in symbols]
            for future in as_completed(futures):
                sym, df = future.result()
                if df is not None:
                    result[sym] = df
        
        return result
    
    def get_klines_multi_interval(self, symbols: Sequence[str], intervals: Sequence[str], limit: int = 300, exchange: str = None) -> Dict[str, Dict[str, pd.DataFrame]]:
        """多周期并行获取数据"""
        exchange = exchange or config.exchange
        if not symbols or not intervals:
            return {}
        
        result = {}
        
        # 并行查询所有周期
        workers = min(len(intervals), self._pool_size - 1, 7)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self.get_klines, symbols, iv, limit, exchange): iv
                for iv in intervals
            }
            for future in as_completed(futures):
                iv = futures[future]
                try:
                    result[iv] = future.result()
                except Exception as e:
                    LOG.error(f"[{iv}] 查询失败: {e}")
                    result[iv] = {}
        
        return result
    
    def _get_klines_fallback(self, symbols: Sequence[str], interval: str, limit: int, exchange: str) -> Dict[str, pd.DataFrame]:
        """回退方案：逐个查询"""
        result = {}
        table = f"candles_{interval}"
        
        with self._conn() as conn:
            for symbol in symbols:
                sql = f"""
                    SELECT bucket_ts, open, high, low, close, volume, 
                           quote_volume, trade_count, taker_buy_volume, taker_buy_quote_volume
                    FROM market_data.{table}
                    WHERE symbol = %s AND exchange = %s
                    ORDER BY bucket_ts DESC
                    LIMIT %s
                """
                try:
                    rows = conn.execute(sql, (symbol, exchange, limit)).fetchall()
                except Exception:
                    continue
                
                if rows:
                    result[symbol] = self._rows_to_df(list(reversed(rows)))
        
        return result
    
    def _rows_to_df(self, rows: list) -> pd.DataFrame:
        """将行数据转换为 DataFrame"""
        df = pd.DataFrame([dict(r) for r in rows])
        if "symbol" in df.columns:
            df.drop(columns=["symbol"], inplace=True)
        df.set_index(pd.DatetimeIndex(df["bucket_ts"], tz="UTC"), inplace=True)
        df.drop(columns=["bucket_ts"], inplace=True)
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    
    def get_symbols(self, exchange: str = None, interval: str = "1m") -> List[str]:
        """获取交易所所有交易对"""
        exchange = exchange or config.exchange
        with self._conn() as conn:
            sql = f"SELECT DISTINCT symbol FROM market_data.candles_{interval} WHERE exchange = %s"
            return [r["symbol"] for r in conn.execute(sql, (exchange,)).fetchall()]
    
    def get_latest_ts(self, interval: str, exchange: str = None):
        """获取某周期最新 K 线时间戳"""
        exchange = exchange or config.exchange
        try:
            with self._conn() as conn:
                sql = f"SELECT MAX(bucket_ts) FROM market_data.candles_{interval} WHERE exchange = %s"
                row = conn.execute(sql, (exchange,)).fetchone()
                if row and row["max"]:
                    return row["max"]
        except Exception:
            pass
        return None
    
    def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.close()
            self._pool = None


class DataWriter:
    """将指标结果写入 SQLite（优化版）"""
    
    def __init__(self, sqlite_path: Path = None):
        self.sqlite_path = sqlite_path or config.sqlite_path
        self._conn = None
        self._lock = threading.Lock()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取或创建连接"""
        if self._conn is None:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.sqlite_path), check_same_thread=False)
            self._conn.execute("PRAGMA auto_vacuum=FULL")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA cache_size=10000")
        return self._conn
    
    def write(self, table: str, df: pd.DataFrame, interval: str = None):
        """写入单个表 - 按周期增量更新"""
        if df.empty:
            return
        
        with self._lock:
            conn = self._get_conn()
            
            # 获取本次数据的周期列表
            intervals = df["周期"].unique().tolist() if "周期" in df.columns else []
            
            # 检查表是否存在及列是否匹配
            try:
                existing_cols = set(c[1] for c in conn.execute(f'PRAGMA table_info([{table}])').fetchall())
            except:
                existing_cols = set()
            
            df_cols = set(df.columns)
            
            if not existing_cols:
                # 表不存在，直接创建
                df.to_sql(table, conn, if_exists="replace", index=False)
            elif not df_cols.issubset(existing_cols):
                # 列不匹配，重建表
                conn.execute(f"DROP TABLE IF EXISTS [{table}]")
                df.to_sql(table, conn, if_exists="replace", index=False)
            else:
                # 表存在且列匹配，删除对应周期的旧数据再插入
                if intervals:
                    placeholders = ",".join("?" * len(intervals))
                    conn.execute(f"DELETE FROM [{table}] WHERE 周期 IN ({placeholders})", intervals)
                df.to_sql(table, conn, if_exists="append", index=False)
            
            conn.commit()
    
    def write_batch(self, data: Dict[str, pd.DataFrame], interval: str):
        """
        批量写入多个表 - 单次事务
        
        所有表的 DELETE + INSERT 在一个事务中完成
        """
        if not data:
            return
        
        with self._lock:
            conn = self._get_conn()
            try:
                # 开始事务
                conn.execute("BEGIN IMMEDIATE")
                
                for table, df in data.items():
                    if df.empty:
                        continue
                    
                    # 检查表是否存在及列是否匹配
                    existing_cols = set()
                    try:
                        existing_cols = set(c[1] for c in conn.execute(f'PRAGMA table_info([{table}])').fetchall())
                    except:
                        pass
                    
                    df_cols = set(df.columns)
                    
                    # 如果表不存在或列不匹配，重建表
                    if not existing_cols or not df_cols.issubset(existing_cols):
                        conn.execute(f"DROP TABLE IF EXISTS [{table}]")
                        df.head(0).to_sql(table, conn, if_exists="replace", index=False)
                    
                    # 删除旧数据
                    try:
                        if "周期" in df.columns:
                            conn.execute(f"DELETE FROM [{table}] WHERE 周期 = ?", (interval,))
                        else:
                            symbols = df["交易对"].unique().tolist()
                            placeholders = ",".join("?" * len(symbols))
                            conn.execute(f"DELETE FROM [{table}] WHERE 交易对 IN ({placeholders})", symbols)
                    except sqlite3.OperationalError:
                        pass
                    
                    # 批量插入
                    df.to_sql(table, conn, if_exists="append", index=False)
                
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
    
    def close(self):
        """关闭连接"""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None


# 全局单例
reader = DataReader()
writer = DataWriter()
