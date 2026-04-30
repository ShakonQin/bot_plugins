# NcatBot bochat 插件仓库

这是一个 NcatBot 兼容bochat  插件集合仓库，包含以下三个插件：

## 插件列表

### 1. GitHub Subscriber (github_subscriber)
GitHub 仓库事件订阅插件，轮询 GitHub Events API 监控仓库动态，将事件格式化后推送至 QQ 群和/或 BoChat 群聊。

**主要功能：**
- 轮询监控 GitHub 仓库事件（Issue、PR、Release、Star、Push 等）
- 事件格式化为结构化中文消息
- 支持同时推送到 QQ 群和 BoChat 群
- 多仓库同时订阅，每个仓库可配置独立的事件白名单和推送目标

### 2. BoChat Forwarder (bochat_forwarder)
BoChat 与 QQ 消息双向转发插件，在 BoChat 平台和 QQ 群之间建立消息桥梁。

**主要功能：**
- BoChat 群消息转发到 QQ 群
- QQ 群消息转发到 BoChat 群
- 支持多种消息类型（文本、图片、文件等）
- 可配置过滤规则和转发目标

### 3. Translator (translator)
中英互译插件，支持在 QQ 群和 BoChat 群中进行实时翻译。

**主要功能：**
- 中英文互译
- 支持 QQ 群和 BoChat 群
- 可配置翻译服务提供商
- 简单的命令触发翻译

## 目录结构

```
ncatbot-plugins/
├── README.md                    # 本文件
├── .gitignore                   # Git 忽略规则
├── github_subscriber/           # GitHub 订阅插件
│   ├── README.md
│   ├── manifest.toml
│   ├── main.py
│   ├── github_poller.py
│   ├── event_formatter.py
│   ├── bochat_bridge.py
│   ├── config.yaml.example      # 配置文件示例
│   └── __init__.py
├── bochat_forwarder/            # BoChat 转发插件
│   ├── README.md
│   ├── manifest.toml
│   ├── main.py
│   ├── bochat_bridge.py
│   ├── formatter.py
│   ├── config.yaml.example      # 配置文件示例
│   └── __init__.py
└── translator/                  # 翻译插件
    ├── README.md
    ├── manifest.toml
    ├── main.py
    ├── translator.py
    ├── bochat_bridge.py
    ├── config.yaml.example      # 配置文件示例
    └── __init__.py
```

## 安装使用

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/ncatbot-plugins.git
cd ncatbot-plugins
```

### 2. 复制插件到 NcatBot

将需要的插件目录复制到 NcatBot 的 `plugins/` 目录下：

```bash
# 复制单个插件
cp -r github_subscriber /path/to/your-bot/plugins/

# 或复制所有插件
cp -r github_subscriber bochat_forwarder translator /path/to/your-bot/plugins/
```

### 3. 安装依赖

```bash
# 通用依赖
pip install httpx pyyaml

# 如需使用 BoChat 功能
pip install bochat-sdk
```

### 4. 配置插件

进入插件目录，复制示例配置文件并编辑：

```bash
cd /path/to/your-bot/plugins/github_subscriber
cp config.yaml.example config.yaml
# 编辑 config.yaml 填入你的配置
```

### 5. 运行

```bash
cd /path/to/your-bot
ncatbot run
```

## 配置说明

每个插件都有自己的 `config.yaml` 配置文件。首次使用时：

1. 复制 `config.yaml.example` 为 `config.yaml`
2. 根据需要修改配置项
3. 重启 NcatBot 或重载插件使配置生效

**重要：** `config.yaml` 包含敏感信息（密码、token 等），已添加到 `.gitignore`，不会被提交到仓库。

## 开发说明

- 每个插件都是独立的，可以单独使用
- 插件基于 NcatBot 插件规范开发
- 配置文件使用 YAML 格式
- 所有插件都支持 QQ 群和 BoChat 群的消息推送

## 注意事项

1. **安全提醒**：不要将包含敏感信息的 `config.yaml` 文件提交到公开仓库
2. **API 限制**：GitHub API 有速率限制，建议配置 Token 以提升限额
3. **依赖管理**：确保已安装所有必要的依赖包
4. **配置备份**：建议备份你的 `config.yaml` 文件，避免丢失配置

