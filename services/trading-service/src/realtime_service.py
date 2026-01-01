#!/usr/bin/env python3
"""
实时指标计算服务入口

基于定时轮询触发，K线周期闭合时自动计算指标。
复用现有的 Engine，0自写K线管理逻辑。
"""
import asyncio
import logging
import time
import sys
from pathlib import Path
from datetime import datetime, timezone

# 设置路径
SERVICE_ROOT = Path(__file__).parent
sys.path.insert(0, str(SERVICE_ROOT))

from config import config
from indicators import get_all_indicators

LOG = logging.getLogger("realtime_service")


class RealtimeIndicatorService:
    """
    实时指标计算服务
    
    按周期定时触发计算，对齐到K线闭合时间。
    """
    
    INTERVAL_SECONDS = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
        "1w": 604800,
    }
    
    def __init__(self, intervals: list = None, workers: int = 4):
        self.intervals = intervals or ["5m", "15m", "1h", "4h", "1d"]
        self.workers = workers
        self._last_trigger = {iv: 0 for iv in self.intervals}
        self._running = False
    
    def _get_next_trigger(self, interval: str) -> float:
        """计算下一个触发时间"""
        period = self.INTERVAL_SECONDS.get(interval, 300)
        now = time.time()
        # 对齐到周期边界 + 5秒延迟（等待数据写入）
        next_boundary = ((int(now) // period) + 1) * period + 5
        return next_boundary
    
    def _should_trigger(self, interval: str) -> bool:
        """检查是否应该触发"""
        period = self.INTERVAL_SECONDS.get(interval, 300)
        now = time.time()
        current_boundary = (int(now) // period) * period
        
        if current_boundary > self._last_trigger[interval]:
            self._last_trigger[interval] = current_boundary
            return True
        return False
    
    def _run_calculation(self, intervals: list):
        """运行指标计算"""
        import subprocess
        import sys
        
        cmd = [
            sys.executable, "-m", "src",
            "--intervals", ",".join(intervals),
            "--workers", str(self.workers),
        ]
        try:
            result = subprocess.run(
                cmd,
                cwd=SERVICE_ROOT.parent,
                env={**__import__("os").environ, "PYTHONPATH": str(SERVICE_ROOT)},
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                LOG.error(f"计算失败: {result.stderr}")
            else:
                # 提取关键日志
                for line in result.stdout.split("\n"):
                    if "计算完成" in line or "ERROR" in line:
                        LOG.info(line.strip())
        except subprocess.TimeoutExpired:
            LOG.error(f"计算超时: {intervals}")
        except Exception as e:
            LOG.error(f"计算失败: {e}")
    
    async def run(self):
        """运行服务"""
        self._running = True
        LOG.info(f"实时指标服务启动: 周期={self.intervals}, 进程数={self.workers}")
        
        # 启动时先跑一次
        LOG.info("启动时执行初始计算...")
        self._run_calculation(self.intervals)
        
        while self._running:
            for interval in self.intervals:
                if self._should_trigger(interval):
                    LOG.info(f"[{interval}] K线闭合，触发计算")
                    self._run_calculation([interval])
            
            await asyncio.sleep(1)
    
    def stop(self):
        self._running = False


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="实时指标计算服务")
    parser.add_argument("--intervals", type=str, default="5m,15m,1h,4h,1d", help="周期列表")
    parser.add_argument("--workers", type=int, default=4, help="并行进程数")
    args = parser.parse_args()
    
    intervals = [x.strip() for x in args.intervals.split(",")]
    
    service = RealtimeIndicatorService(
        intervals=intervals,
        workers=args.workers,
    )
    
    try:
        await service.run()
    except KeyboardInterrupt:
        LOG.info("收到停止信号")
        service.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    asyncio.run(main())
