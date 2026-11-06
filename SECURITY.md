# 安全约定

本仓库是**教程与配置模板**，不含真实凭据、群号、OpenID 或运行时状态。

## 使用本仓库时

1. 复制 `config/.env.example` 到本机 Hermes 工作区的 `.env`，填入真实值。
2. **永远不要**把填好的 `.env`、`auth.json`、含真实 OpenID 的 `config.yaml` 提交回任何公开仓库。
3. 提交前启用本仓库的 hook：

   ```bash
   git config core.hooksPath hooks
   ```

   `hooks/pre-commit` 会拦 `.env` / `auth.json`，并跑 `scripts/check_secrets.py` 扫内容级密钥。

4. OpenID、群号、成员对照表属于**身份标识**，不是 API 密钥，但公开后仍可关联到真人。教程里一律用占位符：
   - `<YOUR_QQ_OWNER_OPENID>`
   - `<YOUR_QQ_GROUP_ID>`
   - `<MEMBER_1_OPENID>`
   - `ou_<YOUR_FEISHU_OPEN_ID>`

## 报告问题

如果发现本仓库误提交了真实密钥或身份标识，请开 issue 或直接联系仓库维护者。密钥类问题请先在对应平台吊销，再报告。
