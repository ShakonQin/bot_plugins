"""BoChat 平台桥接层：仅负责发送消息（无 WebSocket 监听）"""

from __future__ import annotations

import logging

from bochat_sdk import BochatClient

LOG = logging.getLogger("GHSubBridge")


class BochatBridge:
    """精简版 BoChat 桥接，只提供消息发送能力。"""

    def __init__(
        self,
        base_url: str,
        bot_token: str,
    ):
        self._base_url = base_url
        self._bot_token = bot_token
        self._client: BochatClient | None = None

    async def start(self) -> None:
        self._client = (
            BochatClient.builder(self._base_url)
            .bot_token(self._bot_token)
            .build()
        )
        LOG.info("BoChat 客户端已初始化（BOT_TOKEN 模式）")

    async def send_text(self, group_id: str, text: str) -> None:
        if not self._client:
            LOG.error("BochatBridge 尚未启动，无法发送消息")
            return
        try:
            await self._client.messages().send_text(group_id, text)
            LOG.debug("已发送消息到 BoChat 群 %s", group_id)
        except Exception:
            LOG.exception("发送消息到 BoChat 群 %s 失败", group_id)

    async def stop(self) -> None:
        if self._client:
            try:
                await self._client.close()
            except Exception:
                LOG.exception("关闭 BoChat client 时出错")
        LOG.info("BochatBridge 已关闭")
