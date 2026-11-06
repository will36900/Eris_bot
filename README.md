# Eris_bot

基于 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的 QQ / 飞书群聊机器人**配置教程与模板**。

写法上同时参考了：

- [Mikasa](https://github.com/Ceng-0324/MIKASA) — 同样站在 Hermes 之上，偏身份、工程协作与真实仓库接入
- [AstrBot](https://github.com/AstrBotDevs/AstrBot) — 多平台 IM / 插件生态；本仓库的表情包气氛发送、群历史拆法等思路有对照其实现

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

## 设计参考：AstrBot

群聊这部分不是从零想出来的。设计前逐块读过 [AstrBot](https://github.com/AstrBotDevs/AstrBot)（AGPL-3.0）的实现，
借鉴的是**结构拆法**，没有复制代码。三条线的结论各不相同，写在这里免得后来的人重走一遍。

### 1. 人格：做成独立文件，而不是塞进全局提示词

AstrBot 把人格做成可切换的 persona（`provider_settings.default_personality` + persona 管理接口），
风格和规则不写死在主提示词里。本仓库对应的是 `SOUL.md` 作为唯一人格源，另有一份只放使用规则的 skill：
换人只改 SOUL，不动运行时配置。见 [docs/02-soul-guide.md](docs/02-soul-guide.md)。

### 2. 表情包：借鉴了组件模型，但没走工具调用

AstrBot 的消息是 `MessageChain`——`Plain` / `Image` / `Face` / `At` / `Reply` 的组件序列，
平台 adapter 负责把 `Image` 转成平台格式（QQ 上传媒体、飞书 image_key）。
LLM 主动发图靠内置工具 `send_message_to_user`，参数是消息段；不是让模型写代码拼链。
它另外把「收到消息加 reaction」的 `pre_ack_emoji` 和发表情包分得很清，两者别混为一谈。

落到 Hermes 上只保留了组件模型的思路：图片走 markdown 直链 `![](url)`，adapter 自己处理上传，
提示词里直接给库存清单和触发规则。省掉一次工具往返，代价是只能发公网可访问的图。
见 [docs/05-stickers.md](docs/05-stickers.md)。

### 3. 群聊记忆：抄的是三层拆法

AstrBot 的长期记忆（LTM）把「会话共享」和「消息池」拆成两件事，值得抄的是这个拆法：

| 层 | AstrBot 的做法 | 本仓库的对应 |
|---|---|---|
| 会话粒度 | `umo = platform:message_type:session_id`，群消息的 session_id 就是群号，整群一条对话流，没有按人隔离的选项 | `group_sessions_per_user: false`，靠每条消息前的 `[昵称]` 前缀区分说话人（不是系统提示，否则换人说话就 bust prompt cache） |
| 原始消息池 | 表 `platform_message_history(platform_id, user_id=群 umo, sender_id, sender_name, content JSON)`，插入时按最新 N 条环形裁剪，默认 700 条 | 数据本来就在 Hermes 的 `messages` 表里，不需要新建表 |
| 检索入口 | 工具 `get_group_message_history`：`limit` / `before_id` 翻页 / `keyword` 字面搜索 / `sender` 过滤，输出 CSV，**历史默认不注入 prompt，模型需要时自己查** | 同样思路：按当前群 chat_id 做只读检索 |
| 成员画像 | 没有。`persona_mgr` 按 persona 管、不按用户，所以「单独记忆」只到 `sender` 过滤这一级 | 本仓库自己补的一层，见 `examples/memory/` |

最值得抄的是检索那条：历史不主动进上下文，否则 token 随群活跃度线性涨。
反过来，它的并发模型**不能**当参考——事件总线对每个事件直接 `create_task`，不按会话串行，
比 Hermes 还松散；「多人同时 @ 别串台」要靠 Hermes 自己的 `busy_input_mode: queue`。

容量按它的表结构实测过（用真实群消息灌进同构表再 `VACUUM`）：环形消息池保留 700 条约 232 KB，
3000 条约 1.1 MB，10000 条约 4.1 MB，单条稳定在 0.33–0.42 KB，不随总量膨胀。
所以「会不会很占硬盘」是配置问题（默认只留 90 天），不是容量问题。

> 如实说明一处缺口：只读检索这层目前**还没有落地**。消息在库里，但 guest profile 的
> `platform_toolsets` 白名单里没有检索工具，等于「数据在、没入口」。
> 补的时候先做只读入口，不要把消息池搬进系统提示。

## 和 Hermes 的关系

- 运行时依赖上游 Hermes Agent，本仓库不 vendor 其源码
- 配置项名称以你安装的 Hermes 版本为准；本教程描述的是经过验证的接入方式
- 若上游字段更名，以 Hermes 文档为准，欢迎开 issue 同步教程

## 相关项目

| 项目 | 链接 | 和本仓库的关系 |
|---|---|---|
| Hermes Agent | https://github.com/NousResearch/hermes-agent | 运行时与工具层 |
| Mikasa | https://github.com/Ceng-0324/MIKASA | 设计参考：Hermes 上的身份 / 工程协作封装 |
| AstrBot | https://github.com/AstrBotDevs/AstrBot | 设计参考：多平台 bot、表情包与群历史等能力对照 |

本仓库是教程与脱敏模板，不是对上述项目的 fork。

## 许可证

[MIT](LICENSE)

Eris 示例人格为《无职转生》角色的同人设定，仅供学习与非商业群聊使用。表情包示例图库请自行确认素材授权。
