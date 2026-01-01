# tradecat

加密货币量化交易数据平台，提供实时数据采集、技术指标计算和 Telegram Bot 信号推送。

## 🎯 项目目标

为加密货币交易者提供：
- 实时市场数据采集（600+ 币种）
- 38 个技术指标自动计算
- Telegram Bot 信号推送与排行榜

## 📚 真源入口

**所有需求、设计、决策文档的唯一入口**：[docs/index.md](docs/index.md)

## 🏗️ 架构概览

```
data-service (数据采集) → trading-service (指标计算) → telegram-service (用户交互)
```

| 服务 | 职责 | 文档 |
|------|------|------|
| data-service | WebSocket K线 + 期货指标采集 | [完整文档](docs/design/DESIGN-004-data-service完整文档.md) |
| trading-service | 32 个技术指标计算 | [完整文档](docs/design/DESIGN-006-trading-service完整文档.md) |
| telegram-service | Bot 交互 + 排行榜 | [完整文档](docs/design/DESIGN-005-telegram-service完整文档.md) |

## 🚀 快速开始

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 启动数据采集
cd services/data-service && ./scripts/start.sh start

# 3. 启动指标计算
cd services/trading-service && ./scripts/start.sh

# 4. 启动 Telegram Bot
cd services/telegram-service && python -m src.crypto_trading_bot
```

## ✅ 验收一键命令

```bash
# 运行所有验证（格式化、静态检查、测试）
./scripts/verify.sh
```

## 📖 协作指南

- [CONTRIBUTING.md](CONTRIBUTING.md) - 协作规则与提交规范
- [CHANGELOG.md](CHANGELOG.md) - 版本变更摘要
- [docs/index.md](docs/index.md) - 文档真源入口

## 📁 目录结构

```
tradecat/
├── services/
│   ├── data-service/       # 数据采集
│   ├── trading-service/    # 指标计算
│   └── telegram-service/   # Telegram Bot
├── libs/
│   ├── common/utils/       # 共享工具
│   └── database/           # 数据库 schema
├── docs/                   # 📚 单一真源文档中心
│   ├── index.md            # 文档入口
│   ├── requirements/       # 需求文档
│   ├── design/             # 设计文档
│   ├── decisions/adr/      # 架构决策记录
│   ├── prompts/            # AI 提示词模板
│   ├── sessions/           # 会话记录
│   └── retros/             # 迭代复盘
├── scripts/                # 脚本工具
└── .github/                # GitHub 配置
```

## 📜 License

MIT License
