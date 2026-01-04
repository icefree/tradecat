# Markets Service

全市场数据采集服务 - 支持加密货币、股票、期货、期权、外汇、债券、宏观经济

## 架构

采用 **Provider 模式** (参考 OpenBB Platform):

```
src/
├── core/              # 核心框架
│   ├── fetcher.py     # TET Pipeline 基类
│   └── registry.py    # Provider 注册表
│
├── models/            # 标准化数据模型
│   ├── candle.py      # K线
│   ├── ticker.py      # 行情
│   └── trade.py       # 成交
│
├── providers/         # 数据源适配器 (8个)
│   ├── ccxt/          # 加密货币 REST (100+ 交易所)
│   ├── cryptofeed/    # 加密货币 WebSocket
│   ├── akshare/       # A股/港股/期货/债券
│   ├── baostock/      # A股免费历史数据
│   ├── yfinance/      # 美股/港股/外汇
│   ├── fredapi/       # 美联储宏观数据
│   ├── quantlib/      # 期权/债券定价
│   └── openbb/        # 综合聚合 (降级备份)
│
├── storage/           # 存储层
│   └── timescale.py
│
└── collectors/        # 采集任务 (待实现)
```

## 依赖库

| 类别 | 库 | Stars | 免费 |
|:---|:---|---:|:---:|
| 加密货币 | ccxt | 33k | ✅ |
| 加密货币 | cryptofeed | 2.7k | ✅ |
| A股 | akshare | 15k | ✅ |
| A股 | baostock | 2k | ✅ |
| 美股 | yfinance | 14k | ✅ |
| 多源 | pandas-datareader | 3k | ✅ |
| 宏观 | fredapi | 官方 | ✅ |
| 定价 | QuantLib | 5k | ✅ |
| 聚合 | openbb | 35k | ⚠️ |

## 快速开始

```bash
# 初始化
cd services/markets-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 可选: 安装定价和聚合模块
pip install QuantLib openbb

# 测试
python -m src test --provider yfinance --symbol AAPL     # 美股
python -m src test --provider akshare --symbol 000001    # A股
python -m src test --provider baostock --symbol 000001   # A股(免费)
python -m src test --provider ccxt --symbol BTCUSDT      # 加密

# 期权定价
python -m src pricing
```

## 历史数据集

| 市场 | 数据源 | 链接 |
|:---|:---|:---|
| 加密货币 | Binance Vision | https://data.binance.vision/ |
| 加密货币 | 你的 HuggingFace | https://huggingface.co/datasets/123olp/binance-futures-ohlcv-2018-2026 |
| 美股 | Kaggle S&P 500 | https://www.kaggle.com/datasets/andrewmvd/sp-500-stocks |
| A股 | BaoStock API | 通过 baostock 库 |
| 宏观 | FRED | https://fred.stlouisfed.org/ |

## TET Pipeline

每个 Provider 实现 Transform-Extract-Transform 流程:

1. **Transform**: 验证并转换查询参数
2. **Extract**: 从数据源获取原始数据
3. **Transform**: 将原始数据转换为标准模型
