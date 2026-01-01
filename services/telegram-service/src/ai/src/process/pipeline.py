# -*- coding: utf-8 -*-
"""最简管道：取数据 -> 拼提示词+JSON -> 调 LLM -> 返回结果并落盘"""
from __future__ import annotations

import asyncio
from typing import Dict, Any

from src.utils.run_recorder import RunRecorder
from .fetcher import fetch_payload
from .prompt_builder import build_prompt
from .llm_client import call_llm


async def run_process(symbol: str, interval: str, prompt_name: str) -> Dict[str, Any]:
    # 拉数据（阻塞型转线程）
    payload = await asyncio.to_thread(fetch_payload, symbol, interval)

    # 拼提示词（系统）与 JSON（用户输入）
    system_prompt, data_json = await asyncio.to_thread(build_prompt, prompt_name, payload)
    user_content = (
        "请基于以下交易数据进行市场分析，输出中文结论\n"
        "禁止原样粘贴 DATA_JSON 或长表格；只输出摘要和关键数值\n"
        "输出结构（严格按此系统提示词要求的结构）：\n"
        "===DATA_JSON===\n"
        f"{data_json}"
    )

    # 调用 LLM：system + user 分离
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    analysis_text, raw_response = await call_llm(messages)

    # 落盘快照（prompt.txt 存原始提示词，不含 JSON）
    recorder = RunRecorder()
    await asyncio.to_thread(
        recorder.save_run,
        symbol,
        interval,
        prompt_name,
        payload,
        system_prompt,
        analysis_text,
        messages,
    )

    return {
        "analysis": analysis_text,
        "raw_response": raw_response,
        "payload": payload,
    }


__all__ = ["run_process"]
