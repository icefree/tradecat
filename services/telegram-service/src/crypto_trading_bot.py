#!/usr/bin/env python3
# 兼容入口：保留原路径，实际逻辑迁移到 bot/app.py
# 导出所有符号，确保旧的 import crypto_trading_bot 仍可用
from bot.app import *  # noqa: F401,F403
import sys as _sys

# 将当前模块别名为 crypto_trading_bot，便于其他模块引用
_sys.modules.setdefault("crypto_trading_bot", _sys.modules[__name__])

if __name__ == "__main__":
    main()
