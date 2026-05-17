# Translator - BoChat 独立版

中英互译服务，通过 BoChat WebSocket 监听群聊消息，响应 `/trans` 命令。

## 用法

在 BoChat 群聊中发送：

```
/trans c2e 你好世界       # 中译英
/trans e2c Hello World    # 英译中
/trans                    # 查看帮助
```

## 翻译后端

| 后端 | 说明 |
|------|------|
| `mymemory` | 免费，无需密钥，适合轻量使用 |
| `baidu` | 需注册，标准版免费 5万字符/月，翻译质量更高 |

## 配置

编辑 `config.yaml`：

```yaml
bochat:
  base_url: "http://127.0.0.1:8080"
  bot_token: "b_xxx:1710000000:signature"  # BoChat Bot Token（必填）
  # 可选：指定监控的群号列表，留空则监控 Bot 所在的所有群
  # group_ids:
  #   - "g_abc123"
  #   - "g_def456"

translate:
  provider: "mymemory"   # 或 "baidu"
  mymemory:
    email: ""            # 可选，提供邮箱可提升配额
  baidu:
    app_id: ""           # 百度翻译 APP ID
    secret_key: ""       # 百度翻译密钥
```

### 获取 Bot Token

1. 在 BoChat 平台注册并登录
2. 通过 `GET /api/v1/bots` 接口获取 Bot 的 `token` 字段
3. 将 token 填入 `config.yaml` 的 `bochat.bot_token`

## 启动

```bash
# 从项目根目录运行
python -m plugins.translator

# 指定配置文件
python -m plugins.translator --config /path/to/config.yaml

# 或通过统一启动器
python plugins/run.py --only translator
```

## 依赖

- `httpx`
- `pyyaml`
- `bochat_sdk`（项目内 `python-sdk/`）
