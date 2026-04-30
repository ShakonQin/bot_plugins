# GitHub Subscriber - NcatBot GitHub 仓库订阅插件

GitHub 仓库事件订阅插件，基于 [NcatBot](https://docs.ncatbot.xyz/) 插件规范开发，轮询 GitHub Events API 监控仓库动态，将事件格式化后推送至 QQ 群和/或 BoChat 群聊。

## 功能

- 轮询监控 GitHub 仓库事件（Issue、PR、Release、Star、Push 等）
- 事件格式化为结构化中文消息，包含操作者、标题、链接等关键信息
- 支持同时推送到 QQ 群（通过 NcatBot）和 BoChat 群（通过 SDK）
- 多仓库同时订阅，每个仓库可配置独立的事件白名单和推送目标
- ETag 条件请求，节省 GitHub API 配额
- 纯配置文件管理，无需 UI 界面

## 目录结构

```
ncatbot-github-subscriber/
  manifest.toml        # NcatBot 插件元数据
  main.py              # 插件入口（GitHubSubscriberPlugin）
  github_poller.py     # GitHub Events API 轮询客户端
  event_formatter.py   # 事件格式化器
  bochat_bridge.py     # BoChat SDK 桥接层（仅发送）
  config.yaml          # 订阅配置（用户编辑此文件）
```

## 前置条件

- Python >= 3.12
- NcatBot 已安装并可运行 (`pip install ncatbot5`)
- （可选）BoChat 服务已启动（仅推送到 BoChat 群时需要）
- （可选）GitHub Personal Access Token（提升 API 速率限制）

## 安装

1. 将本目录复制到 NcatBot 的 `plugins/` 目录下：

```bash
cp -r ncatbot-github-subscriber /path/to/your-bot/plugins/github_subscriber
```

2. 安装依赖：

```bash
pip install httpx pyyaml
```

如需推送到 BoChat 群，还需安装 bochat-sdk：

```bash
pip install bochat-sdk
# 或从本地仓库安装
cd /path/to/bochat/python-sdk
pip install -e .
```

## 配置

编辑 `plugins/github_subscriber/config.yaml`：

### 1. GitHub 连接配置

```yaml
github:
  token: "ghp_xxxxxxxxxxxx"  # 可选，提升速率限制 60->5000/h
  poll_interval: 60           # 轮询间隔（秒），最小 30
```

### 2. BoChat 连接配置（可选）

仅当推送目标包含 `bochat_group` 时需要配置：

```yaml
bochat:
  base_url: "http://127.0.0.1:8080"
  account: "your_account"
  password: "your_password"
  bot_id: ""  # 留空自动选择第一个活跃 Bot
```

### 3. 配置订阅规则

每条规则定义一个仓库的事件监控与推送关系：

```yaml
subscriptions:
  - name: "我的项目"
    repo: "owner/repo"
    enabled: true
    events:              # 事件白名单，空列表 = 全部事件
      - issues
      - pull_request
      - release
    targets:
      - type: "qq_group"
        id: 123456789
      - type: "bochat_group"
        id: "g_abc123"
```

### 支持的事件类型

| 配置值 | GitHub 事件 | 说明 |
|--------|------------|------|
| `issues` | IssuesEvent | Issue 创建/关闭/重新打开 |
| `pull_request` | PullRequestEvent | PR 创建/关闭/合并 |
| `release` | ReleaseEvent | 新版本发布 |
| `star` | WatchEvent | 仓库被 Star |
| `push` | PushEvent | 代码推送（含提交摘要） |
| `fork` | ForkEvent | 仓库被 Fork |
| `issue_comment` | IssueCommentEvent | Issue/PR 新评论 |
| `create` | CreateEvent | 分支/标签创建 |
| `delete` | DeleteEvent | 分支/标签删除 |

### 推送目标类型

| type | id 格式 | 说明 |
|------|---------|------|
| `qq_group` | 数字（如 `123456789`） | QQ 群号 |
| `bochat_group` | 字符串（如 `"g_abc123"`） | BoChat 群 ID |

## 运行

```bash
cd /path/to/your-bot
ncatbot run
```

插件启动后日志示例：

```
[GitHubSubscriber] 已加载 2 条订阅规则
[GitHubSubscriber] GitHubSubscriber 插件加载完成，轮询间隔: 60s
```

收到事件时的推送消息示例：

```
[owner/repo]
Pull Request #42 已合并
标题: Fix login bug
操作者: username
https://github.com/owner/repo/pull/42
```

## 架构

```
GitHub Events API
       |
       | HTTP 轮询 (ETag 条件请求)
       v
  GitHubPoller
       |
       | 新事件列表
       v
  GitHubSubscriberPlugin
       |
       |  事件白名单过滤
       |  EventFormatter 格式化
       |
       +--------+---------+
       |                   |
       v                   v
  QQ 群 API           BoChat API
(post_group_msg)     (send_text)
```

## 注意事项

- 不要把 GitHub Token 和 BoChat 密码提交到 Git 仓库
- 匿名访问 GitHub API 速率限制为 60 次/小时，建议配置 Token
- 首次启动时最多推送最近 3 条事件，避免消息轰炸
- 修改 `config.yaml` 后需重载插件才能生效
- `poll_interval` 最小 30 秒，GitHub 服务端也可能通过响应头调整轮询间隔
