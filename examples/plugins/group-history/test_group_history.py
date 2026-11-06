"""Tests for the group-history plugin. Run: python -m unittest discover -s examples/plugins/group-history -v"""

import importlib.util
import json
import sqlite3
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

_spec = importlib.util.spec_from_file_location("group_history_plugin", Path(__file__).parent / "__init__.py")
gh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gh)

GROUP_A = "GROUP_A"
GROUP_B = "GROUP_B"


def make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT, chat_id TEXT, chat_type TEXT);
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT,
            timestamp REAL, active INTEGER DEFAULT 1, compacted INTEGER DEFAULT 0,
            _compressed_summary INTEGER DEFAULT 0);
        """
    )
    sessions = [
        ("sA1", "qqbot", GROUP_A, "group"),
        ("sA2", "qqbot", GROUP_A, "group"),   # same group, reset session
        ("sB", "qqbot", GROUP_B, "group"),
        ("sDM", "qqbot", GROUP_A, "dm"),      # same chat_id string but a DM
        ("sOther", "oneshot", GROUP_A, "group"),
    ]
    conn.executemany("INSERT INTO sessions VALUES (?,?,?,?)", sessions)
    return conn


def add(conn, session, role, content, ts=1_700_000_000.0, active=1, compacted=0, summary=0):
    cur = conn.execute(
        "INSERT INTO messages (session_id, role, content, timestamp, active, compacted, _compressed_summary)"
        " VALUES (?,?,?,?,?,?,?)",
        (session, role, content, ts, active, compacted, summary),
    )
    return cur.lastrowid


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.conn = make_db()

    def q(self, **kw):
        return gh.query_group_history(self.conn, GROUP_A, **kw)

    def test_returns_sender_and_text_chronologically(self):
        add(self.conn, "sA1", "user", "[狗叉子] 今天吃什么")
        add(self.conn, "sA1", "assistant", "随便")
        r = self.q()
        self.assertEqual([m["sender"] for m in r["messages"]], ["狗叉子", "assistant"])
        self.assertEqual(r["messages"][0]["text"], "今天吃什么")
        self.assertLess(r["messages"][0]["id"], r["messages"][1]["id"])

    def test_spans_multiple_sessions_of_same_group(self):
        add(self.conn, "sA1", "user", "[甲] 旧会话")
        add(self.conn, "sA2", "user", "[乙] 新会话")
        self.assertEqual(self.q()["count"], 2)

    def test_other_chats_never_returned(self):
        add(self.conn, "sA1", "user", "[甲] 本群")
        add(self.conn, "sB", "user", "[丙] 别的群秘密")
        add(self.conn, "sDM", "user", "[丁] 私聊秘密")
        add(self.conn, "sOther", "user", "[戊] 非qq来源")
        texts = [m["text"] for m in self.q()["messages"]]
        self.assertEqual(texts, ["本群"])
        # and the keyword path cannot reach them either
        self.assertEqual(self.q(keyword="秘密")["count"], 0)

    def test_limit_clamped(self):
        for i in range(70):
            add(self.conn, "sA1", "user", f"[甲] m{i}")
        self.assertEqual(self.q(limit=9999)["count"], gh.MAX_LIMIT)
        self.assertEqual(self.q(limit=0)["count"], 1)
        self.assertEqual(self.q(limit=-5)["count"], 1)
        self.assertEqual(self.q(limit="abc")["count"], gh.DEFAULT_LIMIT)
        self.assertEqual(self.q()["count"], gh.DEFAULT_LIMIT)

    def test_keyword_filter_is_literal(self):
        add(self.conn, "sA1", "user", "[甲] 100% 确定")
        add(self.conn, "sA1", "user", "[甲] 100x 不是")
        add(self.conn, "sA1", "user", "[甲] a_b")
        add(self.conn, "sA1", "user", "[甲] axb")
        self.assertEqual([m["text"] for m in self.q(keyword="100%")["messages"]], ["100% 确定"])
        self.assertEqual([m["text"] for m in self.q(keyword="a_b")["messages"]], ["a_b"])
        self.assertEqual(self.q(keyword="%")["count"], 1)

    def test_sender_filter(self):
        add(self.conn, "sA1", "user", "[狗叉子] 一")
        add(self.conn, "sA1", "user", "[小哭哭] 二")
        add(self.conn, "sA1", "assistant", "狗叉子 被提到的回复")
        r = self.q(sender="狗叉")
        self.assertEqual([m["text"] for m in r["messages"]], ["一"])
        self.assertEqual(self.q(sender="%")["count"], 0)

    def test_pagination_before_id(self):
        ids = [add(self.conn, "sA1", "user", f"[甲] m{i}") for i in range(5)]
        first = self.q(limit=2)
        self.assertEqual([m["id"] for m in first["messages"]], ids[3:])
        self.assertEqual(first["next_before_id"], ids[3])
        second = self.q(limit=2, before_id=first["next_before_id"])
        self.assertEqual([m["id"] for m in second["messages"]], ids[1:3])
        last = self.q(limit=10, before_id=ids[1])
        self.assertNotIn("next_before_id", last)

    def test_bad_before_id_rejected(self):
        with self.assertRaises(ValueError):
            self.q(before_id="x; DROP TABLE messages")

    def test_sql_injection_in_keyword_is_inert(self):
        add(self.conn, "sA1", "user", "[甲] hi")
        self.q(keyword="'; DROP TABLE messages; --", sender="' OR 1=1 --")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 1)

    def test_rewound_hidden_compacted_visible_summary_hidden(self):
        add(self.conn, "sA1", "user", "[甲] 撤回的", active=0, compacted=0)
        add(self.conn, "sA1", "user", "[甲] 压缩归档的", active=0, compacted=1)
        add(self.conn, "sA1", "user", "[甲] 摘要", summary=1)
        add(self.conn, "sA1", "user", "[甲] 正常")
        texts = [m["text"] for m in self.q()["messages"]]
        self.assertEqual(texts, ["压缩归档的", "正常"])

    def test_tool_and_empty_rows_skipped(self):
        add(self.conn, "sA1", "tool", "tool output")
        add(self.conn, "sA1", "session_meta", "meta")
        add(self.conn, "sA1", "user", "")
        add(self.conn, "sA1", "assistant", None)
        self.assertEqual(self.q()["count"], 0)

    def test_text_truncated_and_flagged(self):
        add(self.conn, "sA1", "user", "[甲] " + "x" * 2000)
        m = self.q()["messages"][0]
        self.assertTrue(m["truncated"])
        self.assertLessEqual(len(m["text"]), gh.MAX_TEXT_CHARS + 1)

    def test_local_paths_and_media_redacted(self):
        add(self.conn, "sA1", "user",
            "[甲] [Image attached at: /Users/<YOUR_USERNAME>/.hermes/profiles/guest-qq/cache/images/a.jpg]")
        add(self.conn, "sA1", "assistant", "看这个 MEDIA:/Users/<YOUR_USERNAME>/secret.png 好吧")
        add(self.conn, "sA1", "assistant", "MEDIA:https://x/y.png")
        joined = " ".join(m["text"] for m in self.q()["messages"])
        self.assertNotIn("/Users/", joined)
        self.assertNotIn("MEDIA:", joined)

    def test_missing_sender_prefix_is_unknown(self):
        add(self.conn, "sA1", "user", "没有前缀的消息")
        self.assertEqual(self.q()["messages"][0]["sender"], "unknown")

    def test_no_write_path(self):
        add(self.conn, "sA1", "user", "[甲] hi")
        before = self.conn.total_changes
        self.q(keyword="hi")
        self.assertEqual(self.conn.total_changes, before)


class HandlerTests(unittest.TestCase):
    def _env(self, chat_id, chat_type):
        values = {"HERMES_SESSION_CHAT_ID": chat_id, "HERMES_SESSION_CHAT_TYPE": chat_type}
        mod = types.ModuleType("gateway.session_context")
        mod.get_session_env = lambda name, default="": values.get(name, default)
        pkg = types.ModuleType("gateway")
        return mock.patch.dict(sys.modules, {"gateway": pkg, "gateway.session_context": mod})

    def test_refuses_without_chat_id(self):
        with self._env("", "group"):
            r = json.loads(gh._handler({}))
        self.assertFalse(r["success"])

    def test_refuses_outside_group(self):
        with self._env(GROUP_A, "dm"):
            r = json.loads(gh._handler({}))
        self.assertFalse(r["success"])

    def test_model_supplied_chat_id_is_ignored(self):
        conn = make_db()
        add(conn, "sA1", "user", "[甲] 本群")
        add(conn, "sB", "user", "[丙] 别的群")
        with self._env(GROUP_A, "group"), mock.patch.object(gh, "_open_readonly", return_value=conn):
            r = json.loads(gh._handler({"chat_id": GROUP_B, "session_id": "sB", "limit": 50}))
        self.assertTrue(r["success"])
        self.assertEqual([m["text"] for m in r["messages"]], ["本群"])

    def test_db_unavailable_returns_error_not_traceback(self):
        with self._env(GROUP_A, "group"), mock.patch.object(gh, "_open_readonly", side_effect=OSError("boom")):
            r = json.loads(gh._handler({}))
        self.assertFalse(r["success"])
        self.assertNotIn("boom", json.dumps(r))

    def test_bad_before_id_returns_error(self):
        conn = make_db()
        with self._env(GROUP_A, "group"), mock.patch.object(gh, "_open_readonly", return_value=conn):
            r = json.loads(gh._handler({"before_id": "abc"}))
        self.assertFalse(r["success"])

    def test_readonly_connection_rejects_writes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.db"
            c = sqlite3.connect(p)
            c.execute("CREATE TABLE t (x)")
            c.commit()
            c.close()
            ro = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            ro.execute("PRAGMA query_only = ON")
            with self.assertRaises(sqlite3.OperationalError):
                ro.execute("INSERT INTO t VALUES (1)")
            ro.close()


class RegisterTests(unittest.TestCase):
    def test_registers_single_tool_without_chat_id_param(self):
        ctx = mock.Mock()
        gh.register(ctx)
        ctx.register_tool.assert_called_once()
        kw = ctx.register_tool.call_args.kwargs
        self.assertEqual(kw["name"], "group_history")
        self.assertEqual(kw["toolset"], "group_history")
        props = kw["schema"]["parameters"]["properties"]
        self.assertEqual(set(props), {"limit", "keyword", "sender", "before_id"})


if __name__ == "__main__":
    unittest.main()
