"""GitHub 事件格式化器：将 API 事件转为结构化中文消息"""

from __future__ import annotations

from typing import Any

EVENT_TYPE_MAP: dict[str, str] = {
    "IssuesEvent": "issues",
    "PullRequestEvent": "pull_request",
    "ReleaseEvent": "release",
    "WatchEvent": "star",
    "PushEvent": "push",
    "ForkEvent": "fork",
    "IssueCommentEvent": "issue_comment",
    "CreateEvent": "create",
    "DeleteEvent": "delete",
}

ACTION_LABELS: dict[str, str] = {
    "opened": "创建",
    "closed": "关闭",
    "reopened": "重新打开",
    "merged": "合并",
    "published": "发布",
    "created": "创建",
    "started": "Star",
}


def normalize_event_type(github_type: str) -> str:
    """将 GitHub API 事件类型映射为配置中的简短名称。"""
    return EVENT_TYPE_MAP.get(github_type, github_type.lower().replace("event", ""))


def format_event(event: dict[str, Any]) -> str | None:
    """将 GitHub 事件格式化为可读的中文消息文本。不支持的事件类型返回 None。"""
    event_type = event.get("type", "")
    repo = event.get("repo", {}).get("name", "unknown/unknown")
    actor = event.get("actor", {}).get("login", "unknown")
    payload = event.get("payload", {})

    formatter = _FORMATTERS.get(event_type)
    if formatter is None:
        return None

    body = formatter(payload, repo, actor)
    if body is None:
        return None

    return body


def _fmt_issues(payload: dict, repo: str, actor: str) -> str | None:
    issue = payload.get("issue", {})
    action = payload.get("action", "")
    if action not in ("opened", "closed", "reopened"):
        return None
    label = ACTION_LABELS.get(action, action)
    title = issue.get("title", "")
    number = issue.get("number", "")
    url = issue.get("html_url", "")
    return (
        f"[{repo}]\n"
        f"Issue #{number} 已{label}\n"
        f"标题: {title}\n"
        f"操作者: {actor}\n"
        f"{url}"
    )


def _fmt_pull_request(payload: dict, repo: str, actor: str) -> str | None:
    pr = payload.get("pull_request", {})
    action = payload.get("action", "")
    if action not in ("opened", "closed", "reopened"):
        return None
    merged = pr.get("merged", False)
    if action == "closed" and merged:
        label = "合并"
    else:
        label = ACTION_LABELS.get(action, action)
    title = pr.get("title", "")
    number = pr.get("number", "")
    url = pr.get("html_url", "")
    return (
        f"[{repo}]\n"
        f"Pull Request #{number} 已{label}\n"
        f"标题: {title}\n"
        f"操作者: {actor}\n"
        f"{url}"
    )


def _fmt_release(payload: dict, repo: str, actor: str) -> str | None:
    action = payload.get("action", "")
    if action != "published":
        return None
    release = payload.get("release", {})
    tag = release.get("tag_name", "")
    name = release.get("name", tag)
    url = release.get("html_url", "")
    return (
        f"[{repo}]\n"
        f"新版本发布: {name}\n"
        f"标签: {tag}\n"
        f"发布者: {actor}\n"
        f"{url}"
    )


def _fmt_star(payload: dict, repo: str, actor: str) -> str | None:
    action = payload.get("action", "")
    if action != "started":
        return None
    return f"[{repo}]\n{actor} Star 了此仓库"


def _fmt_push(payload: dict, repo: str, actor: str) -> str | None:
    ref = payload.get("ref", "")
    branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
    commits = payload.get("commits", [])
    count = len(commits)
    if count == 0:
        return None
    lines = [f"[{repo}]", f"{actor} 推送了 {count} 个提交到 {branch}"]
    for c in commits[:3]:
        sha = c.get("sha", "")[:7]
        msg = c.get("message", "").split("\n")[0][:60]
        lines.append(f"  {sha} {msg}")
    if count > 3:
        lines.append(f"  ... 还有 {count - 3} 个提交")
    return "\n".join(lines)


def _fmt_fork(payload: dict, repo: str, actor: str) -> str | None:
    forkee = payload.get("forkee", {})
    full_name = forkee.get("full_name", "")
    url = forkee.get("html_url", "")
    return f"[{repo}]\n{actor} Fork 了此仓库\n{url}"


def _fmt_issue_comment(payload: dict, repo: str, actor: str) -> str | None:
    action = payload.get("action", "")
    if action != "created":
        return None
    issue = payload.get("issue", {})
    comment = payload.get("comment", {})
    number = issue.get("number", "")
    title = issue.get("title", "")
    body = comment.get("body", "")[:100]
    url = comment.get("html_url", "")
    is_pr = "pull_request" in issue
    kind = "PR" if is_pr else "Issue"
    return (
        f"[{repo}]\n"
        f"{actor} 评论了 {kind} #{number}\n"
        f"标题: {title}\n"
        f"内容: {body}\n"
        f"{url}"
    )


def _fmt_create(payload: dict, repo: str, actor: str) -> str | None:
    ref_type = payload.get("ref_type", "")
    ref = payload.get("ref", "")
    if ref_type not in ("branch", "tag"):
        return None
    kind = "分支" if ref_type == "branch" else "标签"
    return f"[{repo}]\n{actor} 创建了{kind}: {ref}"


def _fmt_delete(payload: dict, repo: str, actor: str) -> str | None:
    ref_type = payload.get("ref_type", "")
    ref = payload.get("ref", "")
    if ref_type not in ("branch", "tag"):
        return None
    kind = "分支" if ref_type == "branch" else "标签"
    return f"[{repo}]\n{actor} 删除了{kind}: {ref}"


_FORMATTERS: dict[str, Any] = {
    "IssuesEvent": _fmt_issues,
    "PullRequestEvent": _fmt_pull_request,
    "ReleaseEvent": _fmt_release,
    "WatchEvent": _fmt_star,
    "PushEvent": _fmt_push,
    "ForkEvent": _fmt_fork,
    "IssueCommentEvent": _fmt_issue_comment,
    "CreateEvent": _fmt_create,
    "DeleteEvent": _fmt_delete,
}
