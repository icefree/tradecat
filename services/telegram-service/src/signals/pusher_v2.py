"""
信号推送服务 v2
支持完整信号模板推送
"""
import asyncio
import logging
from typing import Optional
from telegram import Bot
from telegram.constants import ParseMode

from .engine_v2 import Signal, get_engine

logger = logging.getLogger(__name__)


class SignalPusher:
    """信号推送器"""
    
    def __init__(self, bot_token: str, chat_id: str, use_full_template: bool = True):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        self.use_full_template = use_full_template
        self.loop = asyncio.new_event_loop()
    
    def _format_signal(self, signal: Signal) -> str:
        """格式化信号消息"""
        if self.use_full_template and signal.full_message:
            return signal.full_message
        
        # 简化版
        icon = {"BUY": "🟢", "SELL": "🔴", "ALERT": "⚠️"}.get(signal.direction, "📊")
        strength_bar = "█" * (signal.strength // 10) + "░" * (10 - signal.strength // 10)
        
        return f"""
{icon} <b>{signal.direction}</b> | {signal.symbol}

📌 <b>{signal.rule_name}</b>
⏱ 周期: {signal.timeframe}
💰 价格: {signal.price}
📊 强度: [{strength_bar}] {signal.strength}%

💬 {signal.message}
"""
    
    async def _send_async(self, text: str):
        """异步发送"""
        try:
            # Telegram 消息限制 4096 字符
            if len(text) > 4096:
                text = text[:4090] + "\n..."
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=None  # 纯文本，避免格式问题
            )
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
    
    def push(self, signal: Signal):
        """推送信号"""
        text = self._format_signal(signal)
        self.loop.run_until_complete(self._send_async(text))
        logger.info(f"信号已推送: {signal.symbol} {signal.direction} - {signal.rule_name}")


def start_signal_service(
    bot_token: str,
    chat_id: str,
    interval: int = 60,
    use_full_template: bool = True
):
    """启动信号服务"""
    pusher = SignalPusher(bot_token, chat_id, use_full_template)
    engine = get_engine()
    engine.register_callback(pusher.push)
    
    logger.info(f"信号服务启动，推送到 chat_id: {chat_id}，完整模板: {use_full_template}")
    engine.run_loop(interval=interval)
