"""
K线管理器 - 基于 Redis Pub/Sub 的实时触发

复用 data-service 的数据，K线闭合时触发指标计算。
0自写K线管理逻辑，完全复用现有基础设施。
"""
import asyncio
import logging
import time
import json
from datetime import datetime, timezone
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
import redis.asyncio as aioredis

LOG = logging.getLogger("kline_manager")


@dataclass
class KlineEvent:
    """K线闭合事件"""
    symbol: str
    interval: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class KlineManager:
    """
    K线管理器
    
    监听 Redis 的 K线闭合事件，触发回调。
    data-service 已经在做K线采集，这里只负责监听和触发。
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self._callbacks: Dict[str, List[Callable]] = {}  # interval -> callbacks
        self._running = False
    
    async def connect(self):
        """连接 Redis"""
        self._redis = await aioredis.from_url(self.redis_url)
        LOG.info(f"已连接 Redis: {self.redis_url}")
    
    def on_kline_close(self, interval: str, callback: Callable[[KlineEvent], None]):
        """
        注册K线闭合回调
        
        Args:
            interval: 周期 (1m, 5m, 15m, 1h, 4h, 1d, 1w)
            callback: 回调函数，接收 KlineEvent
        """
        if interval not in self._callbacks:
            self._callbacks[interval] = []
        self._callbacks[interval].append(callback)
        LOG.info(f"注册回调: {interval} -> {callback.__name__}")
    
    async def start(self):
        """启动监听"""
        if not self._redis:
            await self.connect()
        
        self._running = True
        pubsub = self._redis.pubsub()
        
        # 订阅所有周期的K线闭合频道
        channels = [f"kline:close:{iv}" for iv in self._callbacks.keys()]
        if channels:
            await pubsub.subscribe(*channels)
            LOG.info(f"订阅频道: {channels}")
        
        # 同时启动定时轮询（兜底）
        asyncio.create_task(self._poll_loop())
        
        # 监听消息
        async for message in pubsub.listen():
            if not self._running:
                break
            if message["type"] == "message":
                await self._handle_message(message)
    
    async def _handle_message(self, message: dict):
        """处理 Redis 消息"""
        try:
            channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
            data = json.loads(message["data"])
            
            # 解析频道: kline:close:5m
            parts = channel.split(":")
            if len(parts) >= 3:
                interval = parts[2]
                event = KlineEvent(
                    symbol=data["symbol"],
                    interval=interval,
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    open=float(data["open"]),
                    high=float(data["high"]),
                    low=float(data["low"]),
                    close=float(data["close"]),
                    volume=float(data["volume"]),
                )
                await self._trigger_callbacks(interval, event)
        except Exception as e:
            LOG.error(f"处理消息失败: {e}")
    
    async def _trigger_callbacks(self, interval: str, event: KlineEvent):
        """触发回调"""
        callbacks = self._callbacks.get(interval, [])
        for cb in callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event)
                else:
                    cb(event)
            except Exception as e:
                LOG.error(f"回调执行失败 {cb.__name__}: {e}")
    
    async def _poll_loop(self):
        """
        定时轮询（兜底机制）
        
        如果 Redis Pub/Sub 没有消息，按周期定时触发
        """
        interval_seconds = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
            "1w": 604800,
        }
        
        last_trigger = {iv: 0 for iv in self._callbacks.keys()}
        
        while self._running:
            now = time.time()
            for interval in self._callbacks.keys():
                period = interval_seconds.get(interval, 300)
                # 检查是否到了触发时间
                if now - last_trigger[interval] >= period:
                    # 对齐到周期边界
                    aligned = int(now // period) * period
                    if aligned > last_trigger[interval]:
                        last_trigger[interval] = aligned
                        LOG.debug(f"定时触发: {interval}")
                        # 创建虚拟事件（实际数据从数据库读取）
                        event = KlineEvent(
                            symbol="*",  # 表示所有币种
                            interval=interval,
                            timestamp=datetime.fromtimestamp(aligned, timezone.utc),
                            open=0, high=0, low=0, close=0, volume=0,
                        )
                        await self._trigger_callbacks(interval, event)
            
            await asyncio.sleep(1)
    
    async def stop(self):
        """停止"""
        self._running = False
        if self._redis:
            await self._redis.close()


# === 集成你的指标计算 ===

async def run_indicator_service():
    """
    运行指标计算服务
    
    K线闭合时自动触发计算
    """
    import sys
    import os
    from pathlib import Path
    
    # 添加路径
    service_root = Path(__file__).parent
    if str(service_root) not in sys.path:
        sys.path.insert(0, str(service_root))
    
    # 设置环境变量让相对导入工作
    os.chdir(service_root.parent)
    
    # 直接导入引擎模块
    import importlib.util
    spec = importlib.util.spec_from_file_location("engine", service_root / "core" / "engine.py")
    engine_module = importlib.util.module_from_spec(spec)
    
    # 先导入依赖
    from config import config
    from db import reader, writer
    from indicators import get_all_indicators
    
    manager = KlineManager()
    
    def run_calculation(intervals: List[str]):
        """运行指标计算"""
        from core.engine import Engine
        Engine(intervals=intervals, max_workers=4).run(mode="all")
    
    def on_5m_close(event: KlineEvent):
        """5分钟K线闭合"""
        LOG.info(f"5m K线闭合触发计算")
        run_calculation(["5m"])
    
    def on_15m_close(event: KlineEvent):
        """15分钟K线闭合"""
        LOG.info(f"15m K线闭合触发计算")
        run_calculation(["15m"])
    
    def on_1h_close(event: KlineEvent):
        """1小时K线闭合"""
        LOG.info(f"1h K线闭合触发计算")
        run_calculation(["1h"])
    
    def on_4h_close(event: KlineEvent):
        """4小时K线闭合"""
        LOG.info(f"4h K线闭合触发计算")
        run_calculation(["4h"])
    
    def on_1d_close(event: KlineEvent):
        """日线闭合"""
        LOG.info(f"1d K线闭合触发计算")
        run_calculation(["1d"])
    
    # 注册回调
    manager.on_kline_close("5m", on_5m_close)
    manager.on_kline_close("15m", on_15m_close)
    manager.on_kline_close("1h", on_1h_close)
    manager.on_kline_close("4h", on_4h_close)
    manager.on_kline_close("1d", on_1d_close)
    
    LOG.info("指标计算服务启动，等待K线闭合事件...")
    await manager.start()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    asyncio.run(run_indicator_service())
