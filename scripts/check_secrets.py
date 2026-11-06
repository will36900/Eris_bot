#!/usr/bin/env python3
"""暂存区内容级密钥扫描。

pre-commit 的文件名规则（``.env`` / ``*.pem`` / ``credential``）挡不住
「密钥写进了 config.yaml」这种情况。config.yaml 从 2026-10-29 起进仓库跟踪，
所以这里补一道内容检查。

只看暂存区（``git show :path``），不看工作区；命中即返回 1。

误报的三类照 OpenID 的处理：标识符字段（user_id / chat_id / open_id /
admin_from）、环境变量名（``key_env: HERMES_FOO_API_KEY``）、占位符
（``${DEEPSEEK_API_KEY}`` / ``<your-key>``）都不算密钥。
"""
from __future__ import annotations

import re
import subprocess
import sys

# 这些键名装的是标识符或变量名，不是密钥本体。
IDENTIFIER_KEY = re.compile(
    r"(user_id|chat_id|open_id|union_id|admin_from|_env|env_name)$", re.I
)
# 全大写下划线：环境变量名（HERMES_FOO_API_KEY）。
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{7,}$")
# 占位符：${VAR} / <your-key> / ****** / xxxxxx
PLACEHOLDER = re.compile(r"^(\$\{[^}]+\}|\*{4,}|x{6,}|<[^>]+>)$", re.I)
# QQ / 飞书 openid 是全大写 16 进制（32 位），不是密钥。
HEX_ID = re.compile(r"^[0-9A-F]{16,}$")

# 有明确厂商前缀的，直接判。
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("API key (sk-)", re.compile(r"sk-[A-Za-z0-9_\-]{16,}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("私钥块", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("带凭据的 URL", re.compile(r"://[^/\s:@]+:[^/\s@]{6,}@")),
]

# 键名像密钥 + 值是长字面量。过滤交给 _is_secret_value。
KV = re.compile(
    r"""^\s*["']?([\w.\-]*(?:api[_\-]?key|secret|token|passw(?:or)?d|credential)[\w.\-]*)"""
    r"""["']?\s*[:=]\s*["']?(\$\{[^}]*\}|[^\s"'#,}\]]{8,})""",
    re.I,
)

TEXT_SUFFIXES = {
    ".yaml", ".yml", ".json", ".toml", ".ini", ".conf", ".cfg",
    ".md", ".sh", ".py", ".js", ".ts", ".txt", ".env", ".template",
}
MAX_BYTES = 512 * 1024


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, check=False,
    ).stdout
    return [p for p in out.splitlines() if p.strip()]


def staged_content(path: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f":{path}"], capture_output=True, check=False,
    )
    if proc.returncode != 0 or len(proc.stdout) > MAX_BYTES:
        return None
    try:
        return proc.stdout.decode("utf-8", "ignore")
    except Exception:
        return None


def _is_secret_value(key: str, value: str) -> bool:
    if IDENTIFIER_KEY.search(key):
        return False
    if PLACEHOLDER.match(value) or ENV_NAME.match(value) or HEX_ID.match(value):
        return False
    # 纯数字、纯标点、明显的 URL（凭据 URL 已由 PATTERNS 覆盖）
    if value.isdigit() or value.startswith(("http://", "https://")):
        return False
    return True


def mask(value: str) -> str:
    head = value[:4]
    return f"{head}…(len {len(value)})"


def scan(path: str, text: str) -> list[str]:
    hits: list[str] = []
    suffix = "." + path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""
    if suffix not in TEXT_SUFFIXES and not path.endswith(".env"):
        return hits
    for lineno, line in enumerate(text.splitlines(), 1):
        if len(line) > 4000:
            continue
        for label, pattern in PATTERNS:
            m = pattern.search(line)
            if m:
                hits.append(f"{path}:{lineno}  {label}  {mask(m.group(0))}")
                break
        else:
            m = KV.search(line)
            if m and _is_secret_value(m.group(1), m.group(2)):
                hits.append(f"{path}:{lineno}  键 {m.group(1)}  {mask(m.group(2))}")
    return hits


def main() -> int:
    problems: list[str] = []
    for path in staged_files():
        text = staged_content(path)
        if text is None:
            continue
        problems.extend(scan(path, text))
    if problems:
        for p in problems:
            print(p)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
