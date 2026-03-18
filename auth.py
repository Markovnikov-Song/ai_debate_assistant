"""
轻量用户认证模块
- 用户数据存储在 users.json
- 密码使用 bcrypt 加密
- 支持注册、登录、登出、管理员面板
- 使用 cookie 持久化登录状态，刷新不退出
"""

import json
import os
import bcrypt
import streamlit as st
from streamlit_cookies_controller import CookieController

USERS_FILE = "users.json"
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
COOKIE_KEY = "debate_user"

# 全局 cookie 控制器（每次页面加载只初始化一次）
_cookie = CookieController()


def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: dict):
    tmp = USERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    os.replace(tmp, USERS_FILE)


def register(username: str, password: str) -> tuple[bool, str]:
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
    username = username.strip()
    users    = _load_users()
    if username not in users:
        return False, "用户名不存在"
    if bcrypt.checkpw(password.encode(), users[username]["password"].encode()):
        return True, "登录成功"
    return False, "密码错误"


def is_admin() -> bool:
    return st.session_state.get("current_user") == ADMIN_USER


def _restore_from_cookie():
    """页面加载时尝试从 cookie 恢复登录状态"""
    if st.session_state.get("logged_in"):
        return
    try:
        username = _cookie.get(COOKIE_KEY)
        if username and username in _load_users():
            st.session_state.logged_in    = True
            st.session_state.current_user = username
    except Exception:
        pass


def render_admin_panel():
    if not is_admin():
        return
    with st.expander("🛡️ 管理员面板", expanded=False):
        users = _load_users()
        st.caption(f"当前注册用户数：{len(users)}")
        for uname in list(users.keys()):
            c1, c2, c3 = st.columns([4, 3, 3])
            with c1:
                st.text(uname)
            with c2:
                new_pw = st.text_input("新密码", key=f"reset_{uname}", placeholder="留空不改")
                if st.button("重置", key=f"do_reset_{uname}"):
                    if new_pw and len(new_pw) >= 6:
                        users[uname]["password"] = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
                        _save_users(users)
                        st.success(f"{uname} 密码已重置")
                    else:
                        st.warning("密码至少 6 位")
            with c3:
                if uname != ADMIN_USER:
                    if st.button("删除", key=f"del_user_{uname}"):
                        del users[uname]
                        _save_users(users)
                        st.rerun()


def logout():
    """登出：清除 session 和 cookie"""
    st.session_state.logged_in    = False
    st.session_state.current_user = ""
    try:
        _cookie.remove(COOKIE_KEY)
    except Exception:
        pass
    st.rerun()


def render_auth_page() -> bool:
    """已登录返回 True，未登录渲染登录页并返回 False"""
    _restore_from_cookie()

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
                st.session_state.logged_in    = True
                st.session_state.current_user = u.strip()
                # 写入 cookie，有效期 7 天
                _cookie.set(COOKIE_KEY, u.strip(), max_age=7 * 24 * 3600)
                st.rerun()
            else:
                st.error(msg)

    with tab_register:
        u2 = st.text_input("用户名", key="reg_u")
        p2 = st.text_input("密码（至少6位）", type="password", key="reg_p")
        p3 = st.text_input("确认密码",        type="password", key="reg_p2")
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
