"""布林带指标"""
import numpy as np
import pandas as pd
from ..base import Indicator, IndicatorMeta, register


@register
class Bollinger(Indicator):
    meta = IndicatorMeta(name="布林带扫描器.py", lookback=30, is_incremental=False)
    
    def compute(self, df: pd.DataFrame, symbol: str, interval: str) -> pd.DataFrame:
        if len(df) < 21:
            return pd.DataFrame()
        close = df["close"]
        mid = close.rolling(20).mean()
        std = close.rolling(20).std()
        upper = mid + 2 * std
        lower = mid - 2 * std
        m, u, l = float(mid.iloc[-1]), float(upper.iloc[-1]), float(lower.iloc[-1])
        if any(map(np.isnan, [m, u, l])) or m == 0:
            return pd.DataFrame()
        bandwidth = (u - l) / m * 100
        pct_b = (float(close.iloc[-1]) - l) / (u - l) if u != l else 0
        half = max(1, 10)
        slope = (m - float(mid.iloc[-half])) / half
        quote = df.get("quote_volume", df["volume"] * df["close"])
        turnover = float(quote.iloc[-1]) if not pd.isna(quote.iloc[-1]) else 0
        return self._make_result(df, symbol, interval, {
            "带宽": round(bandwidth, 4),
            "中轨斜率": round(slope, 6),
            "中轨价格": round(m, 6),
            "上轨价格": round(u, 6),
            "下轨价格": round(l, 6),
            "百分比b": round(pct_b, 4),
            "价格": float(close.iloc[-1]),
            "成交额": turnover,
        })
