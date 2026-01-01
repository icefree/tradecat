# -*- coding: utf-8 -*-
"""提示词拼装器：不做摘要，直接把 JSON 拼到提示词末尾。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Tuple

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


def build_prompt(prompt_name: str, payload: Dict[str, Any]) -> Tuple[str, str]:
    prompt_path = PROMPT_DIR / f"{prompt_name}.txt"
    if not prompt_path.is_file():
        raise FileNotFoundError(f"prompt not found: {prompt_path}")
    base = prompt_path.read_text(encoding="utf-8")
    data_json = json.dumps(payload, ensure_ascii=False)
    # 返回系统提示词文本与用户侧 JSON，调用方负责组装多消息
    return base, data_json


__all__ = ["build_prompt"]
