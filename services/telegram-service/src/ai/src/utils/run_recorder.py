# -*- coding: utf-8 -*-
"""
RunRecorder
- 为每次 AI 分析落盘一套完整的数据快照，便于排查与复现。
- 目录结构：data/ai/{symbol}_{timestamp}/
  - raw_payload.json : AICoinQueryManager 返回的完整字典
  - prompt.txt       : 本次使用的提示词内容（可选）
  - analysis.txt     : LLM 输出文本（可选）
  - meta.json        : 请求参数、时间戳等元信息
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List

from .data_docs import DATA_DOCS


class RunRecorder:
    def __init__(self, base_dir: Optional[str] = None) -> None:
        default_dir = Path(__file__).resolve().parents[2] / "data" / "ai"
        self.base_dir = Path(base_dir) if base_dir else default_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_run(
        self,
        symbol: str,
        interval: str,
        prompt_name: str,
        payload: Dict[str, Any],
        prompt_text: Optional[str] = None,
        analysis_text: Optional[str] = None,
        request_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        folder = self.base_dir / f"{symbol}_{timestamp}"
        folder.mkdir(parents=True, exist_ok=True)

        variable_map = self._build_variable_map(payload)

        # 元信息
        meta = {
            "symbol": symbol,
            "interval": interval,
            "prompt_name": prompt_name,
            "timestamp_utc": timestamp,
            "variable_map": variable_map,
            "docs": self._attach_docs(payload),
        }
        (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        # 原始数据
        (folder / "raw_payload.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )

        # 提示词文本
        if prompt_text:
            prompt_filename = f"{prompt_name}.txt"
            (folder / prompt_filename).write_text(prompt_text, encoding="utf-8")

        # 本次发送给 LLM 的完整消息（system/user 等）
        if request_messages:
            (folder / "request_messages.json").write_text(
                json.dumps(request_messages, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
            )

        # AI 输出
        if analysis_text:
            (folder / "analysis.txt").write_text(analysis_text, encoding="utf-8")

        return str(folder)

    # ==================== 内部工具 ====================
    def _build_variable_map(self, payload: Dict[str, Any]) -> list:
        """根据 payload 自动生成变量对照表，便于排查。

        输出示例:
        [
          {"name": "candles_latest_50", "type": "dict[str->list]", "summary": "7 intervals, each ~50 rows"},
          {"name": "metrics_5m_latest_50", "type": "list", "summary": "50 rows of 5m metrics"},
          ...
        ]
        """
        table: list = []

        for key, value in payload.items():
            entry = {"name": key, "type": type(value).__name__, "summary": ""}

            try:
                if isinstance(value, dict):
                    if key == "candles_latest_50":
                        intervals = list(value.keys())
                        lens = {k: len(v) if isinstance(v, list) else 0 for k, v in value.items()}
                        entry["type"] = "dict[str->list]"
                        entry["summary"] = f"{len(intervals)} intervals; rows per interval: {lens}"
                    elif key == "indicator_samples":
                        entry["type"] = "dict[str->list|error]"
                        counts = {k: (len(v) if isinstance(v, list) else v) for k, v in value.items()}
                        entry["summary"] = f"{len(value)} tables; rows: {counts}"
                    else:
                        entry["summary"] = f"dict keys: {list(value.keys())[:5]}{'...' if len(value)>5 else ''}"

                elif isinstance(value, list):
                    entry["summary"] = f"list len={len(value)}"
                else:
                    entry["summary"] = str(value)[:200]
            except Exception as exc:
                entry["summary"] = f"summary_error: {exc}"

            table.append(entry)

        return table

    def _attach_docs(self, payload: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """为已有数据块附加 what/why/how 说明，未定义则给默认提示。"""
        docs: Dict[str, Dict[str, str]] = {}
        for key in payload.keys():
            doc = DATA_DOCS.get(key)
            if doc:
                docs[key] = doc
            else:
                docs[key] = {
                    "what": "未定义",
                    "why": "未定义",
                    "how": "未定义",
                }
        return docs


# 便捷实例（可在全局复用）
def get_default_recorder() -> RunRecorder:
    return RunRecorder()
