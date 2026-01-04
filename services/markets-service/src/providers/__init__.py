"""Providers 模块 - 数据源适配器"""
# 导入时自动注册到 ProviderRegistry

# 加密货币
from . import ccxt
from . import cryptofeed

# A股/国内
from . import akshare
from . import baostock

# 美股/全球
from . import yfinance

# 宏观经济
from . import fredapi

# 衍生品定价
from . import quantlib

# 综合聚合 (降级备份)
from . import openbb

__all__ = [
    "ccxt", "cryptofeed",
    "akshare", "baostock", 
    "yfinance",
    "fredapi",
    "quantlib",
    "openbb",
]
