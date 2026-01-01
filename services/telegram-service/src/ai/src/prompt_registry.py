"""提示词注册与缓存管理器。

职责：
- 扫描 `prompts/` 目录下的所有 `.txt` 文件，按相对路径（去掉后缀）建立键名，例如 `system/quant_sage_v1`
- 缓存内容与 mtime，减少重复 IO
- 支持热重载（全量或增量），用于 `/reload_prompts`
- 提供列表接口给 UI 生成提示词选择按钮
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptRegistry:
    """文件系统驱动的提示词注册表。"""

    def __init__(self, prompts_dir: Path | str = Path(__file__).parent / "prompts", max_file_size: int = 256_000):
        self.prompts_dir = Path(prompts_dir).resolve()
        self.max_file_size = max_file_size
        self.cache: Dict[str, Dict[str, object]] = {}  # {name: {"content": str, "mtime": float, "path": Path}}
        if not self.prompts_dir.exists():
            logger.warning(f"提示词目录不存在，将尝试创建: {self.prompts_dir}")
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.load_all_prompts()

    # ==================== 公共接口 ====================
    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """按名称获取提示词内容，未命中返回 default。"""
        key = self._normalize_key(name)
        entry = self.cache.get(key)
        if entry:
            return entry["content"]  # type: ignore[return-value]
        logger.warning(f"提示词未命中: {name}")
        return default

    def list_prompts(self, grouped: bool = False):
        """列出当前缓存的提示词。

        grouped=False: 返回 [{'name': 'system/quant_sage_v1', 'title': 'quant_sage_v1', 'group': 'system'}, ...]
        grouped=True:  返回 {'system': [...], 'analysis': [...], 'cards': [...], 'other': [...]}
        """
        items = []
        for name, meta in self.cache.items():
            group, title = self._split_group_title(name)
            items.append(
                {
                    "name": name,
                    "title": title,
                    "group": group,
                    "mtime": meta.get("mtime"),
                }
            )
        items.sort(key=lambda x: (x["group"], x["title"]))
        if not grouped:
            return items

        grouped_items: Dict[str, List[dict]] = {}
        for item in items:
            grouped_items.setdefault(item["group"], []).append(item)
        return grouped_items

    def reload(self, changed_only: bool = True) -> int:
        """重载提示词。

        Args:
            changed_only: True 只更新 mtime 变化的文件；False 则全量重读。
        Returns:
            更新的文件数量（新增+变更+删除）。
        """
        updated = 0
        existing = set(self.cache.keys())

        for path in self._iter_prompt_files():
            key = self._normalize_key(path.relative_to(self.prompts_dir))
            mtime = path.stat().st_mtime
            if changed_only and key in self.cache and self.cache[key].get("mtime") == mtime:
                existing.discard(key)
                continue
            if self._load_prompt(path):
                updated += 1
            existing.discard(key)

        # 清理已删除的文件
        for stale_key in existing:
            logger.info(f"移除已删除的提示词: {stale_key}")
            self.cache.pop(stale_key, None)
            updated += 1

        logger.info(f"提示词重载完成，更新 {updated} 个文件")
        return updated

    def load_all_prompts(self) -> int:
        """全量加载提示词，返回加载数量。"""
        count = 0
        for path in self._iter_prompt_files():
            if self._load_prompt(path):
                count += 1
        logger.info(f"提示词加载完成，共 {count} 个")
        return count

    # ==================== 内部工具 ====================
    def _iter_prompt_files(self):
        for path in self.prompts_dir.rglob("*.txt"):
            if path.is_file():
                yield path

    def _normalize_key(self, name: str | Path) -> str:
        """统一键名：相对路径、去掉后缀、使用 `/` 分隔。"""
        path = Path(name)
        if path.is_absolute():
            path = path.relative_to(self.prompts_dir)
        key_path = path.with_suffix("")
        parts = key_path.parts
        return "/".join(parts)

    def _split_group_title(self, key: str) -> tuple[str, str]:
        """将键名拆分成组名与标题。"""
        parts = key.split("/")
        if len(parts) == 1:
            return "other", parts[0]
        return parts[0], "/".join(parts[1:])

    def _load_prompt(self, path: Path) -> bool:
        """加载单个提示词文件。"""
        try:
            if not path.is_file():
                return False
            if path.stat().st_size > self.max_file_size:
                logger.warning(f"跳过过大的提示词文件: {path}")
                return False

            key = self._normalize_key(path.relative_to(self.prompts_dir))
            mtime = path.stat().st_mtime
            content = path.read_text(encoding="utf-8")

            self.cache[key] = {
                "content": content,
                "mtime": mtime,
                "path": path,
            }
            logger.debug(f"加载提示词: {key}")
            return True
        except UnicodeDecodeError:
            logger.error(f"提示词文件编码错误（需UTF-8）: {path}")
            return False
        except Exception as exc:
            logger.error(f"加载提示词失败 {path}: {exc}")
            return False
