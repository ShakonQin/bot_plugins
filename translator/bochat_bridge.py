"""BoChat 平台桥接层：WebSocket 监听消息 + HTTP 发送消息"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

from bochat_sdk import BochatClient, MessageResponse, WsDispatcher

LOG = logging.getLogger("TransBridge")


class BochatBridge:

    def __init__(
        self,
        base_url: str,
        bot_token: str,
        group_ids: list[str] | None = None,
    ):
        self._base_url = base_url
        self._bot_token = bot_token
        self._group_ids = set(group_ids) if group_ids else None
        self._client: BochatClient | None = None
        self._dispatcher: WsDispatcher | None = None
        self._bot_id: str = ""
        self._on_message: Callable[[MessageResponse], Coroutine[Any, Any, None]] | None = None

    @property
    def bot_id(self) -> str:
        return self._bot_id

    async def start(self) -> None:
        self._client = (
            BochatClient.builder(self._base_url)
            .bot_token(self._bot_token)
            .build()
        )
        LOG.info("BoChat 客户端已初始化（BOT_TOKEN 模式）")

        session = await self._client.ws().build()
        handle = await session.spawn()
        self._dispatcher = handle.into_dispatcher()

        conn = await self._dispatcher.wait_connection_payload(timeout=15)
        self._bot_id = conn.bot_id
        if self._group_ids:
            available = set(conn.group_ids)
            monitored = available & self._group_ids
            LOG.info("BoChat WebSocket 已连接，监控群: %s", ", ".join(monitored) or "(无匹配)")
        else:
            LOG.info("BoChat WebSocket 已连接，可用群: %s", ", ".join(conn.group_ids))

    def register_message_handler(
        self,
        callback: Callable[[MessageResponse], Coroutine[Any, Any, None]],
    ) -> None:
        self._on_message = callback

        if self._dispatcher is None:
            LOG.warning("Dispatcher 尚未初始化，回调将在连接后生效")
            return

        LOG.info("正在注册 WebSocket 消息处理器 (on_message)")

        @self._dispatcher.on_message()
        async def _handler(msg: MessageResponse) -> None:
            LOG.info(
                "收到 WebSocket 消息: group=%s, sender=%s, type=%s",
                msg.group_id, msg.sender_id, msg.msg_type,
            )
            if self._group_ids and msg.group_id not in self._group_ids:
                LOG.debug("消息群 %s 不在监控列表中，跳过", msg.group_id)
                return
            if self._on_message:
                try:
                    await self._on_message(msg)
                except Exception:
                    LOG.exception("处理 BoChat 消息时出错")

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
        if self._dispatcher:
            try:
                await self._dispatcher.shutdown()
            except Exception:
                LOG.exception("关闭 BoChat dispatcher 时出错")
        if self._client:
            try:
                await self._client.close()
            except Exception:
                LOG.exception("关闭 BoChat client 时出错")
        LOG.info("BochatBridge 已关闭")
