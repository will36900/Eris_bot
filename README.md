# Eris_bot

基于 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的 QQ / 飞书群聊机器人**配置教程与模板**。

本仓库教你三件事：

1. 怎么写 `SOUL.md`（人格）
2. 怎么接 QQ 和飞书，并用 profile 做权限隔离
3. 怎么做「库存优先」的表情包链路

> **这不是可直接运行的 bot 实例。**  
> 真实密钥、OpenID、群号、成员表只应出现在你本机的 `~/.hermes`，不要提交到公开仓库。  
> 维护者自己的运行实例是私有的；这里只有脱敏后的模板。

## 你能得到什么

| 能力 | 说明 |
|---|---|
| 群聊人格 | 精简版 Eris 示例 + 最小人格模板 |
| QQ 接入 | 路由、共享群记忆、slash 白名单、工具白名单 |
| 飞书接入 | 同样的权限拆分思路 |
| 表情包 | 公网直链库存 + CDN 节点坑 + 提示词写法 |
| 防泄露 | `pre-commit` + 内容级密钥扫描脚本 |

## 5 步上手

```bash
git clone https://github.com/will36900/Eris_bot.git
cd Eris_bot
cp config/.env.example ~/.hermes/.env   # 然后填真实值
# 对照 docs/01-quickstart.md 合并 SOUL 与 config 片段
```

详细步骤：[docs/01-quickstart.md](docs/01-quickstart.md)

## 文档

| 文档 | 内容 |
|---|---|
| [快速开始](docs/01-quickstart.md) | 装好 Hermes 之后怎么用本仓库 |
| [SOUL 指南](docs/02-soul-guide.md) | 人格怎么写、怎么生效、常见坑 |
| [QQ 接入](docs/03-qq.md) | 路由、openid、白名单、验证清单 |
| [飞书接入](docs/04-feishu.md) | 应用创建与权限模型 |
| [表情包系统](docs/05-stickers.md) | 库存优先 + CDN + 复用步骤 |
| [安全约定](SECURITY.md) | 占位符规范与漏洞反馈 |

## 目录结构

```
Eris_bot/
├── README.md
├── LICENSE                 # MIT
├── SECURITY.md
├── config/
│   ├── .env.example
│   ├── .env.feishu.example
│   ├── gateway-qq.template.yaml
│   └── config.snippet.yaml
├── docs/
│   ├── 01-quickstart.md
│   ├── 02-soul-guide.md
│   ├── 03-qq.md
│   ├── 04-feishu.md
│   └── 05-stickers.md
├── examples/
│   ├── souls/
│   │   ├── minimal.SOUL.md
│   │   └── eris-qq.SOUL.md
│   └── memory/
│       └── guest-qq.MEMORY.example.md
├── hooks/pre-commit
└── scripts/check_secrets.py
```

## 占位符约定

公开文件里只允许这些形式（以及 `${ENV_VAR}`）：

| 占位符 | 含义 |
|---|---|
| `<YOUR_QQ_OWNER_OPENID>` | 你的 QQ openid |
| `<YOUR_QQ_GROUP_ID>` | 群 openid |
| `<MEMBER_N_OPENID>` | 群成员 openid |
| `ou_<YOUR_FEISHU_OPEN_ID>` | 飞书 owner Open ID |
| `sk-your-...` / `cli_your_...` | 密钥类示例 |

看到大写 32 位 hex、真实 `ou_...`、或可调用的 API key，就当作泄露处理。

## 和 Hermes 的关系

- 运行时依赖上游 Hermes Agent，本仓库不 vendor 其源码
- 配置项名称以你安装的 Hermes 版本为准；本教程描述的是经过验证的接入方式
- 若上游字段更名，以 Hermes 文档为准，欢迎开 issue 同步教程

## 许可证

[MIT](LICENSE)

Eris 示例人格为《无职转生》角色的同人设定，仅供学习与非商业群聊使用。表情包示例图库请自行确认素材授权。
