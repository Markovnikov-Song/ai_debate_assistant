"""
GitHub 持久化存储模块
- 所有数据存储在指定 GitHub 私有仓库
- 通过 GitHub Contents API 读写 JSON 文件
- 需要在 Streamlit Secrets 中配置：
    GITHUB_TOKEN = "ghp_xxx"
    GITHUB_REPO  = "username/repo-name"   # 存储数据的仓库
"""

import json
import base64
import os
import streamlit as st
import requests

# ── 从 Streamlit Secrets 或环境变量读取配置 ──────────────────────────
def _cfg(key: str) -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, "")

def _headers() -> dict:
    token = _cfg("GITHUB_TOKEN")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

def _api(path: str) -> str:
    repo = _cfg("GITHUB_REPO")
    return f"https://api.github.com/repos/{repo}/contents/{path}"


# ── 底层读写 ─────────────────────────────────────────────────────────
def gh_read(path: str):
    """读取文件，返回 (内容dict/list, sha)，文件不存在返回 (None, None)"""
    r = requests.get(_api(path), headers=_headers(), timeout=10)
    if r.status_code == 404:
        return None, None
    r.raise_for_status()
    data = r.json()
    content = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    return content, data["sha"]


def gh_write(path: str, content, message: str = "update", sha: str = None):
    """写入文件（新建或更新）"""
    encoded = base64.b64encode(
        json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")
    payload = {"message": message, "content": encoded}
    if sha:
        payload["sha"] = sha
    r = requests.put(_api(path), headers=_headers(), json=payload, timeout=10)
    if not r.ok:
        raise Exception(f"GitHub API error {r.status_code}: {r.text}")
    r.raise_for_status()


def gh_delete(path: str, message: str = "delete"):
    """删除文件"""
    _, sha = gh_read(path)
    if sha is None:
        return
    payload = {"message": message, "sha": sha}
    r = requests.delete(_api(path), headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()


def gh_list(prefix: str) -> list[str]:
    """列出目录下所有文件名（不含路径前缀）"""
    r = requests.get(_api(prefix), headers=_headers(), timeout=10)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return [item["name"] for item in r.json() if item["type"] == "file"]


# ── 业务封装 ─────────────────────────────────────────────────────────
USERS_PATH    = "data/users.json"
FEEDBACK_PATH = "data/feedback.json"


def load_users() -> dict:
    data, _ = gh_read(USERS_PATH)
    return data or {}


def save_users(users: dict):
    _, sha = gh_read(USERS_PATH)
    gh_write(USERS_PATH, users, message="update users", sha=sha)


def load_feedback() -> list:
    data, _ = gh_read(FEEDBACK_PATH)
    return data or []


def save_feedback(feedbacks: list):
    _, sha = gh_read(FEEDBACK_PATH)
    gh_write(FEEDBACK_PATH, feedbacks, message="update feedback", sha=sha)


def load_agent_config(username: str):
    path = f"data/agent_config_{username}.json"
    data, _ = gh_read(path)
    return data


def save_agent_config(username: str, agents: list):
    path = f"data/agent_config_{username}.json"
    _, sha = gh_read(path)
    gh_write(path, agents, message=f"update agent config for {username}", sha=sha)


def load_debate(username: str, filename: str):
    path = f"data/debate_history/{username}/{filename}"
    data, _ = gh_read(path)
    return data


def save_debate(username: str, filename: str, data: dict):
    path = f"data/debate_history/{username}/{filename}"
    _, sha = gh_read(path)
    gh_write(path, data, message=f"save debate {filename}", sha=sha)


def delete_debate(username: str, filename: str):
    path = f"data/debate_history/{username}/{filename}"
    gh_delete(path, message=f"delete debate {filename}")


def list_debates(username: str) -> list[str]:
    return gh_list(f"data/debate_history/{username}")
