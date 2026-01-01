# -*- coding: utf-8 -*-
"""
Telegram 前端入口（精简版）
- 保持现有前端交互：币种选择 -> 周期选择 -> 提示词选择 -> 触发 AI 分析
- 所有 UI 逻辑集中于此文件，AI 核心仍在 src/ai/ai.py
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, List, Optional

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.ai import AICoinQueryManager  # 由 __init__.py 输出
from src.ai.ai import prompt_registry  # 复用现有提示词注册表
from src.process import run_process
from src.utils.run_recorder import RunRecorder

logger = logging.getLogger(__name__)

# 会话状态
SELECTING_COIN, SELECTING_INTERVAL = range(2)


class AITelegramHandler:
    """AI 点位的 Telegram 交互处理器（精简）"""

    def __init__(self, coin_query_manager: AICoinQueryManager):
        self.query_manager = coin_query_manager
        self.default_prompt = "深度报告"
        self.reply_keyboard = ReplyKeyboardMarkup([["🏠 主菜单"]], resize_keyboard=True)
        self.recorder = RunRecorder()

    # -------- 主流程 --------
    async def start_coin_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data.setdefault("prompt_name", self.default_prompt)
        context.user_data["coin_selection_page"] = 0
        return await self._show_coin_selection(update, context)

    async def handle_coin_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        if not query or not query.data:
            return ConversationHandler.END
        await query.answer()
        data = query.data

        if data == "coin_page_prev":
            context.user_data["coin_selection_page"] = max(0, context.user_data.get("coin_selection_page", 0) - 1)
            return await self._show_coin_selection(update, context)
        if data == "coin_page_next":
            context.user_data["coin_selection_page"] = context.user_data.get("coin_selection_page", 0) + 1
            return await self._show_coin_selection(update, context)

        if data == "select_prompt":
            return await self._show_prompt_selection(update, context)
        if data.startswith("set_prompt_"):
            return await self._handle_prompt_selected(update, context)

        if data.startswith("coin_"):
            symbol = data.replace("coin_", "")
            context.user_data["selected_symbol"] = symbol
            return await self._show_interval_selection(update, context, symbol)

        return ConversationHandler.END

    async def handle_interval_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        if not query or not query.data:
            return ConversationHandler.END
        await query.answer()
        data = query.data

        if data == "back_to_coin":
            return await self._show_coin_selection(update, context)

        if data in {"select_prompt"} or data.startswith("set_prompt_"):
            return await self.handle_coin_selection(update, context)

        if data.startswith("interval_"):
            interval = data.replace("interval_", "")
            symbol = context.user_data.get("selected_symbol")
            prompt_name = context.user_data.get("prompt_name", self.default_prompt)
            if not symbol:
                await query.edit_message_text("❌ 未选择币种，请返回重新选择")
                return ConversationHandler.END
            await query.edit_message_text(f"🔄 正在分析 {symbol} @ {interval} ...")
            asyncio.create_task(self._run_analysis(update, context, symbol, interval, prompt_name))
            return ConversationHandler.END

        return ConversationHandler.END

    # -------- 视图构建 --------
    async def _show_coin_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        symbols = self.query_manager.get_supported_symbols()
        symbols = [s for s in symbols if s.endswith("USDT")]
        page = context.user_data.get("coin_selection_page", 0)
        per_page = 10
        total_pages = max(1, (len(symbols) + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        context.user_data["coin_selection_page"] = page
        page_symbols = symbols[page * per_page : (page + 1) * per_page]

        keyboard: List[List[InlineKeyboardButton]] = []
        for i in range(0, len(page_symbols), 5):
            row = [
                InlineKeyboardButton(sym.replace("USDT", ""), callback_data=f"coin_{sym}")
                for sym in page_symbols[i : i + 5]
            ]
            keyboard.append(row)

        keyboard.append(
            [
                InlineKeyboardButton("⬅️ 上一页", callback_data="coin_page_prev"),
                InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="page_info"),
                InlineKeyboardButton("➡️ 下一页", callback_data="coin_page_next"),
            ]
        )

        prompt_label = context.user_data.get("prompt_name", self.default_prompt)
        keyboard.append([InlineKeyboardButton(f"🧠 提示词: {prompt_label}", callback_data="select_prompt")])
        keyboard.append([InlineKeyboardButton("🏠 返回主菜单", callback_data="cancel_analysis")])

        markup = InlineKeyboardMarkup(keyboard)
        text = "🤖 请选择要分析的合约币种（USDT）"
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        elif update.message:
            await update.message.reply_text(text, reply_markup=markup)
        return SELECTING_COIN

    async def _show_interval_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str) -> int:
        keyboard = [
            [
                InlineKeyboardButton("5m", callback_data="interval_5m"),
                InlineKeyboardButton("15m", callback_data="interval_15m"),
                InlineKeyboardButton("1h", callback_data="interval_1h"),
                InlineKeyboardButton("4h", callback_data="interval_4h"),
                InlineKeyboardButton("1d", callback_data="interval_1d"),
            ],
            [
                InlineKeyboardButton("🔙 重新选择币种", callback_data="back_to_coin"),
                InlineKeyboardButton("🏠 返回主菜单", callback_data="cancel_analysis"),
            ],
        ]
        prompt_label = context.user_data.get("prompt_name", self.default_prompt)
        text = f"📌 已选择: {symbol.replace('USDT','')}\n请选择分析周期\n🧠 当前提示词: {prompt_label}"
        markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        elif update.message:
            await update.message.reply_text(text, reply_markup=markup)
        return SELECTING_INTERVAL

    async def _show_prompt_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        if query:
            await query.answer()
        selected = context.user_data.get("prompt_name", self.default_prompt)
        items = prompt_registry.list_prompts(grouped=False)
        keyboard: List[List[InlineKeyboardButton]] = []
        for item in items:
            name = item["name"]
            label = item["title"]
            mark = " ✅" if name == selected else ""
            keyboard.append([InlineKeyboardButton(f"{label}{mark}", callback_data=f"set_prompt_{name}")])
        if not keyboard:
            keyboard.append([InlineKeyboardButton("未找到提示词文件", callback_data="select_prompt")])
        keyboard.append([InlineKeyboardButton("⬅️ 返回币种选择", callback_data="back_to_coin_selection")])
        markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🧠 选择要使用的提示词（基于文件名）", reply_markup=markup)
        return SELECTING_COIN

    async def _handle_prompt_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        if not query or not query.data:
            return ConversationHandler.END
        await query.answer()
        prompt_key = query.data.replace("set_prompt_", "", 1)
        context.user_data["prompt_name"] = prompt_key
        return await self._show_coin_selection(update, context)

    # -------- 分析触发 --------
    async def _run_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str, interval: str, prompt: str):
        try:
            result = await run_process(symbol, interval, prompt)
            analysis_text = result.get("analysis", "未生成AI分析结果")
            if update.callback_query:
                await update.callback_query.edit_message_text(analysis_text[:4000])
            elif update.message:
                await update.message.reply_text(analysis_text[:4000])
        except Exception as exc:
            logger.exception("分析失败")
            await self._send_error(update, f"❌ 分析失败：{exc}")

    async def _send_error(self, update: Update, text: str):
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        elif update.message:
            await update.message.reply_text(text)

    # -------- 常驻键盘 --------
    async def handle_persistent_keyboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message
        if not message or not message.text:
            return ConversationHandler.END
        text = message.text.strip()
        if text == "🏠 主菜单" or text in {"🎲 AI点位", "🎯 开始AI分析"}:
            return await self.start_coin_analysis(update, context)
        if text.endswith("@"):
            symbol = text[:-1].strip().upper()
            symbol = symbol if symbol.endswith("USDT") else f"{symbol}USDT"
            context.user_data["selected_symbol"] = symbol
            return await self._show_interval_selection(update, context, symbol)
        await message.reply_text("🤖 发送 币种@（如：BTC@）或点击主菜单开始分析。", reply_markup=self.reply_keyboard)
        return ConversationHandler.END

    # -------- Handler 注册 --------
    def get_conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start_coin_analysis),
                CommandHandler("reload_prompts", self._handle_reload_prompts),
                CallbackQueryHandler(self.start_coin_analysis, pattern="^start_coin_analysis$"),
                CallbackQueryHandler(self.handle_coin_selection, pattern="^coin_[A-Z0-9]{2,15}USDT$"),
                CallbackQueryHandler(self.handle_interval_selection, pattern="^interval_[0-9]+[mhd]$"),
            ],
            states={
                SELECTING_COIN: [
                    CallbackQueryHandler(self._show_prompt_selection, pattern="^select_prompt$"),
                    CallbackQueryHandler(self._handle_prompt_selected, pattern="^set_prompt_.*$"),
                    CallbackQueryHandler(self.handle_coin_selection),
                    MessageHandler(filters.Regex("^(🏠 主菜单)$"), self.handle_persistent_keyboard),
                ],
                SELECTING_INTERVAL: [
                    CallbackQueryHandler(self.handle_interval_selection),
                    MessageHandler(filters.Regex("^(🏠 主菜单)$"), self.handle_persistent_keyboard),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self._handle_cancel_analysis, pattern="^cancel_analysis$"),
                CallbackQueryHandler(self._handle_cancel_analysis, pattern="^main_menu$"),
                CallbackQueryHandler(self._handle_cancel_analysis, pattern="^refresh_main_menu$"),
                CallbackQueryHandler(self.handle_interval_selection, pattern="^back_to_coin$"),
                CallbackQueryHandler(self.handle_coin_selection, pattern="^back_to_coin_selection$"),
                CallbackQueryHandler(lambda *_: ConversationHandler.END, pattern="^page_info$"),
            ],
        )

    async def _handle_cancel_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data.clear()
        if update.callback_query:
            await update.callback_query.answer()
        return await self.start_coin_analysis(update, context)

    async def _handle_reload_prompts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        updated = prompt_registry.reload()
        msg = f"✅ 提示词已刷新，更新 {updated} 个文件"
        if update.message:
            await update.message.reply_text(msg, reply_markup=self.reply_keyboard)
        elif update.callback_query:
            await update.callback_query.answer(msg, show_alert=True)
        return ConversationHandler.END


# -------- Bot 应用入口 --------
_ai_handler: Optional[AITelegramHandler] = None


def _ensure_ai_handler() -> AITelegramHandler:
    global _ai_handler
    if _ai_handler is None:
        logger.info("初始化 AI 模块…")
        query_manager = AICoinQueryManager()
        _ai_handler = AITelegramHandler(query_manager)
    return _ai_handler


def build_application() -> Application:
    token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("未找到 BOT_TOKEN，请在环境变量或 .env 中配置。")

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    application = Application.builder().token(token).build()

    handler = _ensure_ai_handler()
    application.add_handler(handler.get_conversation_handler())
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))

    async def post_init(app: Application) -> None:
        _ensure_ai_handler()
        await app.bot.set_my_commands([BotCommand("start", "打开主菜单")])

    application.post_init = post_init
    return application


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handler = _ensure_ai_handler()
    message = update.message
    if not message or not message.text:
        return ConversationHandler.END
    text = message.text.strip()
    if text.startswith("/"):
        return ConversationHandler.END
    return await handler.handle_persistent_keyboard(update, context)


def main() -> None:
    application = build_application()
    logger.info("AI Bot 就绪：直接进入币种选择界面")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
