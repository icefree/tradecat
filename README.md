<p align="center">
  <img src="https://github.com/tukuaiai.png" alt="TradeCat" width="100px">
</p>

<div align="center">

# 🐱 TradeCat

**加密货币数据采集 → 指标计算 → Bot 推送 全流程平台**

[English](README_EN.md) | 简体中文

---

<p>
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/TimescaleDB-时序数据库-orange?style=for-the-badge&logo=postgresql&logoColor=white" alt="TimescaleDB">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

<p>
  <a href="https://t.me/tradecat_ai_channel"><img src="https://img.shields.io/badge/Telegram-频道-blue?style=flat-square&logo=telegram" alt="Telegram"></a>
  <a href="https://t.me/glue_coding"><img src="https://img.shields.io/badge/Telegram-交流群-blue?style=flat-square&logo=telegram" alt="交流群"></a>
  <a href="https://x.com/123olp"><img src="https://img.shields.io/badge/Twitter-@123olp-black?style=flat-square&logo=x" alt="Twitter"></a>
</p>

</div>

---

## 这是什么

一个完整的加密货币数据平台，从数据采集到用户交互的全链路：

```
币安 API → 数据采集 → TimescaleDB → 指标计算 → SQLite → Telegram Bot → 用户
```

**核心能力**：
- 实时 WebSocket K线采集 + 期货指标
- 技术指标批量计算（RSI/MACD/布林带/K线形态等）
- Telegram Bot 交互查询 + 信号推送

---

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                        币安交易所                            │
│              WebSocket K线  │  REST 期货指标                 │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                      data-service                           │
│         历史回填 │ 实时采集 │ 期货指标                        │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                      TimescaleDB                            │
│              K线数据 (candles_1m) │ 期货数据                 │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    trading-service                          │
│           指标计算引擎 │ 定时调度 │ 高优先级筛选              │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                   SQLite (market_data.db)                   │
│                      指标计算结果                            │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                   telegram-service                          │
│         排行榜卡片 │ 信号检测 │ Bot 交互                     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
                        Telegram 用户
```

### 服务职责

| 服务 | 职责 |
|:---|:---|
| **data-service** | WebSocket K线采集、期货指标采集、历史回填 |
| **trading-service** | 技术指标计算、高优先级币种筛选、定时调度 |
| **telegram-service** | Bot 交互、排行榜、信号推送 |
| **order-service** | 交易执行（开发中） |

---

## 快速开始

### 🤖 AI 一键安装（推荐）

复制提示词到 **Claude / ChatGPT**，AI 生成安装脚本：

<details>
<summary><strong>📋 点击展开安装提示词</strong></summary>

```
生成一个 TradeCat 全自动安装脚本，要求：

1. 系统: Ubuntu 22.04/24.04
2. 安装: TimescaleDB 2.x + TA-Lib + Python 3.10+
3. 项目: github.com/tukuaiai/tradecat
4. 数据库: postgres/postgres@localhost:5432/market_data

脚本要求：
- 一个 bash 脚本，复制执行即可
- 自动检测已安装的组件，跳过
- 每步有清晰的进度提示
- 最后输出验证结果
- 出错时显示具体原因

脚本结构：
1. 检查系统
2. 安装系统依赖
3. 安装 TimescaleDB
4. 创建数据库
5. 安装 TA-Lib
6. 克隆项目到 ~/.projects/tradecat
7. 运行 ./scripts/init.sh
8. 验证安装

直接输出完整脚本，不要解释。
```

</details>

执行：

```bash
chmod +x install_tradecat.sh && ./install_tradecat.sh
```

### 🪟 Windows WSL2 用户

先配置 `.wslconfig`：

```powershell
notepad "$env:USERPROFILE\.wslconfig"
```

```ini
[wsl2]
memory=10GB
processors=6
swap=12GB
networkingMode=mirrored
```

重启：`wsl --shutdown`

### ⚙️ 配置

```bash
vim ~/.projects/tradecat/services/telegram-service/config/.env
```

```ini
TELEGRAM_BOT_TOKEN=你的Token
HTTPS_PROXY=http://127.0.0.1:7890  # 如需代理
```

### 🎬 启动

```bash
cd ~/.projects/tradecat
./scripts/start.sh daemon    # 启动
./scripts/start.sh status    # 状态
```

---

<details>
<summary><strong>📖 手动安装</strong></summary>

```bash
# 1. 系统依赖
sudo apt install -y build-essential python3-dev python3-pip python3-venv

# 2. TA-Lib
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz && cd ta-lib
./configure --prefix=/usr && make && sudo make install
cd .. && rm -rf ta-lib*

# 3. 项目
git clone https://github.com/tukuaiai/tradecat.git ~/.projects/tradecat
cd ~/.projects/tradecat && ./scripts/init.sh

# 4. 启动
./scripts/start.sh daemon
```

</details>

---

## 目录结构

```
tradecat/
├── services/
│   ├── data-service/        # 数据采集
│   ├── trading-service/     # 指标计算
│   ├── telegram-service/    # Telegram Bot
│   └── order-service/       # 交易执行
├── libs/
│   ├── database/            # SQLite 数据
│   └── common/              # 共享工具
├── scripts/                 # 启动/初始化脚本
├── config/                  # 全局配置
└── backups/                 # 数据备份
```

---

## 运维

```bash
# 服务管理
./scripts/start.sh daemon       # 启动 + 守护
./scripts/start.sh status       # 状态
./scripts/start.sh daemon-stop  # 停止

# 日志
tail -f services/telegram-service/logs/bot.log

# 验证
./scripts/verify.sh
```

---

## 历史数据

从 [HuggingFace](https://huggingface.co/datasets/123olp/binance-futures-ohlcv-2018-2026) 下载后导入：

```bash
zstd -d candles_1m.bin.zst -c | psql -d market_data \
    -c "COPY market_data.candles_1m FROM STDIN WITH (FORMAT binary)"
```

---

## 联系

- **Telegram 频道**: [@tradecat_ai_channel](https://t.me/tradecat_ai_channel)
- **交流群**: [@glue_coding](https://t.me/glue_coding)
- **Twitter**: [@123olp](https://x.com/123olp)

---

## 支持项目

- **币安 UID**: `572155580`
- **Tron (TRC20)**: `TQtBXCSTwLFHjBqTS4rNUp7ufiGx51BRey`
- **Solana**: `HjYhozVf9AQmfv7yv79xSNs6uaEU5oUk2USasYQfUYau`

---

## License

[MIT](LICENSE)
