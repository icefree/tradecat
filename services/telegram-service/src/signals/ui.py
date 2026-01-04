"""
信号开关管理 - 按表开关
"""
from typing import Dict, Set
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .rules import RULES_BY_TABLE

# 表名映射为简短名称
TABLE_NAMES = {
    "智能RSI扫描器.py": "RSI",
    "KDJ随机指标扫描器.py": "KDJ",
    "CCI.py": "CCI",
    "WilliamsR.py": "WR",
    "MFI资金流量扫描器.py": "MFI",
    "ADX.py": "ADX",
    "谐波信号扫描器.py": "谐波",
    "SuperTrend.py": "SuperTrend",
    "超级精准趋势扫描器.py": "精准趋势",
    "Ichimoku.py": "一目均衡",
    "零延迟趋势扫描器.py": "零延迟",
    "趋势云反转扫描器.py": "趋势云",
    "趋势线榜单.py": "趋势线",
    "多空信号扫描器.py": "多空信号",
    "量能信号扫描器.py": "量能信号",
    "G，C点扫描器.py": "GC点",
    "布林带扫描器.py": "布林带",
    "ATR波幅扫描器.py": "ATR",
    "Donchian.py": "唐奇安",
    "Keltner.py": "肯特纳",
    "全量支撑阻力扫描器.py": "支撑阻力",
    "VWAP离线信号扫描.py": "VWAP",
    "MACD柱状扫描器.py": "MACD",
    "OBV能量潮扫描器.py": "OBV",
    "CVD信号排行榜.py": "CVD",
    "成交量比率扫描器.py": "量比",
    "主动买卖比扫描器.py": "买卖比",
    "期货情绪聚合表.py": "期货情绪",
    "K线形态扫描器.py": "K线形态",
    "大资金操盘扫描器.py": "SMC智能资金",
    "量能斐波狙击扫描器.py": "斐波那契",
    "VPVR排行生成器.py": "VPVR",
    "流动性扫描器.py": "流动性",
    "剥头皮信号扫描器.py": "剥头皮",
    "基础数据同步器.py": "基础数据",
}

# 所有表
ALL_TABLES = list(RULES_BY_TABLE.keys())

# 用户订阅 {user_id: {"enabled": bool, "tables": set}}
_subs: Dict[int, Dict] = {}


def get_sub(uid: int) -> Dict:
    if uid not in _subs:
        # 默认开启推送，开启全部信号
        _subs[uid] = {"enabled": True, "tables": set(ALL_TABLES)}
    return _subs[uid]


def get_short_name(table: str) -> str:
    return TABLE_NAMES.get(table, table.replace(".py", "").replace("扫描器", ""))


def get_menu_text(uid: int) -> str:
    sub = get_sub(uid)
    status = "✅ 开启" if sub["enabled"] else "❌ 关闭"
    enabled = len(sub["tables"])
    total = len(ALL_TABLES)
    
    # 只显示已开启的
    enabled_list = []
    for table in ALL_TABLES:
        if table in sub["tables"]:
            name = get_short_name(table)
            count = len(RULES_BY_TABLE[table])
            enabled_list.append(f"{name} ({count}条)")
    
    if enabled_list:
        content = "\n".join(enabled_list)
    else:
        content = "暂无开启的信号"
    
    return f"🔔 信号\n<pre>{content}</pre>\n推送: {status} 已选: {enabled}/{total}"


def get_menu_kb(uid: int) -> InlineKeyboardMarkup:
    sub = get_sub(uid)
    rows = []
    
    # 表开关 每行3个，选中的有✅，未选的只有文字
    for i in range(0, len(ALL_TABLES), 3):
        row = []
        for table in ALL_TABLES[i:i+3]:
            name = get_short_name(table)
            if len(name) > 6:
                name = name[:5] + ".."
            if table in sub["tables"]:
                row.append(InlineKeyboardButton(f"✅{name}", callback_data=f"sig_t_{table}"))
            else:
                row.append(InlineKeyboardButton(name, callback_data=f"sig_t_{table}"))
        rows.append(row)
    
    # 开启/关闭
    if sub["enabled"]:
        rows.append([
            InlineKeyboardButton("✅开启推送", callback_data="sig_nop"),
            InlineKeyboardButton("关闭推送", callback_data="sig_toggle"),
        ])
    else:
        rows.append([
            InlineKeyboardButton("开启推送", callback_data="sig_toggle"),
            InlineKeyboardButton("✅关闭推送", callback_data="sig_nop"),
        ])
    
    rows.append([InlineKeyboardButton("🏠 返回", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(rows)


async def handle(update, context) -> bool:
    """处理 sig_ 开头的回调"""
    q = update.callback_query
    data = q.data
    uid = q.from_user.id
    
    if not data.startswith("sig_"):
        return False
    
    await q.answer()
    sub = get_sub(uid)
    
    if data == "sig_toggle":
        sub["enabled"] = not sub["enabled"]
    elif data == "sig_all":
        sub["tables"] = set(ALL_TABLES)
    elif data == "sig_none":
        sub["tables"] = set()
    elif data.startswith("sig_t_"):
        table = data[6:]
        if table in sub["tables"]:
            sub["tables"].discard(table)
        else:
            sub["tables"].add(table)
    elif data == "sig_menu":
        pass
    else:
        return False
    
    await q.edit_message_text(get_menu_text(uid), reply_markup=get_menu_kb(uid), parse_mode='HTML')
    return True


def is_table_enabled(uid: int, table: str) -> bool:
    """判断表是否启用"""
    sub = get_sub(uid)
    return sub["enabled"] and table in sub["tables"]


def get_signal_push_kb(symbol: str) -> InlineKeyboardMarkup:
    """信号推送消息的内联键盘，带币种分析和AI分析跳转"""
    # 去掉USDT后缀用于显示
    coin = symbol.replace("USDT", "")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"🔍 {coin}分析", callback_data=f"single_query_{symbol}"),
            InlineKeyboardButton(f"🤖 AI分析", callback_data=f"ai_coin_{symbol}"),
        ]
    ])
