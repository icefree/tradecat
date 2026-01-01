#!/bin/bash
# tradecat Pro 全服务守护进程
# 用法: ./scripts/daemon.sh [start|stop|status]

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DAEMON_PID="$ROOT/daemon.pid"
DAEMON_LOG="$ROOT/daemon.log"
TELEGRAM_PID="$ROOT/services/telegram-service/pids/bot.pid"

check_data_service() {
    cd "$ROOT/services/data-service"
    for name in backfill metrics ws; do
        pid_file="pids/${name}.pid"
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if ! kill -0 "$pid" 2>/dev/null; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] data-service/$name 挂了，重启..."
                ./scripts/start.sh "$name"
            fi
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] data-service/$name 未启动，启动..."
            ./scripts/start.sh "$name"
        fi
    done
}

check_trading_service() {
    cd "$ROOT/services/trading-service"
    pid_file="pids/simple_scheduler.pid"
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] trading-service 挂了，重启..."
            ./scripts/start.sh start
        fi
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] trading-service 未启动，启动..."
        ./scripts/start.sh start
    fi
}

check_telegram_service() {
    cd "$ROOT/services/telegram-service"
    mkdir -p pids
    
    # 用 PID 文件检测，避免重复启动
    if [ -f "$TELEGRAM_PID" ]; then
        pid=$(cat "$TELEGRAM_PID")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # 正常运行
        fi
    fi
    
    # 检查是否有进程在运行但没有 PID 文件
    existing=$(pgrep -f "python3 -m src.crypto_trading_bot" | head -1)
    if [ -n "$existing" ]; then
        echo "$existing" > "$TELEGRAM_PID"
        return 0
    fi
    
    # 启动（设置代理）
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] telegram-service 未运行，启动..."
    export HTTPS_PROXY=http://127.0.0.1:9910
    export HTTP_PROXY=http://127.0.0.1:9910
    PYTHONPATH=src nohup python3 -m src.crypto_trading_bot > logs/bot.log 2>&1 &
    echo $! > "$TELEGRAM_PID"
}

daemon_loop() {
    echo "=== tradecat Pro 守护进程启动 ==="
    echo "检查间隔: 30秒"
    while true; do
        check_data_service
        check_trading_service
        check_telegram_service
        sleep 30
    done
}

case "$1" in
    start)
        if [ -f "$DAEMON_PID" ] && kill -0 "$(cat "$DAEMON_PID")" 2>/dev/null; then
            echo "守护进程已在运行 (PID: $(cat "$DAEMON_PID"))"
            exit 0
        fi
        nohup "$0" run >> "$DAEMON_LOG" 2>&1 &
        echo $! > "$DAEMON_PID"
        echo "守护进程已启动 (PID: $!)"
        ;;
    stop)
        if [ -f "$DAEMON_PID" ]; then
            kill "$(cat "$DAEMON_PID")" 2>/dev/null
            rm -f "$DAEMON_PID"
            echo "守护进程已停止"
        else
            echo "守护进程未运行"
        fi
        ;;
    status)
        if [ -f "$DAEMON_PID" ] && kill -0 "$(cat "$DAEMON_PID")" 2>/dev/null; then
            echo "守护进程运行中 (PID: $(cat "$DAEMON_PID"))"
        else
            echo "守护进程未运行"
        fi
        ;;
    run)
        daemon_loop
        ;;
    *)
        echo "用法: $0 {start|stop|status}"
        exit 1
        ;;
esac
