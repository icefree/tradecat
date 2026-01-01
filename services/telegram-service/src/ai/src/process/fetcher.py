# -*- coding: utf-8 -*-
"""
极简数据抓取器
- 需求：不做摘要，直接抓全量 K 线 + 元数据 + SQLite 指标，返回统一 payload
- 同步实现，供上层 asyncio 用 asyncio.to_thread 包裹
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import sqlite3
from datetime import datetime, timezone
from src.utils.data_docs import DATA_DOCS

BASE_DIR = Path(__file__).resolve().parents[2]
INDICATOR_DB = (BASE_DIR.parents[2] / "data-service" / "data" / "csv" / "market_data.db").resolve()
PSQL_CONN = {
    "host": "localhost",
    "port": "5433",
    "user": "postgres",
    "database": "market_data",
}
DEFAULT_INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]


def _run_psql(sql: str) -> List[str]:
    cmd = [
        "psql",
        "-h",
        PSQL_CONN["host"],
        "-p",
        PSQL_CONN["port"],
        "-U",
        PSQL_CONN["user"],
        "-d",
        PSQL_CONN["database"],
        "-A",
        "-F",
        ",",
        "-q",
        "-t",
        "-P",
        "footer=off",
        "-c",
        sql,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip())
    return [l for l in res.stdout.splitlines() if l.strip()]


def fetch_candles(symbol: str, intervals: List[str] = DEFAULT_INTERVALS) -> Dict[str, List[Dict[str, Any]]]:
    candles: Dict[str, List[Dict[str, Any]]] = {}
    for iv in intervals:
        table = f"market_data.candles_{iv}"
        sql = (
            "SELECT bucket_ts,open,high,low,close,volume,quote_volume,trade_count,"
            "taker_buy_volume,taker_buy_quote_volume "
            f"FROM {table} WHERE symbol='{symbol}' ORDER BY bucket_ts DESC LIMIT 50"
        )
        rows = _run_psql(sql)
        parsed: List[Dict[str, Any]] = []
        for line in rows:
            parts = line.split(",")
            parsed.append(
                {
                    "bucket_ts": parts[0],
                    "open": float(parts[1]),
                    "high": float(parts[2]),
                    "low": float(parts[3]),
                    "close": float(parts[4]),
                    "volume": float(parts[5]),
                    "quote_volume": float(parts[6]) if len(parts) > 6 and parts[6] else None,
                    "trade_count": int(parts[7]) if len(parts) > 7 and parts[7] else None,
                    "taker_buy_volume": float(parts[8]) if len(parts) > 8 and parts[8] else None,
                    "taker_buy_quote_volume": float(parts[9]) if len(parts) > 9 and parts[9] else None,
                }
            )
        candles[iv] = parsed
    return candles


def fetch_metrics(symbol: str) -> List[Dict[str, Any]]:
    sql = (
        "SELECT create_time,symbol,sum_open_interest,sum_open_interest_value,"
        "sum_toptrader_long_short_ratio,sum_taker_long_short_vol_ratio "
        "FROM market_data.binance_futures_metrics_5m "
        f"WHERE symbol='{symbol}' ORDER BY create_time DESC LIMIT 50"
    )
    rows = _run_psql(sql)
    return [
        dict(
            zip(
                [
                    "create_time",
                    "symbol",
                    "sum_open_interest",
                    "sum_open_interest_value",
                    "sum_toptrader_long_short_ratio",
                    "sum_taker_long_short_vol_ratio",
                ],
                r.split(","),
            )
        )
        for r in rows
    ]


def fetch_indicators(symbol: str) -> Dict[str, Any]:
    db_path = INDICATOR_DB
    indicators: Dict[str, Any] = {}

    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
    except Exception:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for tbl in tables:
        try:
            cols = [d[1] for d in cur.execute(f"PRAGMA table_info('{tbl}')").fetchall()]
            if not cols:
                indicators[tbl] = {"error": "empty table"}
                continue
            sym_col = None
            for cand in ["交易对", "symbol", "Symbol", "SYMBOL"]:
                if cand in cols:
                    sym_col = cand
                    break
            if sym_col is None:
                indicators[tbl] = {"error": "no symbol column"}
                continue
            rows = cur.execute(f"SELECT * FROM '{tbl}' WHERE `{sym_col}`=?", (symbol,)).fetchall()
            indicators[tbl] = [dict(zip(cols, r)) for r in rows]
        except Exception as e:
            indicators[tbl] = {"error": str(e)}
    cur.close()
    conn.close()
    return indicators


def fetch_payload(symbol: str, interval: str) -> Dict[str, Any]:
    payload = {
        "symbol": symbol,
        "interval_requested": interval,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candles_latest_50": fetch_candles(symbol),
        "metrics_5m_latest_50": fetch_metrics(symbol),
        "indicator_samples": fetch_indicators(symbol),
        "docs": DATA_DOCS,
    }
    return payload


__all__ = ["fetch_payload"]
