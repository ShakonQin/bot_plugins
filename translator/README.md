# Translator - NcatBot 中英互译插件

中英文互译插件，基于 [NcatBot](https://docs.ncatbot.xyz/) 插件规范开发，通过 `/trans` 命令实现中译英和英译中。优先支持 BoChat 群聊，同时兼容 QQ 群聊与私聊。

## 功能

- `/trans c2e <文本>` 中文翻译为英文
- `/trans e2c <文本>` 英文翻译为中文
- 仅输入 `/trans` 时返回用法提示
- BoChat 群聊翻译（通过 WebSocket 实时监听 + 回复）
- QQ 群聊和私聊翻译（通过 NcatBot OneBot 协议）
- 双翻译后端：MyMemory（免费，开箱即用）/ 百度翻译（高额度，需注册）

## 目录结构

```
ncatbot-translator/
  manifest.toml      # NcatBot 插件元数据
  main.py            # 插件入口（TranslatorPlugin）
  bochat_bridge.py   # BoChat SDK 桥接层（WebSocket 监听 + 消息发送）
  translator.py      # 翻译 API 客户端（MyMemory + 百度）
  config.yaml        # 插件配置（用户编辑此文件）
```

## 前置条件

- Python >= 3.12
- NcatBot 已安装并可运行 (`pip install ncatbot5`)
- BoChat 服务已启动（BoChat 群聊翻译必需）
- 已有 BoChat 账号（注册后自动创建默认 Bot）

## 安装

1. 将本目录复制到 NcatBot 的 `plugins/` 目录下：

```bash
cp -r ncatbot-translator /path/to/your-bot/plugins/translator
```

2. 安装依赖：

```bash
pip install "bochat-sdk[ws]" httpx pyyaml
```

如果 bochat-sdk 尚未发布到 PyPI，可从仓库本地安装：

```bash
cd /path/to/bochat/python-sdk
pip install -e ".[ws]"
```

## 配置

编辑 `plugins/translator/config.yaml`：

### 1. BoChat 连接配置

插件优先支持 BoChat 群聊，需要配置 BoChat 平台连接信息：

```yaml
bochat:
  base_url: "http://127.0.0.1:8080"
  account: "your_account"
  password: "your_password"
  bot_id: ""  # 留空自动选择第一个活跃 Bot
```

### 2. 翻译后端选择

插件支持两种翻译后端，通过 `provider` 字段切换：

| 后端 | 是否免费 | 是否需要密钥 | 额度 |
|------|---------|-------------|------|
| `mymemory` | 免费 | 否（可选填邮箱提额） | 匿名 1000 词/天，填邮箱 10000 词/天 |
| `baidu` | 标准版免费 | 是 | 5 万字符/月 |

### 方案一：MyMemory（默认，零配置）

开箱即用，无需任何密钥：

```yaml
translate:
  provider: "mymemory"
  mymemory:
    email: ""  # 可选，填写后提升至 10000 词/天
```

### 方案二：百度翻译

需要到 [百度翻译开放平台](https://fanyi-api.baidu.com/) 注册并获取 APP ID 和密钥：

```yaml
translate:
  provider: "baidu"
  baidu:
    app_id: "your_app_id"
    secret_key: "your_secret_key"
```

## 命令格式

```
/trans <模式> <待翻译文本>
```

### 模式说明

| 模式 | 方向 | 示例 |
|------|------|------|
| `c2e` | 中文 → 英文 | `/trans c2e 你好世界` |
| `e2c` | 英文 → 中文 | `/trans e2c Hello World` |

仅支持中英文互译，不支持其他语种。

### 交互示例

```
用户: /trans c2e 今天天气真好
Bot:  [中→英] The weather is really nice today

用户: /trans e2c Machine learning is fascinating
Bot:  [英→中] 机器学习令人着迷

用户: /trans
Bot:  用法: /trans <模式> <文本>
      模式: c2e (中译英) | e2c (英译中)
      示例: /trans c2e 你好世界
```

## 运行

```bash
cd /path/to/your-bot
ncatbot run
```

插件启动后日志示例：

```
[TransBridge] 正在登录 BoChat 账号: your_account
[TransBridge] BoChat 登录成功
[TransBridge] 已选择 Bot: MyBot (bot_xxx)
[TransBridge] BoChat WebSocket 已连接，可用群: g_abc123, g_def456
[TranslatorPlugin] Translator 插件加载完成 (BoChat + QQ)
```

如果 BoChat 连接失败，插件仍会以 QQ-only 模式运行：

```
[TranslatorPlugin] 连接 BoChat 平台失败，BoChat 群聊翻译不可用
[TranslatorPlugin] Translator 插件加载完成 (仅 QQ)
```

## 架构

```
BoChat 用户                       QQ 用户
   |                                 |
   | /trans c2e 你好                  | /trans e2c Hello
   v                                 v
BoChat 平台                     NcatBot (OneBot v11)
   |                                 |
   | WebSocket 推送                   | 群聊/私聊事件
   v                                 v
BochatBridge  ──────>  TranslatorPlugin  <────── registrar
                            |
                   命令解析 (/trans + 模式 + 文本)
                            |
                            v
                      TranslateClient
                            |
                  +--- MyMemory API
                  |         或
                  +--- 百度翻译 API
                            |
                            v
              翻译结果 -> BoChat 群 / QQ 群/私聊 回复
```

## 注意事项

- 不要把 BoChat 账号密码和百度翻译密钥提交到 Git 仓库
- BoChat 连接失败时插件自动降级为 QQ-only 模式，不影响 QQ 侧翻译
- MyMemory 匿名访问有每日词数限制，高频使用建议填写邮箱或切换百度后端
- 修改 `config.yaml` 后需重载插件才能生效
- 命令模式仅限 `c2e` / `e2c`，输入其他模式不会触发翻译
- Bot 自身发送的消息会被自动忽略，防止回环
