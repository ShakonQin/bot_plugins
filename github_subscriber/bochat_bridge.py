"""BoChat 平台桥接层：仅负责登录和发送消息（无 WebSocket 监听）"""

from __future__ import annotations

from ncatbot.utils import get_log

LOG = get_log("GHSubBridge")

from bochat_sdk import BochatClient


class BochatBridge:
    """精简版 BoChat 桥接，只提供消息发送能力。"""

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

        self._client.set_bot_token(selected.token)
        LOG.info("已选择 Bot: %s (%s)", selected.name, selected.bot_id)

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
