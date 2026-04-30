# GitHub Subscriber - BoChat 独立版

监控 GitHub 仓库事件，自动推送到 BoChat 群聊。

## 支持的事件类型

| 事件 | 说明 |
|------|------|
| `issues` | Issue 创建/关闭/重新打开 |
| `pull_request` | PR 创建/关闭/合并 |
| `release` | 新版本发布 |
| `star` | 仓库被 Star |
| `push` | 代码推送 |
| `fork` | 仓库被 Fork |
| `issue_comment` | Issue/PR 评论 |
| `create` | 分支/标签创建 |
| `delete` | 分支/标签删除 |

## 配置

编辑 `config.yaml`：

```yaml
github:
  token: ""              # GitHub Token，可选，匿名限速 60次/时，有 Token 5000次/时
  poll_interval: 60      # 轮询间隔（秒），最小 30

bochat:
  base_url: "http://127.0.0.1:8080"
  account: "your_account"
  password: "your_password"
  bot_id: ""             # 留空自动选择第一个活跃 Bot

subscriptions:
  - name: "我的项目"
    repo: "owner/repo"
    enabled: true
    events:              # 空列表 = 监听全部事件
      - issues
      - pull_request
      - release
    targets:
      - id: "g_xxx"     # BoChat 群 ID
```

## 启动

```bash
# 从项目根目录运行
python -m plugins.github_subscriber

# 指定配置文件
python -m plugins.github_subscriber --config /path/to/config.yaml

# 或通过统一启动器
python plugins/run.py --only github_subscriber
```

## 依赖

- `httpx`
- `pyyaml`
- `bochat_sdk`（项目内 `python-sdk/`）
