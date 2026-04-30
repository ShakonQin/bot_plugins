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
        account: str,
        password: str,
        bot_id: str = "",
    ):
        self._base_url = base_url
        self._account = account
        self._password = password
        self._preferred_bot_id = bot_id
        self._client: BochatClient | None = None
        self._dispatcher: WsDispatcher | None = None
        self._bot_id: str = ""
        self._on_message: Callable[[MessageResponse], Coroutine[Any, Any, None]] | None = None

    @property
    def bot_id(self) -> str:
        return self._bot_id

    async def start(self) -> None:
        self._client = BochatClient.builder(self._base_url).build()

        LOG.info("正在登录 BoChat 账号: %s", self._account)
        await (
            self._client.auth()
            .login()
            .account(self._account)
            .password(self._password)
            .send()
        )
        LOG.info("BoChat 登录成功")

        bots = await self._client.bots().list()
        if not bots:
            raise RuntimeError("BoChat 账号下没有可用的 Bot")

        selected = None
        if self._preferred_bot_id:
            selected = next((b for b in bots if b.bot_id == self._preferred_bot_id), None)
            if not selected:
                LOG.warning("指定的 bot_id=%s 未找到，将使用第一个活跃 Bot", self._preferred_bot_id)

        if not selected:
            active_bots = [b for b in bots if b.status == "active"]
            if not active_bots:
                raise RuntimeError("没有处于 active 状态的 Bot")
            selected = active_bots[0]

        self._bot_id = selected.bot_id
        self._client.set_bot_token(selected.token)
        LOG.info("已选择 Bot: %s (%s)", selected.name, selected.bot_id)

        session = await self._client.ws().build()
        handle = await session.spawn()
        self._dispatcher = handle.into_dispatcher()

        conn = await self._dispatcher.wait_connection_payload(timeout=15)
        LOG.info("BoChat WebSocket 已连接，可用群: %s", ", ".join(conn.group_ids))

    def register_message_handler(
        self,
        callback: Callable[[MessageResponse], Coroutine[Any, Any, None]],
    ) -> None:
        self._on_message = callback

        if self._dispatcher is None:
            LOG.warning("Dispatcher 尚未初始化，回调将在连接后生效")
            return

        @self._dispatcher.on_message()
        async def _handler(msg: MessageResponse) -> None:
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
