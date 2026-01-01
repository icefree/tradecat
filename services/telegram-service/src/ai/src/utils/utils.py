# -*- coding: utf-8 -*-
"""
合并后的 utils 模块，实现集中管理。
"""
from __future__ import annotations

# ==== BEGIN time_utils.py ====
"""
时间工具模块 - 提供时间格式化和转换功能
避免循环导入问题
"""

from datetime import datetime, timezone, timedelta
from typing import Union

def get_beijing_time() -> datetime:
    """获取北京时间"""
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz)

def format_beijing_time(time_str: Union[str, datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化北京时间
    
    Args:
        time_str: 时间字符串或datetime对象
        format_str: 格式化字符串
        
    Returns:
        格式化后的时间字符串
    """
    try:
        if isinstance(time_str, str):
            # 解析ISO格式时间字符串
            if 'T' in time_str:
                # ISO格式
                if time_str.endswith('Z'):
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                elif '+' in time_str or time_str.count('-') > 2:
                    dt = datetime.fromisoformat(time_str)
                else:
                    dt = datetime.fromisoformat(time_str)
            else:
                # 尝试解析常见格式
                dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                
            # 转换为北京时间
            if dt.tzinfo is None:
                # 如果没有时区信息，假设为UTC
                dt = dt.replace(tzinfo=timezone.utc)
            
            beijing_tz = timezone(timedelta(hours=8))
            beijing_time = dt.astimezone(beijing_tz)
            
        elif isinstance(time_str, datetime):
            if time_str.tzinfo is None:
                # 如果没有时区信息，假设为UTC
                time_str = time_str.replace(tzinfo=timezone.utc)
            
            beijing_tz = timezone(timedelta(hours=8))
            beijing_time = time_str.astimezone(beijing_tz)
        else:
            # 如果输入格式不支持，返回当前北京时间
            beijing_time = get_beijing_time()
            
        return beijing_time.strftime(format_str)
        
    except Exception as e:
        # 如果解析失败，返回当前北京时间
        beijing_time = get_beijing_time()
        return beijing_time.strftime(format_str)
# ==== END time_utils.py ====

# ==== BEGIN progress_display.py ====
"""
🎯 智能进度显示和等待优化
"""

import asyncio
import json
import random
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ProgressDisplay:
    """智能进度显示器"""
    
    def __init__(self):
        self.knowledge_file = "trading_knowledge.json"
        self.trading_tips = []
        self.agent_statuses = []
        self.load_knowledge_base()
        
        # 进度阶段配置
        self.progress_stages = [
            (10, "🔍 初始化分析引擎..."),
            (20, "📊 获取市场数据..."),
            (35, "🧮 计算技术指标..."),
            (50, "🤖 启动AI中..."),
            (65, "🎯 多维度分析中..."),
            (80, "🧠 AI深度学习..."),
            (95, "📈 生成分析报告..."),
            (99, "🎯 AI协同分析中...")
        ]
        
        # 知识刷新间隔（秒）
        self.knowledge_refresh_interval = 7
        
    def load_knowledge_base(self):
        """加载交易知识库"""
        try:
            if os.path.exists(self.knowledge_file):
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trading_tips = data.get('trading_tips', [])
                    self.agent_statuses = data.get('agent_statuses', [])
                logger.info(f"✅ 加载交易知识库: {len(self.trading_tips)} 条知识")
            else:
                logger.warning(f"⚠️ 知识库文件不存在: {self.knowledge_file}")
                self._create_default_knowledge()
        except Exception as e:
            logger.error(f"❌ 加载知识库失败: {e}")
            self._create_default_knowledge()
    
    def _create_default_knowledge(self):
        """创建默认知识库"""
        self.trading_tips = [
            {"category": "technical", "tip": "RSI指标超过70通常表示超买状态，低于30则可能是超卖信号"},
            {"category": "risk", "tip": "设置止损是保护资金的最佳方式"},
            {"category": "strategy", "tip": "趋势是你的朋友，顺势而为"}
        ]
        self.agent_statuses = [
            "🔍 Market Data Agent - 实时数据采集中...",
            "📊 Technical Agent - 计算技术指标...",
            "🎯 Signal Agent - 生成交易信号..."
        ]
    
    def get_random_tip(self, category: Optional[str] = None) -> str:
        """获取随机交易小知识"""
        try:
            if category:
                filtered_tips = [tip for tip in self.trading_tips if tip.get('category') == category]
                tips_pool = filtered_tips if filtered_tips else self.trading_tips
            else:
                tips_pool = self.trading_tips
            
            if tips_pool:
                tip = random.choice(tips_pool)
                return tip.get('tip', '交易需要耐心和纪律')
            else:
                return "交易需要耐心和纪律"
        except Exception as e:
            logger.error(f"获取交易小知识失败: {e}")
            return "交易需要耐心和纪律"
    
    def get_random_agent_status(self) -> str:
        """获取随机Agent状态"""
        try:
            if self.agent_statuses:
                return random.choice(self.agent_statuses)
            else:
                return "🤖 AI Agent 分析中..."
        except Exception as e:
            logger.error(f"获取Agent状态失败: {e}")
            return "🤖 AI Agent 分析中..."
    
    def generate_progress_bar(self, progress: int, length: int = 10) -> str:
        """生成进度条"""
        filled = int(progress / 100 * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"{bar} {progress}%"
    

    def calculate_elapsed_time(self, start_time: float) -> str:
        """计算已用时间"""
        import time
        current_time = time.time()
        elapsed = current_time - start_time

        # 确保elapsed不为负数
        if elapsed < 0:
            elapsed = 0

        if elapsed < 60:
            return f"{int(elapsed)}秒"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            return f"{minutes}分{seconds}秒"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            return f"{hours}小时{minutes}分钟"
    
    async def show_progress_with_knowledge(self, callback_query, symbol: str,
                                         analysis_start_time: float = None) -> None:
        """显示带知识的进度条"""
        try:
            # 使用传入的分析开始时间，如果没有则使用当前时间
            if analysis_start_time is None:
                import time
                analysis_start_time = time.time()

            last_knowledge_update = 0
            current_tip = self.get_random_tip()

            # 进度更新循环 - 跟随知识刷新节奏
            for stage_progress, stage_desc in self.progress_stages[:-1]:  # 排除99%阶段
                # 每个阶段显示时间根据知识刷新间隔
                updates_per_stage = 2  # 每个阶段更新2次

                for _ in range(updates_per_stage):
                    import time
                    current_time = time.time()
                    elapsed = current_time - analysis_start_time

                    # 检查是否需要更新知识（每7秒）
                    if elapsed - last_knowledge_update >= self.knowledge_refresh_interval:
                        current_tip = self.get_random_tip()
                        last_knowledge_update = elapsed

                    # 生成进度显示
                    progress_bar = self.generate_progress_bar(stage_progress)
                    elapsed_time = self.calculate_elapsed_time(analysis_start_time)

                    message = f"""🤖 AI点位分析中...

{progress_bar}
{stage_desc}

💡 交易小知识：
{current_tip}

⏱️ 已用时间：{elapsed_time}"""

                    try:
                        await callback_query.edit_message_text(message)
                    except Exception as edit_error:
                        logger.warning(f"更新进度消息失败: {edit_error}")

                    # 按知识刷新间隔等待
                    await asyncio.sleep(self.knowledge_refresh_interval)

        except Exception as e:
            logger.error(f"显示进度失败: {e}")
    
    async def show_ai_analysis_progress(self, callback_query, symbol: str, start_time: float = None) -> None:
        """显示AI分析阶段的进度（99%）"""
        try:
            # 在AI分析阶段，每7秒更新一次知识和时间
            last_knowledge_update = 0
            current_tip = self.get_random_tip()
            agent_status = self.get_random_agent_status()

            # AI分析阶段持续显示，直到分析完成
            for _ in range(10):  # 最多显示70秒（10 * 7秒）
                import time
                current_time = time.time()

                if start_time:
                    elapsed = current_time - start_time

                    # 每7秒更新知识和Agent状态
                    if elapsed - last_knowledge_update >= self.knowledge_refresh_interval:
                        current_tip = self.get_random_tip()
                        agent_status = self.get_random_agent_status()
                        last_knowledge_update = elapsed

                    elapsed_time = self.calculate_elapsed_time(start_time)
                    time_display = f"⏱️ 已用时间：{elapsed_time}"
                else:
                    time_display = "⏱️ AI深度分析进行中，请稍候..."

                progress_bar = self.generate_progress_bar(99)

                message = f"""🤖 AI点位分析中...

{progress_bar}
🎯 AI协同分析中...

🧠 当前状态：
{agent_status}

💡 交易小知识：
{current_tip}

{time_display}
"""

                try:
                    await callback_query.edit_message_text(message)
                except Exception as edit_error:
                    logger.warning(f"更新AI分析进度失败: {edit_error}")

                # 按知识刷新间隔等待
                await asyncio.sleep(self.knowledge_refresh_interval)

        except Exception as e:
            logger.error(f"显示AI分析进度失败: {e}")
    
    async def show_completion_message(self, callback_query, symbol: str) -> None:
        """显示完成消息"""
        try:
            progress_bar = self.generate_progress_bar(100)
            
            message = f"""🤖 AI点位分析完成！

{progress_bar}
✅ 分析完成，正在生成报告...

🎯 AI分析结果：
• 技术指标计算完成
• 市场情绪分析完成  
• 风险评估完成
• 交易信号生成完成

📋 详细分析报告即将发送...
"""
            
            try:
                await callback_query.edit_message_text(message)
            except Exception as edit_error:
                logger.warning(f"更新完成消息失败: {edit_error}")
                
        except Exception as e:
            logger.error(f"显示完成消息失败: {e}")

class ProgressManager:
    """进度管理器"""
    
    def __init__(self):
        self.display = ProgressDisplay()
        self.active_progress = {}  # 记录活跃的进度显示
    
    async def start_analysis_progress(self, callback_query, symbol: str,
                                    analysis_id: str) -> None:
        """开始分析进度显示"""
        try:
            import time
            start_time = time.time()  # 使用time.time()保持一致
            self.active_progress[analysis_id] = {
                'symbol': symbol,
                'start_time': start_time,
                'callback_query': callback_query
            }

            # 显示初始进度，传入开始时间
            await self.display.show_progress_with_knowledge(callback_query, symbol, start_time)

        except Exception as e:
            logger.error(f"启动进度显示失败: {e}")

    async def update_to_ai_analysis(self, analysis_id: str) -> None:
        """更新到AI分析阶段"""
        try:
            if analysis_id in self.active_progress:
                progress_info = self.active_progress[analysis_id]
                await self.display.show_ai_analysis_progress(
                    progress_info['callback_query'],
                    progress_info['symbol'],
                    progress_info['start_time']
                )
        except Exception as e:
            logger.error(f"更新AI分析进度失败: {e}")
    
    async def complete_analysis(self, analysis_id: str) -> None:
        """完成分析"""
        try:
            if analysis_id in self.active_progress:
                progress_info = self.active_progress[analysis_id]
                await self.display.show_completion_message(
                    progress_info['callback_query'], 
                    progress_info['symbol']
                )
                
                # 清理进度记录
                del self.active_progress[analysis_id]
                
        except Exception as e:
            logger.error(f"完成分析进度失败: {e}")

# 全局进度管理器实例
progress_manager = ProgressManager()
# ==== END progress_display.py ====

# ==== BEGIN markdown_to_image_renderer.py ====
"""
Markdown转PNG图片渲染器
使用Playwright将AI分析报告渲染为高质量的PNG图片
"""

import os
import asyncio
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MarkdownImageRenderer:
    """Markdown转图片渲染器"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        # 不再持久化单个页面，改为每次渲染创建独立上下文/页面，避免并发污染
        self.page = None  # 保持属性以兼容旧代码路径，但不再使用
        self.context = None  # 持久化浏览器上下文，渲染时每次新建页面
        self._user_data_dir = None  # 持久化上下文的用户数据目录
        # 初始化/渲染并发控制
        try:
            import asyncio as _asyncio  # 局部导入以避免顶层循环依赖
            self._init_lock = _asyncio.Lock()
            # 控制并发渲染，避免资源争用；如需提高并发可调整值
            self._render_semaphore = _asyncio.Semaphore(3)
        except Exception:
            self._init_lock = None
            self._render_semaphore = None
        
        # 高分辨率优化样式配置
        self.default_style = """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                width: 1920px;  /* 提高到1920px以匹配新的视口宽度 */
                margin: 0;
                padding: 80px;  /* 增加内边距 */
                background: #f5f5f5;
                font-size: 28px;  /* 提高基础字体大小 */
                -webkit-font-smoothing: antialiased;  /* 字体抗锯齿 */
                -moz-osx-font-smoothing: grayscale;   /* Firefox字体平滑 */
                text-rendering: optimizeLegibility;   /* 优化文本渲染 */
            }

            .container {
                background: white;
                padding: 80px;  /* 增加内边距 */
                margin: 0;
                border-radius: 24px;  /* 稍微增加圆角 */
                box-shadow: 0 24px 72px rgba(0,0,0,0.3);  /* 增强阴影效果 */
            }

            h1 {
                color: #2c3e50;
                border-bottom: 6px solid #888;  /* 增加边框厚度 */
                padding-bottom: 20px;
                margin-bottom: 35px;
                font-size: 64px;  /* 提高字体大小 */
                font-weight: 700;
                text-rendering: optimizeLegibility;
            }

            h2 {
                color: #34495e;
                margin-top: 40px;
                margin-bottom: 25px;
                font-size: 48px;  /* 提高字体大小 */
                font-weight: 600;
                border-left: 8px solid #888;  /* 增加边框厚度 */
                padding-left: 35px;
                text-rendering: optimizeLegibility;
            }

            h3 {
                color: #2c3e50;
                margin-top: 30px;
                margin-bottom: 20px;
                font-size: 36px;  /* 提高字体大小 */
                font-weight: 600;
                text-rendering: optimizeLegibility;
            }

            p {
                margin-bottom: 24px;
                text-align: justify;
                font-size: 28px;  /* 提高字体大小 */
                line-height: 1.7;  /* 稍微增加行高 */
                text-rendering: optimizeLegibility;
            }

            ul, ol {
                margin-bottom: 30px;
                padding-left: 50px;  /* 增加缩进 */
            }

            li {
                margin-bottom: 15px;
                font-size: 28px;  /* 提高字体大小 */
                line-height: 1.6;
                text-rendering: optimizeLegibility;
            }

            strong {
                color: #2c3e50;
                font-weight: 600;
                text-rendering: optimizeLegibility;
            }

            em {
                color: #7f8c8d;
                font-style: italic;
                text-rendering: optimizeLegibility;
            }

            code {
                background: #f8f9fa;
                padding: 8px 14px;  /* 增加内边距 */
                border-radius: 6px;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                font-size: 26px;  /* 提高字体大小 */
                color: #666;
                border: 1px solid #ddd;
                text-rendering: optimizeLegibility;
            }

            pre {
                background: #2c3e50;
                color: #ecf0f1;
                padding: 40px;  /* 增加内边距 */
                border-radius: 12px;
                overflow-x: auto;
                margin: 40px 0;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                font-size: 26px;  /* 提高字体大小 */
                line-height: 1.7;
                text-rendering: optimizeLegibility;
            }

            blockquote {
                border-left: 8px solid #888;  /* 增加边框厚度 */
                margin: 40px 0;
                padding: 35px 40px;  /* 增加内边距 */
                background: #f8f9fa;
                border-radius: 0 12px 12px 0;
                font-style: italic;
                color: #555;
                font-size: 28px;  /* 提高字体大小 */
                text-rendering: optimizeLegibility;
            }

            table {
                border-collapse: collapse;
                width: 100%;
                margin: 35px 0;
                font-size: 22px;  /* 提高字体大小 */
                background: white;
                box-shadow: 0 3px 12px rgba(0,0,0,0.1);  /* 增强阴影 */
                border-radius: 10px;
                overflow: hidden;
                table-layout: fixed;
            }

            th, td {
                border: 1px solid #ddd;
                padding: 15px 10px;  /* 增加内边距 */
                text-align: left;
                vertical-align: top;
                word-wrap: break-word;
                overflow-wrap: break-word;
                white-space: normal;
                max-width: 0;
                text-rendering: optimizeLegibility;
            }

            th {
                background: #888;
                color: white;
                font-weight: 600;
                font-size: 20px;  /* 提高字体大小 */
                padding: 12px 8px;
                text-rendering: optimizeLegibility;
            }

            tr:nth-child(even) {
                background: #f8f9fa;
            }

            /* 多列表格特殊优化 */
            table:has(th:nth-child(7)),
            table th:nth-child(n+7),
            table td:nth-child(n+7) {
                font-size: 14px;
                padding: 8px 4px;
            }

            /* 技术指标表格优化 */
            table th:first-child,
            table td:first-child {
                min-width: 120px;
                font-weight: 600;
            }

            /* 数值列优化 */
            table td:not(:first-child) {
                font-size: 16px;
                text-align: center;
            }

            .emoji {
                font-size: 22px;
            }

            /* 涨跌颜色样式 */
            .bullish {
                color: #27ae60;
                font-weight: bold;
            }

            .bearish {
                color: #e74c3c;
                font-weight: bold;
            }

            .neutral {
                color: #95a5a6;
                font-weight: bold;
            }

            /* 置信度样式 */
            .confidence-high {
                color: #27ae60;
                font-weight: bold;
                background: rgba(39, 174, 96, 0.1);
                padding: 2px 6px;
                border-radius: 3px;
            }

            .confidence-medium {
                color: #f39c12;
                font-weight: bold;
                background: rgba(243, 156, 18, 0.1);
                padding: 2px 6px;
                border-radius: 3px;
            }

            .confidence-low {
                color: #e74c3c;
                font-weight: bold;
                background: rgba(231, 76, 60, 0.1);
                padding: 2px 6px;
                border-radius: 3px;
            }
            
            .emoji {
                font-size: 22px;
            }

            .highlight {
                background: linear-gradient(120deg, #a8edea 0%, #fed6e3 100%);
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: 500;
            }

            .footer {
                margin-top: 60px;
                padding-top: 30px;
                border-top: 1px solid #eee;
                text-align: center;
                color: #7f8c8d;
                font-size: 18px;
            }
            
            /* 特殊样式 */
            .bullish { color: #27ae60; font-weight: 600; }
            .bearish { color: #e74c3c; font-weight: 600; }
            .neutral { color: #f39c12; font-weight: 600; }
            
            .price-up { color: #27ae60; }
            .price-down { color: #e74c3c; }
            .price-neutral { color: #7f8c8d; }
            
            .confidence-high {
                background: linear-gradient(45deg, #27ae60, #2ecc71);
                color: white;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 20px;
            }

            .confidence-medium {
                background: linear-gradient(45deg, #f39c12, #e67e22);
                color: white;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 20px;
            }

            .confidence-low {
                background: linear-gradient(45deg, #e74c3c, #c0392b);
                color: white;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 20px;
            }
        </style>
        """
    
    async def initialize(self):
        """初始化Playwright与浏览器（带锁与重试）"""
        # 避免重复初始化
        if self.browser:
            try:
                if getattr(self.browser, "is_connected", None) and self.browser.is_connected():
                    return True
            except Exception:
                pass

        lock = self._init_lock
        if lock is not None:
            # 串行化初始化，避免并发竞争
            async with lock:
                # 双重检查
                if self.browser:
                    try:
                        if getattr(self.browser, "is_connected", None) and self.browser.is_connected():
                            return True
                    except Exception:
                        pass
                return await self._do_initialize()
        else:
            return await self._do_initialize()

    async def _do_initialize(self):
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()

            launch_args_primary = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',  # 关键：避免/dev/shm过小导致崩溃
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--force-device-scale-factor=2',
                '--high-dpi-support=1',
                '--force-color-profile=srgb'
            ]

            try:
                # 使用持久化上下文，避免频繁 new_context 引起的崩溃
                import tempfile
                self._user_data_dir = tempfile.mkdtemp(prefix='pw-persistent-')
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self._user_data_dir,
                    headless=True,
                    args=launch_args_primary,
                    viewport={"width": 1920, "height": 1080},
                    device_scale_factor=2
                )
                # 兼容旧逻辑，保留 browser 引用
                try:
                    self.browser = self.context.browser
                except Exception:
                    self.browser = None
            except Exception as primary_error:
                # 回退方案：在受限环境再加一些稳定性参数
                logger.warning(f"⚠️ Chromium启动失败，尝试回退参数: {primary_error}")
                fallback_args = launch_args_primary + [
                    '--no-zygote',
                    '--single-process'
                ]
                import tempfile
                self._user_data_dir = tempfile.mkdtemp(prefix='pw-persistent-')
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self._user_data_dir,
                    headless=True,
                    args=fallback_args,
                    viewport={"width": 1920, "height": 1080},
                    device_scale_factor=2
                )
                try:
                    self.browser = self.context.browser
                except Exception:
                    self.browser = None

            # 健康检查：尝试创建并关闭一个页面
            try:
                _page = await self.context.new_page()
                await _page.close()
            except Exception as health_error:
                logger.warning(f"⚠️ 启动后健康检查失败，重建浏览器: {health_error}")
                await self.close()
                return await self._do_initialize()

            logger.info("✅ Markdown渲染器初始化成功")
            return True

        except ImportError as import_error:
            logger.error("❌ Playwright未安装，请运行: pip install playwright && playwright install chromium")
            logger.error(f"❌ 导入错误详情: {str(import_error)}")
            return False
        except Exception as e:
            logger.error(f"❌ Markdown渲染器初始化失败: {str(e)}")
            logger.error(f"❌ 初始化错误类型: {type(e).__name__}")

            # 添加详细的调试信息
            import traceback
            logger.error(f"❌ 初始化错误堆栈: {traceback.format_exc()}")

            # 检查系统环境
            try:
                import sys
                logger.error(f"❌ Python版本: {sys.version}")
                logger.error(f"❌ 系统平台: {sys.platform}")
            except Exception:
                pass

            # 清理损坏状态
            try:
                if self.context:
                    await self.context.close()
            except Exception:
                pass
            try:
                if self.playwright:
                    await self.playwright.stop()
            except Exception:
                pass
            self.browser = None
            self.context = None
            self.playwright = None
            return False
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("✅ Markdown渲染器已关闭")
        except Exception as e:
            logger.error(f"关闭渲染器失败: {str(e)}")
    
    def preprocess_markdown(self, markdown_text: str) -> str:
        """预处理Markdown文本，增强样式"""
        # 处理特殊标记
        processed = markdown_text
        
        # 处理方向指示符
        processed = processed.replace('🟢🔼', '<span class="bullish">🟢🔼</span>')
        processed = processed.replace('🔴🔽', '<span class="bearish">🔴🔽</span>')
        processed = processed.replace('⚪→', '<span class="neutral">⚪→</span>')
        
        # 处理置信度
        import re
        confidence_pattern = r'置信度[：:]\s*(\d+)%'
        def replace_confidence(match):
            confidence = int(match.group(1))
            if confidence >= 80:
                return f'置信度: <span class="confidence-high">{confidence}%</span>'
            elif confidence >= 60:
                return f'置信度: <span class="confidence-medium">{confidence}%</span>'
            else:
                return f'置信度: <span class="confidence-low">{confidence}%</span>'
        
        processed = re.sub(confidence_pattern, replace_confidence, processed)
        
        # 处理价格变化
        price_up_pattern = r'\+[\d.]+%'
        price_down_pattern = r'-[\d.]+%'
        
        processed = re.sub(price_up_pattern, lambda m: f'<span class="price-up">{m.group()}</span>', processed)
        processed = re.sub(price_down_pattern, lambda m: f'<span class="price-down">{m.group()}</span>', processed)
        
        return processed
    
    async def render_markdown_to_image(self, markdown_text: str, 
                                     output_path: str = None,
                                     title: str = None,
                                     custom_style: str = None) -> Optional[str]:
        """
        将Markdown文本渲染为PNG图片
        
        Args:
            markdown_text: Markdown文本
            output_path: 输出文件路径，如果为None则自动生成
            title: 报告标题
            custom_style: 自定义CSS样式
            
        Returns:
            生成的图片文件路径
        """
        # 控制并发渲染，避免共享资源竞争
        semaphore = self._render_semaphore
        if semaphore is not None:
            async with semaphore:
                return await self._render_markdown_to_image_impl(markdown_text, output_path, title, custom_style)
        # 如果信号量不可用（极端情况），直接渲染
        return await self._render_markdown_to_image_impl(markdown_text, output_path, title, custom_style)

    async def _render_markdown_to_image_impl(self, markdown_text: str,
                                             output_path: str = None,
                                             title: str = None,
                                             custom_style: str = None) -> Optional[str]:
        try:
            if not await self.initialize():
                return None

            # 预处理Markdown
            processed_markdown = self.preprocess_markdown(markdown_text)
            
            # 转换Markdown为HTML
            html_content = await self._markdown_to_html(processed_markdown, title, custom_style)
            
            # 生成输出路径
            if not output_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f"ai_analysis_report_{timestamp}.png"

            # 验证输出路径
            logger.info(f"📝 准备生成PNG图片: {output_path}")

            # 确保输出目录存在
            import os
            output_dir = os.path.dirname(output_path) if os.path.dirname(output_path) else '.'
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    logger.info(f"📁 创建输出目录: {output_dir}")
                except Exception as dir_error:
                    logger.error(f"❌ 创建输出目录失败: {str(dir_error)}")
                    raise
            
            # 使用持久化上下文，每次渲染仅新建页面
            try:
                page = await self.context.new_page()
            except Exception:
                # 上下文可能已关闭，重建后再试一次
                await self.close()
                if not await self.initialize():
                    return None
                page = await self.context.new_page()

            await page.set_content(html_content, wait_until='networkidle')
            await asyncio.sleep(2)

            logger.info(f"📸 开始截图...")
            await page.screenshot(
                path=output_path,
                full_page=True,
                type='png',
                omit_background=False,
                animations='disabled'
            )

            # 验证文件是否成功生成
            import os
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"✅ PNG图片生成成功: {output_path}")
                logger.info(f"📏 文件大小: {file_size:,} 字节 ({file_size/1024:.1f} KB)")

                # 验证文件是否为有效的PNG格式
                try:
                    with open(output_path, 'rb') as f:
                        header = f.read(8)
                        if header.startswith(b'\x89PNG\r\n\x1a\n'):
                            logger.info(f"✅ PNG文件格式验证通过")
                        else:
                            logger.warning(f"⚠️ PNG文件格式可能异常")
                except Exception as verify_error:
                    logger.warning(f"⚠️ PNG文件格式验证失败: {str(verify_error)}")

                return output_path
            else:
                logger.error(f"❌ PNG文件生成失败: 文件不存在 - {output_path}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Markdown渲染失败: {str(e)}")
            logger.error(f"❌ 错误类型: {type(e).__name__}")

            # 添加详细的调试信息
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")

            # 记录关键参数信息
            logger.error(f"❌ 输出路径: {output_path}")
            logger.error(f"❌ 标题: {title}")
            logger.error(f"❌ Markdown内容长度: {len(markdown_text) if markdown_text else 0} 字符")

            # 检查浏览器状态
            # 针对浏览器/目标关闭的恢复性重试
            try:
                err_text = str(e)
                if 'TargetClosedError' in err_text or 'browser has been closed' in err_text.lower():
                    logger.warning("🔁 检测到浏览器已关闭，尝试自动重建后重试一次...")
                    await self.close()
                    await asyncio.sleep(0.5)
                    if await self.initialize():
                        return await self._render_markdown_to_image_impl(markdown_text, output_path, title, custom_style)
            except Exception:
                pass

            return None
        finally:
            # 关闭上下文与页面，防止资源泄露
            try:
                if 'page' in locals() and page:
                    await page.close()
            except Exception:
                pass




    async def _markdown_to_html(self, markdown_text: str, title: str = None, custom_style: str = None) -> str:
        """将Markdown转换为HTML"""
        try:
            import markdown
            
            # 配置Markdown扩展
            extensions = [
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code',
                'markdown.extensions.codehilite',
                'markdown.extensions.toc',
                'markdown.extensions.nl2br'
            ]
            
            # 转换Markdown
            md = markdown.Markdown(extensions=extensions)
            html_body = md.convert(markdown_text)
            
            # 构建完整HTML
            html_content = f"""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{title or 'AI分析报告'}</title>
                {custom_style or self.default_style}
            </head>
            <body>
                <div class="container">
                    {html_body}
                    <div class="footer">
                        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>由AI量化分析系统生成</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html_content
            
        except ImportError:
            logger.error("❌ markdown库未安装，请运行: pip install markdown")
            return self._simple_markdown_to_html(markdown_text, title)
        except Exception as e:
            logger.error(f"Markdown转HTML失败: {str(e)}")
            return self._simple_markdown_to_html(markdown_text, title)
    
    def _simple_markdown_to_html(self, markdown_text: str, title: str = None) -> str:
        """简单的Markdown转HTML（备用方案）"""
        # 简单的Markdown解析
        html_body = markdown_text
        
        # 基本替换
        import re
        
        # 标题
        html_body = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
        
        # 粗体和斜体
        html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
        html_body = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_body)
        
        # 段落
        paragraphs = html_body.split('\n\n')
        html_body = '</p><p>'.join(paragraphs)
        html_body = f'<p>{html_body}</p>'
        
        # 构建完整HTML
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title or 'AI分析报告'}</title>
            {self.default_style}
        </head>
        <body>
            <div class="container">
                {f'<h1>{title}</h1>' if title else ''}
                {html_body}
                <div class="footer">
                    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>由AI量化分析系统生成</p>
                </div>
            </div>
        </body>
        </html>
        """

# 全局渲染器实例
_renderer_instance = None

async def get_renderer():
    """获取全局渲染器实例"""
    global _renderer_instance
    if _renderer_instance is None:
        _renderer_instance = MarkdownImageRenderer()
        await _renderer_instance.initialize()
    return _renderer_instance

async def render_ai_analysis_to_image(ai_analysis_text: str, 
                                    symbol: str = None,
                                    timeframe: str = None,
                                    output_path: str = None) -> Optional[str]:
    """
    将AI分析报告渲染为图片
    
    Args:
        ai_analysis_text: AI分析文本
        symbol: 币种符号
        timeframe: 时间周期
        output_path: 输出路径
        
    Returns:
        生成的图片文件路径
    """
    try:
        renderer = await get_renderer()
        
        # 构建标题
        title_parts = []
        if symbol:
            title_parts.append(symbol.replace('USDT', ''))
        title_parts.append('AI量化分析报告')
        if timeframe:
            title_parts.append(f'({timeframe})')
        
        title = ' '.join(title_parts)
        
        # 渲染图片
        return await renderer.render_markdown_to_image(
            ai_analysis_text,
            output_path=output_path,
            title=title
        )
        
    except Exception as e:
        logger.error(f"渲染AI分析报告失败: {str(e)}")
        return None

# ==== END markdown_to_image_renderer.py ====

