# 快速开始

本教程假设你已经能跑起 [Hermes Agent](https://github.com/NousResearch/hermes-agent)。如果还没有，先按上游 README 安装。

## 1. 克隆本仓库

```bash
git clone https://github.com/will36900/Eris_bot.git
cd Eris_bot
```

这里只有模板和文档，**不会**替换你本机的 `~/.hermes` 运行实例。

## 2. 准备环境变量

```bash
cp config/.env.example ~/.hermes/.env
# 按需把 config/.env.feishu.example 的内容也追加进去
```

打开 `~/.hermes/.env`，把所有 `<PLACEHOLDER>` 换成真实值：

| 变量 | 从哪来 |
|---|---|
| `DEEPSEEK_API_KEY` 等 | 你的 LLM 提供商 |
| `QQ_APP_ID` / `QQ_CLIENT_SECRET` | [QQ 开放平台](https://q.qq.com/) |
| `QQ_OWNER_OPENID` | 私聊 bot 后看 gateway 日志里的 `user_id` |
| `QQ_GROUP_ID` | 群消息事件里的 `chat_id` / group openid |
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | [飞书开放平台](https://open.feishu.cn/app) |

**填好的 `.env` 永远不要 `git add`。**

## 3. 拷贝人格与配置片段

```bash
# 人格示例 → 你的 guest-qq profile 实际读取的 SOUL 路径
cp examples/souls/eris-qq.SOUL.md ~/.hermes/config/guest-qq.SOUL.md

# QQ 平台片段：对照 config/gateway-qq.template.yaml
# 把 platforms 段和 profile_routes 合并进本机 config.yaml
```

占位符对照：

- `<YOUR_QQ_OWNER_OPENID>` → 你的 QQ openid
- `<YOUR_QQ_GROUP_ID>` → 群 openid
- `<MEMBER_N_OPENID>` → 群成员 openid（写在 `group_member_names` 的 **key** 上，不能用 `${VAR}`）

## 4. 启动并验证

```bash
hermes gateway start   # 或你平时用的启动方式
```

检查：

1. 私聊 bot，应路由到 default profile
2. 群里 @bot，应路由到 guest-qq，且工具白名单生效（不能读本地文件）
3. 改完 SOUL 后要换会话才生效：群里 `@bot /new`

## 5. 启用本仓库的提交检查（可选）

如果你 fork 后继续改这个教程仓库：

```bash
git config core.hooksPath hooks
```

之后每次 commit 会拦 `.env` / `auth.json`，并跑内容级密钥扫描。

## 下一步

- [编写 SOUL.md](02-soul-guide.md)
- [接入 QQ](03-qq.md)
- [接入飞书](04-feishu.md)
- [表情包系统](05-stickers.md)
