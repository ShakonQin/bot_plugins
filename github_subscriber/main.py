"""GitHub 仓库事件订阅服务

独立于 ncatbot 运行，轮询 GitHub Events API 监控仓库动态，
将事件格式化后推送至 BoChat 群聊。
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .bochat_bridge import BochatBridge
from .event_formatter import format_event, normalize_event_type
from .github_poller import GitHubPoller

LOG = logging.getLogger("GitHubSubscriber")

VALID_EVENTS = {
    "issues", "pull_request", "release", "star", "push",
    "fork", "issue_comment", "create", "delete",
}
REPO_PATTERN = re.compile(r"^[\w.\-]+/[\w.\-]+$")


# ── 配置数据结构 ─────────────────────────────────────────────


@dataclass
class Target:
    id: str  # BoChat 群 ID


@dataclass
class Subscription:
    name: str
    repo: str
    enabled: bool
    events: list[str]
    targets: list[Target]


def _parse_subscriptions(raw: list[dict[str, Any]]) -> list[Subscription]:
    subs: list[Subscription] = []
    for item in raw:
        if not item.get("enabled", False):
            continue

        repo = item.get("repo", "")
        if not REPO_PATTERN.match(repo):
            LOG.warning("跳过无效仓库格式: '%s'", repo)
            continue

        events = item.get("events") or []
        invalid = [e for e in events if e not in VALID_EVENTS]
        if invalid:
            LOG.warning("仓库 '%s' 包含无效事件类型: %s", repo, invalid)
            events = [e for e in events if e in VALID_EVENTS]

        targets: list[Target] = []
        for t in item.get("targets", []):
            t_id = t.get("id", "")
            if isinstance(t_id, str) and t_id:
                targets.append(Target(id=t_id))
            else:
                LOG.warning("仓库 '%s' 包含无效目标: id=%s", repo, t_id)

        if not targets:
            LOG.warning("仓库 '%s' 没有有效推送目标，跳过", repo)
            continue

        subs.append(Subscription(
            name=item.get("name", repo),
            repo=repo,
            enabled=True,
            events=events,
            targets=targets,
        ))
    return subs


# ── 服务主类 ─────────────────────────────────────────────────


class GitHubSubscriberService:
    """独立的 GitHub 订阅服务，不依赖 ncatbot。"""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else Path(__file__).parent / "config.yaml"
        self._poller: GitHubPoller | None = None
        self._bridge: BochatBridge | None = None
        self._subs: list[Subscription] = []
        self._poll_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """启动服务。"""
        config = self._load_config()
        if config is None:
            return

        gh_cfg = config.get("github", {})
        bochat_cfg = config.get("bochat", {})
        raw_subs = config.get("subscriptions", [])

        self._subs = _parse_subscriptions(raw_subs)
        if not self._subs:
            LOG.warning("没有已启用的订阅规则，服务将空转")
            return

        LOG.info("已加载 %d 条订阅规则", len(self._subs))

        token = gh_cfg.get("token", "")
        interval = max(int(gh_cfg.get("poll_interval", 60)), 30)
        self._poller = GitHubPoller(token=token, poll_interval=interval)

        for sub in self._subs:
            self._poller.add_repo(sub.repo)

        self._bridge = BochatBridge(
            base_url=bochat_cfg.get("base_url", "http://127.0.0.1:8080"),
            account=bochat_cfg.get("account", ""),
            password=bochat_cfg.get("password", ""),
            bot_id=bochat_cfg.get("bot_id", ""),
        )
        try:
            await self._bridge.start()
        except Exception:
            LOG.exception("连接 BoChat 平台失败，推送不可用")
            self._bridge = None

        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop(interval))
        LOG.info("GitHubSubscriber 服务启动完成，轮询间隔: %ds", interval)

    async def stop(self) -> None:
        """停止服务。"""
        self._running = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        if self._poller:
            await self._poller.close()
        if self._bridge:
            await self._bridge.stop()
        LOG.info("GitHubSubscriber 服务已停止")

    async def run_forever(self) -> None:
        """启动服务并持续运行，直到收到取消信号。"""
        await self.start()
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    # ── 配置加载 ─────────────────────────────────────────────

    def _load_config(self) -> dict[str, Any] | None:
        if not self._config_path.exists():
            LOG.error("配置文件不存在: %s", self._config_path)
            return None
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            LOG.exception("读取配置文件失败: %s", self._config_path)
            return None

    # ── 轮询循环 ─────────────────────────────────────────────

    async def _poll_loop(self, interval: int) -> None:
        await asyncio.sleep(5)
        while self._running:
            for sub in self._subs:
                try:
                    await self._poll_subscription(sub)
                except Exception:
                    LOG.exception("[%s] 轮询仓库 %s 时出错", sub.name, sub.repo)
            await asyncio.sleep(interval)

    async def _poll_subscription(self, sub: Subscription) -> None:
        if not self._poller:
            return

        events = await self._poller.poll(sub.repo)
        if not events:
            return

        for event in events:
            event_type = event.get("type", "")
            short_type = normalize_event_type(event_type)

            if sub.events and short_type not in sub.events:
                continue

            text = format_event(event)
            if text is None:
                continue

            await self._dispatch(sub, text)

    async def _dispatch(self, sub: Subscription, text: str) -> None:
        for target in sub.targets:
            try:
                if self._bridge:
                    await self._bridge.send_text(target.id, text)
                    LOG.info(
                        "[%s] -> BoChat(%s): %s",
                        sub.name, target.id, text[:50],
                    )
            except Exception:
                LOG.exception(
                    "[%s] 推送到 BoChat(%s) 失败", sub.name, target.id,
                )
