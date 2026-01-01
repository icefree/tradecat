#!/bin/bash
# 指标计算服务统一启动脚本
# 用法: ./start.sh [start|stop|status|restart|once]
# 模式: simple(默认轮询) / listener(数据库触发)
# bash
# cd to trading-service directory
# 
# ./scripts/start.sh          # 启动（轮询模式）
# ./scripts/start.sh stop     # 停止
# ./scripts/start.sh status   # 状态
# ./scripts/start.sh restart  # 重启
# ./scripts/start.sh once     # 一次性计算

cd "$(dirname "$0")/.."
mkdir -p pids logs

MODE="${MODE:-simple}"  # 默认简单轮询模式

# PID/日志文件
SIMPLE_PID="pids/simple_scheduler.pid"
SIMPLE_LOG="logs/simple_scheduler.log"
LISTENER_PID="pids/kline_listener.pid"
LISTENER_LOG="logs/kline_listener.log"
HEALTH_FILE="pids/listener_health"

activate() { source ../../.venv/bin/activate; }

start() {
    echo "=== 指标计算服务 (模式: $MODE) ==="
    
    if [ "$MODE" = "listener" ]; then
        # 数据库触发模式
        if [ -f "$LISTENER_PID" ] && kill -0 $(cat "$LISTENER_PID") 2>/dev/null; then
            echo "已在运行 (PID: $(cat $LISTENER_PID))"
            return
        fi
        activate
        nohup python3 -u src/kline_listener.py >> "$LISTENER_LOG" 2>&1 &
        echo $! > "$LISTENER_PID"
        echo "✓ 已启动 (PID: $!) 日志: $LISTENER_LOG"
    else
        # 简单轮询模式（默认）
        if [ -f "$SIMPLE_PID" ] && kill -0 $(cat "$SIMPLE_PID") 2>/dev/null; then
            echo "已在运行 (PID: $(cat $SIMPLE_PID))"
            return
        fi
        activate
        nohup python3 -u src/simple_scheduler.py >> "$SIMPLE_LOG" 2>&1 &
        echo $! > "$SIMPLE_PID"
        echo "✓ 已启动 (PID: $!) 日志: $SIMPLE_LOG"
    fi
}

stop() {
    local stopped=0
    for pid_file in "$SIMPLE_PID" "$LISTENER_PID"; do
        if [ -f "$pid_file" ]; then
            kill $(cat "$pid_file") 2>/dev/null && stopped=1
            rm -f "$pid_file"
        fi
    done
    rm -f "$HEALTH_FILE"
    [ $stopped -eq 1 ] && echo "✓ 已停止" || echo "未运行"
}

status() {
    local running=0
    if [ -f "$SIMPLE_PID" ] && kill -0 $(cat "$SIMPLE_PID") 2>/dev/null; then
        echo "✓ 轮询模式运行中 (PID: $(cat $SIMPLE_PID))"
        echo ""; tail -10 "$SIMPLE_LOG"
        running=1
    fi
    if [ -f "$LISTENER_PID" ] && kill -0 $(cat "$LISTENER_PID") 2>/dev/null; then
        echo "✓ 监听模式运行中 (PID: $(cat $LISTENER_PID))"
        [ -f "$HEALTH_FILE" ] && cat "$HEALTH_FILE" | python3 -m json.tool 2>/dev/null
        echo ""; tail -10 "$LISTENER_LOG"
        running=1
    fi
    [ $running -eq 0 ] && echo "✗ 未运行"
}

once() {
    echo "=== 一次性全量计算 ==="
    activate
    PYTHONPATH=src python3 -m indicator_service --intervals 1m,5m,15m,1h,4h,1d,1w
}

case "${1:-start}" in
    start)   start ;;
    stop)    stop ;;
    status)  status ;;
    restart) stop; sleep 1; start ;;
    once)    once ;;
    *)       echo "用法: $0 [start|stop|status|restart|once]"
             echo "环境变量: MODE=simple(默认) 或 MODE=listener" ;;
esac
