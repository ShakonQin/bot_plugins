"""中英互译插件

基于 NcatBot 插件规范开发，通过 /trans 命令实现中英文互译。
优先支持 BoChat 群聊，同时兼容 QQ 群聊和私聊场景。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from ncatbot.core import registrar
from ncatbot.event.qq import GroupMessageEvent, PrivateMessageEvent
from ncatbot.plugin import NcatBotPlugin
from ncatbot.utils import get_log

from bochat_sdk import MessageResponse

from .bochat_bridge import BochatBridge
from .translator import LANG_MAP, TranslateClient, TranslateError

LOG = get_log("TranslatorPlugin")

USAGE = (
    "用法: /trans <模式> <文本>\n"
    "模式: c2e (中译英) | e2c (英译中)\n"
    "示例: /trans c2e 你好世界"
)


class TranslatorPlugin(NcatBotPlugin):
    name = "translator"
    version = "1.0.0"
    author = "BoChat Community"
    description = "中英互译插件"

    def __init__(self) -> None:
        super().__init__()
        self._client: TranslateClient | None = None
        self._bridge: BochatBridge | None = None

    # ── 生命周期 ─────────────────────────────────────────────

    async def on_load(self) -> None:
        config = self._load_config()
        if config is None:
            return

        t_cfg = config.get("translate", {})
        provider = t_cfg.get("provider", "mymemory")
        opts = t_cfg.get(provider, {}) or {}
        self._client = TranslateClient(provider=provider, **opts)
        LOG.info("翻译后端: %s", provider)

        bochat_cfg = config.get("bochat", {})
        self._bridge = BochatBridge(
            base_url=bochat_cfg.get("base_url", "http://127.0.0.1:8080"),
            account=bochat_cfg.get("account", ""),
            password=bochat_cfg.get("password", ""),
            bot_id=bochat_cfg.get("bot_id", ""),
        )
        try:
            await self._bridge.start()
            self._bridge.register_message_handler(self._on_bochat_message)
            LOG.info("Translator 插件加载完成 (BoChat + QQ)")
        except Exception:
            LOG.exception("连接 BoChat 平台失败，BoChat 群聊翻译不可用")
            self._bridge = None
            LOG.info("Translator 插件加载完成 (仅 QQ)")

    async def on_close(self) -> None:
        if self._bridge:
            await self._bridge.stop()
        if self._client:
            await self._client.close()
        LOG.info("Translator 插件已卸载")

    # ── 配置加载 ─────────────────────────────────────────────

    def _load_config(self) -> dict[str, Any] | None:
        config_path = Path(__file__).parent / "config.yaml"
        if not config_path.exists():
            LOG.error("配置文件不存在: %s", config_path)
            return None
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            LOG.exception("读取配置文件失败: %s", config_path)
            return None

    # ── 命令解析 ─────────────────────────────────────────────

    @staticmethod
    def _parse_command(raw_message: str) -> tuple[str, str] | None:
        raw_message = raw_message.strip()
        if not raw_message.startswith("/trans "):
            return None

        parts = raw_message.split(None, 2)
        if len(parts) < 3:
            return None

        mode = parts[1].lower()
        text = parts[2].strip()
        if mode not in LANG_MAP or not text:
            return None

        return mode, text

    # ── 翻译并回复 ───────────────────────────────────────────

    async def _handle_translate(self, mode: str, text: str) -> str:
        if not self._client:
            return "翻译服务未初始化，请检查插件配置"
        try:
            result = await self._client.translate(text, mode)
            label = "中→英" if mode == "c2e" else "英→中"
            return f"[{label}] {result}"
        except TranslateError as e:
            LOG.warning("翻译失败: %s", e)
            return f"翻译失败: {e}"
        except Exception:
            LOG.exception("翻译时发生未知错误")
            return "翻译服务异常，请稍后重试"

    # ── BoChat 群聊消息处理 ────────────────────────────────────

    async def _on_bochat_message(self, msg: MessageResponse) -> None:
        LOG.debug(
            "收到 BoChat 消息: group=%s, sender=%s, type=%s, content=%s",
            msg.group_id, msg.sender_id, msg.msg_type, msg.content.to_dict() if hasattr(msg.content, "to_dict") else msg.content,
        )
        if self._bridge and msg.sender_id == self._bridge.bot_id:
            LOG.debug("忽略自身消息")
            return

        content = msg.content.to_dict() if hasattr(msg.content, "to_dict") else {}
        raw_text = content.get("text", "")
        if not raw_text:
            LOG.debug("消息无文本内容，跳过")
            return

        LOG.debug("提取到文本: '%s'", raw_text)
        parsed = self._parse_command(raw_text)
        if parsed is None:
            if raw_text.strip() == "/trans" and self._bridge:
                await self._bridge.send_text(msg.group_id, USAGE)
            return

        mode, text = parsed
        LOG.info("执行翻译命令: mode=%s, text='%s'", mode, text)
        reply = await self._handle_translate(mode, text)
        LOG.info("翻译结果: %s", reply)
        if self._bridge:
            await self._bridge.send_text(msg.group_id, reply)

    # ── QQ 群聊/私聊消息处理 ─────────────────────────────────

    @registrar.on_group_message()
    async def on_group_message(self, event: GroupMessageEvent) -> None:
        parsed = self._parse_command(event.raw_message)
        if parsed is None:
            if event.raw_message.strip() == "/trans":
                await self.api.qq.post_group_msg(event.group_id, text=USAGE)
            return

        mode, text = parsed
        reply = await self._handle_translate(mode, text)
        await self.api.qq.post_group_msg(event.group_id, text=reply)

    @registrar.on_private_message()
    async def on_private_message(self, event: PrivateMessageEvent) -> None:
        parsed = self._parse_command(event.raw_message)
        if parsed is None:
            if event.raw_message.strip() == "/trans":
                await self.api.qq.post_private_msg(event.user_id, text=USAGE)
            return

        mode, text = parsed
        reply = await self._handle_translate(mode, text)
        await self.api.qq.post_private_msg(event.user_id, text=reply)
