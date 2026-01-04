"""Cryptofeed WebSocket 流处理器"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Any

from cryptofeed import FeedHandler
from cryptofeed.defines import CANDLES, TRADES, L2_BOOK
from cryptofeed.exchanges import Binance


@dataclass
class CandleEvent:
    """K线事件"""
    exchange: str
    symbol: str
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool


class CryptoFeedStream:
    """Cryptofeed WebSocket 流 - 用于实时数据采集"""
    
    def __init__(self, exchange: str = "binance"):
        self.exchange = exchange
        self._handler: FeedHandler | None = None
        self._callbacks: dict[str, Callable] = {}
    
    def on_candle(self, callback: Callable[[CandleEvent], None]):
        """注册 K 线回调"""
        self._callbacks["candle"] = callback
    
    async def _candle_callback(self, candle, receipt_timestamp):
        """内部 K 线回调"""
        if "candle" in self._callbacks:
            event = CandleEvent(
                exchange=candle.exchange,
                symbol=candle.symbol,
                timestamp=candle.timestamp,
                open=float(candle.open),
                high=float(candle.high),
                low=float(candle.low),
                close=float(candle.close),
                volume=float(candle.volume),
                closed=candle.closed,
            )
            self._callbacks["candle"](event)
    
    def subscribe(self, symbols: list[str], channels: list[str] = None):
        """订阅交易对"""
        channels = channels or [CANDLES]
        
        self._handler = FeedHandler()
        
        # 根据交易所选择
        exchange_cls = Binance  # 可扩展其他交易所
        
        callbacks = {}
        if CANDLES in channels:
            callbacks[CANDLES] = self._candle_callback
        
        self._handler.add_feed(
            exchange_cls(
                symbols=symbols,
                channels=channels,
                callbacks=callbacks
            )
        )
    
    def run(self):
        """运行 (阻塞)"""
        if self._handler:
            self._handler.run()
    
    def stop(self):
        """停止"""
        if self._handler:
            self._handler.stop()
