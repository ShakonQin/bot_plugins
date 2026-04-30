"""BoChat <-> QQ 消息格式转换器"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FormatConfig:
    """单条路由的格式配置"""
    show_sender: bool = True
    prefix: str = "[{sender}] "


@dataclass
class ForwardMessage:
    """统一的转发消息中间表示"""
    text: str
    sender_name: str
    source_label: str


def bochat_msg_to_text(
    content: dict[str, Any],
    msg_type: str,
    sender_name: str | None,
    fmt: FormatConfig,
) -> str | None:
    """将 BoChat 消息转为可发送到 QQ 的纯文本。

    仅处理 text 类型消息，其他类型返回 None。
    """
    text = content.get("text")
    if not isinstance(text, str) or not text.strip():
        if msg_type == "file":
            url = content.get("url", "")
            text = f"[文件] {url}" if url else "[文件]"
        else:
            return None

    if not fmt.show_sender:
        return text

    sender = sender_name or "未知"
    prefix = fmt.prefix.format(sender=sender, group="")
    return f"{prefix}{text}"


def qq_msg_to_bochat_text(
    raw_message: str,
    sender_name: str,
    fmt: FormatConfig,
) -> str | None:
    """将 QQ 消息转为可发送到 BoChat 的文本。

    过滤 CQ 码中的非文本内容，提取纯文本部分。
    """
    text = _strip_cq_codes(raw_message)
    if not text.strip():
        return None

    if not fmt.show_sender:
        return text

    sender = sender_name or "未知"
    prefix = fmt.prefix.format(sender=sender, group="")
    return f"{prefix}{text}"


def _strip_cq_codes(message: str) -> str:
    """移除 CQ 码，保留纯文本。

    CQ 码格式: [CQ:type,param=value,...]
    对于 image/face 等非文本 CQ 码替换为占位符。
    """
    import re

    def _replace_cq(match: re.Match) -> str:
        cq_type = match.group(1)
        if cq_type == "at":
            params = match.group(2)
            qq_match = re.search(r"qq=(\d+|all)", params)
            if qq_match:
                qq_val = qq_match.group(1)
                return f"@{qq_val}" if qq_val != "all" else "@全体成员"
        elif cq_type == "image":
            return "[图片]"
        elif cq_type == "face":
            return "[表情]"
        elif cq_type == "record":
            return "[语音]"
        elif cq_type == "video":
            return "[视频]"
        elif cq_type == "reply":
            return ""
        return f"[{cq_type}]"

    return re.sub(r"\[CQ:(\w+)([^\]]*)\]", _replace_cq, message)


def matches_keywords(text: str, keywords: list[str] | None) -> bool:
    """检查消息文本是否匹配关键词白名单。空列表或 None 表示不过滤。"""
    if not keywords:
        return True
    return any(kw in text for kw in keywords)
