# Data Service 完整文档

- **版本**: v1.0
- **更新时间**: 2024-12-29
- **来源**: services/data-service/README.md + AGENTS.md
- **状态**: 当前

---

# Data Service

Binance 期货市场数据采集服务，提供 1m K线和 5m 期货指标的实时采集、历史补齐和缺口修复。

## 功能特性

- **实时 K 线采集** - WebSocket 订阅 600+ USDT 永续合约 1m K线
- **期货指标采集** - 5 分钟周期采集持仓量、多空比、主动买卖比等
- **智能数据补齐** - ZIP 历史下载 + REST API 分页补齐
- **自动缺口修复** - 周期巡检 + 启动时补齐
- **IP Ban 保护** - 自动检测封禁并等待解除
- **全局限流** - 跨进程共享限流器，防止触发 Binance 限制

## 目录结构

```
services/data-service/
├── src/
│   ├── adapters/              # 外部服务适配层
│   │   ├── ccxt.py            # 交易所 API + Ban 检测
│   │   ├── shared_limiter.py  # 跨进程共享限流器
│   │   ├── cryptofeed.py      # WebSocket 适配器
│   │   ├── timescale.py       # TimescaleDB 适配器 (COPY 批量写入)
│   │   └── metrics.py         # 监控指标单例
│   ├── collectors/            # 数据采集器
│   │   ├── ws.py              # WebSocket K线采集
│   │   ├── metrics.py         # 期货指标采集器
│   │   ├── metrics_loop.py    # 指标采集主循环 (对齐5分钟整点)
│   │   └── backfill.py        # 数据补齐系统 (ZIP + REST)
│   └── config.py              # 配置管理
├── scripts/
│   ├── start.sh               # 服务启动脚本
│   └── ctl.sh                 # 控制脚本
├── logs/                      # 运行日志
├── pids/                      # 进程 PID 文件
├── tests/                     # 测试目录
├── pyproject.toml             # 项目配置
└── .env                       # 环境变量（不提交）
```

## 快速开始

### 环境要求

- Python >= 3.10
- TimescaleDB (PostgreSQL, 端口 5433)
- 代理服务 (默认 127.0.0.1:9910)

### 安装依赖

```bash
cd services/data-service

# 使用 pip
pip install cryptofeed>=2.4.0 ccxt>=4.0.0 psycopg[binary]>=3.1 psycopg-pool>=3.1 \
    duckdb>=0.9.0 python-dotenv>=1.0.0 requests>=2.28.0

# 或使用 pyproject.toml
pip install -e .

# 开发依赖
pip install -e ".[dev]"
```

### 启动服务

#### 方式一：使用启动脚本（推荐）

```bash
# 启动全部服务
./scripts/start.sh start

# 启动单个服务
./scripts/start.sh ws        # WebSocket K线采集
./scripts/start.sh metrics   # Metrics 采集
./scripts/start.sh backfill  # 数据补齐

# 查看状态
./scripts/start.sh status

# 停止服务
./scripts/start.sh stop
```

#### 方式二：手动启动

```bash
cd services/data-service

# 1. WebSocket K线采集（需要代理）
HTTP_PROXY=http://127.0.0.1:9910 HTTPS_PROXY=http://127.0.0.1:9910 \
nohup python3 -m src.collectors.ws > logs/ws.log 2>&1 &

# 2. 期货指标采集（对齐5分钟整点）
nohup python3 -m src.collectors.metrics_loop > logs/metrics.log 2>&1 &

# 3. 数据补齐
nohup python3 -m src.collectors.backfill --all --workers 2 > logs/backfill.log 2>&1 &
```

### 停止服务

```bash
pkill -f "src.collectors"
```

## 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql://opentd:OpenTD_pass@localhost:5433/market_data` | TimescaleDB 连接串 |
| `HTTP_PROXY` | `http://127.0.0.1:9910` | HTTP 代理地址 |
| `DATA_SERVICE_LOG_DIR` | `services/data-service/logs` | 日志目录 |
| `DATA_SERVICE_DATA_DIR` | `libs/database/csv` | 数据下载目录 |
| `KLINE_DB_SCHEMA` | `market_data` | 数据库 schema |
| `BINANCE_WS_DB_EXCHANGE` | `binance_futures_um` | 交易所标识 |
| `BINANCE_WS_CCXT_EXCHANGE` | `binance` | CCXT 交易所名 |
| `BINANCE_WS_GAP_INTERVAL` | `600` | 缺口巡检间隔（秒） |
| `BINANCE_WS_GAP_LOOKBACK` | `10080` | 缺口回溯时间（分钟） |
| `BINANCE_WS_SOURCE` | `binance_ws` | 数据来源标识 |

### 配置文件示例 (.env)

```bash
DATABASE_URL=postgresql://opentd:OpenTD_pass@localhost:5433/market_data
HTTP_PROXY=http://127.0.0.1:9910
KLINE_DB_SCHEMA=market_data
```

## 数据表

| 表名 | 说明 | 主键 |
|------|------|------|
| `market_data.candles_1m` | 1分钟K线 | (exchange, symbol, bucket_ts) |
| `market_data.binance_futures_metrics_5m` | 5分钟期货指标 | (symbol, create_time) |

## 常用命令

```bash
# 数据补齐（指定回溯天数和并发数）
python3 -m src.collectors.backfill --all --lookback 7 --workers 2

# 仅补齐 K 线
python3 -m src.collectors.backfill --klines --lookback 3

# 仅补齐 Metrics
python3 -m src.collectors.backfill --metrics --lookback 3

# 查看日志
tail -f logs/ws.log
tail -f logs/metrics.log
tail -f logs/backfill.log
```

## 性能指标

| 操作 | 速度 |
|------|------|
| ZIP 月度下载 | ~17,280 rows/sec |
| ZIP 日度下载 | ~2,286 rows/sec |
| REST API | ~300 rows/sec |
| DB COPY 写入 | ~11,000 rows/sec |

## 限流策略

- **跨进程共享限流器**: 2000 请求/分钟（Binance USDT-M 期货限制 2400/min 的 83%）
- 实现: `src/adapters/shared_limiter.py`（文件锁 + 令牌桶）
- 状态文件: `logs/.rate_limit_state`
- 环境变量: `RATE_LIMIT_PER_MINUTE` 可覆盖默认值
- IP Ban 自动检测和等待（解析 ban 解除时间戳）

## 补齐策略

1. **历史月份** → 优先月度 ZIP，失败降级日度 ZIP
2. **当月数据** → 直接日度 ZIP（月度 ZIP 未生成）
3. **小缺口** → REST API 分页补齐
4. **实时缺口** → WebSocket 周期巡检（10分钟）

---

# AI Agent 指南

## 1. Mission & Scope（目标与边界）

### 允许的操作
- 修改 `src/` 下的业务代码
- 添加新的采集器到 `src/collectors/`
- 添加新的适配器到 `src/adapters/`
- 修改 `scripts/` 下的运维脚本
- 更新 `tests/` 下的测试代码

### 禁止的操作
- **禁止修改** `.env` 中的生产凭证
- **禁止修改** `DATABASE_URL` 中的密码（除非明确要求）
- **禁止删除** 现有的限流逻辑（`shared_limiter`, `_check_and_wait_ban`）
- **禁止** 在代码中硬编码 API 密钥或代理凭证
- **禁止** 大范围重构除非任务明确要求

### 敏感区域（修改需谨慎）
- `src/adapters/shared_limiter.py` - 跨进程共享限流器
- `src/adapters/ccxt.py` - Ban 检测逻辑
- `src/adapters/timescale.py` - 数据库连接池配置
- `src/config.py` - 默认配置值

---

## 2. Golden Path（推荐执行路径）

```bash
# 1. 进入项目目录
cd services/data-service

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 验证语法
python3 -m py_compile src/adapters/ccxt.py src/collectors/backfill.py

# 4. 运行测试（如有）
pytest tests/ -v

# 5. 代码检查
ruff check src/

# 6. 修改代码...

# 7. 再次验证
python3 -m py_compile <修改的文件>
ruff check src/

# 8. 更新文档（如有变更）
# 同步更新 README.md 和 AGENTS.md

# 9. 提交
git add -A
git commit -m "<type>(<scope>): <description>"
```

---

## 3. Must-Run Commands（必须执行的命令清单）

### 环境准备
```bash
cd services/data-service
pip install -e ".[dev]"
```

### 语法验证（修改后必须执行）
```bash
python3 -m py_compile src/adapters/ccxt.py src/collectors/backfill.py src/collectors/metrics.py
```

### 代码检查
```bash
ruff check src/
mypy src/
```

### 服务启动（测试）
```bash
# 检查代理
curl -x http://127.0.0.1:9910 https://fapi.binance.com/fapi/v1/ping

# 启动服务
./scripts/start.sh start

# 检查状态
./scripts/start.sh status

# 查看日志
tail -f logs/ws.log
```

### 服务停止
```bash
pkill -f "src.collectors"
```

---

## 4. Code Change Rules（修改约束）

### 架构原则
- **适配器层** (`adapters/`) - 只负责外部服务交互，不含业务逻辑
- **采集器层** (`collectors/`) - 业务逻辑，调用适配器
- **配置层** (`config.py`) - 所有可配置项集中管理

### 依赖添加规则
- 新依赖必须添加到 `pyproject.toml` 的 `dependencies`
- 开发依赖添加到 `[project.optional-dependencies].dev`

### 限流约束
- 所有 Binance API 调用必须经过 `shared_acquire()` 或 `async_shared_acquire()`
- 请求前必须调用 `_check_and_wait_ban()`
- 禁止绕过共享限流器直接调用 API

### 数据库约束
- 批量写入使用 `upsert_candles()` / `upsert_metrics()`
- 禁止使用 `executemany`，必须使用 COPY 协议

### 当月数据约束
- 禁止尝试下载当月的月度 ZIP（未生成）
- 当月数据必须使用日度 ZIP 或 REST API

---

## 5. Style & Quality（风格与质量标准）

### 格式化工具
- **Linter**: ruff
- **Type Checker**: mypy
- **Line Length**: 120 (来源: `pyproject.toml`)

### 命名约定
- 类名: `PascalCase`
- 函数/变量: `snake_case`
- 常量: `UPPER_SNAKE_CASE`
- 私有成员: `_leading_underscore`

### 日志规范
```python
import logging
logger = logging.getLogger(__name__)

logger.info("操作完成: %d 条", count)
logger.warning("警告: %s", message)
logger.error("错误: %s", error)
```

### 错误处理
- 网络错误必须重试（使用 `@retry` 装饰器）
- Ban 错误必须等待后重试
- 数据库错误记录日志后继续

---

## 6. Project Map（项目结构速览）

```
src/
├── adapters/                 # 外部服务适配层
│   ├── shared_limiter.py    # [核心] 跨进程共享限流器 (2000/min)
│   ├── ccxt.py              # [核心] 交易所 API + Ban 检测
│   │   ├── _check_and_wait_ban()  # Ban 检测
│   │   ├── load_symbols()   # 加载交易对
│   │   └── fetch_ohlcv()    # 获取 K 线
│   ├── cryptofeed.py        # WebSocket 适配器
│   ├── timescale.py         # [核心] 数据库适配器
│   │   ├── upsert_candles() # K 线批量写入
│   │   └── upsert_metrics() # 指标批量写入
│   └── metrics.py           # 监控指标单例
├── collectors/              # 数据采集器
│   ├── ws.py               # [入口] WebSocket K线采集
│   ├── metrics.py          # 期货指标采集器
│   ├── metrics_loop.py     # [入口] 指标采集主循环
│   └── backfill.py         # [入口] 数据补齐系统
│       ├── GapScanner      # 缺口扫描
│       ├── ZipBackfiller   # ZIP 下载补齐
│       └── RestBackfiller  # REST API 补齐
└── config.py               # 配置管理
```

### 入口文件
- `python3 -m src.collectors.ws` - WebSocket 采集
- `python3 -m src.collectors.metrics_loop` - Metrics 采集
- `python3 -m src.collectors.backfill` - 数据补齐

---

## 7. Common Pitfalls（常见坑与修复）

### IP 被 Ban
**现象**: 日志出现 `418 I'm a teapot` 或 `429 Too Many Requests`
**原因**: 请求频率超过 Binance 限制
**修复**: 系统自动等待 ban 解除；如需手动，等待日志中的时间戳后重启

### WebSocket 连接失败
**现象**: `未加载到交易对`
**原因**: 代理未设置或不可用
**修复**: 
```bash
export HTTP_PROXY=http://127.0.0.1:9910
export HTTPS_PROXY=http://127.0.0.1:9910
```

### 当月 ZIP 下载失败
**现象**: 月度 ZIP 404
**原因**: Binance 当月数据未生成月度 ZIP
**修复**: 代码已处理，自动降级到日度 ZIP

### 数据库连接超时
**现象**: `connection timeout`
**原因**: 连接池耗尽或数据库负载高
**修复**: 检查 `timescale.py` 中的 `pool_max` 配置

---

## 8. PR / Commit Rules（提交与 CI 规则）

### Commit Message 规范
```
<type>(<scope>): <description>

[optional body]
```

**Type**:
- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 重构
- `docs`: 文档更新
- `chore`: 杂项

**Scope**: `data-service`, `adapters`, `collectors`, `config`

**示例**:
```
feat(collectors): 添加期货资金费率采集
fix(adapters): 修复 Ban 检测时间解析
docs(data-service): 更新 README 配置说明
```

### 分支策略
- `main` / `pro`: 生产分支，禁止直接推送
- `feature/*`: 功能分支
- `fix/*`: 修复分支

---

## 数据流

```
Binance API
    │
    ├─── WebSocket ──→ ws.py ──→ 时间窗口缓冲 ──→ TimescaleDB (candles_1m)
    │
    ├─── REST API ──→ metrics.py ──→ 批量写入 ──→ TimescaleDB (metrics_5m)
    │
    └─── ZIP Files ──→ backfill.py ──→ COPY 写入 ──→ TimescaleDB
```

## 数据库表结构

### candles_1m
```sql
CREATE TABLE market_data.candles_1m (
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    bucket_ts TIMESTAMPTZ NOT NULL,
    open NUMERIC(38,12) NOT NULL,
    high NUMERIC(38,12) NOT NULL,
    low NUMERIC(38,12) NOT NULL,
    close NUMERIC(38,12) NOT NULL,
    volume NUMERIC(38,12) NOT NULL,
    quote_volume NUMERIC(38,12),
    trade_count BIGINT,
    is_closed BOOLEAN DEFAULT FALSE,
    source TEXT DEFAULT 'binance_ws',
    taker_buy_volume NUMERIC(38,12),
    taker_buy_quote_volume NUMERIC(38,12),
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (exchange, symbol, bucket_ts)
);
```

### binance_futures_metrics_5m
```sql
CREATE TABLE market_data.binance_futures_metrics_5m (
    create_time TIMESTAMP NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT DEFAULT 'binance_futures_um',
    sum_open_interest NUMERIC,
    sum_open_interest_value NUMERIC,
    count_toptrader_long_short_ratio NUMERIC,
    sum_toptrader_long_short_ratio NUMERIC,
    count_long_short_ratio NUMERIC,
    sum_taker_long_short_vol_ratio NUMERIC,
    source TEXT DEFAULT 'binance_zip',
    is_closed BOOLEAN DEFAULT TRUE,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, create_time)
);
```

## Troubleshooting

### IP 被 Ban (418/429 错误)

```
Way too many requests; IP banned until ...
```

**解决方案**：系统会自动检测并等待 ban 解除。如需手动处理：
1. 查看日志中的 ban 解除时间
2. 等待后重启服务
3. 降低并发：`--workers 1`

### WebSocket 连接失败

```
未加载到交易对
```

**解决方案**：
1. 检查代理是否正常：`curl -x http://127.0.0.1:9910 https://fapi.binance.com/fapi/v1/ping`
2. 确保设置了 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量

### 数据库连接失败

**解决方案**：
1. 检查 TimescaleDB 是否运行：`pg_isready -h localhost -p 5433`
2. 验证连接串：`psql $DATABASE_URL -c "SELECT 1"`

## 监控指标

通过 `adapters/metrics.py` 收集：

| 指标 | 说明 |
|------|------|
| `requests_total` | 总请求数 |
| `requests_failed` | 失败请求数 |
| `rows_written` | 写入行数 |
| `gaps_found` | 发现缺口数 |
| `gaps_filled` | 填充缺口数 |
| `zip_downloads` | ZIP 下载数 |
