"""
宽表数据库写入器 - 保留所有原始字段

表结构：每个(symbol, interval)一行，所有指标字段作为列
列名格式：{指标名}_{字段名}
"""
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Set

from ..config import config

# 所有指标及其字段（完整保留）
INDICATOR_FIELDS = {
    "MACD柱状扫描器": ["数据时间", "信号概述", "MACD", "MACD信号线", "MACD柱状图", "DIF", "DEA", "成交额", "当前价格"],
    "KDJ随机指标扫描器": ["数据时间", "J值", "K值", "D值", "信号概述", "成交额", "当前价格"],
    "ATR波幅扫描器": ["数据时间", "波动分类", "ATR百分比", "上轨", "中轨", "下轨", "成交额", "当前价格"],
    "G，C点扫描器": ["数据时间", "EMA7", "EMA25", "EMA99", "价格", "趋势方向", "带宽评分"],
    "OBV能量潮扫描器": ["数据时间", "OBV值", "OBV变化率"],
    "CVD信号排行榜": ["数据时间", "CVD值", "变化率"],
    "基础数据同步器": ["数据时间", "开盘价", "最高价", "最低价", "收盘价", "当前价格", "成交量", "成交额", "振幅", "变化率", "交易次数", "成交笔数", "主动买入量", "主动买量", "主动买额", "主动卖出量", "主动买卖比", "主动卖出额", "资金流向", "平均每笔成交额"],
    "主动买卖比扫描器": ["数据时间", "主动买量", "主动卖量", "主动买卖比", "价格"],
    "期货情绪元数据": ["数据时间", "持仓张数", "持仓金额", "大户多空比样本", "大户多空比总和", "全体多空比样本", "主动成交多空比总和", "大户多空比", "全体多空比", "主动成交多空比"],
    "K线形态扫描器": ["数据时间", "形态类型", "检测数量", "强度", "成交额（USDT）", "当前价格"],
    "趋势线榜单": ["数据时间", "趋势方向", "距离趋势线%", "当前价格"],
    "全量支撑阻力扫描器": ["数据时间", "支撑位", "阻力位", "当前价格", "ATR", "距支撑百分比", "距阻力百分比", "距关键位百分比"],
    "VPVR排行生成器": ["数据时间", "VPVR价格", "成交量分布", "价值区下沿", "价值区上沿", "价值区宽度", "价值区宽度百分比", "价值区覆盖率", "高成交节点", "低成交节点", "价值区位置"],
    "超级精准趋势扫描器": ["数据时间", "趋势方向", "趋势持续根数", "趋势强度", "趋势带", "最近翻转时间", "量能偏向"],
    "布林带扫描器": ["数据时间", "带宽", "中轨斜率", "中轨价格", "上轨价格", "下轨价格", "百分比b", "价格", "成交额"],
    "VWAP离线信号扫描": ["数据时间", "VWAP价格", "偏离度", "偏离百分比", "成交量加权", "当前价格", "成交额（USDT）", "VWAP上轨", "VWAP下轨", "VWAP带宽", "VWAP带宽百分比"],
    "成交量比率扫描器": ["数据时间", "量比", "信号概述", "成交额", "当前价格"],
    "MFI资金流量扫描器": ["数据时间", "MFI值"],
    "流动性扫描器": ["数据时间", "流动性得分", "流动性等级", "Amihud得分", "Kyle得分", "波动率得分", "成交量得分", "Amihud原值", "Kyle原值", "成交额（USDT）", "当前价格"],
    "智能RSI扫描器": ["数据时间", "信号", "方向", "强度", "RSI均值", "RSI7", "RSI14", "RSI21", "位置", "背离", "超买阈值", "超卖阈值"],
    "趋势云反转扫描器": ["数据时间", "信号", "方向", "强度", "形态", "SMMA200", "EMA2"],
    "大资金操盘扫描器": ["数据时间", "信号", "方向", "评分", "结构事件", "偏向", "订单块", "订单块上沿", "订单块下沿", "缺口类型", "价格区域", "摆动高点", "摆动低点"],
    "量能斐波狙击扫描器": ["数据时间", "信号", "方向", "强度", "价格区域", "VWMA基准"],
    "零延迟趋势扫描器": ["数据时间", "信号", "方向", "强度", "ZLEMA", "波动带宽", "上轨", "下轨", "趋势值"],
    "量能信号扫描器": ["数据时间", "信号", "方向", "强度", "多头比例", "空头比例", "MA100"],
    "多空信号扫描器": ["数据时间", "信号", "方向", "强度", "颜色", "实体大小", "影线长度", "HA开盘", "HA收盘"],
    "剥头皮信号扫描器": ["数据时间", "剥头皮信号", "RSI", "EMA9", "EMA21", "当前价格"],
    "谐波信号扫描器": ["数据时间", "谐波值"],
    "期货情绪聚合表": ["数据时间", "是否闭合", "数据新鲜秒", "持仓金额", "持仓张数", "大户多空比", "全体多空比", "主动成交多空比", "大户样本", "持仓变动", "持仓变动%", "大户偏离", "全体偏离", "主动偏离", "情绪差值", "情绪差值绝对值", "波动率", "OI连续根数", "主动连续根数", "风险分", "市场占比", "大户波动", "全体波动", "持仓斜率", "持仓Z分数", "大户情绪动量", "主动情绪动量", "情绪翻转信号", "主动跳变幅度", "稳定度分位", "贡献度排名", "陈旧标记"],
    "SuperTrend": ["数据时间", "SuperTrend", "方向", "上轨", "下轨"],
    "ADX": ["数据时间", "ADX", "正向DI", "负向DI"],
    "CCI": ["数据时间", "CCI"],
    "WilliamsR": ["数据时间", "WilliamsR"],
    "Donchian": ["数据时间", "上轨", "中轨", "下轨"],
    "Keltner": ["数据时间", "上轨", "中轨", "下轨", "ATR"],
    "Ichimoku": ["数据时间", "转换线", "基准线", "先行带A", "先行带B", "迟行带", "当前价格", "信号", "方向", "强度"],
    "数据监控": ["数据时间", "已加载根数", "最新时间", "本周应有根数", "缺口"],
}


def _make_col_name(indicator: str, field: str) -> str:
    """生成列名：指标名_字段名，处理特殊字符"""
    # 简化指标名
    ind = indicator.replace("扫描器", "").replace("排行榜", "").replace("排行生成器", "").replace("榜单", "")
    # 处理特殊字符
    col = f"{ind}_{field}"
    col = col.replace("，", "_").replace("（", "_").replace("）", "").replace("%", "pct").replace(" ", "_")
    return col


# 生成所有列定义
ALL_COLUMNS: List[tuple] = []  # [(col_name, indicator, field)]
for indicator, fields in INDICATOR_FIELDS.items():
    for field in fields:
        col_name = _make_col_name(indicator, field)
        ALL_COLUMNS.append((col_name, indicator, field))


class WideTableWriter:
    """宽表写入器 - 保留所有字段"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.sqlite_path.parent / "indicator_wide.db"
        self._conn = None
        self._lock = threading.Lock()
        self._col_names = ["symbol", "interval", "updated_at"] + [c[0] for c in ALL_COLUMNS]
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn
    
    def _init_db(self):
        """初始化表结构 - 仅在表不存在时创建"""
        conn = self._get_conn()
        
        # 检查表是否存在
        exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data'").fetchone()
        if exists:
            return
        
        # 构建列定义
        col_defs = ["symbol TEXT NOT NULL", "interval TEXT NOT NULL", "updated_at TEXT NOT NULL"]
        for col_name, _, _ in ALL_COLUMNS:
            col_defs.append(f'"{col_name}" TEXT')
        
        create_sql = f"""
            CREATE TABLE data (
                {', '.join(col_defs)},
                PRIMARY KEY (symbol, interval)
            )
        """
        conn.execute(create_sql)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_interval ON data(interval)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON data(symbol)")
        
        # meta表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
    
    def write_batch(self, results: Dict[str, Dict[str, Any]]):
        """
        批量写入
        results: {symbol: {interval: {indicator: {field: value}}}}
        """
        now = datetime.now(timezone.utc).isoformat()
        placeholders = ",".join(["?"] * len(self._col_names))
        
        rows = []
        for symbol, intervals in results.items():
            for interval, indicators in intervals.items():
                row = [symbol, interval, now]
                # 填充每个字段
                for col_name, indicator, field in ALL_COLUMNS:
                    value = None
                    if indicator in indicators:
                        value = indicators[indicator].get(field)
                    row.append(str(value) if value is not None else None)
                rows.append(row)
        
        with self._lock:
            conn = self._get_conn()
            conn.executemany(f"""
                INSERT OR REPLACE INTO data ({','.join(f'"{c}"' for c in self._col_names)})
                VALUES ({placeholders})
            """, rows)
            conn.commit()
            self._update_meta(conn, len(results), len(rows), now)
    
    def _update_meta(self, conn, symbol_count: int, row_count: int, now: str):
        conn.executemany("""
            INSERT OR REPLACE INTO meta (key, value, updated_at) VALUES (?, ?, ?)
        """, [
            ('total_symbols', str(conn.execute("SELECT COUNT(DISTINCT symbol) FROM data").fetchone()[0]), now),
            ('total_rows', str(conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]), now),
            ('total_columns', str(len(ALL_COLUMNS)), now),
            ('last_update', now, now),
        ])
        conn.commit()
    
    def close(self):
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None


# 禁用宽表写入 - 只使用 market_data.db
# wide_writer = WideTableWriter()
wide_writer = None
