# BoChat Forwarder - NcatBot 消息转发插件

BoChat <-> QQ 双向消息转发插件，基于 [NcatBot](https://docs.ncatbot.xyz/) 插件规范开发，使用 [BoChat Python SDK](../../python-sdk/) 与 BoChat 平台通信。

## 功能

- BoChat 群消息 -> QQ 群 / QQ 私聊
- QQ 群消息 -> BoChat 群
- QQ 私聊消息 -> BoChat 群
- 多条路由规则并行，按需启用
- 关键词过滤、发送者前缀、Bot 回环防护

## 目录结构

```
ncatbot-bochat-forwarder/
  manifest.toml      # NcatBot 插件元数据
  main.py            # 插件入口（BochatForwarderPlugin）
  bochat_bridge.py   # BoChat SDK 桥接层（登录/WS/发消息）
  formatter.py       # 消息格式转换（CQ码处理、前缀拼接）
  config.yaml        # 转发路由配置（用户编辑此文件）
```

## 前置条件

- Python >= 3.12
- NcatBot 已安装并可运行 (`pip install ncatbot5`)
- BoChat 服务已启动
- 已有 BoChat 账号（注册后自动创建默认 Bot）

## 安装

1. 将本目录复制到 NcatBot 的 `plugins/` 目录下：

```bash
cp -r ncatbot-bochat-forwarder /path/to/your-bot/plugins/bochat_forwarder
```

2. 安装依赖：

```bash
pip install bochat-sdk[ws] pyyaml
```

如果 bochat-sdk 尚未发布到 PyPI，可从仓库本地安装：

```bash
cd /path/to/bochat/python-sdk
pip install -e ".[ws]"
```

## 配置

编辑 `plugins/bochat_forwarder/config.yaml`：

### 1. 填写 BoChat 连接信息

```yaml
bochat:
  base_url: "http://127.0.0.1:8080"
  account: "your_account"
  password: "your_password"
  bot_id: ""  # 留空自动选择第一个活跃 Bot
```

### 2. 配置转发路由

每条路由定义一个单向转发关系。需要双向转发时，配两条规则即可。

```yaml
routes:
  # BoChat 群 -> QQ 群
  - name: "项目通知"
    direction: "bochat_to_qq"
    enabled: true
    source:
      bochat_group_id: "g_abc123"
    target:
      qq_group_id: 123456789
    filter:
      ignore_bots: true       # 忽略 Bot 自身消息，防止回环
      keywords: []             # 空 = 不过滤，全部转发
    format:
      show_sender: true
      prefix: "[BoChat|{sender}] "

  # QQ 群 -> BoChat 群
  - name: "QQ反馈"
    direction: "qq_to_bochat"
    enabled: true
    source:
      qq_group_id: 123456789
    target:
      bochat_group_id: "g_abc123"
    format:
      prefix: "[QQ|{sender}] "
```

### 路由字段速查

| 字段 | 说明 |
|------|------|
| `direction` | `"bochat_to_qq"` 或 `"qq_to_bochat"` |
| `enabled` | `true` / `false` |
| `source.bochat_group_id` | BoChat 群 ID（如 `g_xxx`） |
| `source.qq_group_id` | QQ 群号 |
| `source.qq_user_id` | QQ 用户 ID（私聊来源） |
| `target.bochat_group_id` | 目标 BoChat 群 ID |
| `target.qq_group_id` | 目标 QQ 群号 |
| `target.qq_user_id` | 目标 QQ 用户 ID（私聊转发） |
| `filter.ignore_bots` | 忽略 Bot 自身消息（默认 `true`） |
| `filter.keywords` | 关键词白名单，空列表 = 全部转发 |
| `format.show_sender` | 是否显示发送者名称（默认 `true`） |
| `format.prefix` | 前缀模板，支持 `{sender}` 和 `{group}` 变量 |

## 运行

```bash
cd /path/to/your-bot
ncatbot run
```

插件会在启动时自动加载，日志中可看到：

```
[BochatForwarder] 已加载 2 条转发路由 (bochat->qq: 1, qq->bochat: 1)
[BochatBridge] BoChat WebSocket 已连接，可用群: g_abc123, g_def456
[BochatForwarder] BochatForwarder 插件加载完成
```

## 架构

```
QQ 用户                          BoChat 平台
   |                                  |
   | QQ群/私聊消息                     | WebSocket 推送
   v                                  v
NcatBot (OneBot v11)          BochatBridge (SDK)
   |                                  |
   +---> BochatForwarderPlugin <------+
              |          |
              |  路由匹配 + 格式转换
              |          |
              v          v
         BoChat API    QQ API
        (send_text)  (post_group_msg)
```

## 注意事项

- 不要把 BoChat 账号密码提交到 Git 仓库
- `ignore_bots: true` 可防止 Bot 自身消息被转发导致的无限回环
- 双向转发时两条路由都应开启 `ignore_bots`
- 修改 `config.yaml` 后需重载插件才能生效
