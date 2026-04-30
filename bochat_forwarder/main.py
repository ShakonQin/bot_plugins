"""BoChat <-> QQ 双向消息转发插件

基于 NcatBot 插件规范开发，使用 BoChat Python SDK 实现与 BoChat 平台的通信。
支持通过 config.yaml 配置多条转发路由规则，实现灵活的消息桥接。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from ncatbot.core import registrar
from ncatbot.event.qq import GroupMessageEvent, PrivateMessageEvent
from ncatbot.plugin import NcatBotPlugin
from ncatbot.utils import get_log

from bochat_sdk import MessageResponse

from .bochat_bridge import BochatBridge
from .formatter import (
    FormatConfig,
    bochat_msg_to_text,
    matches_keywords,
    qq_msg_to_bochat_text,
)

LOG = get_log("BochatForwarder")


# ── 路由配置数据结构 ──────────────────────────────────────────


@dataclass
class RouteSource:
    bochat_group_id: str = ""
    qq_group_id: int = 0
    qq_user_id: int = 0


@dataclass
class RouteTarget:
    bochat_group_id: str = ""
    qq_group_id: int = 0
    qq_user_id: int = 0


@dataclass
class RouteFilter:
    ignore_bots: bool = True
    keywords: list[str] = field(default_factory=list)


@dataclass
class ForwardRoute:
    name: str
    direction: str  # "bochat_to_qq" | "qq_to_bochat"
    enabled: bool
    source: RouteSource
    target: RouteTarget
    filter: RouteFilter = field(default_factory=RouteFilter)
    format: FormatConfig = field(default_factory=FormatConfig)


def _parse_routes(raw_routes: list[dict[str, Any]]) -> list[ForwardRoute]:
    """从 YAML 配置解析路由规则列表。"""
    routes: list[ForwardRoute] = []
    for item in raw_routes:
        if not item.get("enabled", False):
            continue

        src = item.get("source", {})
        tgt = item.get("target", {})
        flt = item.get("filter", {})
        fmt = item.get("format", {})

        route = ForwardRoute(
            name=item.get("name", "unnamed"),
            direction=item.get("direction", ""),
            enabled=True,
            source=RouteSource(
                bochat_group_id=str(src.get("bochat_group_id", "")),
                qq_group_id=int(src.get("qq_group_id", 0)),
                qq_user_id=int(src.get("qq_user_id", 0)),
            ),
            target=RouteTarget(
                bochat_group_id=str(tgt.get("bochat_group_id", "")),
                qq_group_id=int(tgt.get("qq_group_id", 0)),
                qq_user_id=int(tgt.get("qq_user_id", 0)),
            ),
            filter=RouteFilter(
                ignore_bots=flt.get("ignore_bots", True),
                keywords=flt.get("keywords") or [],
            ),
            format=FormatConfig(
                show_sender=fmt.get("show_sender", True),
                prefix=fmt.get("prefix", "[{sender}] "),
            ),
        )

        if route.direction not in ("bochat_to_qq", "qq_to_bochat"):
            LOG.warning("跳过无效路由 '%s': direction=%s", route.name, route.direction)
            continue

        routes.append(route)
    return routes


# ── 插件主类 ──────────────────────────────────────────────────


class BochatForwarderPlugin(NcatBotPlugin):
    name = "bochat_forwarder"
    version = "1.0.0"
    author = "BoChat Community"
    description = "BoChat <-> QQ 双向消息转发插件"

    def __init__(self) -> None:
        super().__init__()
        self._bridge: BochatBridge | None = None
        self._routes: list[ForwardRoute] = []
        self._bochat_to_qq_routes: list[ForwardRoute] = []
        self._qq_to_bochat_group_routes: dict[int, list[ForwardRoute]] = {}
        self._qq_to_bochat_private_routes: dict[int, list[ForwardRoute]] = {}

    # ── 生命周期 ──────────────────────────────────────────────

    async def on_load(self) -> None:
        config = self._load_config()
        if config is None:
            return

        bochat_cfg = config.get("bochat", {})
        raw_routes = config.get("routes", [])
        self._routes = _parse_routes(raw_routes)

        if not self._routes:
            LOG.warning("没有已启用的转发路由，插件将空转")
            return

        self._index_routes()
        LOG.info(
            "已加载 %d 条转发路由 (bochat->qq: %d, qq->bochat: %d)",
            len(self._routes),
            len(self._bochat_to_qq_routes),
            sum(len(v) for v in self._qq_to_bochat_group_routes.values())
            + sum(len(v) for v in self._qq_to_bochat_private_routes.values()),
        )

        self._bridge = BochatBridge(
            base_url=bochat_cfg.get("base_url", "http://127.0.0.1:8080"),
            account=bochat_cfg.get("account", ""),
            password=bochat_cfg.get("password", ""),
            bot_id=bochat_cfg.get("bot_id", ""),
        )

        try:
            await self._bridge.start()
            self._bridge.register_message_handler(self._on_bochat_message)
            LOG.info("BochatForwarder 插件加载完成")
        except Exception:
            LOG.exception("连接 BoChat 平台失败，bochat->qq 方向转发不可用")

    async def on_close(self) -> None:
        if self._bridge:
            await self._bridge.stop()
        LOG.info("BochatForwarder 插件已卸载")

    # ── 配置加载 ──────────────────────────────────────────────

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

    def _index_routes(self) -> None:
        """按方向和来源索引路由，加速消息匹配。"""
        self._bochat_to_qq_routes = [
            r for r in self._routes if r.direction == "bochat_to_qq"
        ]
        for r in self._routes:
            if r.direction != "qq_to_bochat":
                continue
            if r.source.qq_group_id:
                self._qq_to_bochat_group_routes.setdefault(
                    r.source.qq_group_id, []
                ).append(r)
            elif r.source.qq_user_id:
                self._qq_to_bochat_private_routes.setdefault(
                    r.source.qq_user_id, []
                ).append(r)

    # ── BoChat -> QQ 转发 ─────────────────────────────────────

    async def _on_bochat_message(self, msg: MessageResponse) -> None:
        """收到 BoChat 消息时，按路由规则转发到 QQ。"""
        for route in self._bochat_to_qq_routes:
            if route.source.bochat_group_id != msg.group_id:
                continue

            # 忽略自身 Bot 发送的消息，防止回环
            if route.filter.ignore_bots and self._bridge:
                if msg.sender_id == self._bridge.bot_id:
                    continue

            text = bochat_msg_to_text(
                content=msg.content.to_dict(),
                msg_type=msg.msg_type,
                sender_name=msg.sender_name,
                fmt=route.format,
            )
            if text is None:
                continue

            if not matches_keywords(text, route.filter.keywords or None):
                continue

            try:
                if route.target.qq_group_id:
                    await self.api.qq.post_group_msg(
                        route.target.qq_group_id, text=text
                    )
                    LOG.info(
                        "[%s] BoChat(%s) -> QQ群(%s): %s",
                        route.name, msg.group_id, route.target.qq_group_id,
                        text[:50],
                    )
                elif route.target.qq_user_id:
                    await self.api.qq.post_private_msg(
                        route.target.qq_user_id, text=text
                    )
                    LOG.info(
                        "[%s] BoChat(%s) -> QQ私聊(%s): %s",
                        route.name, msg.group_id, route.target.qq_user_id,
                        text[:50],
                    )
            except Exception:
                LOG.exception("[%s] 转发 BoChat->QQ 失败", route.name)

    # ── QQ -> BoChat 转发 ─────────────────────────────────────

    @registrar.on_group_message()
    async def on_qq_group_message(self, event: GroupMessageEvent) -> None:
        """收到 QQ 群消息时，按路由规则转发到 BoChat。"""
        group_id = event.group_id
        routes = self._qq_to_bochat_group_routes.get(group_id, [])
        if not routes:
            return

        sender_name = event.sender.get("nickname", "") if isinstance(event.sender, dict) else str(event.user_id)

        for route in routes:
            if not self._bridge:
                continue

            text = qq_msg_to_bochat_text(
                raw_message=event.raw_message,
                sender_name=sender_name,
                fmt=route.format,
            )
            if text is None:
                continue

            if not matches_keywords(text, route.filter.keywords or None):
                continue

            try:
                await self._bridge.send_text(route.target.bochat_group_id, text)
                LOG.info(
                    "[%s] QQ群(%s) -> BoChat(%s): %s",
                    route.name, group_id, route.target.bochat_group_id,
                    text[:50],
                )
            except Exception:
                LOG.exception("[%s] 转发 QQ群->BoChat 失败", route.name)

    @registrar.on_private_message()
    async def on_qq_private_message(self, event: PrivateMessageEvent) -> None:
        """收到 QQ 私聊消息时，按路由规则转发到 BoChat。"""
        user_id = event.user_id
        routes = self._qq_to_bochat_private_routes.get(user_id, [])
        if not routes:
            return

        sender_name = event.sender.get("nickname", "") if isinstance(event.sender, dict) else str(event.user_id)

        for route in routes:
            if not self._bridge:
                continue

            text = qq_msg_to_bochat_text(
                raw_message=event.raw_message,
                sender_name=sender_name,
                fmt=route.format,
            )
            if text is None:
                continue

            if not matches_keywords(text, route.filter.keywords or None):
                continue

            try:
                await self._bridge.send_text(route.target.bochat_group_id, text)
                LOG.info(
                    "[%s] QQ私聊(%s) -> BoChat(%s): %s",
                    route.name, user_id, route.target.bochat_group_id,
                    text[:50],
                )
            except Exception:
                LOG.exception("[%s] 转发 QQ私聊->BoChat 失败", route.name)
