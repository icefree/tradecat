# -*- coding: utf-8 -*-
"""
AI模块 - 提供AI分析功能

模块结构:
- src/ai/: 核心AI功能
  - ai.py: 主要AI实现（包含AICoinQueryManager, AITelegramHandler等）
"""

import sys
from pathlib import Path

# 添加src到PYTHONPATH，支持内部from src.utils导入
_ai_dir = Path(__file__).parent
_src_dir = _ai_dir / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# 从子模块导入
try:
    from .src.ai import AICoinQueryManager
    from .src.bot.bot import AITelegramHandler
    __all__ = ["AICoinQueryManager", "AITelegramHandler"]
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ AI模块导入失败: {e}")
    __all__ = []
