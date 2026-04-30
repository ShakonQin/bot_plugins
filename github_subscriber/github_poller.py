"""GitHub Events API 轮询客户端"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

LOG = logging.getLogger("GitHubPoller")

EVENTS_URL = "https://api.github.com/repos/{repo}/events"


@dataclass
class RepoState:
    """单个仓库的轮询状态"""
    repo: str
    etag: str = ""
    last_event_id: str = ""
    poll_interval: int = 60


class GitHubPoller:
    """异步轮询 GitHub 仓库事件，支持 ETag 条件请求和事件去重。"""

    def __init__(self, token: str = "", poll_interval: int = 60):
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._client = httpx.AsyncClient(headers=headers, timeout=30)
        self._default_interval = max(poll_interval, 30)
        self._repos: dict[str, RepoState] = {}

    def add_repo(self, repo: str) -> None:
        if repo not in self._repos:
            self._repos[repo] = RepoState(repo=repo, poll_interval=self._default_interval)

    async def poll(self, repo: str) -> list[dict[str, Any]]:
        """轮询指定仓库的新事件，返回按时间正序排列的新事件列表。"""
        state = self._repos.get(repo)
        if not state:
            return []

        url = EVENTS_URL.format(repo=repo)
        req_headers: dict[str, str] = {}
        if state.etag:
            req_headers["If-None-Match"] = state.etag

        try:
            resp = await self._client.get(url, headers=req_headers)
        except httpx.HTTPError as e:
            LOG.warning("请求 GitHub API 失败 [%s]: %s", repo, e)
            return []

        if resp.status_code == 304:
            return []

        if resp.status_code == 403:
            remaining = resp.headers.get("x-ratelimit-remaining", "?")
            LOG.warning("GitHub API 速率限制 [%s], 剩余: %s", repo, remaining)
            return []

        if resp.status_code != 200:
            LOG.warning("GitHub API 返回 %d [%s]", resp.status_code, repo)
            return []

        if etag := resp.headers.get("etag"):
            state.etag = etag

        if interval := resp.headers.get("x-poll-interval"):
            state.poll_interval = max(int(interval), 30)

        try:
            events: list[dict[str, Any]] = resp.json()
        except Exception:
            LOG.warning("解析 GitHub 事件响应失败 [%s]", repo)
            return []

        if not events:
            return []

        new_events: list[dict[str, Any]] = []
        if not state.last_event_id:
            state.last_event_id = str(events[0].get("id", ""))
            new_events = events[:3]
        else:
            for ev in events:
                if str(ev.get("id", "")) == state.last_event_id:
                    break
                new_events.append(ev)
            if new_events:
                state.last_event_id = str(new_events[0].get("id", ""))

        new_events.reverse()
        return new_events

    async def close(self) -> None:
        await self._client.aclose()
