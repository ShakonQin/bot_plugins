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
  account: "your_account"
  password: "your_password"
  bot_id: ""             # 留空自动选择

translate:
  provider: "mymemory"   # 或 "baidu"
  mymemory:
    email: ""            # 可选，提供邮箱可提升配额
  baidu:
    app_id: ""           # 百度翻译 APP ID
    secret_key: ""       # 百度翻译密钥
```

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
