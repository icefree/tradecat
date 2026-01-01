#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ccxt币安永续合约工具
---------------------------------
从币安WSS数据获取脚本中提取的币安USDT永续合约相关工具函数
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ccxt

# 使用路径助手统一管理路径
from libs.common.utils.路径助手 import 获取仓库根目录

仓库根目录 = 获取仓库根目录()
SRC根目录 = 仓库根目录 / "src"

# 将源码目录加入Python路径
if str(仓库根目录) not in sys.path:
    sys.path.insert(0, str(仓库根目录))
if str(SRC根目录) not in sys.path:
    sys.path.insert(0, str(SRC根目录))

try:
    from dotenv import load_dotenv
    env_path = 仓库根目录 / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

try:
    from cryptofeed.defines import PERPETUAL  # type: ignore
    from cryptofeed.symbols import Symbol, Symbols  # type: ignore
except Exception:  # pragma: no cover - 兜底以避免依赖缺失阻塞基础功能
    PERPETUAL = "perpetual"

    class Symbol:  # type: ignore
        def __init__(self, base: str, quote: str, type: str = ""):
            self.base = base.upper()
            self.quote = quote.upper()
            self.type = type

        @property
        def normalized(self) -> str:
            return f"{self.base}{self.quote}"

    class Symbols:  # 最小占位，当前模块未用到
        pass
try:
    from libs.common.utils.数据库操作工具 import 创建数据库操作器  # type: ignore
except ImportError:
    # 回退：从当前同级目录导入
    import importlib.util

    当前文件目录 = Path(__file__).parent
    db_utils_path = 当前文件目录 / "数据库操作工具.py"
    spec = importlib.util.spec_from_file_location("数据库操作工具", db_utils_path)
    if spec and spec.loader:
        模块 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(模块)  # type: ignore
        创建数据库操作器 = 模块.创建数据库操作器  # type: ignore
    else:
        raise

logger = logging.getLogger(__name__)

# ---------- 环境配置与常量 ----------
PROXY_URL = (
    os.getenv("GLOBAL_PROXY_URL")
    or os.getenv("HTTP_PROXY")
    or os.getenv("HTTPS_PROXY")
    or "http://127.0.0.1:9910"
)

TARGET_QUOTE_ASSET = os.getenv("KLINE_TARGET_QUOTE_ASSET", "USDT").upper()
SYMBOL_REFRESH_SECONDS = max(60, int(os.getenv("KLINE_SYMBOL_REFRESH_SECONDS", "900")))

BINANCE_WEIGHT_LIMIT = max(100, int(os.getenv("KLINE_BINANCE_WEIGHT_LIMIT_PER_MIN", "1200")))
BYBIT_WEIGHT_LIMIT = max(100, int(os.getenv("KLINE_BYBIT_WEIGHT_LIMIT_PER_MIN", "600")))
DEFAULT_WEIGHT_LIMIT = max(100, int(os.getenv("KLINE_DEFAULT_WEIGHT_LIMIT_PER_MIN", "600")))
LOAD_MARKETS_WEIGHT = max(1, int(os.getenv("KLINE_LOAD_MARKETS_WEIGHT", "100")))

_EXCHANGE_RATE_LIMITS: Dict[str, int] = {
    "binance": BINANCE_WEIGHT_LIMIT,
    "bybit": BYBIT_WEIGHT_LIMIT,
}


# ---------- 限流与缓存 ----------
class RateLimiter:
    """简单 token bucket 限流器，用于控制 CCXT 权重。"""

    def __init__(self, capacity_per_minute: int) -> None:
        self.capacity = float(max(1, capacity_per_minute))
        self.tokens = float(self.capacity)
        self.refill_rate = self.capacity / 60.0
        self.last_refill = time.monotonic()

    def acquire(self, weight: int = 1) -> None:
        weight = max(1, weight)
        while True:
            now = time.monotonic()
            elapsed = now - self.last_refill
            if elapsed > 0:
                self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
                self.last_refill = now
            if self.tokens >= weight:
                self.tokens -= weight
                return
            deficit = weight - self.tokens
            wait_time = max(deficit / self.refill_rate, 0.05)
            time.sleep(wait_time)


_RATE_LIMITERS: Dict[str, RateLimiter] = {}
_CCXT_CLIENTS: Dict[str, ccxt.Exchange] = {}
_SYMBOL_CACHE: Dict[str, Tuple[List[str], float]] = {}


def _get_rate_limiter(exchange: str) -> RateLimiter:
    exchange_lower = exchange.lower()
    limiter = _RATE_LIMITERS.get(exchange_lower)
    if limiter is None:
        capacity = _EXCHANGE_RATE_LIMITS.get(exchange_lower, DEFAULT_WEIGHT_LIMIT)
        limiter = RateLimiter(capacity)
        _RATE_LIMITERS[exchange_lower] = limiter
    return limiter


def _acquire_rate_limit(exchange: str, weight: int) -> None:
    limiter = _get_rate_limiter(exchange)
    limiter.acquire(weight)


# ---------- CCXT 客户端与市场工具 ----------
def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().replace("/", "").replace(":", "")


def _get_ccxt_client(exchange: str) -> Optional[ccxt.Exchange]:
    """获取或创建 CCXT 客户端实例。"""
    if exchange in _CCXT_CLIENTS:
        return _CCXT_CLIENTS[exchange]

    exchange_lower = exchange.lower()
    try:
        if exchange_lower == "binance":
            client = ccxt.binance({
                "enableRateLimit": True,
                "options": {"defaultType": "future"},
                "proxies": {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None,
            })
        elif exchange_lower == "bybit":
            client = ccxt.bybit({
                "enableRateLimit": True,
                "options": {"defaultType": "linear"},
                "proxies": {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None,
            })
        else:
            logger.warning("不支持的交易所: %s", exchange)
            return None

        _CCXT_CLIENTS[exchange] = client
        return client
    except Exception as exc:  # pragma: no cover - 网络/依赖异常
        logger.error("创建 %s CCXT 客户端失败：%s", exchange, exc)
        return None


def _ensure_markets_loaded(exchange: str, client: ccxt.Exchange) -> bool:
    """确保已加载市场列表，避免重复高权重请求。"""
    if getattr(client, "markets", None):
        return True
    try:
        _acquire_rate_limit(exchange, LOAD_MARKETS_WEIGHT)
        client.load_markets()
        return True
    except Exception as exc:  # pragma: no cover
        logger.debug("加载 %s 市场列表失败：%s", exchange, exc)
        return False


def _match_quote_filter(market: dict) -> bool:
    """只保留与目标报价资产匹配的市场。"""
    quote = market.get("quote") or market.get("quoteId") or ""
    if not quote:
        info = market.get("info") or {}
        quote = info.get("quoteAsset") or info.get("quoteCoin") or ""
    return quote.upper() == TARGET_QUOTE_ASSET


def _is_target_market(exchange: str, market: dict) -> bool:
    """判定是否为目标 USDT 永续合约市场。"""
    if not market or not market.get("active", True):
        return False
    if not (market.get("symbol") or market.get("id")):
        return False
    if not _match_quote_filter(market):
        return False

    exchange_lower = exchange.lower()
    if exchange_lower in {"binance", "bybit"}:
        if not market.get("swap", False):
            return False
        if exchange_lower == "bybit" and market.get("linear") is False:
            return False

    return True


def _load_symbols_from_db(exchange: str, db_url: Optional[str] = None, interval: str = "1m") -> List[str]:
    """从 TimescaleDB 回退加载已有符号列表。"""
    try:
        with 创建数据库操作器(db_url) as db:
            return db.获取符号列表(exchange, interval=interval)
    except Exception as exc:  # pragma: no cover - DB 异常
        logger.debug("从数据库回退加载 %s 交易对失败：%s", exchange, exc)
        return []


def _load_symbols_for_exchange(exchange: str, *, db_url: Optional[str] = None) -> List[str]:
    """加载目标交易所的 USDT 永续符号，带缓存与 DB 回退。"""
    cache_entry = _SYMBOL_CACHE.get(exchange)
    now = time.time()
    if cache_entry and (now - cache_entry[1]) < SYMBOL_REFRESH_SECONDS:
        return cache_entry[0]

    client = _get_ccxt_client(exchange)
    markets_loaded = False
    if client:
        markets_loaded = _ensure_markets_loaded(exchange, client)

    if not markets_loaded:
        fallback = _load_symbols_from_db(exchange, db_url=db_url)
        if fallback:
            logger.warning("使用数据库中已存在的 %s 交易对列表作为回退，数量=%s", exchange, len(fallback))
            _SYMBOL_CACHE[exchange] = (fallback, now)
            return fallback
        return cache_entry[0] if cache_entry else []

    markets = client.markets or {}
    symbols_set = {
        _normalize_symbol(mkt.get("id") or mkt.get("symbol") or "")
        for mkt in markets.values()
        if _is_target_market(exchange, mkt)
    }
    symbols_set.discard("")

    symbols_list = sorted(symbols_set)
    _SYMBOL_CACHE[exchange] = (symbols_list, now)
    logger.info(
        "自动加载 %s 交易对: 原始 %s 个, 保留 %s 个 USDT 合约",
        exchange, len(markets), len(symbols_list)
    )
    return symbols_list


def _resolve_ccxt_symbol(exchange: str, symbol: str) -> Optional[str]:
    """将标准化符号转换为 CCXT 市场符号。"""
    client = _get_ccxt_client(exchange)
    if not client:
        return None

    if not _ensure_markets_loaded(exchange, client):
        return None

    # 直接命中
    if symbol in client.markets:
        return symbol

    normalized = _normalize_symbol(symbol)

    for market_symbol in client.markets.keys():
        if _normalize_symbol(market_symbol) == normalized:
            return market_symbol

    for quote in ["USDT", "USDC", "USD", "BUSD"]:
        if normalized.endswith(quote):
            base = normalized[:-len(quote)]
            candidates = [
                f"{base}/{quote}",
                f"{base}/{quote}:{quote}",
            ]
            for candidate in candidates:
                if candidate in client.markets:
                    return candidate

    logger.debug("无法解析 %s 符号：%s", exchange, symbol)
    return None


def 获取币安永续合约符号列表(exchange: str = "binance") -> List[str]:
    """
    从CCXT加载币安USDT永续合约交易对列表

    参数:
        exchange: 交易所名称, 默认为 "binance"

    返回:
        交易对符号列表(如 ["BTCUSDT", "ETHUSDT", ...])
    """
    return _load_symbols_for_exchange(exchange)


def 标准化永续合约符号(symbol: str) -> Optional[str]:
    """
    标准化交易对符号, 只保留USDT永续合约

    参数:
        symbol: 原始交易对符号(如 "BTC/USDT", "BTCUSDT" 等)

    返回:
        标准化后的符号(如 "BTCUSDT"), 如果不是USDT永续合约则返回None
    """
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        return None
    base = symbol[:-4]
    quote = symbol[-4:]
    if not base:
        return None
    normalized = Symbol(base, quote, type=PERPETUAL).normalized
    return normalized


def 创建币安符号映射(exchange: str = "binance") -> Dict[str, str]:
    """
    创建币安永续合约标准化符号到原始符号的映射

    参数:
        exchange: 交易所名称, 默认为 "binance"

    返回:
        Dict[str, str]: 键是标准化符号(如"BTCUSDT"), 值是原始符号(如"BTCUSDT")
    """
    symbols = 获取币安永续合约符号列表(exchange)
    if not symbols:
        raise RuntimeError("未能加载任何 Binance 交易对")

    mapping: Dict[str, str] = {}
    for raw_symbol in symbols:
        normalized = 标准化永续合约符号(raw_symbol)
        if not normalized:
            continue
        mapping[normalized] = raw_symbol.upper()

    return mapping


def 解析币安CCXT符号(exchange: str, symbol: str) -> Optional[str]:
    """
    解析币安CCXT符号

    参数:
        exchange: 交易所名称
        symbol: 交易对符号

    返回:
        CCXT格式的符号或None
    """
    return _resolve_ccxt_symbol(exchange, symbol)


def 获取币安USDT永续合约数量(exchange: str = "binance") -> int:
    """
    获取币安USDT永续合约的数量

    参数:
        exchange: 交易所名称, 默认为 "binance"

    返回:
        USDT永续合约数量
    """
    mapping = 创建币安符号映射(exchange)
    return len(mapping)


def 列出所有币安永续合约(exchange: str = "binance") -> List[str]:
    """
    列出所有币安USDT永续合约交易对

    参数:
        exchange: 交易所名称, 默认为 "binance"

    返回:
        所有USDT永续合约交易对列表(已排序)
    """
    mapping = 创建币安符号映射(exchange)
    return sorted(mapping.keys())


# 统一符号获取：数据库 + CCXT 并集去重
def 获取统一币安永续符号列表(
    db_url: Optional[str] = None,
    exchange_in_db: str = "binance_futures_um",
    interval: str = "1m",
    ccxt_exchange: str = "binance",
) -> List[str]:
    """
    优先从数据库拉取实际有行情的符号，再与 CCXT 全集并集去重，统一返回 USDT 永续符号。
    """
    符号集合 = set()

    # 1) 数据库实际可用符号
    try:
        with 创建数据库操作器(db_url) as db:
            符号集合.update(db.获取符号列表(exchange_in_db, interval=interval))
    except Exception:
        # 数据库不可用时继续用 CCXT
        pass

    # 2) CCXT 全集
    try:
        ccxt符号 = 列出所有币安永续合约(ccxt_exchange)
        符号集合.update(ccxt符号)
    except Exception:
        pass

    # 3) 标准化（只保留 USDT 永续）
    结果 = []
    for sym in 符号集合:
        标准 = 标准化永续合约符号(sym)
        if 标准:
            # 数据库使用形如 BTCUSDT 的符号，去掉“-USDT-PERP”连字符
            标准 = 标准.replace("-USDT-PERP", "USDT").replace("/", "")
            结果.append(标准)

    return sorted(set(结果))
