# -*- coding: utf-8 -*-
"""LLM 客户端封装：调用仓库里的 LLM客户端 工具。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Tuple, List, Dict


# 将仓库根目录加入 sys.path，便于导入 libs/common/utils
REPO_ROOT = Path(__file__).resolve().parents[6]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libs.common.utils.LLM客户端 import 创建LLM客户端  # type: ignore


async def call_llm(messages: List[Dict[str, str]], model: str = "gemini-2.5-flash") -> Tuple[str, str]:
    """
    调用统一 LLM 网关。

    Args:
        messages: OpenAI 兼容的消息列表，已包含 system/user 等角色。
        model: 模型名称，默认 gemini-2.5-flash。
    """
    try:
        # 允许通过环境变量设置代理，兼容 http_proxy/https_proxy/LLM_PROXY
        proxy_url = (
            os.getenv("LLM_PROXY")
            or os.getenv("HTTPS_PROXY")
            or os.getenv("https_proxy")
            or os.getenv("HTTP_PROXY")
            or os.getenv("http_proxy")
            or os.getenv("DEFAULT_PROXY_URL")
            or "http://127.0.0.1:9910"
        )
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        os.environ["http_proxy"] = proxy_url
        os.environ["https_proxy"] = proxy_url

        client = 创建LLM客户端()
        resp = client.聊天(
            messages=messages,
            model=model,
            temperature=0.5,
            max_tokens=1000000,
            stream=False,
            req_timeout=600,
        )
        content = resp.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            content = json.dumps(resp, ensure_ascii=False)
        return content, json.dumps(resp, ensure_ascii=False)
    except Exception as e:
        err = f"[LLM_ERROR] {e}"
        return err, json.dumps({"error": str(e)}, ensure_ascii=False)


__all__ = ["call_llm"]
