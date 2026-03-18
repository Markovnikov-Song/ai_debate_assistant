"""
轻量用户认证模块
- 用户数据存储在 users.json
- 密码使用 bcrypt 加密
- 支持注册、登录、登出
"""

import json
import os
import bcrypt
import streamlit as st

USERS_FILE = "users.json"


def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def register(username: str, password: str) -> tuple[bool, str]:
    """注册新用户，返回 (成功, 消息)"""
    username = username.strip()
    if not username or not password:
        return False, "用户名和密码不能为空"
    if len(username) < 2:
        return False, "用户名至少 2 个字符"
    if len(password) < 6:
        return False, "密码至少 6 位"
    users = _load_users()
    if username in users:
        return False, "用户名已存在"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[username] = {"password": hashed}
    _save_users(users)
    return True, "注册成功"


def login(username: str, password: str) -> tuple[bool, str]:
    """验证登录，返回 (成功, 消息)"""
    username = username.strip()
    users = _load_users()
    if username not in users:
        return False, "用户名不存在"
    hashed = users[username]["password"].encode()
    if bcrypt.checkpw(password.encode(), hashed):
        return True, "登录成功"
    return False, "密码错误"


def render_auth_page():
    """
    渲染登录/注册页面。
    已登录则直接返回 True，未登录返回 False。
    """
    # 已登录
    if st.session_state.get("logged_in"):
        return True

    st.title("🔐 多 AI 辩论决策助手")
    st.caption("请登录或注册后使用")
    st.divider()

    tab_login, tab_register = st.tabs(["登录", "注册"])

    with tab_login:
        u = st.text_input("用户名", key="login_u")
        p = st.text_input("密码", type="password", key="login_p")
        if st.button("登录", use_container_width=True, type="primary"):
            ok, msg = login(u, p)
            if ok:
                st.session_state.logged_in = True
                st.session_state.current_user = u
                st.rerun()
            else:
                st.error(msg)

    with tab_register:
        u2 = st.text_input("用户名", key="reg_u")
        p2 = st.text_input("密码（至少6位）", type="password", key="reg_p")
        p3 = st.text_input("确认密码", type="password", key="reg_p2")
        if st.button("注册", use_container_width=True):
            if p2 != p3:
                st.error("两次密码不一致")
            else:
                ok, msg = register(u2, p2)
                if ok:
                    st.success(msg + "，请切换到登录标签")
                else:
                    st.error(msg)

    return False
