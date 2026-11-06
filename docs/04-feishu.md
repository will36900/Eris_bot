# 接入飞书

## 目标架构

```
飞书开放平台
    │
    ▼
Hermes gateway (feishu adapter)
    │
    ├─ owner  → default profile（完整工具）
    └─ 其他人 → guest / guest-feishu（白名单工具）
```

和 QQ 同一套思路：开放对话，用 profile + 工具白名单收权限。

## 1. 创建应用

1. 打开 [飞书开放平台](https://open.feishu.cn/app)，创建企业自建应用
2. 开通机器人能力，订阅消息相关事件（按 Hermes 飞书文档要求勾选）
3. 拿到 `App ID` / `App Secret`

## 2. 写入环境变量

把 [config/.env.feishu.example](../config/.env.feishu.example) 追加到本机 `~/.hermes/.env`：

```bash
FEISHU_APP_ID=cli_your_app_id_here
FEISHU_APP_SECRET=<your-app-secret>
FEISHU_DOMAIN=feishu
FEISHU_CONNECTION_MODE=websocket
FEISHU_GROUP_POLICY=open
GATEWAY_ALLOW_ALL_USERS=true
FEISHU_OWNER_OPEN_ID=ou_<YOUR_FEISHU_OPEN_ID>
```

Owner Open ID 获取：私聊机器人一条，看 gateway 日志里的 `ou_...`。

## 3. 权限模型建议

| 角色 | 能做什么 |
|---|---|
| 所有人 | 聊天、问答、只读类工具（web / vision / clarify / tts） |
| owner | 文件、终端、Git、改配置等高权限操作 |

具体白名单写在 guest profile 的 `platform_toolsets.feishu`；slash 命令可用 `group_allow_admin_from: ["ou_<YOUR_FEISHU_OPEN_ID>"]` 收回。

## 4. 验证清单

- [ ] 私聊 bot 有回复
- [ ] 群里 @bot 有回复
- [ ] 非 owner 无法触发高权限工具
- [ ] owner Open ID 填错时，自己也会被当成 guest（这是预期行为，修好 ID 即可）

## 和 QQ 的差异（简表）

| | QQ | 飞书 |
|---|---|---|
| Owner ID 形态 | 大写 hex openid | `ou_...` |
| 群成员昵称 | 事件里通常没有，靠 `group_member_names` | 一般能拿到显示名 |
| 未认证限制 | 常见：只能进自己管理的群 | 取决于企业应用权限审批 |
| 连接方式 | QQ 开放平台回调 / 平台约定 | websocket 或 webhook |

更细的事件字段以当前 Hermes 版本文档为准；本教程只固定"权限怎么拆"，不绑定某一版 API 细节。
