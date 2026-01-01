#!/usr/bin/env bash
# 一键创建虚拟环境、安装依赖并启动 AI Telegram 机器人

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] 未检测到 python3，请先安装 Python 3.10+。" >&2
  exit 1
fi

VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[INFO] 创建虚拟环境: $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "[ERROR] 虚拟环境创建失败，未找到 $PYTHON" >&2
  exit 1
fi

echo "[INFO] 使用虚拟环境 Python: $PYTHON"

"$PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null

hash_file_from_req() {
  local req_file="$1"
  local hash
  hash=$("$PYTHON" - <<'PY' "$req_file"
import hashlib, pathlib, sys
path = pathlib.Path(sys.argv[1])
if path.exists():
    print(hashlib.sha256(path.read_bytes()).hexdigest())
else:
    print("")
PY
)
  echo "$hash"
}

install_reqs_if_needed() {
  local req_file="$1"
  local marker_file="$VENV_DIR/.requirements.$(basename "$req_file").sha256"
  if [[ -f "$req_file" ]]; then
    local new_hash
    new_hash=$(hash_file_from_req "$req_file")
    local old_hash=""
    [[ -f "$marker_file" ]] && old_hash="$(<"$marker_file")"
    if [[ "$new_hash" != "$old_hash" || -z "$old_hash" ]]; then
      echo "[INFO] 安装依赖: $req_file"
      "$PIP" install -r "$req_file"
      echo "$new_hash" > "$marker_file"
    else
      echo "[INFO] $req_file 无变化，跳过安装"
    fi
  fi
}

install_reqs_if_needed "$PROJECT_ROOT/requirements.txt"
install_reqs_if_needed "$PROJECT_ROOT/requirements-core.txt"
install_reqs_if_needed "$PROJECT_ROOT/requirements-binance.txt"

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  echo "[WARN] 未找到 .env 文件，请确保已导出 BOT_TOKEN 环境变量。"
fi

if ! command -v proxychains4 >/dev/null 2>&1; then
  echo "[ERROR] proxychains4 未安装，无法通过指定代理启动。" >&2
  exit 1
fi

echo "[INFO] 通过 proxychains4 启动 AI Telegram Bot..."
exec proxychains4 -q "$PYTHON" -m src.bot.bot "$@"
