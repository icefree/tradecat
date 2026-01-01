#!/bin/bash
# Data Service 启动 + 守护脚本
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$(pwd)
LOG_DIR="$ROOT/logs"
PID_DIR="$ROOT/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# ========== 启动函数 ==========
start_backfill() {
    echo -e "${GREEN}[1/3] 启动数据补齐...${NC}"
    PYTHONPATH=src nohup python3 -m collectors.backfill --all --lookback 7 \
        > "$LOG_DIR/backfill.log" 2>&1 &
    echo $! > "$PID_DIR/backfill.pid"
    echo "  PID: $(cat $PID_DIR/backfill.pid)"
}

start_metrics() {
    echo -e "${GREEN}[2/3] 启动 Metrics 采集...${NC}"
    PYTHONPATH=src nohup python3 -c "
import time, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from collectors.metrics import MetricsCollector
c = MetricsCollector()
while True:
    try:
        c.run_once()
    except Exception as e:
        logging.error('Metrics error: %s', e)
    time.sleep(300)
" > "$LOG_DIR/metrics.log" 2>&1 &
    echo $! > "$PID_DIR/metrics.pid"
    echo "  PID: $(cat $PID_DIR/metrics.pid)"
}

start_ws() {
    echo -e "${GREEN}[3/3] 启动 WebSocket 采集...${NC}"
    PYTHONPATH=src nohup python3 -m collectors.ws > "$LOG_DIR/ws.log" 2>&1 &
    echo $! > "$PID_DIR/ws.pid"
    echo "  PID: $(cat $PID_DIR/ws.pid)"
}

# ========== 控制函数 ==========
start_all() {
    start_backfill
    sleep 2
    start_metrics
    start_ws
    echo -e "\n${GREEN}全部启动完成${NC}"
}

stop_all() {
    echo "停止所有服务..."
    for pid_file in "$PID_DIR"/*.pid; do
        [ -f "$pid_file" ] || continue
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" && echo "  停止 PID $pid"
        fi
        rm -f "$pid_file"
    done
}

status() {
    echo "=== 服务状态 ==="
    for name in backfill metrics ws; do
        pid_file="$PID_DIR/${name}.pid"
        if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            echo -e "  ${GREEN}$name: 运行中 (PID $(cat $pid_file))${NC}"
        else
            echo -e "  ${RED}$name: 未运行${NC}"
        fi
    done
}

# ========== 守护进程 ==========
daemon() {
    echo -e "${YELLOW}=== 守护进程启动 (间隔30秒) ===${NC}"
    while true; do
        for name in backfill metrics ws; do
            pid_file="$PID_DIR/${name}.pid"
            if [ ! -f "$pid_file" ] || ! kill -0 "$(cat "$pid_file")" 2>/dev/null; then
                echo "[$(date '+%H:%M:%S')] $name 重启..."
                start_$name
            fi
        done
        sleep 30
    done
}

# ========== 入口 ==========
case "${1:-help}" in
    start)  start_all ;;
    stop)   stop_all ;;
    status) status ;;
    daemon) start_all; daemon ;;
    backfill|metrics|ws) start_$1 ;;
    *)
        echo "用法: $0 {start|stop|status|daemon|backfill|metrics|ws}"
        echo "  start   - 启动全部服务"
        echo "  stop    - 停止全部服务"
        echo "  status  - 查看状态"
        echo "  daemon  - 启动 + 守护（自动重启）"
        exit 1
        ;;
esac
