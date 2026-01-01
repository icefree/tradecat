#!/usr/bin/env python3
"""
监听物化视图更新推送，触发指标计算

启动时:
1. 检查数据库连接
2. 检查各周期数据完整性
3. 执行一次全量计算

运行时:
- 监听 candle_update / metrics_update 推送
- 自动触发对应周期的指标计算
"""
import asyncio
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# 配置（从环境变量读取）
DB_URL = os.environ.get("DATABASE_URL", "postgresql://opentd:OpenTD_pass@localhost:5433/market_data")
TRADING_SERVICE_DIR = Path(os.environ.get("TRADING_SERVICE_DIR", str(Path(__file__).parent.parent)))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT_CALC", "10"))
HEALTH_FILE = TRADING_SERVICE_DIR / "pids" / "listener_health"

KLINE_INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
FUTURES_INTERVALS = ["5m", "15m", "1h", "4h", "1d", "1w"]

# 并发控制信号量
_semaphore: asyncio.Semaphore = None
# 统计
_stats = {"total": 0, "success": 0, "error": 0, "last_update": None}


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


async def check_db_connection() -> bool:
    """检查数据库连接"""
    try:
        async with await psycopg.AsyncConnection.connect(DB_URL) as conn:
            await conn.execute("SELECT 1")
        log("✓ 数据库连接正常")
        return True
    except Exception as e:
        log(f"✗ 数据库连接失败: {e}")
        return False


async def check_data_freshness() -> dict:
    """检查各周期数据新鲜度"""
    result = {"kline": {}, "futures": {}}
    
    async with await psycopg.AsyncConnection.connect(DB_URL, row_factory=dict_row) as conn:
        # K线数据 - 只查最新时间
        for interval in KLINE_INTERVALS:
            table = f"candles_{interval}"
            try:
                row = await (await conn.execute(f"""
                    SELECT bucket_ts as latest FROM market_data.{table}
                    ORDER BY bucket_ts DESC LIMIT 1
                """)).fetchone()
                
                if row and row["latest"]:
                    age = datetime.now(row["latest"].tzinfo) - row["latest"]
                    result["kline"][interval] = {"age_minutes": int(age.total_seconds() / 60)}
            except:
                pass
        
        # 期货数据
        try:
            row = await (await conn.execute("""
                SELECT create_time as latest FROM market_data.binance_futures_metrics_5m
                ORDER BY create_time DESC LIMIT 1
            """)).fetchone()
            
            if row and row["latest"]:
                age = datetime.now(row["latest"].tzinfo) - row["latest"]
                result["futures"]["5m"] = {"age_minutes": int(age.total_seconds() / 60)}
        except:
            pass
    
    return result


def print_data_status(data: dict):
    """打印数据状态"""
    log("数据状态:")
    
    for interval, info in data.get("kline", {}).items():
        age = info["age_minutes"]
        status = "✓" if age < 10 else "⚠"
        log(f"  {status} K线 {interval}: {age}分钟前")
    
    for interval, info in data.get("futures", {}).items():
        age = info["age_minutes"]
        status = "✓" if age < 10 else "⚠"
        log(f"  {status} 期货 {interval}: {age}分钟前")


def run_full_calculation():
    """执行全量计算"""
    log("执行全量指标计算...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    
    # K线指标
    log("  计算 K线指标 (全周期)...")
    subprocess.run(
        ["python3", "-m", "src", "--intervals", ",".join(KLINE_INTERVALS)],
        cwd=TRADING_SERVICE_DIR,
        env=env,
        capture_output=True
    )
    
    # 期货指标
    log("  计算 期货指标 (全周期)...")
    subprocess.run(
        ["python3", "-m", "src", "--intervals", ",".join(FUTURES_INTERVALS), "--mode", "futures"],
        cwd=TRADING_SERVICE_DIR,
        env=env,
        capture_output=True
    )
    
    log("✓ 全量计算完成")


async def run_calculation(interval: str, symbol: str, data_type: str):
    """执行单次指标计算（带并发控制）"""
    global _semaphore, _stats
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    _stats["total"] += 1
    
    async with _semaphore:
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        env["TEST_SYMBOLS"] = symbol
        
        mode = "kline" if data_type == "candle" else "futures"
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "-m", "src", "--intervals", interval, "--mode", mode,
                cwd=str(TRADING_SERVICE_DIR),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                _stats["success"] += 1
            else:
                _stats["error"] += 1
                if stderr:
                    log(f"计算错误 {symbol} {interval}: {stderr.decode()[:200]}")
                    
            _stats["last_update"] = datetime.now().isoformat()
            
        except Exception as e:
            _stats["error"] += 1
            log(f"计算异常 {symbol} {interval}: {e}")
            traceback.print_exc()


async def listen():
    """监听数据库推送"""
    conn = await psycopg.AsyncConnection.connect(DB_URL, autocommit=True)
    
    await conn.execute("LISTEN candle_1m_update")
    await conn.execute("LISTEN candle_update")
    await conn.execute("LISTEN metrics_5m_update")
    await conn.execute("LISTEN metrics_update")
    
    log("监听中... (等待数据推送)")
    
    async for notify in conn.notifies():
        try:
            data = json.loads(notify.payload)
            channel = notify.channel
            symbol = data["symbol"]
            
            if channel == "candle_1m_update":
                if data.get("is_closed"):
                    log(f"K线 1m {symbol}")
                    asyncio.create_task(run_calculation("1m", symbol, "candle"))
                    
            elif channel == "candle_update":
                interval = data["interval"]
                log(f"K线 {interval} {symbol}")
                asyncio.create_task(run_calculation(interval, symbol, "candle"))
                
            elif channel == "metrics_5m_update":
                if data.get("is_closed"):
                    log(f"期货 5m {symbol}")
                    asyncio.create_task(run_calculation("5m", symbol, "futures"))
                    
            elif channel == "metrics_update":
                interval = data["interval"]
                log(f"期货 {interval} {symbol}")
                asyncio.create_task(run_calculation(interval, symbol, "futures"))
                
        except Exception as e:
            log(f"解析错误: {e}")
            traceback.print_exc()


async def health_check_loop():
    """定期写入健康检查文件"""
    while True:
        try:
            HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
            HEALTH_FILE.write_text(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "stats": _stats,
                "status": "running"
            }))
        except Exception as e:
            log(f"健康检查写入失败: {e}")
        await asyncio.sleep(30)


async def db_reconnect_loop():
    """数据库断连自动重连"""
    while True:
        try:
            await listen()
        except psycopg.OperationalError as e:
            log(f"数据库连接断开: {e}")
            log("5秒后重连...")
            await asyncio.sleep(5)
        except Exception as e:
            log(f"监听异常: {e}")
            traceback.print_exc()
            await asyncio.sleep(5)


async def main():
    log("=" * 50)
    log("K线监听服务启动")
    log("=" * 50)
    
    # 1. 检查数据库
    if not await check_db_connection():
        sys.exit(1)
    
    # 2. 检查数据新鲜度
    data_status = await check_data_freshness()
    print_data_status(data_status)
    
    # 3. 启动时全量计算
    run_full_calculation()
    
    # 4. 开始监听（带健康检查和自动重连）
    log("-" * 50)
    await asyncio.gather(
        db_reconnect_loop(),
        health_check_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())

